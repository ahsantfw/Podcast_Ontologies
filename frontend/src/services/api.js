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
  query: async (question, sessionId = null) => {
    const response = await api.post('/query', {
      question,
      session_id: sessionId,
    })
    return response.data
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

