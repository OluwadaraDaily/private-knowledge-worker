import { useEffect, useState } from 'react'
import './App.css'

type Connection = {
  connected: boolean
  email: string | null
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/v1'

function App() {
  const [status, setStatus] = useState<
    'checking' | 'available' | 'unavailable'
  >('checking')
  const [connection, setConnection] = useState<Connection | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [disconnecting, setDisconnecting] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    let backendReady = false

    fetch(`${API_URL}/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Health check failed')
        return response.json()
      })
      .then(() => {
        backendReady = true
        setStatus('available')
        return fetch(`${API_URL}/auth/google/status`, {
          credentials: 'include',
          signal: controller.signal,
        })
      })
      .then((response) => {
        if (!response.ok) throw new Error('Connection status failed')
        return response.json() as Promise<Connection>
      })
      .then((data) => {
        setConnection(data)
        setConnectionError(null)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        if (!backendReady) setStatus('unavailable')
        setConnectionError('Unable to load Google connection status.')
      })

    return () => controller.abort()
  }, [])

  async function disconnectGoogle() {
    setDisconnecting(true)
    setConnectionError(null)
    try {
      const response = await fetch(`${API_URL}/auth/google`, {
        method: 'DELETE',
        credentials: 'include',
      })
      if (!response.ok) throw new Error('Disconnect failed')
      setConnection({ connected: false, email: null })
    } catch {
      setConnectionError('Unable to disconnect Google. Please try again.')
    } finally {
      setDisconnecting(false)
    }
  }

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
      {status === 'available' && connection?.connected && (
        <section aria-labelledby="google-connection-heading">
          <h2 id="google-connection-heading">Google connected</h2>
          <p>{connection.email}</p>
          <button
            type="button"
            onClick={disconnectGoogle}
            disabled={disconnecting}
          >
            {disconnecting ? 'Disconnecting…' : 'Disconnect Google'}
          </button>
        </section>
      )}
      {status === 'available' && connection && !connection.connected && (
        <section aria-labelledby="google-connection-heading">
          <h2 id="google-connection-heading">Connect Google</h2>
          <p>Connect your Google account to search your owned Docs.</p>
          <a href={`${API_URL}/auth/google/start`}>Connect Google</a>
        </section>
      )}
      {connectionError && <p role="alert">{connectionError}</p>}
    </main>
  )
}

export default App
