import { createContext, useContext, useState, useEffect } from 'react'

const WorkspaceContext = createContext()

export function useWorkspace() {
  const context = useContext(WorkspaceContext)
  if (!context) {
    throw new Error('useWorkspace must be used within WorkspaceProvider')
  }
  return context
}

export function WorkspaceProvider({ children }) {
  const [workspaceId, setWorkspaceId] = useState(() => {
    return localStorage.getItem('workspace_id') || 'default'
  })
  const [workspaces, setWorkspaces] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    localStorage.setItem('workspace_id', workspaceId)
  }, [workspaceId])

  useEffect(() => {
    loadWorkspaces()
  }, [])

  const loadWorkspaces = async () => {
    try {
      setLoading(true)
      const { workspaceAPI } = await import('../services/api')
      const data = await workspaceAPI.list()
      if (data.workspaces) {
        setWorkspaces(data.workspaces)
        // If current workspace not in list, add it
        if (!data.workspaces.find(w => w.workspace_id === workspaceId)) {
          setWorkspaces([...data.workspaces, {
            workspace_id: workspaceId,
            name: workspaceId,
            created_at: null
          }])
        }
      }
    } catch (error) {
      console.error('Failed to load workspaces:', error)
      // Fallback: at least have default
      setWorkspaces([{
        workspace_id: 'default',
        name: 'default',
        created_at: null
      }])
    } finally {
      setLoading(false)
    }
  }

  const changeWorkspace = (newWorkspaceId) => {
    setWorkspaceId(newWorkspaceId)
    localStorage.setItem('workspace_id', newWorkspaceId)
    // Clear session when switching workspace
    localStorage.removeItem('session_id')
  }

  const createWorkspace = async (name) => {
    try {
      const { workspaceAPI } = await import('../services/api')
      const data = await workspaceAPI.create(name)
      await loadWorkspaces() // Reload list
      setWorkspaceId(data.workspace_id)
      return data
    } catch (error) {
      console.error('Failed to create workspace:', error)
      throw error
    }
  }

  return (
    <WorkspaceContext.Provider
      value={{
        workspaceId,
        workspaces,
        loading,
        changeWorkspace,
        createWorkspace,
        loadWorkspaces,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

