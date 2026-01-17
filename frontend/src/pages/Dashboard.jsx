import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useWorkspace } from '../context/WorkspaceContext'
import { graphAPI } from '../services/api'
import {
  MessageCircle,
  Upload,
  FileText,
  Network,
  Database,
  Link2,
  TrendingUp,
  ArrowLeft,
} from 'lucide-react'

export default function Dashboard() {
  const { workspaceId } = useWorkspace()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
  }, [workspaceId])

  const loadStats = async () => {
    try {
      setLoading(true)
      const data = await graphAPI.getStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const quickActions = [
    {
      icon: MessageCircle,
      label: 'Ask a Question',
      path: '/',
      color: 'bg-blue-500',
    },
    {
      icon: Upload,
      label: 'Upload Transcripts',
      path: '/upload',
      color: 'bg-green-500',
    },
    {
      icon: FileText,
      label: 'Generate Script',
      path: '/scripts',
      color: 'bg-purple-500',
    },
    {
      icon: Network,
      label: 'Explore Graph',
      path: '/explore',
      color: 'bg-orange-500',
    },
  ]

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Back to Chat Button */}
        <Link to="/" className="inline-flex items-center text-blue-600 hover:text-blue-700 mb-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Chat
        </Link>

        {/* Header Section */}
        <div className="bg-white rounded-xl shadow-sm p-8 border border-gray-200">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Dashboard</h1>
          <p className="text-lg text-gray-600">Overview of your Knowledge Graph</p>
        </div>

        {/* Stats Cards - Workspace first */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Knowledge Graph Statistics</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Workspace - Position #1 */}
          <button
            className="group relative overflow-hidden rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 p-6 text-left text-white shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl"
            disabled
          >
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-2">
                <Database className="h-8 w-8 opacity-90" />
                <span className="text-xs font-medium opacity-75">Workspace</span>
              </div>
              <div className="text-2xl font-bold truncate">
                {workspaceId}
              </div>
            </div>
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </button>

          {/* Total Nodes - Position #2 */}
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
                {stats?.total_nodes || 0}
              </div>
            </div>
            <div className="absolute inset-0 bg-gradient-to-br from-blue-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </button>

          {/* Relationships - Position #3 */}
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
                {stats?.total_relationships || 0}
              </div>
            </div>
            <div className="absolute inset-0 bg-gradient-to-br from-green-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </button>

          {/* Concepts - Position #4 */}
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
                {stats?.by_type?.Concept || 0}
              </div>
            </div>
            <div className="absolute inset-0 bg-gradient-to-br from-purple-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </button>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {quickActions.map((action) => {
              const Icon = action.icon
              return (
                <Link
                  key={action.path}
                  to={action.path}
                  className={`${action.color} text-white rounded-xl p-6 hover:opacity-90 transition-all duration-300 hover:scale-105 hover:shadow-xl flex flex-col items-center justify-center space-y-3 shadow-lg`}
                >
                  <Icon className="h-8 w-8" />
                  <span className="text-sm font-semibold text-center">{action.label}</span>
                </Link>
              )
            })}
          </div>
        </div>

        {/* Node Types Breakdown */}
        {stats?.by_type && Object.keys(stats.by_type).length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              Nodes by Type
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(stats.by_type)
                .slice(0, 8)
                .map(([type, count]) => (
                  <div
                    key={type}
                    className="flex justify-between items-center p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200 hover:border-purple-300 hover:shadow-sm transition-all"
                  >
                    <span className="text-sm font-semibold text-gray-800">
                      {type}
                    </span>
                    <span className="text-lg font-bold text-purple-600 bg-purple-50 px-3 py-1 rounded-full">
                      {count}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Relationship Types */}
        {stats?.relationships_by_type &&
          Object.keys(stats.relationships_by_type).length > 0 && (
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Top Relationships
              </h2>
              <div className="space-y-3">
                {Object.entries(stats.relationships_by_type)
                  .slice(0, 10)
                  .map(([type, count]) => (
                    <div
                      key={type}
                      className="flex justify-between items-center p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all"
                    >
                      <span className="text-sm font-semibold text-gray-800">
                        {type}
                      </span>
                      <span className="text-lg font-bold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">
                        {count}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
      </div>
    </div>
  )
}

