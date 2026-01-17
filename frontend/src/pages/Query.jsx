import { useState, useEffect, useRef } from 'react'
import { queryAPI } from '../services/api'
import { MessageCircle, Eye, EyeOff, Network, Trash2, Send } from 'lucide-react'

export default function Query() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [answer, setAnswer] = useState(null)
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem('session_id') || null
  })
  const [conversation, setConversation] = useState([])
  const [showSources, setShowSources] = useState(false)
  const [showGraph, setShowGraph] = useState(false)
  const conversationEndRef = useRef(null)

  useEffect(() => {
    if (sessionId) {
      loadConversationHistory()
    }
  }, [sessionId])

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation])

  const loadConversationHistory = async () => {
    if (!sessionId) return
    try {
      const data = await queryAPI.getHistory(sessionId)
      if (data.messages) {
        setConversation(data.messages)
      }
    } catch (error) {
      console.error('Failed to load conversation history:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!question.trim() || loading) return

    const userQuestion = question.trim()
    setQuestion('')
    setLoading(true)

    // Add user question to conversation
    const userMessage = { role: 'user', content: userQuestion }
    setConversation([...conversation, userMessage])

    try {
      const response = await queryAPI.query(userQuestion, sessionId)
      
      // Store session ID
      if (response.session_id) {
        setSessionId(response.session_id)
        localStorage.setItem('session_id', response.session_id)
      }

      // Add assistant answer to conversation
      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        metadata: response.metadata,
      }
      setConversation([...conversation, userMessage, assistantMessage])
      setAnswer(response)
    } catch (error) {
      console.error('Query failed:', error)
      alert(`Query failed: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const clearConversation = () => {
    setConversation([])
    setAnswer(null)
    setSessionId(null)
    localStorage.removeItem('session_id')
  }

  const formatAnswer = (text) => {
    return text.split('\n').map((line, i) => (
      <p key={i} className="mb-2">
        {line}
      </p>
    ))
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Main Query Area */}
      <div className="lg:col-span-2 space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Query Knowledge Graph</h1>
          <p className="mt-2 text-gray-600">Ask questions about your knowledge base</p>
        </div>

        {/* Query Form */}
        <div className="bg-white rounded-lg shadow p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Question
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g., What practices are most associated with improving clarity?"
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="flex items-center px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Querying...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Query
                </>
              )}
            </button>
          </form>
        </div>

        {/* Answer Display */}
        {answer && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">Answer</h2>
              <div className="flex space-x-2">
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="flex items-center px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-md text-sm"
                >
                  {showSources ? (
                    <>
                      <EyeOff className="h-4 w-4 mr-1" />
                      Hide Sources
                    </>
                  ) : (
                    <>
                      <Eye className="h-4 w-4 mr-1" />
                      Show Sources
                    </>
                  )}
                </button>
                <button
                  onClick={() => setShowGraph(!showGraph)}
                  className="flex items-center px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-md text-sm"
                >
                  {showGraph ? (
                    <>
                      <EyeOff className="h-4 w-4 mr-1" />
                      Hide Graph
                    </>
                  ) : (
                    <>
                      <Network className="h-4 w-4 mr-1" />
                      Show Graph
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="prose max-w-none mb-4">
              {formatAnswer(answer.answer)}
            </div>

            {/* Metadata */}
            {answer.metadata && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex items-center space-x-4 text-sm text-gray-600">
                  <span className={`px-2 py-1 rounded ${
                    answer.metadata.method === 'hybrid'
                      ? 'bg-blue-100 text-blue-800'
                      : answer.metadata.method === 'rag'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-purple-100 text-purple-800'
                  }`}>
                    {answer.metadata.method?.toUpperCase() || 'UNKNOWN'}
                  </span>
                  {answer.metadata.rag_count !== undefined && (
                    <span>RAG: {answer.metadata.rag_count}</span>
                  )}
                  {answer.metadata.kg_count !== undefined && (
                    <span>KG: {answer.metadata.kg_count}</span>
                  )}
                </div>
              </div>
            )}

            {/* Sources */}
            {showSources && answer.sources && answer.sources.length > 0 && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  Sources
                </h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {answer.sources.slice(0, 10).map((source, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-gray-50 rounded border border-gray-200"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">
                          {source.episode_id || 'Unknown Episode'}
                        </span>
                        {source.timestamp && (
                          <span className="text-xs text-gray-500">
                            {source.timestamp}
                          </span>
                        )}
                      </div>
                      {source.speaker && (
                        <span className="text-xs text-gray-600">
                          Speaker: {source.speaker}
                        </span>
                      )}
                      <p className="text-sm text-gray-700 mt-2">
                        {source.text?.substring(0, 200)}...
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Graph Visualization */}
            {showGraph && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  Graph Visualization
                </h3>
                <div className="h-64 bg-gray-50 rounded border border-gray-200 flex items-center justify-center">
                  <p className="text-gray-500">Graph visualization coming soon</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Conversation History Sidebar */}
      <div className="lg:col-span-1">
        <div className="bg-white rounded-lg shadow p-6 sticky top-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-900">Conversation</h2>
            {conversation.length > 0 && (
              <button
                onClick={clearConversation}
                className="p-2 text-red-600 hover:bg-red-50 rounded"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
          <div className="space-y-4 max-h-[600px] overflow-y-auto">
            {conversation.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                No conversation yet
              </p>
            ) : (
              conversation.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded ${
                    msg.role === 'user'
                      ? 'bg-blue-50 text-right'
                      : 'bg-gray-50 text-left'
                  }`}
                >
                  <div className="text-xs font-medium text-gray-500 mb-1">
                    {msg.role === 'user' ? 'You' : 'Assistant'}
                  </div>
                  <div className="text-sm text-gray-900">
                    {msg.content?.substring(0, 150)}
                    {msg.content?.length > 150 && '...'}
                  </div>
                </div>
              ))
            )}
            <div ref={conversationEndRef} />
          </div>
        </div>
      </div>
    </div>
  )
}

