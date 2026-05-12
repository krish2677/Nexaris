import { useEffect, useState } from 'react';
import { Zap, Users, Clock, Trophy, Target, Award, Flame, Shield, ChevronRight } from 'lucide-react';
import { api } from '../api';

function CountdownTimer({ endTime }: { endTime: string | null }) {
  const [remaining, setRemaining] = useState('');
  useEffect(() => {
    if (!endTime) { setRemaining('∞'); return; }
    const tick = () => {
      const diff = new Date(endTime).getTime() - Date.now();
      if (diff <= 0) { setRemaining('Ended'); return; }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setRemaining(`${h}h ${m}m ${s}s`);
    };
    tick();
    const iv = setInterval(tick, 1000);
    return () => clearInterval(iv);
  }, [endTime]);
  return <span style={{ fontFamily: 'monospace', color: 'var(--amber)', fontWeight: 700 }}>{remaining}</span>;
}

const typeIcons: Record<string, React.ReactNode> = {
  supply_balancing: <Zap size={16} />, retention: <Users size={16} />,
  streak: <Flame size={16} />, new_contributor: <Users size={16} />,
  referral: <Award size={16} />, dataset_completion: <Target size={16} />,
  reliability: <Shield size={16} />, time_based: <Clock size={16} />,
  experimental: <Trophy size={16} />,
};

const priorityColors: Record<string, string> = {
  critical: 'var(--red)', high: 'var(--amber)', medium: 'var(--cyan)', low: 'var(--green)',
};

export default function CampaignArena() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [joining, setJoining] = useState(false);
  const [rankings, setRankings] = useState<any>(null);

  useEffect(() => {
    const load = () => {
      api.getActiveCampaigns().then(d => setCampaigns(d?.campaigns || [])).catch(() => {});
      api.getUserRankings().then(setRankings).catch(() => {});
    };
    load();
    const iv = setInterval(load, 8000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    if (!selected) return;
    const load = () => {
      api.getCampaignDetail(selected.id).then(d => {
        setSelected(d);
        setLeaderboard(d?.leaderboard || []);
      }).catch(() => {});
    };
    load();
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, [selected?.id]);

  const handleJoin = async (campaignId: string) => {
    setJoining(true);
    try {
      await api.joinCampaign(campaignId);
      // Refresh
      const d = await api.getCampaignDetail(campaignId);
      setSelected(d);
      setLeaderboard(d?.leaderboard || []);
    } catch {}
    setJoining(false);
  };

  return (
    <>
      <div className="page-header">
        <h2>🏟️ Campaign Arena</h2>
        <p>Compete in AI-generated incentive campaigns · Win SOL rewards</p>
      </div>

      {/* My Stats */}
      {rankings && (
        <div className="stats-grid" style={{ marginBottom: 24 }}>
          <div className="stat-card">
            <div className="stat-icon purple"><Trophy size={24} /></div>
            <div>
              <div className="stat-value">{rankings.total_campaigns}</div>
              <div className="stat-label">Campaigns Joined</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon amber"><Award size={24} /></div>
            <div>
              <div className="stat-value">{rankings.total_rewards_sol?.toFixed(4)} SOL</div>
              <div className="stat-label">Total Rewards</div>
            </div>
          </div>
        </div>
      )}

      {selected ? (
        /* Campaign Detail View */
        <div>
          <button onClick={() => setSelected(null)} className="btn btn-secondary" style={{ marginBottom: 16, fontSize: 13 }}>
            ← Back to Campaigns
          </button>

          <div className="card" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ color: priorityColors[selected.priority] || 'var(--cyan)' }}>
                    {typeIcons[selected.campaign_type] || <Zap size={16} />}
                  </span>
                  <h3 style={{ margin: 0 }}>{selected.name}</h3>
                  <span className="badge" style={{ background: 'var(--green-dim)', color: 'var(--green)', fontSize: 10 }}>{selected.status}</span>
                </div>
                {selected.reasoning && (
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '8px 0', fontStyle: 'italic' }}>
                    "{selected.reasoning}"
                  </p>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--amber)' }}>
                  {selected.reward_pool?.toLocaleString()} <span style={{ fontSize: 14 }}>tokens</span>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  <Clock size={12} style={{ marginRight: 4 }} />
                  <CountdownTimer endTime={selected.end_time} />
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 24, marginTop: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
              <span>👥 {selected.participants} participants</span>
              <span>⚡ {selected.multiplier}x multiplier</span>
              <span>⏱ {selected.duration_hours}h duration</span>
              {selected.my_rank && <span style={{ color: 'var(--cyan)', fontWeight: 700 }}>Your rank: #{selected.my_rank}</span>}
              {selected.my_score !== null && selected.my_score !== undefined && <span style={{ color: 'var(--amber)', fontWeight: 700 }}>Score: {selected.my_score}</span>}
            </div>

            {!selected.my_rank && selected.status === 'active' && (
              <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => handleJoin(selected.id)} disabled={joining}>
                {joining ? 'Joining…' : '🏆 Join Competition'}
              </button>
            )}
          </div>

          {/* Leaderboard */}
          <div className="card">
            <div className="card-title">🏆 Live Leaderboard</div>
            {leaderboard.length > 0 ? (
              <div className="table-container">
                <table>
                  <thead><tr><th>Rank</th><th>Contributor</th><th>Score</th><th>Tasks</th><th>Reward</th></tr></thead>
                  <tbody>
                    {leaderboard.map((entry: any, i: number) => (
                      <tr key={entry.user_id} style={{ background: i < 3 ? 'rgba(255,193,7,0.05)' : undefined }}>
                        <td>
                          <span style={{
                            fontWeight: 800, fontSize: 16,
                            color: i === 0 ? '#ffd700' : i === 1 ? '#c0c0c0' : i === 2 ? '#cd7f32' : 'var(--text-primary)',
                          }}>
                            {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${entry.rank}`}
                          </span>
                        </td>
                        <td>
                          <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
                            {entry.email || entry.user_id?.slice(0, 8) + '…'}
                          </span>
                          {entry.wallet && <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 8 }}>{entry.wallet}</span>}
                        </td>
                        <td style={{ fontWeight: 700, color: 'var(--cyan)' }}>{entry.score?.toLocaleString()}</td>
                        <td>{entry.validated_units}</td>
                        <td style={{ color: 'var(--amber)', fontWeight: 600 }}>{entry.reward_earned > 0 ? `${entry.reward_earned} SOL` : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
                No participants yet — be the first!
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Campaign List */
        <div>
          {campaigns.length > 0 ? (
            <div style={{ display: 'grid', gap: 16 }}>
              {campaigns.map(c => (
                <div key={c.id} onClick={() => setSelected(c)} style={{
                  padding: '20px 24px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--glass-border)', cursor: 'pointer',
                  borderLeft: `4px solid ${priorityColors[c.priority] || 'var(--cyan)'}`,
                  transition: 'var(--transition)',
                }} className="campaign-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ color: priorityColors[c.priority] || 'var(--cyan)' }}>
                        {typeIcons[c.campaign_type] || <Zap size={16} />}
                      </span>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 15 }}>{c.name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                          {c.campaign_type?.replace(/_/g, ' ')} · {c.participants} participants · {c.multiplier}x
                        </div>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', display: 'flex', alignItems: 'center', gap: 16 }}>
                      <div>
                        <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--amber)' }}>
                          {c.reward_pool?.toLocaleString()}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          <CountdownTimer endTime={c.end_time} />
                        </div>
                      </div>
                      <ChevronRight size={20} style={{ color: 'var(--text-muted)' }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
              <Trophy size={48} style={{ opacity: 0.3, marginBottom: 16 }} /><br />
              No active campaigns — the AI agent is analyzing the network
            </div>
          )}
        </div>
      )}
    </>
  );
}
