import { useState, useEffect } from 'react'
import StatsPanel from '../components/StatsPanel'
import ChartsGrid from '../components/ChartsGrid'
import RecentListings from '../components/RecentListings'

function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const response = await fetch('/api/dashboard')
        if (!response.ok) throw new Error('Failed to fetch dashboard data')
        const data = await response.json()
        setDashboardData(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-gray-600 dark:text-gray-400">Loading dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-red-600 dark:text-red-400">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="max-w-[1600px] mx-auto p-4">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Stats Panel */}
        <div className="lg:col-span-3">
          <StatsPanel stats={dashboardData?.stats || []} />
        </div>

        {/* Center Charts Grid */}
        <div className="lg:col-span-6">
          <ChartsGrid charts={dashboardData?.charts || []} />
        </div>

        {/* Right Recent Listings */}
        <div className="lg:col-span-3">
          <RecentListings listings={dashboardData?.recent_listings || []} />
        </div>
      </div>
    </div>
  )
}

export default Dashboard
