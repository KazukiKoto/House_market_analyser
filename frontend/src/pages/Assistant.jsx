import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

function Assistant() {
  const [chatHistory, setChatHistory] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const chatEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [chatHistory])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    
    const newHistory = [...chatHistory, { role: 'user', content: userMessage }]
    setChatHistory(newHistory)
    setLoading(true)

    try {
      const response = await fetch('/api/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newHistory })
      })
      
      if (!response.ok) throw new Error('Failed to get response')
      
      const data = await response.json()
      
      if (data.reply) {
        setChatHistory([...newHistory, { role: 'assistant', content: data.reply }])
      }
    } catch (err) {
      console.error('Error:', err)
      setChatHistory([...newHistory, { 
        role: 'assistant', 
        content: 'Sorry, there was an error connecting to the AI assistant.' 
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-4 h-[calc(100vh-120px)] flex flex-col">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md flex flex-col h-full transition-colors">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            AI Property Assistant
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Ask me about properties, e.g., "Show me 3-bedroom houses under £400,000"
          </p>
        </div>

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin">
          {chatHistory.length === 0 && (
            <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
              <p className="text-lg mb-2">👋 Welcome to the AI Property Assistant!</p>
              <p className="text-sm">Ask me anything about the properties in the database.</p>
            </div>
          )}
          
          {chatHistory.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p>{msg.content}</p>
                )}
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={chatEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={sendMessage} className="p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              disabled={loading}
              className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Assistant
