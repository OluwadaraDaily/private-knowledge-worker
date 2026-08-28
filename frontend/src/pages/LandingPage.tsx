import { Link } from '@tanstack/react-router'

import { LogoMark } from '../components/LogoMark'

export function LandingPage() {
  return (
    <div className="site-shell">
      <header className="site-header">
        <Link className="brand" to="/">
          <LogoMark />
          <span>private knowledge worker</span>
        </Link>

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
              <Link className="button button-primary" to="/connect">
                <span>Start with your knowledge</span>
                <span className="button-arrow" aria-hidden="true">
                  ↗
                </span>
              </Link>
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
