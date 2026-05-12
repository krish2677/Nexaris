import { useEffect, useState } from 'react';
import { Trophy } from 'lucide-react';
import { api } from '../api';

export default function Leaderboard() {
  const [entries, setEntries] = useState<any[]>([]);

  useEffect(() => {
    api.getLeaderboard(50).then(d => setEntries(d.leaderboard)).catch(() => {});
    const interval = setInterval(() => {
      api.getLeaderboard(50).then(d => setEntries(d.leaderboard)).catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <div className="page-header">
        <h2>Contributor Leaderboard</h2>
        <p>Top contributors ranked by validated compute score</p>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th style={{ width: 60 }}>Rank</th>
                <th>Contributor</th>
                <th style={{ textAlign: 'right' }}>Score</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, i) => {
                const medals = ['🥇', '🥈', '🥉'];
                const bgColors = ['rgba(255,215,0,0.06)', 'rgba(192,192,192,0.06)', 'rgba(205,127,50,0.06)'];
                return (
                  <tr key={entry.user_id} style={{ background: bgColors[i] || 'transparent' }}>
                    <td style={{ fontSize: i < 3 ? 24 : 14, fontWeight: 700 }}>
                      {medals[i] || `#${i + 1}`}
                    </td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{entry.email}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{entry.user_id.slice(0, 8)}…</div>
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700, fontSize: 18, color: 'var(--cyan)' }}>
                      {Math.round(entry.score).toLocaleString()}
                    </td>
                  </tr>
                );
              })}
              {entries.length === 0 && (
                <tr>
                  <td colSpan={3} style={{ textAlign: 'center', padding: 48 }}>
                    <Trophy size={48} style={{ color: 'var(--text-muted)', marginBottom: 12 }} />
                    <div style={{ color: 'var(--text-muted)' }}>No contributors yet</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
