# Quick Start Guide

Get your Car Video Generator running in 5 minutes!

## Prerequisites

- Python 3.11+
- Node.js 18+
- API Keys (see below)

## Get API Keys (Free)

### 1. Google Gemini API Key
1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key

### 2. Higgsfield/Kling API Key
1. Go to https://platform.higgsfield.ai/
2. Sign up and verify email
3. Go to API Keys section
4. Copy API Key and Secret

### 3. ImgBB API Key
1. Go to https://api.imgbb.com/
2. Sign up (free)
3. Copy API Key

---

## Local Setup (5 Minutes)

### Step 1: Clone & Setup Backend

```bash
# Navigate to project
cd "D:\New folder (16)\New folder"

# Install Python dependencies
pip install -r backend/requirements.txt

# Create .env file
# Copy env.example to .env and fill in your API keys
```

Create `.env` file:
```env
GOOGLE_API_KEY=your_google_key_here
HIGGSFIELD_API_KEY=your_higgsfield_key_here
HIGGSFIELD_API_SECRET=your_higgsfield_secret_here
IMGBB_API_KEY=your_imgbb_key_here
```

```bash
# Start backend
cd backend
python app.py
```

Backend running at: http://localhost:8000

### Step 2: Setup Frontend

Open a new terminal:

```bash
# Navigate to frontend
cd "D:\New folder (16)\New folder\frontend"

# Install dependencies
npm install

# Create .env.local
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local

# Start frontend
npm run dev
```

Frontend running at: http://localhost:3000

### Step 3: Test It Out!

1. Open http://localhost:3000
2. Upload 2-3 car images
3. Click "Generate Video"
4. Wait ~5-10 minutes
5. Download your video!

---

## Deploy to Production (10 Minutes)

### Option 1: One-Click Deploy

1. **Push to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO
git push -u origin main
```

2. **Deploy Backend to Render**
- Go to https://dashboard.render.com/
- New + → Web Service
- Connect GitHub repo
- Add environment variables
- Deploy!

3. **Deploy Frontend to Vercel**
- Go to https://vercel.com/new
- Import GitHub repo
- Set root directory: `frontend`
- Add `NEXT_PUBLIC_API_URL` env var
- Deploy!

### Option 2: Manual Deploy

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

---

## Folder Structure

```
.
├── backend/              # FastAPI backend
│   ├── app.py           # API endpoints
│   ├── requirements.txt # Dependencies
│   └── Dockerfile       # Docker config
│
├── frontend/            # Next.js frontend
│   ├── app/            # Pages
│   └── package.json    # Dependencies
│
├── gg.py               # Core pipeline (don't modify!)
└── README.md           # Documentation
```

---

## Common Issues

### "Module not found: gg"
- Make sure `gg.py` is in project root
- Check Python path in backend/app.py

### "CORS error" in browser
- Update CORS in backend/app.py
- Add your frontend URL

### "API key invalid"
- Check .env file has correct keys
- No quotes needed around values
- No spaces after `=`

### "Disk space full"
- Clean up `uploads/` and `outputs/` folders
- These folders store temporary files

---

## Next Steps

✅ Local setup working
✅ Deployed to production
🎯 Now what?

**Customize**:
- Change UI colors in `frontend/tailwind.config.ts`
- Modify prompts in `gg.py` (carefully!)
- Add authentication
- Add payment system

**Scale**:
- Add Redis for job queue
- Use S3 for file storage
- Add webhooks for notifications
- Implement batch processing

**Monitor**:
- Check Render logs for errors
- Monitor API usage and costs
- Track generation success rate

---

## Cost Breakdown

**Free Tier** (Testing):
- Render: Free (with spin-down)
- Vercel: Free
- APIs: Pay-per-use (~$1-5 per video)

**Production** (Always-on):
- Render: $7-25/month
- Vercel: Free-$20/month
- APIs: $1-5 per video × volume

**Estimate**: $50-100/month for 20-30 videos

---

## Support

Questions? Issues?

1. Check [README.md](./README.md)
2. Check [DEPLOYMENT.md](./DEPLOYMENT.md)
3. Review logs (Render/Vercel dashboards)
4. Open GitHub issue

Happy generating! 🎬
