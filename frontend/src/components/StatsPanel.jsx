function StatsPanel({ stats }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
      <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
        Summary Statistics
      </h2>
      <div className="space-y-4">
        {stats.map((stat, index) => (
          <div 
            key={index}
            className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 transition-colors"
          >
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {stat.label}
            </div>
            <div className="text-xl font-bold mt-2 text-gray-900 dark:text-white">
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default StatsPanel
