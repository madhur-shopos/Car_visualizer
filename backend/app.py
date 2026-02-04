"""
FastAPI Backend for Car Video Generation
Wraps the existing gg.py pipeline with REST API endpoints
"""

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Request
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
from datetime import datetime

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

# Rate limiting: Track generations per IP per day
# Format: { "ip_address": { "date": "YYYY-MM-DD", "count": N } }
rate_limit_store = {}

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

# Rate limiting configuration
MAX_GENERATIONS_PER_DAY = 15

def check_rate_limit(ip_address: str) -> tuple[bool, int]:
    """
    Check if IP address has exceeded daily rate limit.
    Returns (is_allowed, remaining_count)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    if ip_address not in rate_limit_store:
        rate_limit_store[ip_address] = {"date": today, "count": 0}
    
    user_data = rate_limit_store[ip_address]
    
    # Reset count if it's a new day
    if user_data["date"] != today:
        rate_limit_store[ip_address] = {"date": today, "count": 0}
        user_data = rate_limit_store[ip_address]
    
    remaining = MAX_GENERATIONS_PER_DAY - user_data["count"]
    is_allowed = user_data["count"] < MAX_GENERATIONS_PER_DAY
    
    return is_allowed, max(0, remaining)

def increment_rate_limit(ip_address: str):
    """Increment the generation count for an IP address."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    if ip_address not in rate_limit_store:
        rate_limit_store[ip_address] = {"date": today, "count": 0}
    
    rate_limit_store[ip_address]["count"] += 1

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Car Video Generator API"}

@app.get("/api/rate-limit")
async def get_rate_limit(request: Request):
    """Get remaining generations for the current user"""
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, remaining = check_rate_limit(client_ip)
    
    today = datetime.now().strftime("%Y-%m-%d")
    used = rate_limit_store.get(client_ip, {}).get("count", 0) if client_ip in rate_limit_store else 0
    
    return {
        "max_per_day": MAX_GENERATIONS_PER_DAY,
        "used_today": used,
        "remaining_today": remaining,
        "date": today,
        "is_allowed": is_allowed
    }

@app.post("/api/upload", response_model=JobResponse)
async def upload_images(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """
    Upload car images and start video generation
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    # Get client IP address
    client_ip = request.client.host if request.client else "unknown"
    
    # Check rate limit
    is_allowed, remaining = check_rate_limit(client_ip)
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Daily generation limit reached. You have used all {MAX_GENERATIONS_PER_DAY} generations today. Please try again tomorrow."
        )
    
    logger.info(f"Rate limit check for {client_ip}: {remaining} generations remaining")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Create job directory
    job_input_dir = UPLOAD_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id
    job_input_dir.mkdir(parents=True, exist_ok=True)
    job_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded files
    try:
        logger.info(f"Received {len(files)} file(s) for upload")
        saved_files = []
        for idx, file in enumerate(files, 1):
            # Preserve original filename or add index if duplicate
            file_path = job_input_dir / file.filename
            if file_path.exists():
                # Handle duplicate filenames
                stem = file_path.stem
                suffix = file_path.suffix
                file_path = job_input_dir / f"{stem}_{idx}{suffix}"
                logger.warning(f"Duplicate filename detected, saving as: {file_path.name}")
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(str(file_path))
            logger.info(f"Saved file {idx}/{len(files)}: {file_path.name}")
        
        logger.info(f"Successfully saved {len(saved_files)} file(s) to {job_input_dir}")
        
        # Initialize job status
        job_status[job_id] = {
            "status": "queued",
            "progress": "Starting video generation...",
            "input_files": saved_files,
        }
        
        # Increment rate limit counter
        increment_rate_limit(client_ip)
        
        # Start background task
        background_tasks.add_task(
            process_video_generation,
            job_id,
            str(job_input_dir),
            str(job_output_dir)
        )
        
        # Get remaining generations
        _, remaining = check_rate_limit(client_ip)
        
        return JobResponse(
            job_id=job_id,
            status="queued",
            message=f"Processing {len(files)} images. {remaining} generations remaining today. Check status at /api/status/{job_id}"
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
        
        # Check if job was cancelled before starting
        if job_status[job_id].get("status") == "cancelled":
            logger.info(f"Job {job_id} was cancelled before processing started")
            return
        
        job_status[job_id]["status"] = "processing"
        job_status[job_id]["progress"] = "Generating contact sheet..."
        
        # Run the pipeline
        result = await process_car_images(
            input_folder=input_dir,
            output_dir=output_dir
        )
        
        # Check if cancelled during processing
        if job_status[job_id].get("status") == "cancelled":
            logger.info(f"Job {job_id} was cancelled during processing")
            return
        
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
        # Don't mark as failed if it was cancelled
        if job_status[job_id].get("status") != "cancelled":
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

@app.post("/api/cancel/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a running or queued job
    """
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_status[job_id]
    
    # Only allow cancellation of queued or processing jobs
    if job["status"] not in ["queued", "processing"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel job with status: {job['status']}"
        )
    
    # Mark as cancelled
    job_status[job_id]["status"] = "cancelled"
    job_status[job_id]["progress"] = "Job cancelled by user"
    logger.info(f"Job {job_id} cancelled by user")
    
    return {"message": "Job cancelled successfully", "job_id": job_id}

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
