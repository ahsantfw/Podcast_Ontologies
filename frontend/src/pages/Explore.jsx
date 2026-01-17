import { useState } from 'react'
import { graphAPI } from '../services/api'
import { Search, Network, Loader, ArrowRight } from 'lucide-react'

export default function Explore() {
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [concepts, setConcepts] = useState([])
  const [selectedConcept, setSelectedConcept] = useState(null)
  const [loading, setLoading] = useState(false)
  const [conceptLoading, setConceptLoading] = useState(false)

  const handleSearch = async () => {
    if (searchQuery.length < 2) {
      setConcepts([])
      return
    }

    setLoading(true)
    try {
      // Limit results to 20 for better performance
      const data = await graphAPI.getConcepts(searchQuery, typeFilter || null, 20)
      setConcepts(data || [])
    } catch (error) {
      console.error('Search failed:', error)
      alert(`Search failed: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleConceptClick = async (conceptId) => {
    setConceptLoading(true)
    setSelectedConcept(null)
    try {
      const data = await graphAPI.getConcept(conceptId)
      setSelectedConcept(data)
    } catch (error) {
      console.error('Failed to load concept:', error)
      alert(`Failed to load concept: ${error.message}`)
    } finally {
      setConceptLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Search & Concept List */}
      <div className="lg:col-span-1 space-y-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Search Concepts</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search by theme or concept name
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Type at least 2 characters..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  onClick={handleSearch}
                  disabled={loading || searchQuery.length < 2}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {loading ? (
                    <Loader className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by Type
              </label>
              <select
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value)
                  if (searchQuery.length >= 2) {
                    handleSearch()
                  }
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Types</option>
                <option value="Concept">Concept</option>
                <option value="Practice">Practice</option>
                <option value="Outcome">Outcome</option>
                <option value="CognitiveState">Cognitive State</option>
                <option value="Person">Person</option>
              </select>
            </div>
          </div>
        </div>

        {/* Concept List */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Concepts</h2>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {concepts.length === 0 ? (
              <p className="text-gray-500 text-center py-8 text-sm">
                {searchQuery.length < 2
                  ? 'Type at least 2 characters to search'
                  : 'No concepts found'}
              </p>
            ) : (
              concepts.map((concept) => (
                <div
                  key={concept.id}
                  onClick={() => handleConceptClick(concept.id)}
                  className="p-3 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 cursor-pointer transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900 text-sm">
                        {concept.name || concept.id}
                      </h3>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                          {concept.type || 'Unknown'}
                        </span>
                        {concept.episode_ids && concept.episode_ids.length > 0 && (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                            {concept.episode_ids.length} episodes
                          </span>
                        )}
                      </div>
                      {concept.description && (
                        <p className="text-xs text-gray-600 mt-2 line-clamp-2">
                          {concept.description}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Concept Details */}
      <div className="lg:col-span-2">
        {selectedConcept ? (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {selectedConcept.name || selectedConcept.id}
                </h2>
                <span className="inline-block mt-2 px-3 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                  {selectedConcept.type || 'Unknown'}
                </span>
              </div>
              <button
                onClick={() => {
                  // TODO: Implement graph exploration
                  alert('Graph exploration coming soon')
                }}
                className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
              >
                <Network className="h-4 w-4 mr-2" />
                Explore Graph
              </button>
            </div>

            {selectedConcept.description && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Description</h3>
                <p className="text-gray-700">{selectedConcept.description}</p>
              </div>
            )}

            {selectedConcept.episode_ids && selectedConcept.episode_ids.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Appears in Episodes ({selectedConcept.episode_ids.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {selectedConcept.episode_ids.map((ep, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-gray-100 text-gray-700 rounded text-sm"
                    >
                      {ep}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedConcept.relationships && selectedConcept.relationships.length > 0 ? (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Relationships ({selectedConcept.relationships.length})
                  </h3>
                  {selectedConcept.relationships.length > 10 && (
                    <span className="text-xs text-gray-500">
                      Showing first 10 of {selectedConcept.relationships.length}
                    </span>
                  )}
                </div>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {selectedConcept.relationships.slice(0, 10).map((rel, idx) => (
                    <div
                      key={idx}
                      className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-all"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2 flex-1 min-w-0">
                          <span className="font-medium text-gray-900 truncate">
                            {selectedConcept.name || selectedConcept.id}
                          </span>
                          <ArrowRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                          <button
                            onClick={() => handleConceptClick(rel.target_id)}
                            className="font-medium text-blue-600 hover:text-blue-800 truncate"
                            title={rel.target_name || rel.target_id}
                          >
                            {rel.target_name || rel.target_id}
                          </button>
                        </div>
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-medium flex-shrink-0 ml-2">
                          {rel.relationship_type}
                        </span>
                      </div>
                      {rel.description && (
                        <p className="text-sm text-gray-600 mt-2 line-clamp-2">{rel.description}</p>
                      )}
                      <div className="mt-2">
                        <span className="text-xs text-gray-500">
                          Type: {rel.target_type || 'Unknown'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                No relationships found
              </div>
            )}
          </div>
        ) : conceptLoading ? (
          <div className="bg-white rounded-lg shadow p-6 flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <Loader className="h-8 w-8 animate-spin mx-auto mb-2 text-blue-600" />
              <p className="text-gray-600">Loading concept...</p>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-6 flex items-center justify-center min-h-[400px]">
            <div className="text-center text-gray-400">
              <Network className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p>Select a concept to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

