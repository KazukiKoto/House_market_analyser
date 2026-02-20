import { useState, useEffect, useCallback } from 'react'

const PLACEHOLDER_IMAGE = 'data:image/svg+xml,%3Csvg xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22 width%3D%22128%22 height%3D%2296%22 viewBox%3D%220 0 128 96%22%3E%3Crect width%3D%22128%22 height%3D%2296%22 fill%3D%22%23d1d5db%22%2F%3E%3Ctext x%3D%2264%22 y%3D%2252%22 text-anchor%3D%22middle%22 fill%3D%22%236b7280%22 font-size%3D%2212%22%3ENo Image%3C%2Ftext%3E%3C%2Fsvg%3E'

function Houses() {
  const [properties, setProperties] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    on_market: true,
    min_price: '',
    max_price: '',
    min_beds: '',
    max_beds: '',
    min_sqft: '',
    max_sqft: '',
    property_type: '',
    search: ''
  })
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20

  const fetchProperties = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        on_market: filters.on_market,
        limit: 5000
      })
      const response = await fetch(`/api/properties?${params}`)
      if (!response.ok) throw new Error('Failed to fetch properties')
      const data = await response.json()
      setProperties(data)
    } catch (err) {
      console.error('Error fetching properties:', err)
    } finally {
      setLoading(false)
    }
  }, [filters.on_market])

  useEffect(() => {
    fetchProperties()
  }, [fetchProperties])

  const applyFilters = () => {
    setCurrentPage(1)
    fetchProperties()
  }

  const filteredProperties = properties.filter(house => {
    if (filters.min_price && house.price < parseInt(filters.min_price)) return false
    if (filters.max_price && house.price > parseInt(filters.max_price)) return false
    if (filters.min_beds && house.beds < parseInt(filters.min_beds)) return false
    if (filters.max_beds && house.beds > parseInt(filters.max_beds)) return false
    if (filters.min_sqft && house.sqft < parseInt(filters.min_sqft)) return false
    if (filters.max_sqft && house.sqft > parseInt(filters.max_sqft)) return false
    if (filters.property_type && filters.property_type !== '' && house.property_type !== filters.property_type) return false
    if (filters.search && !(house.address?.toLowerCase().includes(filters.search.toLowerCase()) || house.title?.toLowerCase().includes(filters.search.toLowerCase()))) return false
    return true
  })

  const totalPages = Math.ceil(filteredProperties.length / itemsPerPage)
  const paginatedProperties = filteredProperties.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  return (
    <div className="max-w-7xl mx-auto p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Houses for Sale
        </h1>

        {/* Filters */}
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={filters.on_market}
                  onChange={(e) => setFilters({...filters, on_market: e.target.checked})}
                  className="mr-2 w-4 h-4 rounded"
                />
                Currently Listed Only
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Min Price
              </label>
              <input
                type="number"
                value={filters.min_price}
                onChange={(e) => setFilters({...filters, min_price: e.target.value})}
                placeholder="Min price"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Max Price
              </label>
              <input
                type="number"
                value={filters.max_price}
                onChange={(e) => setFilters({...filters, max_price: e.target.value})}
                placeholder="Max price"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Min Bedrooms
              </label>
              <input
                type="number"
                value={filters.min_beds}
                onChange={(e) => setFilters({...filters, min_beds: e.target.value})}
                placeholder="Min beds"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Max Bedrooms
              </label>
              <input
                type="number"
                value={filters.max_beds}
                onChange={(e) => setFilters({...filters, max_beds: e.target.value})}
                placeholder="Max beds"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Min Sqft
              </label>
              <input
                type="number"
                value={filters.min_sqft}
                onChange={(e) => setFilters({...filters, min_sqft: e.target.value})}
                placeholder="Min sqft"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Max Sqft
              </label>
              <input
                type="number"
                value={filters.max_sqft}
                onChange={(e) => setFilters({...filters, max_sqft: e.target.value})}
                placeholder="Max sqft"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Property Type
              </label>
              <select
                value={filters.property_type}
                onChange={(e) => setFilters({...filters, property_type: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="">All Types</option>
                <option value="detached">Detached</option>
                <option value="semi-detached">Semi-Detached</option>
                <option value="terraced">Terraced</option>
                <option value="end-terraced">End-Terraced</option>
                <option value="flat">Flat</option>
                <option value="bungalow">Bungalow</option>
                <option value="maisonette">Maisonette</option>
                <option value="studio">Studio</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Search
              </label>
              <input
                type="text"
                value={filters.search}
                onChange={(e) => setFilters({...filters, search: e.target.value})}
                placeholder="Search address"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
          </div>
          <button
            onClick={applyFilters}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors"
          >
            Apply Filters
          </button>
          <span className="ml-4 text-sm text-gray-600 dark:text-gray-400">
            Showing {filteredProperties.length} of {properties.length} properties
          </span>
        </div>

        {/* Properties List */}
        {loading ? (
          <div className="text-center py-8 text-gray-600 dark:text-gray-400">
            Loading properties...
          </div>
        ) : (
          <>
            <div className="space-y-4 mb-6">
              {paginatedProperties.map((house, idx) => (
                <a
                  key={idx}
                  href={house.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex gap-4 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <img
                    src={(house.images && house.images.length > 0) ? house.images[0] : PLACEHOLDER_IMAGE}
                    alt={house.title || house.address}
                    className="w-32 h-24 object-cover rounded bg-gray-200 dark:bg-gray-600"
                    onError={(e) => { e.target.onerror = null; e.target.src = PLACEHOLDER_IMAGE }}
                  />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                      {house.title || house.address || 'Property'}
                    </h3>
                    <div className="mt-2 text-sm text-gray-600 dark:text-gray-400 space-y-1">
                      <p><span className="font-medium">Price:</span> £{house.price?.toLocaleString() || 'N/A'}</p>
                      <p><span className="font-medium">Bedrooms:</span> {house.beds || 'N/A'}</p>
                      <p><span className="font-medium">Square Footage:</span> {house.sqft?.toLocaleString() || 'N/A'}</p>
                      <p><span className="font-medium">Type:</span> {house.property_type || 'N/A'}</p>
                      <p><span className="font-medium">Address:</span> {house.address || 'N/A'}</p>
                    </div>
                  </div>
                </a>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default Houses
