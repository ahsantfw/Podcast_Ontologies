import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useWorkspace } from '../context/WorkspaceContext'
import { queryAPI, sessionsAPI } from '../services/api'
import ChatMessage from '../components/ChatMessage'
import StyleSelector from '../components/StyleSelector'
import ToneSelector from '../components/ToneSelector'
import { Send, Plus, Settings, Trash2, FileText, Upload, Network, MessageCircle, ChevronDown, Check } from 'lucide-react'

export default function Chat() {
  const navigate = useNavigate()
  const { workspaceId, workspaces, changeWorkspace, createWorkspace, loadWorkspaces } = useWorkspace()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  // Thinking steps are now managed within each message object
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem('session_id') || null
  })
  const [chatHistory, setChatHistory] = useState([])
  const [showSourcesForMessage, setShowSourcesForMessage] = useState({})
  // Store message metadata (RAG count, KG count, Sources) separately for persistence
  const [messageMetadata, setMessageMetadata] = useState(() => {
    try {
      const saved = localStorage.getItem('message_metadata')
      return saved ? JSON.parse(saved) : {}
    } catch {
      return {}
    }
  })
  const [showWorkspaceDropdown, setShowWorkspaceDropdown] = useState(false)
  const [showNewWorkspaceModal, setShowNewWorkspaceModal] = useState(false)
  const [workspaceName, setWorkspaceName] = useState('')
  const [style, setStyle] = useState(() => {
    return localStorage.getItem('chat_style') || 'casual'
  })
  const [tone, setTone] = useState(() => {
    return localStorage.getItem('chat_tone') || 'warm'
  })
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const workspaceDropdownRef = useRef(null)

  // Helper function to remove sources from answer text
  const removeSourcesFromText = (text) => {
    if (!text) return text
    // Remove [Sources: ...] pattern at the end
    return text.replace(/\n*\[Sources:.*?\]\s*$/g, '').trim()
  }

  const loadChatHistory = useCallback(async () => {
    try {
      console.log('Loading chat history for workspace:', workspaceId)
      // Load all sessions from all workspaces
      const data = await sessionsAPI.list(true)
      console.log('Sessions API response:', data)
      
      if (data.sessions && Array.isArray(data.sessions) && data.sessions.length > 0) {
        // Fetch full session details to get message count and first message
        // Limit to first 50 to avoid too many API calls
        const sessionsToLoad = data.sessions.slice(0, 50)
        const historyPromises = sessionsToLoad.map(async (session) => {
          try {
            const fullSession = await sessionsAPI.get(session.session_id)
            const firstMessage = fullSession.messages?.[0]
            const title = firstMessage?.content?.substring(0, 50) || 
                         `Chat ${new Date(session.updated_at || session.created_at).toLocaleDateString()}`
            
            return {
              id: session.session_id,
              title: title,
              timestamp: session.updated_at || session.created_at,
              messageCount: fullSession.messages?.length || 0,
              workspace_id: fullSession.workspace_id || session.workspace_id || workspaceId
            }
          } catch (e) {
            console.error(`Failed to load session ${session.session_id}:`, e)
            return {
              id: session.session_id,
              title: `Chat ${new Date(session.updated_at || session.created_at).toLocaleDateString()}`,
              timestamp: session.updated_at || session.created_at,
              messageCount: 0,
              workspace_id: session.workspace_id || workspaceId
            }
          }
        })
        
        const history = await Promise.all(historyPromises)
        // Filter out any failed loads
        const validHistory = history.filter(h => h.id)
        
        // Sort by timestamp (most recent first)
        validHistory.sort((a, b) => {
          const timeA = new Date(a.timestamp || 0).getTime()
          const timeB = new Date(b.timestamp || 0).getTime()
          return timeB - timeA
        })
        
        console.log('Loaded chat history:', validHistory.length, 'sessions')
        setChatHistory(validHistory)
      } else {
        setChatHistory([])
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
      setChatHistory([])
    }
  }, [workspaceId])

  useEffect(() => {
    // Load chat history when workspace changes
    loadChatHistory()
    loadWorkspaces()
  }, [workspaceId]) // Only depend on workspaceId to avoid infinite loops

  useEffect(() => {
    // Load history and current session on initial mount
    const initializeChat = async () => {
      await loadChatHistory()
      
      // If we have a session_id in localStorage, load that session's messages
      const savedSessionId = localStorage.getItem('session_id')
      if (savedSessionId) {
        console.log('Loading saved session:', savedSessionId)
        await loadSessionMessages(savedSessionId)
      }
    }
    initializeChat()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run on mount - loadChatHistory is stable

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (workspaceDropdownRef.current && !workspaceDropdownRef.current.contains(event.target)) {
        setShowWorkspaceDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setLoading(true)
    // Thinking steps will be managed in the message itself

    const userMsg = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }
    
    // Create placeholder assistant message for streaming with thinking steps
    const assistantMsg = {
      id: `msg_${Date.now()}_${messages.length}`,
      role: 'assistant',
      content: '',
      sources: [],
      metadata: {},
      timestamp: new Date().toISOString(),
      streaming: true,
      thinkingComplete: false, // Track when thinking is done
      thinkingSteps: {
        understanding: false,
        searchingRAG: false,
        searchingKG: false,
        generating: false
      }
    }
    
    // Add both messages and track the assistant message index
    let assistantMsgIndex
    setMessages(prev => {
      const newMessages = [...prev, userMsg, assistantMsg]
      assistantMsgIndex = newMessages.length - 1
      return newMessages
    })

    try {
      // Update thinking step: Understanding
      setMessages(prev => {
        const updated = [...prev]
        const msgIndex = updated.length - 1
        if (updated[msgIndex]) {
          updated[msgIndex] = {
            ...updated[msgIndex],
            thinkingSteps: {
              understanding: true,
              searchingRAG: false,
              searchingKG: false,
              generating: false
            }
          }
        }
        return updated
      })

      // Use streaming query with fallback to regular query
      let fullAnswer = ''
      let finalSessionId = sessionId
      let finalSources = []
      let finalMetadata = {}
      let streamingWorked = false

      try {
        // Simulate thinking steps with shorter delays (reduced from 2 seconds to ~1 second)
        // Understanding completes after 150ms
        setTimeout(() => {
          setMessages(prev => {
            const updated = [...prev]
            const msgIndex = updated.length - 1
            if (updated[msgIndex] && updated[msgIndex].streaming) {
              updated[msgIndex] = {
                ...updated[msgIndex],
                thinkingSteps: {
                  understanding: true,
                  searchingRAG: false,
                  searchingKG: false,
                  generating: false
                }
              }
            }
            return updated
          })
        }, 150)

        // Searching RAG completes after 400ms
        setTimeout(() => {
          setMessages(prev => {
            const updated = [...prev]
            const msgIndex = updated.length - 1
            if (updated[msgIndex] && updated[msgIndex].streaming) {
              updated[msgIndex] = {
                ...updated[msgIndex],
                thinkingSteps: {
                  understanding: true,
                  searchingRAG: true,
                  searchingKG: false,
                  generating: false
                }
              }
            }
            return updated
          })
        }, 400)

        // Searching KG completes after 700ms
        setTimeout(() => {
          setMessages(prev => {
            const updated = [...prev]
            const msgIndex = updated.length - 1
            if (updated[msgIndex] && updated[msgIndex].streaming) {
              updated[msgIndex] = {
                ...updated[msgIndex],
                thinkingSteps: {
                  understanding: true,
                  searchingRAG: true,
                  searchingKG: true,
                  generating: false
                }
              }
            }
            return updated
          })
        }, 700)

        // Start generating after 900ms - show spinner
        setTimeout(() => {
          setMessages(prev => {
            const updated = [...prev]
            const msgIndex = updated.length - 1
            if (updated[msgIndex] && updated[msgIndex].streaming && !updated[msgIndex].thinkingComplete) {
              updated[msgIndex] = {
                ...updated[msgIndex],
                thinkingSteps: {
                  understanding: true,
                  searchingRAG: true,
                  searchingKG: true,
                  generating: true // Show spinner here
                }
              }
            }
            return updated
          })
        }, 900)

        for await (const chunk of queryAPI.queryStream(userMessage, sessionId, style, tone)) {
          streamingWorked = true
          
          if (chunk.error) {
            throw new Error(chunk.chunk || 'Streaming error')
          }

          // When first chunk arrives, ensure generating step is marked and hide thinking UI
          if (chunk.chunk && !fullAnswer) {
            // Mark generating step and hide thinking UI immediately when content starts
            setMessages(prev => {
              const updated = [...prev]
              const msgIndex = updated.length - 1
              if (updated[msgIndex] && updated[msgIndex].streaming) {
                updated[msgIndex] = {
                  ...updated[msgIndex],
                  thinkingSteps: {
                    understanding: true,
                    searchingRAG: true,
                    searchingKG: true,
                    generating: true
                  },
                  thinkingComplete: true // Hide thinking UI immediately when content starts
                }
              }
              return updated
            })
          }

          // Process chunk content - immediate updates for smooth streaming
          if (chunk.chunk) {
            fullAnswer += chunk.chunk
            
            // Update immediately - React 18+ handles batching automatically
            setMessages(prev => {
              const updated = [...prev]
              const msgIndex = updated.length - 1
              if (updated[msgIndex] && updated[msgIndex].streaming) {
                updated[msgIndex] = {
                  ...updated[msgIndex],
                  content: fullAnswer,
                  thinkingComplete: true
                }
              }
              return updated
            })
          }

          // Handle completion
          if (chunk.done) {
            finalSessionId = chunk.session_id || finalSessionId
            finalSources = chunk.sources || []
            finalMetadata = chunk.metadata || { method: 'agent_streaming' }
            break
          }
        }
      } catch (streamError) {
        console.warn('Streaming failed, falling back to regular query:', streamError)
        // Fallback to regular query if streaming fails
        if (!streamingWorked || !fullAnswer) {
          const response = await queryAPI.query(userMessage, sessionId, style, tone)
          
          if (response.session_id) {
            finalSessionId = response.session_id
          }
          
          fullAnswer = response.answer || ''
          finalSources = response.sources || []
          finalMetadata = response.metadata || { method: 'agent' }
          
          // Update message with non-streaming response
          setMessages(prev => {
            const updated = [...prev]
            const msgIndex = updated.length - 1
            if (updated[msgIndex]) {
              updated[msgIndex] = {
                ...updated[msgIndex],
                content: fullAnswer,
                streaming: false,
                thinkingComplete: true // Hide thinking UI
              }
            }
            return updated
          })
        }
      }

      // Update final message (only if we got content)
      if (fullAnswer) {
        const cleanAnswer = removeSourcesFromText(fullAnswer)
        const normalizedMetadata = {
          method: finalMetadata.method || 'agent',
          type: finalMetadata.type || 'knowledge_query',
          rag_count: finalMetadata.rag_count ?? 0,
          kg_count: finalMetadata.kg_count ?? 0,
        }

        setMessages(prev => {
          const updated = [...prev]
          const msgIndex = updated.length - 1 // Last message is always the streaming one
          if (updated[msgIndex]) {
            // Create a unique message ID for this message (use existing ID if present)
            const messageId = updated[msgIndex].id || `msg_${Date.now()}_${msgIndex}`
            
            updated[msgIndex] = {
              ...updated[msgIndex],
              id: messageId,
              content: cleanAnswer,
              sources: finalSources,
              metadata: normalizedMetadata,
              streaming: false,
              thinkingComplete: true // Ensure thinking UI is hidden
            }
            
            // Store metadata separately for persistence
            setMessageMetadata(prevMeta => {
              const newMeta = {
                ...prevMeta,
                [messageId]: {
                  rag_count: normalizedMetadata.rag_count,
                  kg_count: normalizedMetadata.kg_count,
                  sources: finalSources,
                  session_id: finalSessionId || sessionId
                }
              }
              // Persist to localStorage
              try {
                localStorage.setItem('message_metadata', JSON.stringify(newMeta))
              } catch (e) {
                console.error('Failed to save message metadata to localStorage:', e)
              }
              return newMeta
            })
          } else {
            console.error('Message index not found:', msgIndex, 'Total messages:', updated.length)
          }
          return updated
        })
      }

      if (finalSessionId && finalSessionId !== sessionId) {
        setSessionId(finalSessionId)
        localStorage.setItem('session_id', finalSessionId)
      }
      
      // Reload chat history after sending message
      setTimeout(() => {
        loadChatHistory()
      }, 500)
    } catch (error) {
      console.error('Query failed:', error)
      
      // Update error message
      setMessages(prev => {
        const updated = [...prev]
        const msgIndex = updated.length - 1 // Last message is always the streaming one
        if (updated[msgIndex]) {
          updated[msgIndex] = {
            ...updated[msgIndex],
            content: `Error: ${error.message || 'Failed to get response'}`,
            error: true,
            streaming: false
          }
        }
        return updated
      })
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setSessionId(null)
    localStorage.removeItem('session_id')
    setShowSourcesForMessage({})
    inputRef.current?.focus()
  }
  
  const toggleSourcesForMessage = (messageIndex) => {
    setShowSourcesForMessage(prev => ({
      ...prev,
      [messageIndex]: !prev[messageIndex]
    }))
  }

  const handleDeleteChat = async () => {
    if (window.confirm('Are you sure you want to delete this chat?')) {
      if (sessionId) {
        try {
          await sessionsAPI.delete(sessionId)
          // Reload history after deletion
          await loadChatHistory()
        } catch (error) {
          console.error('Failed to delete session:', error)
          alert(`Failed to delete chat: ${error.response?.data?.detail || error.message}`)
        }
      }
      handleNewChat()
    }
  }

  const loadSessionMessages = async (sessionIdToLoad) => {
    if (!sessionIdToLoad) {
      setMessages([])
      setSessionId(null)
      return
    }
    
    setLoading(true)
    try {
      console.log('Loading session messages for:', sessionIdToLoad)
      const session = await sessionsAPI.get(sessionIdToLoad)
      console.log('Session loaded:', session)
      if (session && session.messages && session.messages.length > 0) {
        // Convert session messages to chat format
        // The metadata structure from backend: { sources: [...], method: 'hybrid', rag_count: 10, kg_count: 0, ... }
        const formattedMessages = session.messages.map((msg, idx) => {
          // Remove sources from content if it's an assistant message
          let content = msg.content || ''
          if (msg.role === 'assistant') {
            content = removeSourcesFromText(content)
          }
          
          // Extract metadata - handle both structures:
          // 1. Flat structure (from API): { method, rag_count, kg_count, sources, ... }
          // 2. Nested structure (from DB): { answer, sources, intermediate_steps, metadata: { method, rag_count, kg_count, ... } }
          const metadata = msg.metadata || {}
          
          // Debug logging
          if (msg.role === 'assistant') {
            console.log('Loading assistant message metadata:', JSON.stringify(metadata, null, 2))
          }
          
          // Check if metadata is nested (from DB) or flat (from API)
          const isNested = metadata.metadata !== undefined && typeof metadata.metadata === 'object'
          const sourceMetadata = isNested ? metadata.metadata : metadata
          
          // Extract sources - can be in metadata.sources or directly in metadata
          const sources = sourceMetadata.sources || metadata.sources || []
          
          // Extract method, type, rag_count, kg_count - handle both structures
          // Use 'in' operator or !== undefined to check if value exists (including 0 as valid value)
          const extractedMetadata = {
            method: sourceMetadata.method || 'unknown',
            type: sourceMetadata.type || null,  // Intent type (greeting, knowledge_query, etc.)
            rag_count: ('rag_count' in sourceMetadata) ? sourceMetadata.rag_count : 
                      (sourceMetadata.rag_count !== undefined) ? sourceMetadata.rag_count : undefined,
            kg_count: ('kg_count' in sourceMetadata) ? sourceMetadata.kg_count : 
                     (sourceMetadata.kg_count !== undefined) ? sourceMetadata.kg_count : undefined,
          }
          
          // Debug logging for extracted values
          if (msg.role === 'assistant') {
            console.log('Extracted metadata:', JSON.stringify(extractedMetadata, null, 2))
            console.log('Extracted sources count:', sources.length)
          }
          
          // Create a unique message ID - use existing if present, otherwise generate one
          const messageId = msg.id || `msg_${msg.timestamp || Date.now()}_${idx}_${sessionIdToLoad}`
          
          // Try to restore metadata from localStorage if not in database
          let restoredSources = sources
          let restoredMetadata = extractedMetadata
          
          // Check if we have stored metadata for this message
          // First try exact match by messageId, then try to find by session and position
          const storedMeta = messageMetadata[messageId] || 
            Object.values(messageMetadata).find(m => 
              m.session_id === sessionIdToLoad
            )
          
          if (storedMeta && msg.role === 'assistant') {
            restoredSources = storedMeta.sources || sources
            restoredMetadata = {
              ...extractedMetadata,
              rag_count: extractedMetadata.rag_count !== undefined ? extractedMetadata.rag_count : storedMeta.rag_count,
              kg_count: extractedMetadata.kg_count !== undefined ? extractedMetadata.kg_count : storedMeta.kg_count,
            }
          }
          
          return {
            id: messageId,
            role: msg.role,
            content: content,
            sources: restoredSources || [],
            metadata: restoredMetadata || {},
            timestamp: msg.timestamp,
            error: metadata.error || false
          }
        })
        
        // Ensure all messages have required fields
        const validatedMessages = formattedMessages.map((msg, idx) => ({
          id: msg.id || `msg_${msg.timestamp || Date.now()}_${idx}`,
          role: msg.role || 'user',
          content: msg.content || '',
          sources: msg.sources || [],
          metadata: msg.metadata || {},
          timestamp: msg.timestamp,
          error: msg.error || false,
          streaming: false,
          thinkingComplete: true
        }))
        
        setMessages(validatedMessages)
        setSessionId(sessionIdToLoad)
        localStorage.setItem('session_id', sessionIdToLoad)
        setShowSourcesForMessage({})
        console.log('Loaded', formattedMessages.length, 'messages')
      } else {
        console.log('No messages found in session, clearing')
        setMessages([])
        setSessionId(null)
        localStorage.removeItem('session_id')
      }
    } catch (error) {
      console.error('Failed to load session messages:', error)
      // Don't show alert for 404 errors (session not found)
      if (error.response?.status !== 404) {
        alert(`Failed to load chat: ${error.response?.data?.detail || error.message}`)
      }
      // Clear the invalid session
      setMessages([])
      setSessionId(null)
      localStorage.removeItem('session_id')
    } finally {
      setLoading(false)
    }
  }

  const handleWorkspaceChange = (newWorkspaceId) => {
    changeWorkspace(newWorkspaceId)
    setShowWorkspaceDropdown(false)
    handleNewChat() // Clear current chat when switching workspace
  }

  const handleCreateWorkspace = async () => {
    if (!workspaceName.trim()) {
      alert('Please enter a workspace name')
      return
    }
    try {
      await createWorkspace(workspaceName.trim())
      setShowNewWorkspaceModal(false)
      setWorkspaceName('')
      setShowWorkspaceDropdown(false)
    } catch (error) {
      alert(`Failed to create workspace: ${error.message}`)
    }
  }

  // Auto-resize textarea
  const handleInputChange = (e) => {
    setInput(e.target.value)
    const textarea = e.target
    // Reset height to auto to get accurate scrollHeight
    textarea.style.height = 'auto'
    // Calculate new height (min 52px, max 200px)
    const newHeight = Math.min(Math.max(textarea.scrollHeight, 52), 200)
    textarea.style.height = `${newHeight}px`
    // Enable scrolling if content exceeds max height
    if (textarea.scrollHeight > 200) {
      textarea.style.overflowY = 'auto'
    } else {
      textarea.style.overflowY = 'hidden'
    }
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #181818;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #2B2B2B;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #454545;
        }
      `}</style>
      {/* Sidebar */}
      <div className="w-64 text-white flex flex-col flex-shrink-0" style={{ backgroundColor: '#181818' }}>
        {/* New Chat Button */}
        <button
          onClick={handleNewChat}
          className="m-3 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg transition-colors font-medium hover:opacity-80"
          style={{ backgroundColor: '#2B2B2B' }}
        >
          <Plus className="h-4 w-4" />
          New Chat
        </button>

        {/* Workspace Selector */}
        <div className="px-3 mb-2 relative" ref={workspaceDropdownRef}>
          <button
            onClick={() => setShowWorkspaceDropdown(!showWorkspaceDropdown)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors hover:opacity-80"
            style={{ backgroundColor: '#2B2B2B' }}
          >
            <span className="truncate font-medium">{workspaceId}</span>
            <ChevronDown className={`h-4 w-4 transition-transform ${showWorkspaceDropdown ? 'rotate-180' : ''}`} />
          </button>
          
          {showWorkspaceDropdown && (
            <div className="absolute top-full left-3 right-3 mt-1 border rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto" style={{ backgroundColor: '#2B2B2B', borderColor: '#2B2B2B' }}>
              <div className="p-2">
                {workspaces.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-gray-400">No workspaces</div>
                ) : (
                  workspaces.map((ws) => (
                    <button
                      key={ws.workspace_id}
                      onClick={() => handleWorkspaceChange(ws.workspace_id)}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded text-sm transition-colors hover:opacity-80 ${
                        ws.workspace_id === workspaceId ? '' : ''
                      }`}
                      style={{ backgroundColor: ws.workspace_id === workspaceId ? '#2b2b2b' : 'transparent' }}
                    >
                      <span className="truncate">{ws.name || ws.workspace_id}</span>
                      {ws.workspace_id === workspaceId && (
                        <Check className="h-4 w-4 text-blue-400 flex-shrink-0 ml-2" />
                      )}
                    </button>
                  ))
                )}
                <div className="border-t border-gray-700 mt-2 pt-2">
                  <button
                    onClick={() => {
                      setShowWorkspaceDropdown(false)
                      setShowNewWorkspaceModal(true)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded hover:bg-gray-700 text-sm transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    Create New Workspace
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Chat History */}
        <div 
          className="flex-1 overflow-y-auto px-3 py-2 min-h-0 custom-scrollbar"
          style={{
            scrollbarWidth: 'thin',
            scrollbarColor: '#303030 #181818'
          }}
        >
          <div className="flex items-center justify-between px-3 mb-2">
            <div className="text-xs font-semibold text-gray-400 uppercase">
              Recent Chats ({chatHistory.filter(c => !c.workspace_id || c.workspace_id === workspaceId).length})
            </div>
            {chatHistory.filter(c => !c.workspace_id || c.workspace_id === workspaceId).length > 0 && (
              <button
                onClick={async () => {
                  const currentWorkspaceChats = chatHistory.filter(c => !c.workspace_id || c.workspace_id === workspaceId)
                  if (window.confirm(`Delete all ${currentWorkspaceChats.length} chats in this workspace? This cannot be undone.`)) {
                    try {
                      const deletePromises = currentWorkspaceChats
                        .filter(chat => chat.id)
                        .map(chat => sessionsAPI.delete(chat.id).catch(e => {
                          console.error(`Failed to delete session ${chat.id}:`, e)
                          return null
                        }))
                      
                      await Promise.all(deletePromises)
                      // Reload history after deletion
                      await loadChatHistory()
                      if (sessionId) {
                        handleNewChat()
                      }
                    } catch (error) {
                      alert(`Failed to delete history: ${error.message}`)
                    }
                  }
                }}
                className="text-xs text-gray-400 hover:text-red-400 transition-colors"
                title="Delete all in this workspace"
              >
                Clear All
              </button>
            )}
          </div>
          <div className="space-y-1">
            {chatHistory.length === 0 ? (
              <p className="text-gray-400 text-sm px-3 py-2">No chat history</p>
            ) : (
              <>
                {/* Current workspace chats */}
                {chatHistory.filter(c => !c.workspace_id || c.workspace_id === workspaceId).length === 0 ? (
                  <p className="text-gray-400 text-sm px-3 py-2">No chats in this workspace</p>
                ) : (
                  chatHistory
                    .filter(c => !c.workspace_id || c.workspace_id === workspaceId)
                    .map((chat, idx) => (
                      <div
                        key={chat.id || idx}
                        className={`group px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-colors relative hover:opacity-80 ${
                          chat.id === sessionId ? '' : ''
                        }`}
                        style={{ backgroundColor: chat.id === sessionId ? '#2b2b2b' : 'transparent' }}
                        onClick={async () => {
                          if (chat.id && chat.id !== sessionId) {
                            setSessionId(chat.id)
                            await loadSessionMessages(chat.id)
                          } else if (chat.id === sessionId) {
                            // Already viewing this chat, just reload messages
                            await loadSessionMessages(chat.id)
                          }
                        }}
                        title={chat.title}
                      >
                        <div className="truncate font-medium pr-8">{chat.title}</div>
                        <div className="flex items-center gap-2 mt-0.5">
                          {chat.messageCount > 0 && (
                            <div className="text-xs text-gray-500">{chat.messageCount} messages</div>
                          )}
                          {chat.timestamp && (
                            <div className="text-xs text-gray-600">
                              {new Date(chat.timestamp).toLocaleDateString()}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={async (e) => {
                            e.stopPropagation()
                            if (window.confirm('Delete this chat? This cannot be undone.')) {
                              try {
                                if (chat.id) {
                                  await sessionsAPI.delete(chat.id)
                                  // Reload history instead of just filtering
                                  await loadChatHistory()
                                  if (chat.id === sessionId) {
                                    handleNewChat()
                                  }
                                }
                              } catch (error) {
                                alert(`Failed to delete: ${error.message}`)
                              }
                            }
                          }}
                          className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-400 transition-opacity"
                          title="Delete chat"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    ))
                )}
                
                {/* Other workspace chats (collapsed) */}
                {chatHistory.filter(c => c.workspace_id && c.workspace_id !== workspaceId).length > 0 && (
                  <div className="mt-4 pt-4" style={{ borderTop: '1px solid #454545' }}>
                    <div className="text-xs font-semibold text-gray-400 uppercase px-3 mb-2">
                      Other Workspaces ({chatHistory.filter(c => c.workspace_id && c.workspace_id !== workspaceId).length})
                    </div>
                    {chatHistory
                      .filter(c => c.workspace_id && c.workspace_id !== workspaceId)
                      .slice(0, 5)
                      .map((chat, idx) => (
                        <div
                          key={chat.id || `other-${idx}`}
                          className="px-3 py-2 rounded-lg text-xs text-gray-500 opacity-75"
                          title={`Workspace: ${chat.workspace_id}`}
                        >
                          <div className="truncate">{chat.title}</div>
                          <div className="text-xs text-gray-600 mt-0.5">{chat.workspace_id}</div>
                        </div>
                      ))
                    }
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Account Section */}
        <div className="p-3 flex-shrink-0" style={{ borderTop: '1px solid #454545' }}>
          <div className="flex items-center gap-2 mb-2">
            <Link to="/account" className="flex-1">
              <button className="w-full px-3 py-2 rounded text-sm transition-colors flex items-center justify-center gap-2 hover:opacity-80" style={{ backgroundColor: '#2b2b2b' }}>
                <Settings className="h-4 w-4" />
                Account
              </button>
            </Link>
            <Link to="/dashboard">
              <button className="px-3 py-2 rounded text-sm transition-colors hover:opacity-80" style={{ backgroundColor: '#2b2b2b' }} title="Dashboard">
                <Network className="h-4 w-4" />
              </button>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-3 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Knowledge Graph Assistant</h1>
              <p className="text-xs text-gray-500">Workspace: {workspaceId}</p>
            </div>
            <div className="flex items-center gap-2">
              <StyleSelector
                style={style}
                onChange={(newStyle) => {
                  setStyle(newStyle)
                  localStorage.setItem('chat_style', newStyle)
                }}
              />
              <ToneSelector
                tone={tone}
                onChange={(newTone) => {
                  setTone(newTone)
                  localStorage.setItem('chat_tone', newTone)
                }}
              />
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-2 sm:px-3 py-6 min-h-0">
          {messages.length === 0 ? (
            <div className="max-w-4xl mx-auto mt-12">
              <div className="text-center mb-8">
                <Network className="h-16 w-16 mx-auto text-gray-400 mb-4" />
                <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                  Welcome to Knowledge Graph Assistant
                </h2>
                <p className="text-gray-600 mb-8">
                  Ask questions about your knowledge base, explore concepts, or request scripts.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div 
                  onClick={() => inputRef.current?.focus()}
                  className="p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 cursor-pointer transition-all"
                >
                  <MessageCircle className="h-6 w-6 text-blue-600 mb-2" />
                  <h3 className="font-medium mb-1">Ask Questions</h3>
                  <p className="text-sm text-gray-600">Query your knowledge graph</p>
                </div>
                <Link to="/scripts" className="p-4 border border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 cursor-pointer transition-all block">
                  <FileText className="h-6 w-6 text-green-600 mb-2" />
                  <h3 className="font-medium mb-1">Generate Scripts</h3>
                  <p className="text-sm text-gray-600">Create tapestry-style scripts</p>
                </Link>
                <Link to="/explore" className="p-4 border border-gray-200 rounded-lg hover:border-purple-500 hover:bg-purple-50 cursor-pointer transition-all block">
                  <Network className="h-6 w-6 text-purple-600 mb-2" />
                  <h3 className="font-medium mb-1">Explore Graph</h3>
                  <p className="text-sm text-gray-600">Navigate relationships</p>
                </Link>
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto">
              {messages.map((msg, idx) => (
                <ChatMessage
                  key={idx}
                  message={msg}
                  showSources={showSourcesForMessage[idx] || false}
                  onToggleSources={() => toggleSourcesForMessage(idx)}
                />
              ))}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area - Fixed at Bottom */}
        <div className="bg-white border-t border-gray-200 px-2 sm:px-3 py-4 flex-shrink-0">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto">
            <div className="relative">
              <div className="relative flex items-end">
                <Link
                  to="/upload"
                  className="absolute left-2.5 bottom-2.5 p-2 text-black hover:text-gray-700 transition-colors flex items-center justify-center"
                  style={{ bottom: '10px' }}
                  title="Upload Transcripts"
                >
                  <Plus className="h-5 w-5" />
                </Link>
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSend(e)
                    }
                  }}
                  placeholder="Ask a question about your knowledge graph..."
                  rows={1}
                  className="w-full px-12 py-3 pr-14 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  style={{ minHeight: '52px', maxHeight: '200px', overflowY: 'auto' }}
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  className="absolute right-2.5 bottom-2.5 p-2 text-white rounded-lg hover:opacity-90 disabled:bg-gray-300 disabled:cursor-not-allowed disabled:opacity-50 transition-all flex items-center justify-center shadow-sm"
                  style={{ bottom: '10px', backgroundColor: '#2b2b2b' }}
                  title="Send message (Enter)"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between mt-2 px-1">
              <span className="text-xs text-gray-400">Press Enter to send, Shift+Enter for new line</span>
              <span className="text-xs text-gray-400">{input.length} characters</span>
            </div>
          </form>
        </div>
      </div>

      {/* New Workspace Modal */}
      {showNewWorkspaceModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-xl">
            <h2 className="text-xl font-bold mb-4">Create New Workspace</h2>
            <input
              type="text"
              placeholder="Workspace name"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleCreateWorkspace()}
              className="w-full px-4 py-2 border border-gray-300 rounded-md mb-4 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autoFocus
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowNewWorkspaceModal(false)
                  setWorkspaceName('')
                }}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateWorkspace}
                disabled={!workspaceName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
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
