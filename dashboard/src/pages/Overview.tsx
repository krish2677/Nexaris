import { useEffect, useState } from 'react';
import { Users, Monitor, Cpu, CheckCircle, Clock, Zap, Wifi, WifiOff } from 'lucide-react';
import { api } from '../api';
import { useWebSocket, useWSEvent } from '../hooks/useWebSocket';

interface Stats {
  total_users: number;
  active_devices: number;
  total_jobs: number;
  active_jobs: number;
  completed_tasks: number;
  pending_tasks: number;
  total_compute_hours: number;
  avg_reward_multiplier: number;
}

export default function Overview() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const { messages, connected } = useWebSocket('global');

  // Initial load
  useEffect(() => {
    api.getStats().then(setStats).catch(() => {});
    api.getLeaderboard(10).then(d => setLeaderboard(d.leaderboard)).catch(() => {});
    const interval = setInterval(() => {
      api.getStats().then(setStats).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Live leaderboard updates via WebSocket
  const lbUpdate = useWSEvent(messages, 'leaderboard_update');
  useEffect(() => {
    if (lbUpdate?.entries) {
      setLeaderboard(lbUpdate.entries.slice(0, 10));
    }
  }, [lbUpdate]);

  // Live task validation events (deduplicated by task_id)
  const taskEvent = useWSEvent(messages, 'task_validated');
  const [seenTasks] = useState<Set<string>>(new Set());
  useEffect(() => {
    if (taskEvent?.task_id && stats && !seenTasks.has(taskEvent.task_id)) {
      seenTasks.add(taskEvent.task_id);
      setStats(prev => prev ? { ...prev, completed_tasks: prev.completed_tasks + 1 } : prev);
    }
  }, [taskEvent]);

  return (
    <>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Dashboard Overview</h2>
          <p>Real-time platform metrics and contributor activity</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {connected ? (
            <span className="badge active" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Wifi size={12} /> Live
            </span>
          ) : (
            <span className="badge failed" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <WifiOff size={12} /> Reconnecting
            </span>
          )}
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon cyan"><Users size={24} /></div>
          <div>
            <div className="stat-value">{stats?.total_users ?? '—'}</div>
            <div className="stat-label">Total Contributors</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><Monitor size={24} /></div>
          <div>
            <div className="stat-value">{stats?.active_devices ?? '—'}</div>
            <div className="stat-label">Active Devices</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber"><Cpu size={24} /></div>
          <div>
            <div className="stat-value">{stats?.active_jobs ?? '—'}</div>
            <div className="stat-label">Active Jobs</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon purple"><CheckCircle size={24} /></div>
          <div>
            <div className="stat-value">{stats?.completed_tasks ?? '—'}</div>
            <div className="stat-label">Completed Tasks</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon cyan"><Clock size={24} /></div>
          <div>
            <div className="stat-value">{stats?.pending_tasks ?? '—'}</div>
            <div className="stat-label">Pending Tasks</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber pulse"><Zap size={24} /></div>
          <div>
            <div className="stat-value">{stats?.avg_reward_multiplier?.toFixed(1) ?? '—'}x</div>
            <div className="stat-label">Avg Multiplier</div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Top Contributors</div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Contributor</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((entry, i) => (
                  <tr key={entry.user_id}>
                    <td>{['🥇','🥈','🥉'][i] || `#${i+1}`}</td>
                    <td>{entry.email}</td>
                    <td style={{ fontWeight: 600, color: 'var(--cyan)' }}>
                      {Math.round(entry.score).toLocaleString()}
                    </td>
                  </tr>
                ))}
                {leaderboard.length === 0 && (
                  <tr><td colSpan={3} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No data yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Platform Health</div>
          <div style={{ display: 'grid', gap: 16 }}>
            <HealthItem label="Database" status="healthy" />
            <HealthItem label="Redis" status="healthy" />
            <HealthItem label="MCP Engine" status="active" />
            <HealthItem label="Torque API" status="connected" />
            <HealthItem label="WebSocket" status={connected ? 'connected' : 'disconnected'} />
            <HealthItem label="Task Queue" status={`${stats?.pending_tasks ?? 0} pending`} />
          </div>
        </div>
      </div>

      {/* Live Event Feed */}
      {messages.length > 0 && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-title">Live Event Feed</div>
          <div style={{ maxHeight: 200, overflowY: 'auto', display: 'grid', gap: 4 }}>
            {messages.slice(-10).reverse().map((msg, i) => (
              <div key={i} style={{
                padding: '8px 12px', background: 'var(--glass)', borderRadius: 'var(--radius-sm)',
                fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <span style={{ color: 'var(--cyan)' }}>{msg.type}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                  {msg.user_id?.slice(0, 8) || msg.job_id?.slice(0, 8) || ''}…
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function HealthItem({ label, status }: { label: string; status: string }) {
  const isGood = ['healthy', 'active', 'connected'].includes(status);
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '12px 16px', background: 'var(--glass)', borderRadius: 'var(--radius-sm)',
    }}>
      <span style={{ fontWeight: 500 }}>{label}</span>
      <span className={`badge ${isGood ? 'active' : 'pending'}`}>{status}</span>
    </div>
  );
}
