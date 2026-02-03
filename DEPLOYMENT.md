# Deployment Guide

## Quick Start

### 1. Deploy Backend to Render

#### Step 1: Prepare Repository
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

#### Step 2: Create Render Account
- Go to https://dashboard.render.com/
- Sign up with GitHub

#### Step 3: Create Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `car-video-generator-api`
   - **Environment**: `Docker`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Dockerfile Path**: `./backend/Dockerfile`
   - **Docker Context**: `.` (project root)

#### Step 4: Add Environment Variables
In Render dashboard, add these environment variables:

```
GOOGLE_API_KEY=your_actual_key_here
HIGGSFIELD_API_KEY=your_actual_key_here
HIGGSFIELD_API_SECRET=your_actual_secret_here
IMGBB_API_KEY=your_actual_key_here
PORT=8000
```

Optional (for secondary account):
```
HIGGSFIELD_API_KEY2=your_secondary_key
HIGGSFIELD_API_SECRET2=your_secondary_secret
```

#### Step 5: Deploy
- Click **"Create Web Service"**
- Wait 5-10 minutes for deployment
- Your API will be available at: `https://your-app-name.onrender.com`

#### Step 6: Test Backend
```bash
curl https://your-app-name.onrender.com/
```

Should return: `{"status":"ok","message":"Car Video Generator API"}`

---

### 2. Deploy Frontend to Vercel

#### Step 1: Create Vercel Account
- Go to https://vercel.com/
- Sign up with GitHub

#### Step 2: Import Project
1. Click **"Add New"** → **"Project"**
2. Import your GitHub repository
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `.next` (auto-detected)
   - **Install Command**: `npm install` (auto-detected)

#### Step 3: Add Environment Variable
Add this environment variable in Vercel:

```
NEXT_PUBLIC_API_URL=https://your-render-app-name.onrender.com
```

⚠️ **Important**: Replace `your-render-app-name` with your actual Render service name

#### Step 4: Deploy
- Click **"Deploy"**
- Wait 2-3 minutes
- Your app will be available at: `https://your-app-name.vercel.app`

---

## Update CORS Settings

After deployment, update CORS in `backend/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app-name.vercel.app",
        "http://localhost:3000"  # Keep for local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then push the changes:
```bash
git add backend/app.py
git commit -m "Update CORS for production"
git push
```

Render will automatically redeploy.

---

## Monitoring & Logs

### Render (Backend)
- Go to your service dashboard
- Click **"Logs"** tab
- Monitor real-time logs
- Check for errors

### Vercel (Frontend)
- Go to your project dashboard
- Click on a deployment
- View **"Functions"** and **"Build Logs"**

---

## Troubleshooting

### Backend Issues

**Problem**: "Application failed to start"
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure Docker builds successfully locally

**Problem**: "API not responding"
- Check if service is running in Render dashboard
- Verify health check endpoint: `curl https://your-api.onrender.com/`
- Check if disk space is sufficient

**Problem**: "ImportError: No module named 'gg'"
- Verify `gg.py` is in the project root
- Check Dockerfile copies `gg.py` correctly

### Frontend Issues

**Problem**: "API calls failing with CORS error"
- Update CORS settings in `backend/app.py`
- Add your Vercel domain to `allow_origins`
- Redeploy backend

**Problem**: "Module not found" errors
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again
- Commit and push

**Problem**: "Environment variable not working"
- Ensure it starts with `NEXT_PUBLIC_`
- Redeploy after adding environment variable
- Check spelling exactly matches code

### General Issues

**Problem**: "Slow video generation"
- This is normal! Videos take 1-5 minutes each
- Kling API is processing in the cloud
- Consider implementing webhooks for better UX

**Problem**: "Running out of disk space"
- Implement cleanup job to delete old uploads/outputs
- Use cloud storage (AWS S3) instead of local storage
- Add file size limits

---

## Production Optimizations

### Backend
1. **Add Redis** for job queue (instead of in-memory dict)
2. **Add database** to persist job history
3. **Add S3/Cloudinary** for file storage
4. **Add rate limiting** to prevent abuse
5. **Add authentication** for secure access

### Frontend
1. **Add error boundaries** for better error handling
2. **Add loading skeletons** for better UX
3. **Add image preview** before upload
4. **Add progress bar** with percentage
5. **Add WebSocket** for real-time updates

---

## Cost Estimates

### Render (Backend)
- **Free Tier**: $0/month (spins down after inactivity)
- **Starter**: $7/month (always on, 512MB RAM)
- **Standard**: $25/month (2GB RAM, recommended)

### Vercel (Frontend)
- **Hobby**: $0/month (100GB bandwidth)
- **Pro**: $20/month (1TB bandwidth)

### API Costs
- **Google Gemini**: Pay per use
- **Kling AI**: Pay per video generation
- **ImgBB**: Free (with limits)

---

## Scaling Considerations

When you get more traffic:

1. **Use worker services** for video processing
2. **Add queue system** (BullMQ, Celery)
3. **Use CDN** for static files
4. **Add caching** for repeated requests
5. **Consider serverless** for backend endpoints

---

## Support

Need help? Check:
- Render docs: https://render.com/docs
- Vercel docs: https://vercel.com/docs
- Next.js docs: https://nextjs.org/docs
- FastAPI docs: https://fastapi.tiangolo.com/
