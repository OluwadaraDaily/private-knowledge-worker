import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [status, setStatus] = useState<
    'checking' | 'available' | 'unavailable'
  >('checking')

  useEffect(() => {
    const controller = new AbortController()
    const apiUrl =
      import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/v1'

    fetch(`${apiUrl}/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Health check failed')
        return response.json()
      })
      .then(() => setStatus('available'))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setStatus('unavailable')
      })

    return () => controller.abort()
  }, [])

  return (
    <main>
      <h1>Private Knowledge Worker</h1>
      <p>Read-only search across your Google Docs.</p>
      <p role="status" aria-live="polite">
        {status === 'checking' && 'Connecting to the backend…'}
        {status === 'available' && 'Backend is available.'}
        {status === 'unavailable' &&
          'Backend is unavailable. Start the API and retry.'}
      </p>
    </main>
  )
}

export default App
