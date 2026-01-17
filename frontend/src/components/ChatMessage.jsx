import { useState } from 'react'
import { Copy, Check, Eye, EyeOff } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

// Custom components for markdown rendering with proper styling
const MarkdownComponents = {
  // Headings
  h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2 text-gray-900">{children}</h1>,
  h2: ({ children }) => <h2 className="text-lg font-bold mt-3 mb-2 text-gray-900">{children}</h2>,
  h3: ({ children }) => <h3 className="text-base font-semibold mt-2 mb-1 text-gray-900">{children}</h3>,
  
  // Paragraphs
  p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
  
  // Bold and italic
  strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  
  // Lists
  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1 ml-2">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1 ml-2">{children}</ol>,
  li: ({ children }) => <li className="text-gray-800">{children}</li>,
  
  // Code
  code: ({ inline, children }) => {
    if (inline) {
      return <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800">{children}</code>
    }
    return (
      <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto my-2">
        <code className="text-sm font-mono">{children}</code>
      </pre>
    )
  },
  
  // Blockquotes
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-blue-500 pl-4 py-1 my-2 bg-blue-50 rounded-r-lg italic text-gray-700">
      {children}
    </blockquote>
  ),
  
  // Tables - with proper borders and styling
  table: ({ children }) => (
    <div className="overflow-x-auto my-3">
      <table className="min-w-full border border-gray-300 rounded-lg overflow-hidden">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-gray-100">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-gray-200">{children}</tbody>,
  tr: ({ children }) => <tr className="hover:bg-gray-50">{children}</tr>,
  th: ({ children }) => (
    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-300">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-2 text-sm text-gray-800 border-b border-gray-200">
      {children}
    </td>
  ),
  
  // Links
  a: ({ href, children }) => (
    <a href={href} className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  
  // Horizontal rule
  hr: () => <hr className="my-4 border-gray-300" />,
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
      <div className="flex gap-3 justify-end mb-6">
        <div className="max-w-[80%] sm:max-w-[75%] rounded-2xl px-4 py-3 bg-blue-600 text-white shadow-sm">
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
        </div>
        <div className="w-8 h-8 rounded-full bg-gray-500 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
          U
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3 justify-start mb-6">
      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
        AI
      </div>
      <div className="max-w-[80%] sm:max-w-[75%]">
        <div className={`rounded-2xl px-4 py-3 shadow-sm ${
          message.error
            ? 'bg-red-50 text-red-900 border border-red-200'
            : 'bg-white border border-gray-200 text-gray-900'
        }`}>
          {/* Render markdown content */}
          <div className="text-sm leading-relaxed prose prose-sm max-w-none">
            <ReactMarkdown components={MarkdownComponents}>
              {message.content}
            </ReactMarkdown>
          </div>
          
          {/* Action Buttons */}
          {!message.error && (
            <div className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-200">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                title="Copy message"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
              {message.sources && message.sources.length > 0 && (
                <button
                  onClick={onToggleSources}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                  title={showSources ? "Hide sources" : "Show sources"}
                >
                  {showSources ? (
                    <>
                      <EyeOff className="h-3.5 w-3.5" />
                      <span>Hide Sources</span>
                    </>
                  ) : (
                    <>
                      <Eye className="h-3.5 w-3.5" />
                      <span>Sources ({message.sources.length})</span>
                    </>
                  )}
                </button>
              )}
            </div>
          )}

          {/* Sources */}
          {!message.error && showSources && message.sources && message.sources.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="text-xs font-semibold text-gray-700 mb-3 uppercase tracking-wide">Sources</div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {message.sources.slice(0, 5).map((source, sIdx) => (
                  <div key={sIdx} className="text-xs bg-gray-50 p-3 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
                    <div className="font-semibold text-gray-900 mb-1 flex items-center gap-2">
                      <span>{source.episode_id || 'Unknown Episode'}</span>
                      {source.timestamp && (
                        <span className="text-gray-500 font-normal">({source.timestamp})</span>
                      )}
                    </div>
                    {source.speaker && (
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
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          {!message.error && message.metadata && (
            <div className="mt-3 pt-3 border-t border-gray-200 flex items-center gap-3 text-xs">
              <span className={`px-2 py-1 rounded font-medium ${
                message.metadata.method === 'hybrid' ? 'bg-blue-100 text-blue-800' :
                message.metadata.method === 'rag' ? 'bg-green-100 text-green-800' :
                message.metadata.method?.startsWith('direct_') ? 'bg-emerald-100 text-emerald-800' :
                message.metadata.method === 'agent' ? 'bg-violet-100 text-violet-800' :
                'bg-purple-100 text-purple-800'
              }`}>
                {/* Show intent type for agent, otherwise show method */}
                {message.metadata.method === 'agent' 
                  ? (message.metadata.type?.toUpperCase() || 'AGENT')
                  : (message.metadata.method?.toUpperCase().replace('DIRECT_', '') || 'UNKNOWN')
                }
              </span>
              {(message.metadata.rag_count !== undefined && message.metadata.rag_count !== null) && (
                <span className="text-gray-600">RAG: {message.metadata.rag_count}</span>
              )}
              {(message.metadata.kg_count !== undefined && message.metadata.kg_count !== null) && (
                <span className="text-gray-600">KG: {message.metadata.kg_count}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
