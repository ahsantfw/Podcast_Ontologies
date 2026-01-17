import { Link, useLocation } from 'react-router-dom'
import { useWorkspace } from '../context/WorkspaceContext'
import {
  LayoutDashboard,
  MessageCircle,
  Upload,
  FileText,
  Network,
  Plus,
} from 'lucide-react'
import { useState } from 'react'

export default function Layout({ children }) {
  const location = useLocation()
  const { workspaceId, changeWorkspace, createWorkspace } = useWorkspace()
  const [showWorkspaceModal, setShowWorkspaceModal] = useState(false)
  const [workspaceName, setWorkspaceName] = useState('')

  const isActive = (path) => location.pathname === path

  const handleCreateWorkspace = async () => {
    try {
      await createWorkspace(workspaceName || null)
      setShowWorkspaceModal(false)
      setWorkspaceName('')
    } catch (error) {
      alert(`Failed to create workspace: ${error.message}`)
    }
  }

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/query', icon: MessageCircle, label: 'Query' },
    { path: '/upload', icon: Upload, label: 'Upload' },
    { path: '/scripts', icon: FileText, label: 'Scripts' },
    { path: '/explore', icon: Network, label: 'Explore' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-gray-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex items-center space-x-2 px-3 py-2">
                <Network className="h-6 w-6" />
                <span className="font-bold text-lg">Knowledge Graph</span>
              </Link>
              <div className="hidden md:flex space-x-1 ml-8">
                {navItems.map((item) => {
                  const Icon = item.icon
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive(item.path)
                          ? 'bg-gray-800 text-white'
                          : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                      }`}
                    >
                      <Icon className="h-5 w-5 mr-2" />
                      {item.label}
                    </Link>
                  )
                })}
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-400">
                Workspace: <span className="text-white font-semibold">{workspaceId}</span>
              </span>
              <button
                onClick={() => setShowWorkspaceModal(true)}
                className="flex items-center px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium transition-colors"
              >
                <Plus className="h-4 w-4 mr-1" />
                New Workspace
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile menu */}
      <div className="md:hidden bg-gray-800 border-t border-gray-700">
        <div className="px-2 pt-2 pb-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-3 py-2 rounded-md text-base font-medium ${
                  isActive(item.path)
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <Icon className="h-5 w-5 mr-3" />
                {item.label}
              </Link>
            )
          })}
        </div>
      </div>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Workspace Modal */}
      {showWorkspaceModal && (
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
                  setShowWorkspaceModal(false)
                  setWorkspaceName('')
                }}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateWorkspace}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
