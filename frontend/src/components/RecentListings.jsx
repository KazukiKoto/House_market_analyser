function RecentListings({ listings }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
      <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
        Recent Listings
      </h2>
      <div className="space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto scrollbar-thin">
        {listings.length > 0 ? (
          listings.map((listing, index) => (
            <a
              key={index}
              href={listing.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <div 
                className="w-16 h-16 flex-shrink-0 rounded bg-gray-200 dark:bg-gray-600 bg-cover bg-center"
                style={{ backgroundImage: `url(${listing.thumb})` }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {listing.addr}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  {listing.price} · {listing.beds} beds · {listing.sqft} sqft
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  {listing.days}
                </div>
              </div>
            </a>
          ))
        ) : (
          <div className="text-sm text-gray-500 dark:text-gray-400">
            No recent listings available.
          </div>
        )}
      </div>
    </div>
  )
}

export default RecentListings
