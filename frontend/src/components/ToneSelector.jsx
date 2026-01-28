import { useState, useRef, useEffect } from 'react'
import { Heart, ChevronDown, Heart as WarmIcon, Minus, User, Rocket, HeartHandshake } from 'lucide-react'

const TONE_OPTIONS = [
  { value: 'warm', label: 'Warm', description: 'Friendly and approachable', icon: WarmIcon },
  { value: 'neutral', label: 'Neutral', description: 'Balanced and objective', icon: Minus },
  { value: 'formal', label: 'Formal', description: 'Reserved and respectful', icon: User },
  { value: 'enthusiastic', label: 'Enthusiastic', description: 'Energetic and excited', icon: Rocket },
  { value: 'supportive', label: 'Supportive', description: 'Empathetic and therapeutic', icon: HeartHandshake },
]

export default function ToneSelector({ tone, onChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const currentTone = TONE_OPTIONS.find(t => t.value === tone) || TONE_OPTIONS[0]

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors bg-white min-w-[140px]"
        title="Change response tone"
      >
        <span className="text-gray-700 flex-1 text-left flex items-center gap-1.5">
          {currentTone.icon && (() => {
            const IconComponent = currentTone.icon
            return <IconComponent className="h-4 w-4" />
          })()}
          {currentTone.label}
        </span>
        <ChevronDown className={`h-4 w-4 text-gray-500 transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-xl z-50 overflow-hidden">
          <div className="p-3 border-b border-gray-200 bg-gray-50">
            <h3 className="font-semibold text-sm text-gray-900">Response Tone</h3>
            <p className="text-xs text-gray-600 mt-0.5">Emotional quality of responses</p>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {TONE_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => {
                  onChange(option.value)
                  setIsOpen(false)
                }}
                className={`w-full flex items-start gap-3 p-3 text-left transition-colors ${
                  tone === option.value
                    ? 'bg-blue-50 border-l-4 border-blue-500'
                    : 'hover:bg-gray-50 border-l-4 border-transparent'
                }`}
              >
                {option.icon && (() => {
                  const IconComponent = option.icon
                  return <IconComponent className="h-5 w-5 text-gray-600 flex-shrink-0 mt-0.5" />
                })()}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-gray-900">{option.label}</div>
                  <div className="text-xs text-gray-600 mt-0.5">{option.description}</div>
                </div>
                {tone === option.value && (
                  <svg className="h-5 w-5 text-blue-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
