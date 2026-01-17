import { useState } from 'react'
import { scriptsAPI } from '../services/api'
import { FileText, Download, Loader, Sparkles } from 'lucide-react'

export default function Scripts() {
  const [theme, setTheme] = useState('')
  const [runtime, setRuntime] = useState(45)
  const [style, setStyle] = useState('tapestry')
  const [maxQuotes, setMaxQuotes] = useState(20)
  const [format, setFormat] = useState('markdown')
  const [loading, setLoading] = useState(false)
  const [script, setScript] = useState(null)
  const [error, setError] = useState(null)

  const handleGenerate = async (e) => {
    e.preventDefault()
    if (!theme.trim()) {
      alert('Please enter a theme')
      return
    }

    setLoading(true)
    setError(null)
    setScript(null)

    try {
      const response = await scriptsAPI.generate({
        theme: theme.trim(),
        runtime_minutes: runtime,
        style,
        max_quotes: maxQuotes,
        format,
      })
      setScript(response)
    } catch (err) {
      console.error('Script generation failed:', err)
      // Better error handling
      if (err.response) {
        const errorDetail = err.response.data?.detail || err.response.data?.message || err.message
        setError(errorDetail || 'Failed to generate script')
      } else {
        setError(err.message || 'Failed to generate script. Make sure transcripts have been processed and quotes were extracted.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    if (!script || !script.formatted) {
      alert('No script to download')
      return
    }

    const blob = new Blob([script.formatted], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${script.title || 'script'}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Generate Script</h1>
          <p className="mt-2 text-gray-600">Create tapestry-style scripts from your knowledge graph</p>
        </div>

        <form onSubmit={handleGenerate} className="bg-white rounded-lg shadow p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Theme/Topic *
            </label>
            <input
              type="text"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="e.g., creativity, discipline, clarity"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="mt-1 text-sm text-gray-500">
              The main theme or topic for the script
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Runtime: {runtime} minutes
            </label>
            <input
              type="range"
              min="15"
              max="60"
              value={runtime}
              onChange={(e) => setRuntime(Number(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>15 min</span>
              <span>60 min</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Style
            </label>
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="tapestry">Tapestry (interweaving)</option>
              <option value="thematic">Thematic (by theme)</option>
              <option value="linear">Linear (chronological)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Quotes
            </label>
            <input
              type="number"
              min="5"
              max="50"
              value={maxQuotes}
              onChange={(e) => setMaxQuotes(Number(e.target.value))}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Output Format
            </label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="markdown">Markdown</option>
              <option value="json">JSON</option>
              <option value="plain">Plain Text</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading || !theme.trim()}
            className="w-full flex items-center justify-center px-6 py-3 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <Loader className="h-5 w-5 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="h-5 w-5 mr-2" />
                Generate Script
              </>
            )}
          </button>
        </form>
      </div>

      <div className="space-y-6">
        {/* Script Preview */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-900">Script Preview</h2>
            {script && (
              <button
                onClick={handleDownload}
                className="flex items-center px-3 py-1 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                <Download className="h-4 w-4 mr-1" />
                Download
              </button>
            )}
          </div>
          <div className="min-h-[400px] max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <Loader className="h-8 w-8 animate-spin mb-2" />
                <p>Generating script...</p>
              </div>
            ) : error ? (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="font-semibold text-red-800 mb-2">Error Generating Script</div>
                <div className="text-sm text-red-700 whitespace-pre-wrap">{error}</div>
                <div className="mt-3 text-xs text-red-600">
                  <p className="font-medium mb-1">Possible solutions:</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Make sure transcripts have been processed</li>
                    <li>Try a different theme or more general topic</li>
                    <li>Check that quotes were extracted during processing</li>
                    <li>Try uploading/processing transcripts first</li>
                  </ul>
                </div>
              </div>
            ) : script ? (
              <pre className="p-4 bg-gray-50 rounded border border-gray-200 text-sm whitespace-pre-wrap font-mono">
                {script.formatted}
              </pre>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Script will appear here after generation</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Metadata */}
        {script && script.metadata && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Metadata</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Theme:</span>
                <span className="font-medium">{script.metadata.theme || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Runtime:</span>
                <span className="font-medium">
                  {script.metadata.runtime_minutes || 'N/A'} minutes
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Style:</span>
                <span className="font-medium">{script.metadata.style || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Total Quotes:</span>
                <span className="font-medium">{script.metadata.total_quotes || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Total Segments:</span>
                <span className="font-medium">{script.metadata.total_segments || 0}</span>
              </div>
              {script.metadata.episodes && script.metadata.episodes.length > 0 && (
                <div>
                  <span className="text-gray-600">Episodes:</span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {script.metadata.episodes.map((ep, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs"
                      >
                        {ep}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

