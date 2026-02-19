import { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import Houses from './pages/Houses'
import Assistant from './pages/Assistant'

function App() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode')
    if (!saved) return false
    try {
      const parsed = JSON.parse(saved)
      return typeof parsed === 'boolean' ? parsed : false
    } catch {
      return false
    }
  })

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode))
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  const toggleDarkMode = () => setDarkMode(!darkMode)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/houses" element={<Houses />} />
        <Route path="/assistant" element={<Assistant />} />
      </Routes>
    </div>
  )
}

export default App
