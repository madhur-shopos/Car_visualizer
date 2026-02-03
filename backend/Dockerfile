FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gg.py .
COPY backend/app.py .

# Create directories
RUN mkdir -p uploads outputs

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "app.py"]
