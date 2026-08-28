import { Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'

import { LogoMark } from '../components/LogoMark'

type Connection = {
  connected: boolean
  email: string | null
  driveAccess: 'checking' | 'verified' | 'unavailable'
}

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

export function GoogleConnectionPage() {
  const [backendMessage, setBackendMessage] = useState(
    'Checking your workspace…',
  )
  const [connection, setConnection] = useState<Connection | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [disconnecting, setDisconnecting] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadWorkspaceStatus() {
      try {
        const healthResponse = await fetch(API_BASE + '/health', {
          credentials: 'include',
        })

        if (!cancelled) {
          setBackendMessage(
            healthResponse.ok
              ? 'Your workspace is ready.'
              : 'The workspace service is unavailable.',
          )
        }
      } catch {
        if (!cancelled) {
          setBackendMessage(
            'The workspace service is unavailable. Try again in a moment.',
          )
        }
      }

      try {
        const connectionResponse = await fetch(
          API_BASE + '/auth/google/status',
          { credentials: 'include' },
        )

        if (!cancelled) {
          const connection = connectionResponse.ok
            ? await connectionResponse.json()
            : { connected: false, email: null }
          setConnection({
            ...connection,
            driveAccess: connection.connected ? 'checking' : 'unavailable',
          })

          if (connection.connected) {
            try {
              const verificationResponse = await fetch(
                API_BASE + '/auth/google/verify',
                { credentials: 'include' },
              )
              if (!cancelled) {
                setConnection((current) =>
                  current
                    ? {
                        ...current,
                        driveAccess: verificationResponse.ok
                          ? 'verified'
                          : 'unavailable',
                      }
                    : current,
                )
              }
            } catch {
              if (!cancelled) {
                setConnection((current) =>
                  current
                    ? { ...current, driveAccess: 'unavailable' }
                    : current,
                )
              }
            }
          }
        }
      } catch {
        if (!cancelled) {
          setConnection({
            connected: false,
            email: null,
            driveAccess: 'unavailable',
          })
        }
      }
    }

    void loadWorkspaceStatus()

    return () => {
      cancelled = true
    }
  }, [])

  async function disconnectGoogle() {
    setDisconnecting(true)
    setError(null)

    try {
      const response = await fetch(API_BASE + '/auth/google', {
        method: 'DELETE',
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Disconnect failed')
      }

      setConnection({
        connected: false,
        email: null,
        driveAccess: 'unavailable',
      })
    } catch {
      setError('Unable to disconnect Google.')
    } finally {
      setDisconnecting(false)
    }
  }

  const isConnected = connection?.connected === true
  const isDriveReady = connection?.driveAccess === 'verified'

  return (
    <div className="setup-shell">
      <header className="site-header setup-header">
        <Link className="brand" to="/">
          <LogoMark />
          <span>private knowledge worker</span>
        </Link>
        <span className="setup-progress">setup / 01</span>
      </header>

      <main className="setup-main">
        <Link className="back-link" to="/">
          <span aria-hidden="true">←</span>
          Back to overview
        </Link>

        <div className="setup-layout">
          <section className="setup-intro">
            <p className="eyebrow">First, connect your source</p>
            <h1>Bring your own context.</h1>
            <p className="setup-description">
              Connect the Google account where your knowledge lives. Next,
              you&apos;ll choose the folders your private workspace can read.
            </p>

            <div className="setup-steps" aria-label="Setup progress">
              <div className="setup-step setup-step-active">
                <span>01</span>
                <strong>Connect Google</strong>
              </div>
              <div className="setup-step">
                <span>02</span>
                <strong>Choose folders</strong>
              </div>
              <div className="setup-step">
                <span>03</span>
                <strong>Enter workspace</strong>
              </div>
            </div>
          </section>

          <section
            className="connection-card"
            aria-labelledby="connection-title"
          >
            <div className="connection-card-top">
              <div className="google-badge" aria-hidden="true">
                G
              </div>
              <span className="card-kicker">Source connection</span>
            </div>
            <h2 id="connection-title">Google connection</h2>
            <p>Use the account where your knowledge lives.</p>

            {isConnected ? (
              <div className="connected-account">
                <div className="account-status">
                  <span
                    className={`status-dot${
                      connection.driveAccess === 'unavailable'
                        ? ' status-dot-unavailable'
                        : ''
                    }`}
                    aria-hidden="true"
                  />
                  <span>
                    {isDriveReady
                      ? 'Connected'
                      : connection.driveAccess === 'checking'
                        ? 'Checking Drive access…'
                        : 'Drive access unavailable'}
                  </span>
                </div>
                <strong>{connection.email}</strong>
                {isDriveReady ? (
                  <Link
                    className="button button-dark connection-next-button"
                    to="/folders"
                  >
                    <span>Choose folders</span>
                    <span className="button-arrow" aria-hidden="true">
                      ↗
                    </span>
                  </Link>
                ) : connection.driveAccess === 'checking' ? (
                  <p className="connection-verification-status">
                    Checking Drive access…
                  </p>
                ) : (
                  <a
                    className="button button-dark connection-next-button"
                    href={API_BASE + '/auth/google/start?force_reconsent=true'}
                  >
                    <span>Reconnect Google</span>
                    <span className="button-arrow" aria-hidden="true">
                      ↗
                    </span>
                  </a>
                )}
                <button
                  className="text-button"
                  type="button"
                  onClick={disconnectGoogle}
                  disabled={disconnecting}
                  aria-label="Disconnect Google"
                >
                  {disconnecting ? 'Disconnecting…' : 'Disconnect Google'}
                </button>
              </div>
            ) : (
              <a
                className="button button-dark"
                href={API_BASE + '/auth/google/start'}
              >
                <span>Continue with Google</span>
                <span className="button-arrow" aria-hidden="true">
                  ↗
                </span>
              </a>
            )}

            <div className="card-divider" />
            <p className="privacy-note">
              <span className="lock-icon" aria-hidden="true" />
              Access is read-only. You can review your folder selection later.
            </p>

            <p className="connection-status" role="status">
              {backendMessage}
            </p>
            {error && (
              <p className="error-message" role="alert">
                {error}
              </p>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}
