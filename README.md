# Car Video Generator

Generate professional automotive showcase videos from car images using AI.

## Features

- 🎨 **Contact Sheet Generation**: Creates 9 professional angles using Google Gemini
- 🎬 **Video Generation**: Smooth camera movements using Kling AI
- 📸 **Image Upscaling**: 2K resolution upscaling for crisp details
- 🎯 **Professional Output**: Cinema-quality automotive photography

## Architecture

- **Frontend**: Next.js 15 + Tailwind CSS (Black & White theme)
- **Backend**: FastAPI + Python
- **AI Models**: Google Gemini 3 Pro + Kling 2.6 Pro

## Local Development

### Backend Setup

1. Navigate to the project root:
```bash
cd "D:\New folder (16)\New folder"
```

2. Install Python dependencies:
```bash
pip install -r backend/requirements.txt
```

3. Create `.env` file with your API keys:
```bash
GOOGLE_API_KEY=your_google_api_key
HIGGSFIELD_API_KEY=your_higgsfield_api_key
HIGGSFIELD_API_SECRET=your_higgsfield_api_secret
IMGBB_API_KEY=your_imgbb_api_key
```

4. Run the backend:
```bash
cd backend
python app.py
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local` file:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Run the development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:3000`

## Deployment

### Deploy Backend to Render

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Use these settings:
   - **Build Command**: Leave empty (Docker will handle it)
   - **Start Command**: Leave empty (Docker will handle it)
6. Add environment variables:
   - `GOOGLE_API_KEY`
   - `HIGGSFIELD_API_KEY`
   - `HIGGSFIELD_API_SECRET`
   - `IMGBB_API_KEY`
   - `HIGGSFIELD_API_KEY2` (optional)
   - `HIGGSFIELD_API_SECRET2` (optional)
7. Deploy!

Your backend URL will be: `https://your-app-name.onrender.com`

### Deploy Frontend to Vercel

1. Push your code to GitHub
2. Go to [Vercel Dashboard](https://vercel.com/dashboard)
3. Click "Add New" → "Project"
4. Import your GitHub repository
5. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
6. Add environment variable:
   - `NEXT_PUBLIC_API_URL`: Your Render backend URL
7. Deploy!

Your frontend URL will be: `https://your-app-name.vercel.app`

## API Endpoints

### POST `/api/upload`
Upload car images and start video generation
- **Body**: multipart/form-data with image files
- **Response**: `{ job_id, status, message }`

### GET `/api/status/{job_id}`
Check job status
- **Response**: `{ job_id, status, progress, result, error }`

### GET `/api/download/{job_id}/video`
Download final video
- **Response**: MP4 file

### GET `/api/download/{job_id}/contact-sheet`
Download contact sheet image
- **Response**: PNG file

### DELETE `/api/jobs/{job_id}`
Delete job and associated files
- **Response**: `{ message }`

## Environment Variables

### Backend (.env)
```env
GOOGLE_API_KEY=your_google_api_key
HIGGSFIELD_API_KEY=your_higgsfield_key
HIGGSFIELD_API_SECRET=your_higgsfield_secret
IMGBB_API_KEY=your_imgbb_key
HIGGSFIELD_API_KEY2=your_secondary_key (optional)
HIGGSFIELD_API_SECRET2=your_secondary_secret (optional)
PORT=8000
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
.
├── backend/
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Docker configuration
│   └── render.yaml         # Render deployment config
├── frontend/
│   ├── app/
│   │   ├── layout.tsx      # Root layout
│   │   ├── page.tsx        # Home page
│   │   └── globals.css     # Global styles
│   ├── package.json        # Node dependencies
│   ├── tailwind.config.ts  # Tailwind configuration
│   └── next.config.ts      # Next.js configuration
├── gg.py                   # Core pipeline script
├── env.example             # Example environment file
└── README.md               # This file
```

## How It Works

1. **Upload**: User uploads 2-3 car images
2. **Analysis**: Gemini Flash analyzes images and populates prompt template
3. **Contact Sheet**: Gemini Pro generates 9 professional angles (3×3 grid)
4. **Split**: Contact sheet is split into 9 individual frames
5. **Upscale**: Each frame is upscaled to 2K resolution (3:2 aspect ratio)
6. **Videos**: Kling generates 8 video segments with smooth camera movements
7. **Stitch**: Videos are combined into final showcase video
8. **Download**: User downloads final video and contact sheet

## Credits

- **UI Design**: Minimal black & white theme with Tailwind CSS
- **AI Models**: Google Gemini 3 Pro, Kling 2.6 Pro
- **Image Hosting**: ImgBB
- **Video Processing**: FFmpeg

## License

MIT License - Feel free to use this project!
