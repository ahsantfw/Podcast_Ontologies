import { useState, useRef, useEffect } from 'react'
import { ingestionAPI } from '../services/api'
import { Upload as UploadIcon, File, CheckCircle, XCircle, Play, Loader } from 'lucide-react'

export default function Upload() {
  const [files, setFiles] = useState([])
  const [uploadId, setUploadId] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)
  const [results, setResults] = useState(null)
  const [clearExisting, setClearExisting] = useState(false)
  const fileInputRef = useRef(null)
  const progressIntervalRef = useRef(null)

  useEffect(() => {
    // Check for existing job on mount
    const savedJobId = localStorage.getItem('current_job_id')
    if (savedJobId) {
      setJobId(savedJobId)
      setProcessing(true)
      pollProgress(savedJobId)
    }

    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current)
      }
    }
  }, [])

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files)
    setFiles(selectedFiles)
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      alert('Please select files first')
      return
    }

    setUploading(true)
    try {
      const response = await ingestionAPI.upload(files)
      setUploadId(response.upload_id)
      setFiles(response.files || files)
      alert(`Successfully uploaded ${response.files.length} file(s)`)
    } catch (error) {
      console.error('Upload failed:', error)
      alert(`Upload failed: ${error.message}`)
    } finally {
      setUploading(false)
    }
  }

  const handleProcess = async () => {
    if (!uploadId) {
      alert('Please upload files first')
      return
    }

    setProcessing(true)
    try {
      const response = await ingestionAPI.process(uploadId, clearExisting)
      setJobId(response.job_id)
      localStorage.setItem('current_job_id', response.job_id)
      pollProgress(response.job_id)
    } catch (error) {
      console.error('Processing failed:', error)
      alert(`Failed to start processing: ${error.message}`)
      setProcessing(false)
    }
  }

  const pollProgress = (jobIdToPoll) => {
    // Clear existing interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current)
    }

    // Poll every 2 seconds
    progressIntervalRef.current = setInterval(async () => {
      try {
        const data = await ingestionAPI.getStatus(jobIdToPoll)
        updateProgress(data)
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(progressIntervalRef.current)
          localStorage.removeItem('current_job_id')
        }
      } catch (error) {
        console.error('Error polling progress:', error)
      }
    }, 2000)

    // Initial poll
    ingestionAPI.getStatus(jobIdToPoll).then(updateProgress)
  }

  const updateProgress = (data) => {
    setProgress(data.progress || 0)
    setStatus(data.status)
    setStatusError(data.error || null)

    if (data.status === 'completed') {
      setResults(data.results)
      setProcessing(false)
    } else if (data.status === 'failed') {
      setProcessing(false)
    }
  }

  const clearFiles = () => {
    setFiles([])
    setUploadId(null)
    setJobId(null)
    setProgress(0)
    setStatus(null)
    setResults(null)
    setProcessing(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Upload & Process Transcripts</h1>
          <p className="mt-2 text-gray-600">Upload transcript files and extract knowledge graph</p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Upload Files</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Transcript Files
              </label>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".txt,.md,.text"
                onChange={handleFileSelect}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              <p className="mt-2 text-sm text-gray-500">
                You can select multiple files at once (.txt, .md, .text)
              </p>
            </div>

            {files.length > 0 && (
              <div className="border border-gray-200 rounded-md p-4">
                <h3 className="font-medium text-gray-900 mb-2">
                  Selected Files ({files.length})
                </h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {files.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded"
                    >
                      <div className="flex items-center space-x-2">
                        <File className="h-4 w-4 text-gray-500" />
                        <span className="text-sm text-gray-700">
                          {file.name || file.filename}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500">
                        {file.size
                          ? `${(file.size / 1024).toFixed(2)} KB`
                          : file.size || 'Unknown size'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex space-x-3">
              <button
                onClick={handleUpload}
                disabled={files.length === 0 || uploading}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {uploading ? (
                  <>
                    <Loader className="h-4 w-4 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <UploadIcon className="h-4 w-4 mr-2" />
                    Upload Files
                  </>
                )}
              </button>
              <button
                onClick={clearFiles}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Clear
              </button>
            </div>
          </div>
        </div>

        {/* Processing Section */}
        {(processing || status) && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Processing Status</h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Progress</span>
                  <span className="text-sm font-bold text-gray-900">{progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-8 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      status === 'completed'
                        ? 'bg-green-500'
                        : status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-blue-500'
                    } ${status === 'processing' ? 'animate-pulse' : ''}`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              <div
                className={`p-4 rounded-md ${
                  status === 'completed'
                    ? 'bg-green-50 border border-green-200'
                    : status === 'failed'
                    ? 'bg-red-50 border border-red-200'
                    : 'bg-blue-50 border border-blue-200'
                }`}
              >
                <div className="flex items-center space-x-2">
                  {status === 'completed' ? (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  ) : status === 'failed' ? (
                    <XCircle className="h-5 w-5 text-red-600" />
                  ) : (
                    <Loader className="h-5 w-5 text-blue-600 animate-spin" />
                  )}
                  <span className="font-medium">
                    {status === 'completed'
                      ? 'Processing completed!'
                      : status === 'failed'
                      ? `Processing failed: ${statusError || 'Unknown error'}`
                      : `Processing... (${status})`}
                  </span>
                </div>
              </div>

              {results && (
                <div className="mt-4 p-4 bg-gray-50 rounded-md">
                  <h3 className="font-medium text-gray-900 mb-2">Results:</h3>
                  <ul className="space-y-1 text-sm text-gray-700">
                    <li>Concepts: {results.concepts || 0}</li>
                    <li>Relationships: {results.relationships || 0}</li>
                    <li>Quotes: {results.quotes || 0}</li>
                    {results.total_files && <li>Total Files: {results.total_files}</li>}
                    {results.total_chunks && <li>Total Chunks: {results.total_chunks}</li>}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Sidebar */}
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Instructions</h2>
          <ol className="space-y-2 text-sm text-gray-600 list-decimal list-inside">
            <li>Select transcript files (.txt, .md)</li>
            <li>Click "Upload Files"</li>
            <li>Files will be saved to your workspace</li>
            <li>Click "Start Processing" to extract KG</li>
            <li>Processing can take time (1.5 hours for 1000 files)</li>
            <li>Progress persists even if you refresh the page</li>
          </ol>
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-xs text-yellow-800">
              <strong>Note:</strong> Processing is done in the background. You can close this page and check back later.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Processing Options</h2>
          <div className="space-y-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={clearExisting}
                onChange={(e) => setClearExisting(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">
                Clear existing knowledge graph
              </span>
            </label>
            <button
              onClick={handleProcess}
              disabled={!uploadId || processing}
              className="w-full flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {processing ? (
                <>
                  <Loader className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Start Processing
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

