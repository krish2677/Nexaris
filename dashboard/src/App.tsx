import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Trophy, BarChart3, Database, FileText, Wallet, Swords } from 'lucide-react';
import Overview from './pages/Overview';
import Jobs from './pages/Jobs';
import Leaderboard from './pages/Leaderboard';
import MCPDashboard from './pages/MCPDashboard';
import Datasets from './pages/Datasets';
import ResearchOutputs from './pages/ResearchOutputs';
import CampaignArena from './pages/CampaignArena';
import Treasury from './pages/Treasury';
import LandingPage from '../../landing/src/App';
import { api } from './api';
import { useState } from 'react';

export default function App() {
  return (
    <Routes>
      {/* Public landing page at root */}
      <Route path="/" element={<LandingPage />} />
      {/* Protected dashboard under /dashboard/* */}
      <Route path="/dashboard/*" element={<ProtectedDashboard />} />
      {/* Catch-all sends to landing */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

function ProtectedDashboard() {
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('desci_token'));

  if (!isLoggedIn) {
    return <LoginPage onLogin={() => setIsLoggedIn(true)} />;
  }

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-logo">
          <span>⚡</span>
          <h1>Nexaris</h1>
        </div>
        <div className="nav-links">
          <NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
            <LayoutDashboard size={18} /> <span>Overview</span>
          </NavLink>
          <NavLink to="/dashboard/arena" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Swords size={18} /> <span>Campaign Arena</span>
          </NavLink>
          <NavLink to="/dashboard/treasury" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Wallet size={18} /> <span>Treasury</span>
          </NavLink>
          <NavLink to="/dashboard/jobs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Briefcase size={18} /> <span>Jobs</span>
          </NavLink>
          <NavLink to="/dashboard/datasets" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Database size={18} /> <span>Datasets</span>
          </NavLink>
          <NavLink to="/dashboard/outputs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <FileText size={18} /> <span>Research Outputs</span>
          </NavLink>
          <NavLink to="/dashboard/leaderboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Trophy size={18} /> <span>Leaderboard</span>
          </NavLink>
          <NavLink to="/dashboard/mcp" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <BarChart3 size={18} /> <span>Incentive Engine</span>
          </NavLink>
        </div>
        <button
          className="btn btn-secondary"
          style={{ marginTop: 'auto' }}
          onClick={() => { localStorage.removeItem('desci_token'); setIsLoggedIn(false); }}
        >
          Logout
        </button>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/arena" element={<CampaignArena />} />
          <Route path="/treasury" element={<Treasury />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/datasets" element={<Datasets />} />
          <Route path="/outputs" element={<ResearchOutputs />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/mcp" element={<MCPDashboard />} />
          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Routes>
      </main>
    </div>
  );
}

function LoginPage({ onLogin }: { onLogin: () => void }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (isRegister) {
        await api.register(email, password);
      }
      await api.login(email, password);
      onLogin();
    } catch {
      setError(isRegister ? 'Registration failed' : 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #0a0a14 0%, #1C1040 100%)',
    }}>
      <div className="card" style={{ width: 400, padding: 40 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 48 }}>⚡</div>
          <h2 style={{ fontSize: 24, fontWeight: 700, marginTop: 12, background: 'linear-gradient(135deg, #cdff00, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Researcher Portal
          </h2>
          <p style={{ color: '#9a95b0', fontSize: 14, marginTop: 4 }}>
            AI-Driven Decentralized Compute Competition Network
          </p>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          {error && <p style={{ color: '#f87171', fontSize: 13, marginBottom: 12 }}>{error}</p>}
          <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
            {loading ? 'Please wait…' : isRegister ? 'Register & Login' : 'Login'}
          </button>
          <button
            type="button"
            style={{ width: '100%', textAlign: 'center', marginTop: 12, background: 'none', border: 'none', color: 'var(--lime)', cursor: 'pointer', fontSize: 13 }}
            onClick={() => setIsRegister(!isRegister)}
          >
            {isRegister ? 'Already have an account? Login' : 'Need an account? Register'}
          </button>
          <button
            type="button"
            style={{ width: '100%', textAlign: 'center', marginTop: 8, background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}
            onClick={() => navigate('/')}
          >
            ← Back to Landing Page
          </button>
        </form>
      </div>
    </div>
  );
}
