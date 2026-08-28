import { useEffect, useState } from 'react'

import './App.css'

type Connection = {
  connected: boolean
  email: string | null
}

type Screen = 'home' | 'connect'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

function screenFromLocation(): Screen {
  return window.location.hash === '#connect' ? 'connect' : 'home'
}

function App() {
  const [screen, setScreen] = useState<Screen>(screenFromLocation)

  useEffect(() => {
    const syncScreen = () => setScreen(screenFromLocation())

    window.addEventListener('hashchange', syncScreen)
    window.addEventListener('popstate', syncScreen)

    return () => {
      window.removeEventListener('hashchange', syncScreen)
      window.removeEventListener('popstate', syncScreen)
    }
  }, [])

  const navigateTo = (nextScreen: Screen) => {
    const nextHash = nextScreen === 'connect' ? '#connect' : ''

    if (window.location.hash !== nextHash) {
      window.history.pushState(
        {},
        '',
        `${window.location.pathname}${window.location.search}${nextHash}`,
      )
    }

    setScreen(nextScreen)
  }

  if (screen === 'connect') {
    return <GoogleConnectionPage onBack={() => navigateTo('home')} />
  }

  return <LandingPage onStart={() => navigateTo('connect')} />
}

function LogoMark() {
  return (
    <span className="logo-mark" aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  )
}

function LandingPage({ onStart }: { onStart: () => void }) {
  return (
    <div className="site-shell">
      <header className="site-header">
        <a className="brand" href="/">
          <LogoMark />
          <span>private knowledge worker</span>
        </a>

        <div className="header-note">
          <span className="status-dot" aria-hidden="true" />
          <span>Read-only by design</span>
        </div>
      </header>

      <main>
        <section className="hero-section">
          <div className="hero-copy">
            <p className="eyebrow">Your documents, in conversation</p>
            <h1>Ask better questions of the knowledge you already have.</h1>
            <p className="hero-description">
              A private workspace for exploring your own Google Docs. Choose the
              folders that matter, ask in plain language, and follow every
              answer back to its source.
            </p>

            <div className="hero-actions">
              <button
                className="button button-primary"
                type="button"
                onClick={onStart}
              >
                <span>Start with your knowledge</span>
                <span className="button-arrow" aria-hidden="true">
                  ↗
                </span>
              </button>
              <span className="action-note">No tour. Just your workspace.</span>
            </div>
          </div>

          <KnowledgePreview />
        </section>

        <section
          className="principles-section"
          aria-labelledby="principles-title"
        >
          <div className="section-intro">
            <p className="eyebrow">A calmer way to work</p>
            <h2 id="principles-title">Useful before it is impressive.</h2>
          </div>

          <div className="principles-grid">
            <article className="principle-card">
              <span className="principle-number">01</span>
              <h3>Choose your folders</h3>
              <p>
                Bring in only the parts of Google Drive you want to think with.
              </p>
            </article>
            <article className="principle-card principle-card-accent">
              <span className="principle-number">02</span>
              <h3>Ask in plain language</h3>
              <p>Start with the question, not a complicated search query.</p>
            </article>
            <article className="principle-card">
              <span className="principle-number">03</span>
              <h3>See the source</h3>
              <p>
                Keep the document trail close so every answer stays grounded.
              </p>
            </article>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <span>Private knowledge worker</span>
        <span>Built around your own Google Docs</span>
      </footer>
    </div>
  )
}

function KnowledgePreview() {
  return (
    <div className="knowledge-preview" aria-label="Workspace preview">
      <div className="preview-topbar">
        <span className="preview-breadcrumb">workspace / untitled</span>
        <span className="preview-lock">private</span>
      </div>

      <div className="preview-body">
        <aside className="preview-sidebar">
          <span className="preview-label">your sources</span>
          <div className="source-list">
            <span className="source-item source-item-active">
              <span className="folder-icon" aria-hidden="true" />
              Research
            </span>
            <span className="source-item">
              <span className="folder-icon" aria-hidden="true" />
              Projects
            </span>
            <span className="source-item">
              <span className="folder-icon" aria-hidden="true" />
              Meeting notes
            </span>
          </div>
          <span className="preview-sidebar-footer">3 folders connected</span>
        </aside>

        <div className="preview-answer">
          <span className="preview-label">a question for your workspace</span>
          <p className="preview-question">
            What did we decide about the launch?
          </p>
          <div className="answer-line" aria-hidden="true" />
          <span className="preview-label">source trail</span>
          <p className="preview-result">
            The launch is planned for the second week of May, with a smaller
            private beta starting two weeks earlier.
          </p>
          <div className="source-trail">
            <span className="trail-node trail-node-folder" aria-hidden="true" />
            <span className="trail-line" aria-hidden="true" />
            <span
              className="trail-node trail-node-document"
              aria-hidden="true"
            />
            <span>Launch notes / April 18</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function GoogleConnectionPage({ onBack }: { onBack: () => void }) {
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
        const healthResponse = await fetch(`${API_BASE}/health`, {
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
          `${API_BASE}/auth/google/status`,
          { credentials: 'include' },
        )

        if (!cancelled) {
          setConnection(
            connectionResponse.ok
              ? await connectionResponse.json()
              : { connected: false, email: null },
          )
        }
      } catch {
        if (!cancelled) {
          setConnection({ connected: false, email: null })
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
      const response = await fetch(`${API_BASE}/auth/google`, {
        method: 'DELETE',
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Disconnect failed')
      }

      setConnection({ connected: false, email: null })
    } catch {
      setError('Unable to disconnect Google.')
    } finally {
      setDisconnecting(false)
    }
  }

  const isConnected = connection?.connected === true

  return (
    <div className="setup-shell">
      <header className="site-header setup-header">
        <button className="brand brand-button" type="button" onClick={onBack}>
          <LogoMark />
          <span>private knowledge worker</span>
        </button>
        <span className="setup-progress">setup / 01</span>
      </header>

      <main className="setup-main">
        <button className="back-link" type="button" onClick={onBack}>
          <span aria-hidden="true">←</span>
          Back to overview
        </button>

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
                  <span className="status-dot" aria-hidden="true" />
                  <span>Connected</span>
                </div>
                <strong>{connection.email}</strong>
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
                href={`${API_BASE}/auth/google`}
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

export default App
