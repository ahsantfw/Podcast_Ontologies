import { useState, useEffect } from 'react'
import { useWorkspace } from '../context/WorkspaceContext'
import { workspaceAPI, graphAPI } from '../services/api'
import { User, Settings, Key, Database, Trash2, Plus, ArrowLeft, Network, Link2, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Account() {
  const { workspaceId, changeWorkspace, createWorkspace } = useWorkspace()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [workspaceName, setWorkspaceName] = useState('')
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)

  const handleCreateWorkspace = async () => {
    setLoading(true)
    try {
      await createWorkspace(workspaceName || null)
      setShowCreateModal(false)
      setWorkspaceName('')
    } catch (error) {
      alert(`Failed to create workspace: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteKG = async () => {
    if (!window.confirm('Are you sure you want to delete the Knowledge Graph? This cannot be undone.')) {
      return
    }
    try {
      await workspaceAPI.deleteKG(workspaceId)
      alert('Knowledge Graph deleted successfully')
      loadStats() // Refresh stats after deletion
    } catch (error) {
      alert(`Failed to delete KG: ${error.message}`)
    }
  }

  const handleDeleteEmbeddings = async () => {
    if (!window.confirm('Are you sure you want to delete embeddings? This cannot be undone.')) {
      return
    }
    try {
      await workspaceAPI.deleteEmbeddings(workspaceId)
      alert('Embeddings deleted successfully')
      // Note: Embeddings deletion doesn't affect KG stats, so no refresh needed
    } catch (error) {
      alert(`Failed to delete embeddings: ${error.message}`)
    }
  }

  const handleDeleteAll = async () => {
    if (!window.confirm('Are you sure you want to delete everything? This cannot be undone.')) {
      return
    }
    try {
      await workspaceAPI.deleteAll(workspaceId)
      alert('All data deleted successfully')
      loadStats() // Refresh stats after deletion
    } catch (error) {
      alert(`Failed to delete: ${error.message}`)
    }
  }

  const loadStats = async () => {
    try {
      setStatsLoading(true)
      const data = await graphAPI.getStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to load stats:', error)
      setStats(null)
    } finally {
      setStatsLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
  }, [workspaceId])

  return (
    <div className="min-h-screen bg-gray-50 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Link to="/" className="inline-flex items-center text-blue-600 hover:text-blue-700 mb-6">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Chat
        </Link>

        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="flex items-center mb-8">
            <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-2xl font-bold mr-4">
              <User className="h-8 w-8" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Account Settings</h1>
              <p className="text-gray-600">Manage your workspace and preferences</p>
            </div>
          </div>

          {/* Workspace Section */}
          <div className="mb-8 pb-8 border-b border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                <Database className="h-5 w-5 mr-2" />
                Current Workspace
              </h2>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Plus className="h-4 w-4 mr-2" />
                New Workspace
              </button>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="font-medium text-gray-900 mb-1">{workspaceId}</div>
              <div className="text-sm text-gray-600">Active workspace for all operations</div>
            </div>
          </div>

          {/* KG Statistics */}
          <div className="mb-8 pb-8 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center mb-4">
              <Network className="h-5 w-5 mr-2" />
              Knowledge Graph Statistics
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <button
                className="group relative overflow-hidden rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 p-6 text-left text-white shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl"
                disabled
              >
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-2">
                    <Database className="h-8 w-8 opacity-90" />
                    <span className="text-xs font-medium opacity-75">Total Nodes</span>
                  </div>
                  <div className="text-3xl font-bold">
                    {statsLoading ? '...' : stats?.total_nodes || 0}
                  </div>
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-blue-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              </button>

              <button
                className="group relative overflow-hidden rounded-xl bg-gradient-to-br from-green-500 to-green-600 p-6 text-left text-white shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl"
                disabled
              >
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-2">
                    <Link2 className="h-8 w-8 opacity-90" />
                    <span className="text-xs font-medium opacity-75">Relationships</span>
                  </div>
                  <div className="text-3xl font-bold">
                    {statsLoading ? '...' : stats?.total_relationships || 0}
                  </div>
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-green-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              </button>

              <button
                className="group relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 p-6 text-left text-white shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl"
                disabled
              >
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-2">
                    <TrendingUp className="h-8 w-8 opacity-90" />
                    <span className="text-xs font-medium opacity-75">Concepts</span>
                  </div>
                  <div className="text-3xl font-bold">
                    {statsLoading ? '...' : stats?.by_type?.Concept || 0}
                  </div>
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-purple-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              </button>
            </div>
          </div>

          {/* Danger Zone */}
          <div className="pt-8">
            <h2 className="text-xl font-semibold text-red-600 mb-6">Danger Zone</h2>
            <div className="space-y-4">
              <div className="border border-red-200 rounded-lg p-4 bg-red-50">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 mb-1">Delete Knowledge Graph</h3>
                    <p className="text-sm text-gray-600">Delete all nodes and relationships. Keeps files and sessions.</p>
                  </div>
                  <button
                    onClick={handleDeleteKG}
                    className="w-[120px] px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center justify-center transition-colors"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>

              <div className="border border-red-200 rounded-lg p-4 bg-red-50">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 mb-1">Delete Embeddings</h3>
                    <p className="text-sm text-gray-600">Delete all vector embeddings. Keeps KG and files.</p>
                  </div>
                  <button
                    onClick={handleDeleteEmbeddings}
                    className="w-[120px] px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center justify-center transition-colors"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>

              <div className="border border-red-200 rounded-lg p-4 bg-red-50">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 mb-1">Delete Everything</h3>
                    <p className="text-sm text-gray-600">Delete KG and embeddings. Keeps files and sessions.</p>
                  </div>
                  <button
                    onClick={handleDeleteAll}
                    className="w-[120px] px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center justify-center transition-colors"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>

              <div className="border border-red-200 rounded-lg p-4 bg-red-50">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 mb-1">Delete Entire Workspace</h3>
                    <p className="text-sm text-gray-600">Delete everything including KG, embeddings, sessions, and files. This cannot be undone.</p>
                  </div>
                  <button
                    onClick={async () => {
                      if (!window.confirm(`Are you sure you want to delete the entire workspace "${workspaceId}"? This will delete EVERYTHING including all sessions and cannot be undone.`)) {
                        return
                      }
                      try {
                        await workspaceAPI.delete(workspaceId)
                        alert('Workspace deleted successfully. Redirecting to default workspace...')
                        changeWorkspace('default')
                        window.location.href = '/'
                      } catch (error) {
                        alert(`Failed to delete workspace: ${error.message}`)
                      }
                    }}
                    className="w-[120px] px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center justify-center transition-colors font-semibold"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Create Workspace Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Create New Workspace</h2>
            <input
              type="text"
              placeholder="Workspace name (optional)"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md mb-4"
              onKeyPress={(e) => e.key === 'Enter' && handleCreateWorkspace()}
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowCreateModal(false)
                  setWorkspaceName('')
                }}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateWorkspace}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

