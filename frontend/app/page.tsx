"use client";

import { useState, useCallback } from "react";
import { Upload, Video, Loader2, Download, Image as ImageIcon, CheckCircle2, AlertCircle } from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface JobStatus {
  job_id: string;
  status: string;
  progress?: string;
  result?: {
    contact_sheet: string;
    final_video: string;
    summary: {
      total_frames: number;
      total_videos: number;
      successful_videos: number;
      failed_videos: number;
    };
  };
  error?: string;
}

export default function Home() {
  const [files, setFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files).filter(file =>
      file.type.startsWith('image/')
    );
    setFiles(droppedFiles);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const uploadImages = async () => {
    if (files.length === 0) return;

    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    try {
      const response = await axios.post(`${API_URL}/api/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      const { job_id } = response.data;
      setJobId(job_id);
      pollJobStatus(job_id);
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  const pollJobStatus = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/api/status/${id}`);
        setJobStatus(response.data);

        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Status check failed:', error);
        clearInterval(interval);
      }
    }, 3000);
  };

  const downloadVideo = () => {
    if (jobId) {
      window.open(`${API_URL}/api/download/${jobId}/video`, '_blank');
    }
  };

  const downloadContactSheet = () => {
    if (jobId) {
      window.open(`${API_URL}/api/download/${jobId}/contact-sheet`, '_blank');
    }
  };

  const reset = () => {
    setFiles([]);
    setJobId(null);
    setJobStatus(null);
  };

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-6xl mx-auto px-4 py-12">
        {/* Header */}
        <header className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-4 tracking-tight">
            Car Video Generator
          </h1>
          <p className="text-gray-400 text-lg">
            Transform your car photos into professional showcase videos
          </p>
        </header>

        {/* Upload Section */}
        {!jobId && (
          <div className="space-y-8">
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              className={`
                border-2 border-dashed rounded-lg p-12 text-center transition-all
                ${isDragging ? 'border-white bg-white/5' : 'border-gray-700 hover:border-gray-600'}
              `}
            >
              <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-xl font-semibold mb-2">
                Drop your car images here
              </h3>
              <p className="text-gray-400 mb-6">
                or click to browse files
              </p>
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleFileInput}
                className="hidden"
                id="file-input"
              />
              <label
                htmlFor="file-input"
                className="inline-block px-6 py-3 bg-white text-black font-semibold rounded-lg cursor-pointer hover:bg-gray-200 transition-colors"
              >
                Select Images
              </label>
            </div>

            {/* Selected Files */}
            {files.length > 0 && (
              <div className="border border-gray-800 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">
                  Selected Files ({files.length})
                </h3>
                <div className="space-y-2 mb-6">
                  {files.map((file, idx) => (
                    <div key={idx} className="flex items-center gap-3 text-sm text-gray-400">
                      <ImageIcon className="w-4 h-4" />
                      <span>{file.name}</span>
                      <span className="text-gray-600">
                        ({(file.size / 1024 / 1024).toFixed(2)} MB)
                      </span>
                    </div>
                  ))}
                </div>
                <button
                  onClick={uploadImages}
                  className="w-full py-3 bg-white text-black font-semibold rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center gap-2"
                >
                  <Video className="w-5 h-5" />
                  Generate Video
                </button>
              </div>
            )}
          </div>
        )}

        {/* Progress Section */}
        {jobId && jobStatus && (
          <div className="border border-gray-800 rounded-lg p-8">
            <div className="text-center mb-8">
              {jobStatus.status === 'processing' || jobStatus.status === 'queued' ? (
                <>
                  <Loader2 className="w-16 h-16 mx-auto mb-4 animate-spin text-white" />
                  <h3 className="text-2xl font-semibold mb-2">
                    Processing Your Video
                  </h3>
                  <p className="text-gray-400">{jobStatus.progress}</p>
                </>
              ) : jobStatus.status === 'completed' ? (
                <>
                  <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-white" />
                  <h3 className="text-2xl font-semibold mb-2">
                    Video Ready!
                  </h3>
                  <p className="text-gray-400">
                    Your showcase video has been generated successfully
                  </p>
                </>
              ) : (
                <>
                  <AlertCircle className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-2xl font-semibold mb-2">
                    Generation Failed
                  </h3>
                  <p className="text-gray-400">{jobStatus.error}</p>
                </>
              )}
            </div>

            {/* Results */}
            {jobStatus.status === 'completed' && jobStatus.result && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 text-center">
                  <div className="bg-gray-900 p-4 rounded-lg">
                    <div className="text-3xl font-bold mb-1">
                      {jobStatus.result.summary.total_frames}
                    </div>
                    <div className="text-sm text-gray-400">Frames Generated</div>
                  </div>
                  <div className="bg-gray-900 p-4 rounded-lg">
                    <div className="text-3xl font-bold mb-1">
                      {jobStatus.result.summary.total_videos}
                    </div>
                    <div className="text-sm text-gray-400">Video Segments</div>
                  </div>
                  <div className="bg-gray-900 p-4 rounded-lg">
                    <div className="text-3xl font-bold mb-1">
                      {jobStatus.result.summary.successful_videos}
                    </div>
                    <div className="text-sm text-gray-400">Successful</div>
                  </div>
                </div>

                <div className="flex gap-4">
                  <button
                    onClick={downloadVideo}
                    className="flex-1 py-3 bg-white text-black font-semibold rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Download Video
                  </button>
                  <button
                    onClick={downloadContactSheet}
                    className="flex-1 py-3 bg-gray-900 text-white font-semibold rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2 border border-gray-800"
                  >
                    <ImageIcon className="w-5 h-5" />
                    Download Contact Sheet
                  </button>
                </div>

                <button
                  onClick={reset}
                  className="w-full py-3 text-gray-400 hover:text-white transition-colors"
                >
                  Generate Another Video
                </button>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <footer className="mt-16 text-center text-gray-600 text-sm">
          <p>Powered by Google Gemini & Kling AI</p>
        </footer>
      </div>
    </div>
  );
}
