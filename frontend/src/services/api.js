import axios from 'axios'

// Support environment variable for tunnel URL, fallback to proxy
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add workspace_id to headers
api.interceptors.request.use(
  (config) => {
    const workspaceId = localStorage.getItem('workspace_id') || 'default'
    config.headers['X-Workspace-Id'] = workspaceId
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// API functions
export const queryAPI = {
  query: async (question, sessionId = null, style = 'casual', tone = 'warm') => {
    const response = await api.post('/query', {
      question,
      session_id: sessionId,
      style: style,
      tone: tone,
    })
    return response.data
  },

  queryStream: async function* (question, sessionId = null, style = 'casual', tone = 'warm') {
    /**
     * Stream query results using Server-Sent Events (SSE).
     * 
     * Yields objects with:
     * - chunk: text chunk
     * - done: boolean indicating if stream is complete
     * - session_id: session ID (when done)
     * - sources: array of sources (when done)
     * - metadata: response metadata (when done)
     */
    const workspaceId = localStorage.getItem('workspace_id') || 'default'
    const baseURL = import.meta.env.VITE_API_URL || '/api/v1'
    
    try {
      const response = await fetch(`${baseURL}/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Workspace-Id': workspaceId,
        },
        body: JSON.stringify({
          question,
          session_id: sessionId,
          style: style,
          tone: tone,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          // Process any remaining buffer
          if (buffer.trim()) {
            const lines = buffer.split('\n')
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6))
                  yield data
                  if (data.done) return
                } catch (e) {
                  console.error('Failed to parse SSE data:', e, line)
                }
              }
            }
          }
          break
        }

        // Decode and process immediately for faster streaming
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        // Process all complete lines immediately
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              yield data
              
              if (data.done) {
                return
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e, line)
              // Yield error so frontend can handle it
              yield {
                chunk: `Error parsing stream data: ${e.message}`,
                done: true,
                error: true
              }
              return
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming query failed:', error)
      yield {
        chunk: `Error: ${error.message || 'Failed to get response'}`,
        done: true,
        error: true
      }
    }
  },

  getHistory: async (sessionId) => {
    const response = await api.get(`/query/history?session_id=${sessionId}`)
    return response.data
  },
}

export const scriptsAPI = {
  generate: async (params) => {
    const response = await api.post('/scripts/generate', params)
    return response.data
  },

  list: async () => {
    const response = await api.get('/scripts')
    return response.data
  },

  get: async (scriptId) => {
    const response = await api.get(`/scripts/${scriptId}`)
    return response.data
  },

  delete: async (scriptId) => {
    const response = await api.delete(`/scripts/${scriptId}`)
    return response.data
  },
}

export const ingestionAPI = {
  upload: async (files) => {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })
    const response = await api.post('/ingest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  process: async (uploadId, clearExisting = false) => {
    const response = await api.post('/ingest/process', {
      upload_id: uploadId,
      clear_existing: clearExisting,
    })
    return response.data
  },

  getStatus: async (jobId) => {
    const response = await api.get(`/ingest/status/${jobId}`)
    return response.data
  },
}

export const graphAPI = {
  getStats: async () => {
    const response = await api.get('/graph/stats')
    return response.data
  },

  getConcepts: async (theme = null, conceptType = null, limit = 50) => {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (theme) params.append('theme', theme)
    if (conceptType) params.append('concept_type', conceptType)
    const response = await api.get(`/graph/concepts?${params}`)
    return response.data
  },

  getConcept: async (conceptId) => {
    const response = await api.get(`/graph/concepts/${conceptId}`)
    return response.data
  },

  explore: async (conceptId, depth = 2) => {
    const response = await api.get(`/graph/explore/${conceptId}?depth=${depth}`)
    return response.data
  },
}

export const workspaceAPI = {
  create: async (name = null) => {
    const response = await api.post('/workspaces', { name })
    return response.data
  },

  list: async () => {
    const response = await api.get('/workspaces')
    return response.data
  },

  get: async (workspaceId) => {
    const response = await api.get(`/workspaces/${workspaceId}`)
    return response.data
  },

  deleteKG: async (workspaceId) => {
    const response = await api.delete(`/workspaces/${workspaceId}/kg`)
    return response.data
  },

  deleteEmbeddings: async (workspaceId) => {
    const response = await api.delete(`/workspaces/${workspaceId}/embeddings`)
    return response.data
  },

  deleteAll: async (workspaceId) => {
    const response = await api.delete(`/workspaces/${workspaceId}/all`)
    return response.data
  },

  delete: async (workspaceId) => {
    const response = await api.delete(`/workspaces/${workspaceId}`)
    return response.data
  },
}

export const sessionsAPI = {
  list: async (allWorkspaces = false) => {
    const url = allWorkspaces ? '/sessions?all_workspaces=true' : '/sessions'
    const response = await api.get(url)
    return response.data
  },

  get: async (sessionId) => {
    const response = await api.get(`/sessions/${sessionId}`)
    return response.data
  },

  delete: async (sessionId) => {
    const response = await api.delete(`/sessions/${sessionId}`)
    return response.data
  },
}

export default api

