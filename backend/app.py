"""
FastAPI Backend for Car Video Generation
Wraps the existing gg.py pipeline with REST API endpoints
"""

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import uuid
import shutil
from pathlib import Path
import asyncio
import logging

# Add parent directory to path to import gg.py
sys.path.append(str(Path(__file__).parent.parent))
from gg import process_car_images

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Car Video Generator API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
UPLOAD_DIR = Path("./uploads")
OUTPUT_DIR = Path("./outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Store job status in memory (use Redis in production)
job_status = {}

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Car Video Generator API"}

@app.post("/api/upload", response_model=JobResponse)
async def upload_images(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """
    Upload car images and start video generation
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Create job directory
    job_input_dir = UPLOAD_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id
    job_input_dir.mkdir(parents=True, exist_ok=True)
    job_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded files
    try:
        saved_files = []
        for file in files:
            file_path = job_input_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(str(file_path))
            logger.info(f"Saved file: {file.filename}")
        
        # Initialize job status
        job_status[job_id] = {
            "status": "queued",
            "progress": "Starting video generation...",
            "input_files": saved_files,
        }
        
        # Start background task
        background_tasks.add_task(
            process_video_generation,
            job_id,
            str(job_input_dir),
            str(job_output_dir)
        )
        
        return JobResponse(
            job_id=job_id,
            status="queued",
            message=f"Processing {len(files)} images. Check status at /api/status/{job_id}"
        )
        
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_video_generation(job_id: str, input_dir: str, output_dir: str):
    """
    Background task to process video generation
    """
    try:
        logger.info(f"Starting job {job_id}")
        job_status[job_id]["status"] = "processing"
        job_status[job_id]["progress"] = "Generating contact sheet..."
        
        # Run the pipeline
        result = await process_car_images(
            input_folder=input_dir,
            output_dir=output_dir
        )
        
        if "error" in result:
            job_status[job_id]["status"] = "failed"
            job_status[job_id]["error"] = result["error"]
            logger.error(f"Job {job_id} failed: {result['error']}")
        else:
            job_status[job_id]["status"] = "completed"
            job_status[job_id]["result"] = {
                "contact_sheet": result.get("contact_sheet_path"),
                "final_video": result.get("final_video_path"),
                "summary": result.get("summary"),
            }
            job_status[job_id]["progress"] = "Video generation complete!"
            logger.info(f"Job {job_id} completed successfully")
            
    except Exception as e:
        logger.exception(f"Error processing job {job_id}")
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["error"] = str(e)

@app.get("/api/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a video generation job
    """
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_status[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress"),
        result=job.get("result"),
        error=job.get("error"),
    )

@app.get("/api/download/{job_id}/video")
async def download_video(job_id: str):
    """
    Download the final generated video
    """
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_status[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready yet")
    
    video_path = job["result"]["final_video"]
    if not video_path or not Path(video_path).exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"car_showcase_{job_id}.mp4"
    )

@app.get("/api/download/{job_id}/contact-sheet")
async def download_contact_sheet(job_id: str):
    """
    Download the contact sheet image
    """
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_status[job_id]
    if job["status"] not in ["processing", "completed"]:
        raise HTTPException(status_code=400, detail="Contact sheet not ready yet")
    
    contact_sheet_path = job["result"]["contact_sheet"]
    if not contact_sheet_path or not Path(contact_sheet_path).exists():
        raise HTTPException(status_code=404, detail="Contact sheet not found")
    
    return FileResponse(
        contact_sheet_path,
        media_type="image/png",
        filename=f"contact_sheet_{job_id}.png"
    )

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job and its associated files
    """
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete files
    job_input_dir = UPLOAD_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id
    
    if job_input_dir.exists():
        shutil.rmtree(job_input_dir)
    if job_output_dir.exists():
        shutil.rmtree(job_output_dir)
    
    # Remove from status
    del job_status[job_id]
    
    return {"message": "Job deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
