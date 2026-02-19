import { useState } from 'react'

function ChartsGrid({ charts }) {
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [selectedChart, setSelectedChart] = useState(null)

  const openLightbox = (chart) => {
    setSelectedChart(chart)
    setLightboxOpen(true)
  }

  const closeLightbox = () => {
    setLightboxOpen(false)
    setSelectedChart(null)
  }

  return (
    <>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {charts.map((chart, index) => (
            <div 
              key={index}
              className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 transition-colors"
            >
              <h3 className="text-sm font-medium mb-3 text-gray-900 dark:text-white">
                {chart.title}
              </h3>
              <div className="flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden aspect-square">
                {chart.image ? (
                  <img 
                    src={chart.image} 
                    alt={chart.title}
                    className="w-full h-full object-contain cursor-pointer hover:opacity-90 transition-opacity"
                    onClick={() => openLightbox(chart)}
                  />
                ) : (
                  <div className="text-sm text-gray-400 dark:text-gray-500">
                    No data
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Lightbox Modal */}
      {lightboxOpen && selectedChart && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={closeLightbox}
        >
          <div 
            className="relative max-w-5xl max-h-[90vh] bg-white dark:bg-gray-800 rounded-lg p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={closeLightbox}
              className="absolute top-2 right-2 bg-white dark:bg-gray-700 rounded-lg p-2 shadow-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
              aria-label="Close"
            >
              <svg className="w-6 h-6 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <img 
              src={selectedChart.image} 
              alt={selectedChart.title}
              className="max-w-full max-h-[80vh] object-contain rounded"
            />
            <div className="mt-3 text-center text-gray-900 dark:text-white">
              {selectedChart.title}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default ChartsGrid
