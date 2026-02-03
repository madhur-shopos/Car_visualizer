"use client";

import { useState, useCallback, useRef } from "react";
import { Upload, Video, Loader2, Download, Image as ImageIcon, CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import axios from "axios";

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
  const [isCancelling, setIsCancelling] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

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
      const response = await axios.post('/api/upload', formData, {
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
    // Clear any existing interval
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/status/${id}`);
        setJobStatus(response.data);

        if (response.data.status === 'completed' || response.data.status === 'failed' || response.data.status === 'cancelled') {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
        }
      } catch (error) {
        console.error('Status check failed:', error);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      }
    }, 3000);

    pollingIntervalRef.current = interval;
  };

  const cancelJob = async () => {
    if (!jobId) return;

    setIsCancelling(true);
    try {
      await axios.post(`/api/cancel/${jobId}`);
      
      // Stop polling
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }

      // Update status immediately
      setJobStatus(prev => prev ? {
        ...prev,
        status: 'cancelled',
        progress: 'Job cancelled by user'
      } : null);
    } catch (error) {
      console.error('Cancel failed:', error);
      alert('Failed to cancel job. Please try again.');
    } finally {
      setIsCancelling(false);
    }
  };

  const downloadVideo = () => {
    if (jobId) {
      window.open(`/api/download/${jobId}/video`, '_blank');
    }
  };

  const downloadContactSheet = () => {
    if (jobId) {
      window.open(`/api/download/${jobId}/contact-sheet`, '_blank');
    }
  };

  const reset = () => {
    // Clear polling interval if running
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    
    setFiles([]);
    setJobId(null);
    setJobStatus(null);
    setIsCancelling(false);
  };

  return (
    <div className="min-h-screen bg-white text-black">
      <div className="max-w-6xl mx-auto px-4 py-12">
        {/* Header */}
        <header className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-4 tracking-tight">
            Car Visualizer
          </h1>
          <p className="text-gray-600 text-lg">
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
                ${isDragging ? 'border-black bg-gray-50' : 'border-gray-300 hover:border-gray-400'}
              `}
            >
              <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-xl font-semibold mb-2 text-black">
                Drop your car images here
              </h3>
              <p className="text-gray-500 mb-6">
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
                className="inline-block px-6 py-3 bg-black text-white font-semibold rounded-lg cursor-pointer hover:bg-gray-800 transition-colors"
              >
                Select Images
              </label>
            </div>

            {/* Selected Files */}
            {files.length > 0 && (
              <div className="border border-gray-200 rounded-lg p-6 bg-gray-50">
                <h3 className="text-lg font-semibold mb-4 text-black">
                  Selected Files ({files.length})
                </h3>
                <div className="space-y-2 mb-6">
                  {files.map((file, idx) => (
                    <div key={idx} className="flex items-center gap-3 text-sm text-gray-700">
                      <ImageIcon className="w-4 h-4" />
                      <span>{file.name}</span>
                      <span className="text-gray-500">
                        ({(file.size / 1024 / 1024).toFixed(2)} MB)
                      </span>
                    </div>
                  ))}
                </div>
                <button
                  onClick={uploadImages}
                  className="w-full py-3 bg-black text-white font-semibold rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
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
          <div className="border border-gray-200 rounded-lg p-8 bg-white shadow-sm">
            <div className="text-center mb-8">
              {jobStatus.status === 'processing' || jobStatus.status === 'queued' ? (
                <>
                  <Loader2 className="w-16 h-16 mx-auto mb-4 animate-spin text-black" />
                  <h3 className="text-2xl font-semibold mb-2 text-black">
                    Processing Your Video
                  </h3>
                  <p className="text-gray-600 mb-4">{jobStatus.progress}</p>
                  <button
                    onClick={cancelJob}
                    disabled={isCancelling}
                    className="inline-flex items-center gap-2 px-6 py-2 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isCancelling ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Cancelling...
                      </>
                    ) : (
                      <>
                        <XCircle className="w-4 h-4" />
                        Cancel Generation
                      </>
                    )}
                  </button>
                </>
              ) : jobStatus.status === 'cancelled' ? (
                <>
                  <XCircle className="w-16 h-16 mx-auto mb-4 text-orange-500" />
                  <h3 className="text-2xl font-semibold mb-2 text-black">
                    Generation Cancelled
                  </h3>
                  <p className="text-gray-600 mb-6">
                    The video generation was cancelled
                  </p>
                  <button
                    onClick={reset}
                    className="px-6 py-3 bg-black text-white font-semibold rounded-lg hover:bg-gray-800 transition-colors"
                  >
                    Start New Generation
                  </button>
                </>
              ) : jobStatus.status === 'completed' ? (
                <>
                  <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-green-600" />
                  <h3 className="text-2xl font-semibold mb-2 text-black">
                    Video Ready!
                  </h3>
                  <p className="text-gray-600">
                    Your showcase video has been generated successfully
                  </p>
                </>
              ) : (
                <>
                  <AlertCircle className="w-16 h-16 mx-auto mb-4 text-red-500" />
                  <h3 className="text-2xl font-semibold mb-2 text-black">
                    Generation Failed
                  </h3>
                  <p className="text-red-600">{jobStatus.error}</p>
                </>
              )}
            </div>

            {/* Results */}
            {jobStatus.status === 'completed' && jobStatus.result && (
              <div className="space-y-6">
                {/* Video Preview */}
                <div className="aspect-video bg-black rounded-lg overflow-hidden">
                  <video
                    controls
                    className="w-full h-full"
                    src={`/api/download/${jobId}/video`}
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
                  <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <div className="text-3xl font-bold mb-1 text-black">
                      {jobStatus.result.summary.total_frames}
                    </div>
                    <div className="text-sm text-gray-600">Frames Generated</div>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <div className="text-3xl font-bold mb-1 text-black">
                      {jobStatus.result.summary.total_videos}
                    </div>
                    <div className="text-sm text-gray-600">Video Segments</div>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <div className="text-3xl font-bold mb-1 text-black">
                      {jobStatus.result.summary.successful_videos}
                    </div>
                    <div className="text-sm text-gray-600">Successful</div>
                  </div>
                </div>

                {/* Download Buttons */}
                <div className="flex gap-4">
                  <button
                    onClick={downloadVideo}
                    className="flex-1 py-3 bg-black text-white font-semibold rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Download Video
                  </button>
                  <button
                    onClick={downloadContactSheet}
                    className="flex-1 py-3 bg-white text-black font-semibold rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-center gap-2 border border-gray-300"
                  >
                    <ImageIcon className="w-5 h-5" />
                    Download Contact Sheet
                  </button>
                </div>

                <button
                  onClick={reset}
                  className="w-full py-3 text-gray-600 hover:text-black transition-colors font-medium"
                >
                  Generate Another Video
                </button>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <footer className="mt-16 text-center text-gray-400 text-sm">
          <p>Powered by ShopOS</p>
        </footer>
      </div>
    </div>
  );
}
