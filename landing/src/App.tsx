
import './index.css'

// ── APK Download Configuration ──
const APK_DOWNLOAD_URL = 'https://github.com/TirthC27/Nexaris/releases/latest/download/Nexaris.apk';

function App() {
  return (
    <>
      {/* ═══════ NAVBAR ═══════ */}
      <nav className="navbar">
        <div className="navbar-brand">
          <div className="logo-icon">N</div>
          Nexaris
        </div>
        <div className="navbar-links">
          <a href="#features">Features</a>
          <a href="#how-it-works">How It Works</a>
          <a href="#architecture">Architecture</a>
          <a href="#download">Download</a>
        </div>
        <div className="navbar-cta">
          <a
            href="/dashboard"
            className="btn btn-outline"
          >
            <span className="btn-icon">🔬</span>
            Researcher Dashboard
          </a>
          <a
            className="btn btn-primary btn-glow"
            href={APK_DOWNLOAD_URL}
            download="Nexaris.apk"
          >
            <span className="btn-icon">🤖</span>
            Download APK
          </a>
        </div>
      </nav>

      {/* ═══════ HERO ═══════ */}
      <section className="hero">
        <div className="hero-bg">
          <div className="hero-grid" />
        </div>
        <div className="hero-content">
          <div className="hero-badge">
            <span className="pulse-dot" />
            Network Active on Solana Devnet
          </div>
          <h1>
            Contribute Compute.
            <br />
            <span className="gradient-text">Advance Science.</span>
          </h1>
          <p className="subtitle">
            Nexaris is a decentralized scientific compute network. Your idle
            Android device can power real scientific workloads — Monte Carlo
            simulations, matrix computations, and statistical analysis — while
            earning on-chain rewards.
          </p>
          <div className="hero-actions">
            <a
              className="btn btn-primary btn-large btn-glow"
              href={APK_DOWNLOAD_URL}
              download="Nexaris.apk"
            >
              <span className="btn-icon android-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.523 15.341c-.583 0-1.055-.476-1.055-1.063s.473-1.063 1.055-1.063 1.055.476 1.055 1.063-.472 1.063-1.055 1.063m-11.046 0c-.583 0-1.055-.476-1.055-1.063s.473-1.063 1.055-1.063 1.055.476 1.055 1.063-.472 1.063-1.055 1.063m11.4-6.02l1.91-3.31c.11-.19.045-.433-.145-.542-.19-.11-.433-.045-.542.145l-1.934 3.35C15.56 8.17 13.846 7.68 12 7.68s-3.56.49-5.166 1.284L4.9 5.614c-.11-.19-.353-.255-.543-.145-.19.11-.255.353-.145.542l1.91 3.31C2.92 11.16.536 14.572.001 18.595h23.998c-.535-4.023-2.92-7.435-6.122-9.274" />
                </svg>
              </span>
              Download Android APK
            </a>
            <a
              href="/dashboard"
              className="btn btn-secondary btn-large"
            >
              <span className="btn-icon">🔬</span>
              Researcher Dashboard
            </a>
            <a
              href="https://github.com/TirthC27/Nexaris"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-ghost btn-large"
            >
              <span className="btn-icon">⭐</span>
              Star on GitHub
            </a>
          </div>
          <div className="hero-stats">
            <div className="hero-stat">
              <div className="value">3</div>
              <div className="label">Compute Templates</div>
            </div>
            <div className="hero-stat">
              <div className="value">2x</div>
              <div className="label">Duplicate Validation</div>
            </div>
            <div className="hero-stat">
              <div className="value">∞</div>
              <div className="label">Scalable Workers</div>
            </div>
            <div className="hero-stat">
              <div className="value">SOL</div>
              <div className="label">Reward Token</div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ FEATURES ═══════ */}
      <section className="section" id="features">
        <div className="section-header">
          <div className="section-label">✦ Core Capabilities</div>
          <h2 className="section-title">Built for Verifiable Science</h2>
          <p className="section-desc">
            Every computation is deterministic, every result is validated through
            duplicate execution, and every reward is settled on Solana.
          </p>
        </div>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon lime">🧬</div>
            <h3>Deterministic Compute</h3>
            <p>
              Monte Carlo, Matrix Multiplication, and Dataset Statistics —
              all seeded for bit-perfect reproducibility across any device.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon purple">🔐</div>
            <h3>Trustless Verification</h3>
            <p>
              Every task is executed by 2+ independent workers. Results are
              HMAC-SHA256 signed and cross-validated before acceptance.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon green">🤖</div>
            <h3>MCP Incentive Engine</h3>
            <p>
              An autonomous AI engine monitors network health, detects worker
              shortages, and dynamically adjusts reward multipliers in
              real-time.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon orange">💰</div>
            <h3>On-Chain Treasury</h3>
            <p>
              Solana-based treasury with transparent fund management.
              Deposits, disbursements, and contributor rewards — all
              verifiable on-chain.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon lime">📱</div>
            <h3>Mobile-First Workers</h3>
            <p>
              Native Android app built with Jetpack Compose and Hilt DI.
              Background compute via WorkManager with encrypted JWT storage
              and heartbeat monitoring.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon purple">📊</div>
            <h3>Research Dashboard</h3>
            <p>
              Full-featured React dashboard for researchers to create jobs,
              monitor progress, view leaderboards, and manage campaign
              incentives.
            </p>
          </div>
        </div>
      </section>

      {/* ═══════ HOW IT WORKS ═══════ */}
      <section className="section" id="how-it-works">
        <div className="section-header">
          <div className="section-label">⚡ How It Works</div>
          <h2 className="section-title">From Idle Phone to Scientific Breakthroughs</h2>
          <p className="section-desc">
            A 4-step pipeline that turns any Android device into a
            contributing node in a global scientific compute network.
          </p>
        </div>
        <div className="steps-container">
          <div className="step">
            <div className="step-number">01</div>
            <div className="step-content">
              <h3>Install & Register</h3>
              <p>
                Download the Nexaris Android app, create an account, and
                register your device. Your phone's compute profile is
                fingerprinted and stored on the backend.
              </p>
            </div>
          </div>
          <div className="step">
            <div className="step-number">02</div>
            <div className="step-content">
              <h3>Receive Work Units</h3>
              <p>
                The backend assigns deterministic compute tasks to your
                device — Monte Carlo simulations, matrix operations, or
                dataset aggregations — each with unique seeds.
              </p>
            </div>
          </div>
          <div className="step">
            <div className="step-number">03</div>
            <div className="step-content">
              <h3>Compute & Submit</h3>
              <p>
                Your device executes the work unit locally and submits the
                HMAC-signed result. The server cross-validates against
                duplicate submissions from other workers.
              </p>
            </div>
          </div>
          <div className="step">
            <div className="step-number">04</div>
            <div className="step-content">
              <h3>Earn Rewards</h3>
              <p>
                Validated contributions are scored by the MCP engine based on
                device power, task urgency, and accuracy — then rewarded
                in SOL from the on-chain treasury.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ ARCHITECTURE ═══════ */}
      <section className="section" id="architecture">
        <div className="section-header">
          <div className="section-label">🏗️ Architecture</div>
          <h2 className="section-title">Production-Grade Infrastructure</h2>
          <p className="section-desc">
            Built with FastAPI, PostgreSQL, Redis, and Docker — with
            Prometheus + Grafana observability baked in.
          </p>
        </div>
        <div className="arch-diagram">
          {`┌─────────────────┐       ┌──────────────────────────────┐
│                 │       │                              │
│  `}<span className="highlight">Android App</span>{`    │──────▶│     `}<span className="purple-hl">FastAPI Backend</span>{`           │
│  (Kotlin/Compose)│       │     (Uvicorn + Workers)      │
│                 │       │                              │
└─────────────────┘       └──────┬───────┬───────┬───────┘
                                 │       │       │
                    ┌────────────┘       │       └────────────┐
                    ▼                    ▼                    ▼
           ┌────────────────┐  ┌─────────────────┐  ┌────────────────┐
           │  `}<span className="green-hl">PostgreSQL</span>{`     │  │   `}<span className="highlight">Redis</span>{`          │  │  `}<span className="purple-hl">Torque API</span>{`    │
           │  (Supabase)    │  │   (Task Queue)  │  │  (Campaigns)   │
           └────────────────┘  └─────────────────┘  └────────────────┘
                                       │
                              ┌────────┴────────┐
                              ▼                 ▼
                     ┌──────────────┐   ┌──────────────┐
                     │ `}<span className="highlight">Prometheus</span>{`   │   │  `}<span className="green-hl">Grafana</span>{`     │
                     │ (Metrics)    │   │ (Dashboards) │
                     └──────────────┘   └──────────────┘`}
        </div>

        <div style={{ marginTop: 48 }}>
          <div className="section-header" style={{ marginBottom: 32 }}>
            <div className="section-label">🛠️ Tech Stack</div>
          </div>
          <div className="tech-grid">
            <div className="tech-pill"><span className="tech-icon">🐍</span><div><div className="tech-name">FastAPI</div><div className="tech-role">Backend API</div></div></div>
            <div className="tech-pill"><span className="tech-icon">🐘</span><div><div className="tech-name">PostgreSQL</div><div className="tech-role">Supabase Database</div></div></div>
            <div className="tech-pill"><span className="tech-icon">⚡</span><div><div className="tech-name">Redis</div><div className="tech-role">Queue & Cache</div></div></div>
            <div className="tech-pill"><span className="tech-icon">🤖</span><div><div className="tech-name">Kotlin</div><div className="tech-role">Android (Compose)</div></div></div>
            <div className="tech-pill"><span className="tech-icon">⚛️</span><div><div className="tech-name">React + Vite</div><div className="tech-role">Dashboard</div></div></div>
            <div className="tech-pill"><span className="tech-icon">☀️</span><div><div className="tech-name">Solana</div><div className="tech-role">On-Chain Treasury</div></div></div>
            <div className="tech-pill"><span className="tech-icon">🐳</span><div><div className="tech-name">Docker</div><div className="tech-role">Containerization</div></div></div>
            <div className="tech-pill"><span className="tech-icon">📈</span><div><div className="tech-name">Prometheus</div><div className="tech-role">Monitoring</div></div></div>
          </div>
        </div>
      </section>

      {/* ═══════ DOWNLOAD SECTION ═══════ */}
      <section className="download-section" id="download">
        <div className="download-card">
          <div className="download-content">
            <div className="download-icon-wrap">
              <svg className="android-icon-large" width="64" height="64" viewBox="0 0 24 24" fill="var(--lime)">
                <path d="M17.523 15.341c-.583 0-1.055-.476-1.055-1.063s.473-1.063 1.055-1.063 1.055.476 1.055 1.063-.472 1.063-1.055 1.063m-11.046 0c-.583 0-1.055-.476-1.055-1.063s.473-1.063 1.055-1.063 1.055.476 1.055 1.063-.472 1.063-1.055 1.063m11.4-6.02l1.91-3.31c.11-.19.045-.433-.145-.542-.19-.11-.433-.045-.542.145l-1.934 3.35C15.56 8.17 13.846 7.68 12 7.68s-3.56.49-5.166 1.284L4.9 5.614c-.11-.19-.353-.255-.543-.145-.19.11-.255.353-.145.542l1.91 3.31C2.92 11.16.536 14.572.001 18.595h23.998c-.535-4.023-2.92-7.435-6.122-9.274" />
              </svg>
            </div>
            <h2>Download the Android App</h2>
            <p>
              Turn your idle Android device into a node in the Nexaris
              decentralized scientific compute network. Earn SOL rewards for
              every verified computation.
            </p>

            {/* ── APK Info Pills ── */}
            <div className="apk-info-row">
              <div className="apk-info-pill">
                <span className="apk-info-label">Version</span>
                <span className="apk-info-value">v1.0.0</span>
              </div>
              <div className="apk-info-pill">
                <span className="apk-info-label">Size</span>
                <span className="apk-info-value">~15 MB</span>
              </div>
              <div className="apk-info-pill">
                <span className="apk-info-label">Android</span>
                <span className="apk-info-value">8.0+</span>
              </div>
            </div>

            <div className="download-actions">
              <a
                className="btn btn-primary btn-large btn-glow download-btn-main"
                href={APK_DOWNLOAD_URL}
                download="Nexaris.apk"
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" className="dl-arrow">
                  <path d="M12 16l-5-5 1.41-1.41L11 12.17V4h2v8.17l2.59-2.58L17 11l-5 5z" />
                  <path d="M5 20h14v-2H5v2z" />
                </svg>
                Download Android APK
              </a>
              <a
                href="https://github.com/TirthC27/Nexaris"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary btn-large"
              >
                <span className="btn-icon">📦</span>
                View Source Code
              </a>
            </div>
            <div className="download-meta">
              <span><span className="check">✓</span> No root required</span>
              <span><span className="check">✓</span> Open source</span>
              <span><span className="check">✓</span> Direct download</span>
              <span><span className="check">✓</span> No Play Store needed</span>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ FOOTER ═══════ */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span style={{ fontSize: 24 }}>⚡</span>
            Nexaris
          </div>
          <div className="footer-links">
            <a href="https://github.com/TirthC27/Nexaris" target="_blank" rel="noopener noreferrer">GitHub</a>
            <a href="#features">Features</a>
            <a href="#download">Download</a>
          </div>
          <div className="footer-copy">
            © {new Date().getFullYear()} Nexaris. Built for Decentralized Science.
          </div>
        </div>
      </footer>
    </>
  )
}

export default App
