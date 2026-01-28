import { useState } from 'react'
import { Copy, Check, Eye, EyeOff } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

// Custom components for markdown rendering with proper styling
const MarkdownComponents = {
  // Headings - Better spacing and hierarchy
  h1: ({ children }) => <h1 className="text-2xl font-bold mt-6 mb-4 text-gray-900 leading-tight border-b border-gray-200 pb-2">{children}</h1>,
  h2: ({ children }) => <h2 className="text-xl font-bold mt-5 mb-3 text-gray-900 leading-tight">{children}</h2>,
  h3: ({ children }) => <h3 className="text-lg font-semibold mt-4 mb-2 text-gray-900 leading-tight">{children}</h3>,
  h4: ({ children }) => <h4 className="text-base font-semibold mt-3 mb-2 text-gray-900">{children}</h4>,
  
  // Paragraphs - Better spacing and readability
  p: ({ children }) => <p className="mb-4 leading-relaxed text-gray-800">{children}</p>,
  
  // Bold and italic - More prominent
  strong: ({ children }) => <strong className="font-bold text-gray-900">{children}</strong>,
  em: ({ children }) => <em className="italic text-gray-700">{children}</em>,
  
  // Lists - Better spacing and indentation
  ul: ({ children }) => <ul className="list-disc list-outside mb-4 space-y-2 ml-6 text-gray-800">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-outside mb-4 space-y-2 ml-6 text-gray-800">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed pl-1">{children}</li>,
  
  // Code - Better styling
  code: ({ inline, children }) => {
    if (inline) {
      return <code className="bg-gray-100 px-2 py-0.5 rounded text-sm font-mono text-gray-900 border border-gray-200">{children}</code>
    }
    return (
      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto my-4 border border-gray-700">
        <code className="text-sm font-mono leading-relaxed">{children}</code>
      </pre>
    )
  },
  
  // Blockquotes - More prominent
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-blue-500 pl-5 py-2 my-4 bg-blue-50 rounded-r-lg text-gray-800 italic">
      {children}
    </blockquote>
  ),
  
  // Tables - Better borders and styling
  table: ({ children }) => (
    <div className="overflow-x-auto my-4 border border-gray-200 rounded-lg">
      <table className="min-w-full divide-y divide-gray-200">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-gray-100">{children}</thead>,
  tbody: ({ children }) => <tbody className="bg-white divide-y divide-gray-200">{children}</tbody>,
  tr: ({ children }) => <tr className="hover:bg-gray-50 transition-colors">{children}</tr>,
  th: ({ children }) => (
    <th className="px-4 py-3 text-left text-sm font-bold text-gray-900 border-b-2 border-gray-300">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-3 text-sm text-gray-800 border-b border-gray-200">
      {children}
    </td>
  ),
  
  // Links - Better styling
  a: ({ href, children }) => (
    <a href={href} className="text-blue-600 hover:text-blue-800 underline font-medium" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  
  // Horizontal rule - More visible
  hr: () => <hr className="my-6 border-gray-300 border-t-2" />,
  
  // Line breaks
  br: () => <br className="block my-1" />,
}

export default function ChatMessage({ message, showSources = false, onToggleSources }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  if (message.role === 'user') {
    return (
      <div className="flex gap-3 justify-end mb-6 items-start">
        <div className="max-w-2xl rounded-2xl px-4 py-3 text-white shadow-sm" style={{ backgroundColor: '#353535' }}>
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3 justify-start mb-6 items-start">
      <div className="max-w-4xl w-full">
        <div className={`rounded-2xl px-4 py-3 ${
          message.error
            ? 'bg-red-50 text-red-900 border border-red-200'
            : 'bg-gray-50 text-gray-900'
        }`}>
          {/* Thinking Steps UI - Show ONLY when thinking is NOT complete */}
          {message.streaming && message.thinkingSteps && !message.thinkingComplete && (
            <div className="mb-4 space-y-2">
              {/* Understanding Step */}
              <div className="flex items-center gap-2 text-sm">
                {message.thinkingSteps.understanding ? (
                  <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: '#2b2b2b' }}>
                    <Check className="h-3 w-3 text-white" />
                  </div>
                ) : (
                  <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                    <svg className="w-5 h-5 animate-spin text-gray-700" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" fill="none"/>
                    </svg>
                  </div>
                )}
                <span className={message.thinkingSteps.understanding ? 'text-gray-700' : 'text-gray-400'}>
                  Understood the question and identifying how to answer
                </span>
              </div>

              {/* Searching RAG Step */}
              <div className="flex items-center gap-2 text-sm">
                {message.thinkingSteps.searchingRAG ? (
                  <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: '#2b2b2b' }}>
                    <Check className="h-3 w-3 text-white" />
                  </div>
                ) : message.thinkingSteps.understanding ? (
                  <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                    <svg className="w-5 h-5 animate-spin text-gray-700" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" fill="none"/>
                    </svg>
                  </div>
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-300 flex-shrink-0"></div>
                )}
                <span className={message.thinkingSteps.searchingRAG ? 'text-gray-700' : 'text-gray-400'}>
                  Searching in the RAG database for relevant information
                </span>
              </div>

              {/* Searching KG Step */}
              <div className="flex items-center gap-2 text-sm">
                {message.thinkingSteps.searchingKG ? (
                  <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: '#2b2b2b' }}>
                    <Check className="h-3 w-3 text-white" />
                  </div>
                ) : message.thinkingSteps.searchingRAG ? (
                  <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                    <svg className="w-5 h-5 animate-spin text-gray-700" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" fill="none"/>
                    </svg>
                  </div>
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-300 flex-shrink-0"></div>
                )}
                <span className={message.thinkingSteps.searchingKG ? 'text-gray-700' : 'text-gray-400'}>
                  Searching knowledge graph for related concepts and relationships
                </span>
              </div>

              {/* Generating Step */}
              <div className="flex items-center gap-2 text-sm">
                {message.thinkingSteps.generating ? (
                  <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                    <svg className="w-5 h-5 animate-spin text-gray-700" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" fill="none"/>
                    </svg>
                  </div>
                ) : message.thinkingSteps.searchingKG ? (
                  <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                    <svg className="w-5 h-5 animate-spin text-gray-700" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" fill="none"/>
                    </svg>
                  </div>
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-300 flex-shrink-0"></div>
                )}
                <span className={message.thinkingSteps.generating ? 'text-gray-700' : 'text-gray-400'}>
                  Synthesizing answer from retrieved information
                </span>
              </div>
            </div>
          )}

          {/* Render markdown content - Show when thinking is complete OR when not streaming */}
          {(message.thinkingComplete || !message.streaming || !message.thinkingSteps) && (
            <div className="text-sm leading-relaxed prose prose-sm max-w-none min-h-[2rem] prose-headings:font-bold prose-p:mb-4 prose-ul:mb-4 prose-ol:mb-4">
              <ReactMarkdown components={MarkdownComponents}>
                {message.content || ''}
              </ReactMarkdown>
            </div>
          )}
          
          {/* Action Buttons - Only show when message is complete (not streaming) - Aligned with text */}
          {!message.error && !message.streaming && message.content && (
            <div className="flex items-center gap-3 mt-3">
              {/* Copy Icon - No text - 1px outside alignment */}
              <button
                onClick={handleCopy}
                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors -ml-[7px]"
                title="Copy message"
              >
                {copied ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
              
              {/* RAG Count - Always show if available */}
              {message.metadata && (message.metadata.rag_count !== undefined && message.metadata.rag_count !== null) && (
                <span className="text-xs text-gray-600">RAG: {message.metadata.rag_count}</span>
              )}
              
              {/* KG Count - Always show if available */}
              {message.metadata && (message.metadata.kg_count !== undefined && message.metadata.kg_count !== null) && (
                <span className="text-xs text-gray-600">KG: {message.metadata.kg_count}</span>
              )}
              
              {/* Sources Icon - Always show if sources exist */}
              {message.sources && message.sources.length > 0 && (
                <button
                  onClick={onToggleSources}
                  className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                  title={showSources ? "Hide sources" : `Show ${message.sources.length} sources`}
                >
                  {showSources ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              )}
            </div>
          )}

          {/* Sources */}
          {!message.error && showSources && message.sources && message.sources.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="text-xs font-semibold text-gray-700 mb-3 uppercase tracking-wide">Sources ({message.sources.length})</div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {message.sources.map((source, sIdx) => {
                  // Handle transcript sources (RAG)
                  if (source.type === 'transcript' || !source.type) {
                    const episodeName = source.episode_name || source.episode_id || 'Unknown Episode'
                    const confidence = source.confidence !== undefined ? source.confidence : null
                    
                    return (
                      <div key={sIdx} className="text-xs bg-gray-50 p-3 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
                        <div className="font-semibold text-gray-900 mb-1 flex items-center gap-2 flex-wrap">
                          <span>{episodeName}</span>
                          {source.timestamp && (
                            <span className="text-gray-500 font-normal">({source.timestamp})</span>
                          )}
                          {confidence !== null && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium">
                              {Math.round(confidence * 100)}%
                            </span>
                          )}
                        </div>
                        {source.speaker && source.speaker !== 'Unknown Speaker' && (
                          <div className="text-gray-600 mb-1.5">
                            <span className="font-medium">Speaker:</span> {source.speaker}
                          </div>
                        )}
                        {source.text && (
                          <div className="text-gray-700 mt-2 italic text-xs leading-relaxed">
                            "{source.text.substring(0, 250)}{source.text.length > 250 ? '...' : ''}"
                          </div>
                        )}
                      </div>
                    )
                  }
                  
                  // Handle knowledge graph sources
                  if (source.type === 'knowledge_graph') {
                    const confidence = source.confidence !== undefined ? source.confidence : null
                    const episodeNames = source.episode_names && source.episode_names.length > 0 
                      ? source.episode_names 
                      : (source.episode_ids && source.episode_ids.length > 0 
                          ? source.episode_ids.map(id => id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()))
                          : [])
                    
                    return (
                      <div key={sIdx} className="text-xs bg-purple-50 p-3 rounded-lg border border-purple-200 hover:border-purple-300 transition-colors">
                        <div className="font-semibold text-purple-900 mb-1 flex items-center gap-2 flex-wrap">
                          <span className="text-purple-700 font-medium">KG:</span>
                          <span>{source.concept || source.node_type || 'Concept'}</span>
                          {confidence !== null && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-medium">
                              {Math.round(confidence * 100)}%
                            </span>
                          )}
                        </div>
                        {source.description && (
                          <div className="text-purple-700 mb-1.5 text-xs">
                            {source.description}
                          </div>
                        )}
                        {episodeNames.length > 0 && (
                          <div className="text-purple-600 mt-2 text-xs">
                            <span className="font-medium">Episodes:</span> {episodeNames.slice(0, 3).join(', ')}
                            {episodeNames.length > 3 && ` +${episodeNames.length - 3} more`}
                          </div>
                        )}
                      </div>
                    )
                  }
                  
                  // Fallback for unknown source types
                  return (
                    <div key={sIdx} className="text-xs bg-gray-50 p-3 rounded-lg border border-gray-200">
                      <div className="text-gray-700">{JSON.stringify(source)}</div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Response Category Badge - HIDDEN in UI (kept in backend) */}
        </div>
      </div>
    </div>
  )
}
