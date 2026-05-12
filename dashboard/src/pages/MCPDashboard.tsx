import { useEffect, useState } from 'react';
import { Activity, TrendingUp, AlertTriangle, Users, Zap, Brain, Shield, Gift, Target, Clock, Wallet, RefreshCw, ChevronRight, BarChart2, Award, Flame } from 'lucide-react';
import { api } from '../api';

interface MetricCardProps { icon: React.ReactNode; label: string; value: string | number; color: string; sub?: string; }
function MetricCard({ icon, label, value, color, sub }: MetricCardProps) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${color}`}>{icon}</div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
        {sub && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, { bg: string; fg: string }> = {
    critical: { bg: 'var(--red-dim)', fg: 'var(--red)' },
    high: { bg: 'var(--amber-dim)', fg: 'var(--amber)' },
    medium: { bg: 'var(--cyan-dim)', fg: 'var(--cyan)' },
    low: { bg: 'var(--green-dim)', fg: 'var(--green)' },
  };
  const c = colors[priority] || colors.low;
  return <span className="badge" style={{ background: c.bg, color: c.fg, fontSize: 10 }}>{priority}</span>;
}

function TypeIcon({ type }: { type: string }) {
  const icons: Record<string, React.ReactNode> = {
    supply_balancing: <Zap size={14} />, retention: <RefreshCw size={14} />,
    streak: <Flame size={14} />, new_contributor: <Users size={14} />,
    referral: <Award size={14} />, dataset_completion: <Target size={14} />,
    reliability: <Shield size={14} />, time_based: <Clock size={14} />,
    experimental: <Brain size={14} />,
  };
  return <>{icons[type] || <Activity size={14} />}</>;
}

export default function MCPDashboard() {
  const [mcpStatus, setMCPStatus] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [treasury, setTreasury] = useState<any>(null);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [retention, setRetention] = useState<any>(null);
  const [tab, setTab] = useState<'overview' | 'campaigns' | 'treasury' | 'retention'>('overview');

  useEffect(() => {
    const load = () => {
      api.getMCPStatus().then(setMCPStatus).catch(() => {});
      api.getNetworkHealth().then(setHealth).catch(() => {});
      api.getTreasury().then(setTreasury).catch(() => {});
      api.getMCPCampaigns().then(d => setCampaigns(d?.campaigns || [])).catch(() => {});
      api.getRetention().then(setRetention).catch(() => {});
    };
    load();
    const iv = setInterval(load, 8000);
    return () => clearInterval(iv);
  }, []);

  const activeCampaigns = campaigns.filter(c => c.status === 'active');
  const recentActions = mcpStatus?.recent_actions || [];

  return (
    <>
      <div className="page-header">
        <h2>⚡ Autonomous Incentive Orchestration</h2>
        <p>AI-driven reward engine powered by Torque MCP &bull; Cycle #{mcpStatus?.engine_cycle ?? 0}</p>
      </div>

      {/* Tab navigation */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24 }}>
        {(['overview', 'campaigns', 'treasury', 'retention'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{
              padding: '8px 18px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)',
              background: tab === t ? 'var(--cyan-dim)' : 'var(--glass)', color: tab === t ? 'var(--cyan)' : 'var(--text-secondary)',
              cursor: 'pointer', fontWeight: 600, fontSize: 13, fontFamily: 'inherit', textTransform: 'capitalize',
            }}>{t}</button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab health={health} mcpStatus={mcpStatus} activeCampaigns={activeCampaigns} recentActions={recentActions} treasury={treasury} />}
      {tab === 'campaigns' && <CampaignsTab campaigns={campaigns} />}
      {tab === 'treasury' && <TreasuryTab treasury={treasury} />}
      {tab === 'retention' && <RetentionTab retention={retention} />}
    </>
  );
}

/* ═══════════════════════════════════════ OVERVIEW TAB ═══════════════════════════════════════ */
function OverviewTab({ health, mcpStatus, activeCampaigns, recentActions, treasury }: any) {
  return (
    <>
      <div className="stats-grid">
        <MetricCard icon={<Users size={24} />} label="Active Contributors" value={health?.active_contributors ?? '—'} color="cyan" sub={`${health?.inactive_contributors ?? 0} inactive`} />
        <MetricCard icon={<Activity size={24} />} label="Online Devices" value={health?.online_devices ?? '—'} color="green" sub={`${health?.computing_devices ?? 0} computing`} />
        <MetricCard icon={<AlertTriangle size={24} />} label="Under-Supplied" value={health?.under_supplied_count ?? '—'} color="red" sub={`${health?.stalled_workloads ?? 0} stalled`} />
        <MetricCard icon={<TrendingUp size={24} />} label="Avg Multiplier" value={`${mcpStatus?.avg_multiplier?.toFixed(1) ?? '1.0'}x`} color="amber" />
        <MetricCard icon={<Gift size={24} />} label="Active Campaigns" value={mcpStatus?.active_campaigns ?? 0} color="purple" />
        <MetricCard icon={<Wallet size={24} />} label="Treasury" value={`${((treasury?.available_balance ?? 0) / 1000).toFixed(1)}K`} color="cyan" sub={`${((treasury?.utilization_rate ?? 0) * 100).toFixed(1)}% utilized`} />
      </div>

      {/* Network health indicators */}
      {health && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-title">Network Health Indicators</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
            <HealthBar label="Retention Rate" value={health.retention_rate} color="var(--green)" />
            <HealthBar label="Validation Quality" value={1 - health.validation_failure_rate} color="var(--cyan)" />
            <HealthBar label="Top Reliability" value={health.top_contributor_reliability} color="var(--purple)" />
            <HealthBar label="Growth Rate" value={Math.min(health.daily_growth_rate * 10, 1)} color="var(--amber)" suffix={`${(health.daily_growth_rate * 100).toFixed(1)}%`} />
          </div>
        </div>
      )}

      <div className="grid-2">
        {/* Live Agent Actions */}
        <div className="card">
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Brain size={16} style={{ color: 'var(--purple)' }} /> Agent Decision Log
          </div>
          {recentActions.length > 0 ? (
            <div style={{ display: 'grid', gap: 8, maxHeight: 380, overflowY: 'auto' }}>
              {recentActions.slice(0, 15).map((a: any) => (
                <div key={a.id} style={{
                  padding: '10px 14px', background: 'var(--glass)', borderRadius: 'var(--radius-sm)',
                  borderLeft: `3px solid ${a.source === 'llm' ? 'var(--purple)' : a.action_type?.includes('campaign') ? 'var(--amber)' : 'var(--cyan)'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{a.action_type?.replace(/_/g, ' ')}</span>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <span className="badge" style={{
                        background: a.source === 'llm' ? 'var(--purple-dim)' : 'var(--cyan-dim)',
                        color: a.source === 'llm' ? 'var(--purple)' : 'var(--cyan)', fontSize: 10,
                      }}>{a.source === 'llm' ? '🧠 GPT-4o' : '⚡ Rule'}</span>
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {a.parameters?.campaign_name && <span>{a.parameters.campaign_name} • </span>}
                    {a.parameters?.new_multiplier && <span>→ {a.parameters.new_multiplier}x </span>}
                    {a.parameters?.reasoning && <span style={{ fontStyle: 'italic' }}>{a.parameters.reasoning.slice(0, 80)}…</span>}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                    {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 32 }}>
              <Brain size={32} style={{ opacity: 0.3, marginBottom: 8 }} /><br />
              Agent initializing — actions will appear here
            </div>
          )}
        </div>

        {/* Active Campaigns */}
        <div className="card">
          <div className="card-title">Active Campaigns ({activeCampaigns.length})</div>
          {activeCampaigns.length > 0 ? (
            <div style={{ display: 'grid', gap: 10, maxHeight: 380, overflowY: 'auto' }}>
              {activeCampaigns.map((c: any) => (
                <CampaignCard key={c.id} campaign={c} compact />
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 32 }}>
              <Target size={32} style={{ opacity: 0.3, marginBottom: 8 }} /><br />
              No active campaigns — agent is analyzing network
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════ CAMPAIGNS TAB ═══════════════════════════════════════ */
function CampaignsTab({ campaigns }: { campaigns: any[] }) {
  const [filter, setFilter] = useState('all');
  const filtered = filter === 'all' ? campaigns : campaigns.filter(c => c.status === filter);
  const statusCounts = campaigns.reduce((acc: any, c) => { acc[c.status] = (acc[c.status] || 0) + 1; return acc; }, {});

  return (
    <>
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {['all', 'active', 'proposed', 'completed', 'expired', 'failed'].map(s => (
          <button key={s} onClick={() => setFilter(s)} style={{
            padding: '6px 14px', borderRadius: 20, border: '1px solid var(--glass-border)',
            background: filter === s ? 'var(--cyan-dim)' : 'var(--glass)', color: filter === s ? 'var(--cyan)' : 'var(--text-secondary)',
            cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'inherit',
          }}>{s} {s !== 'all' && statusCounts[s] ? `(${statusCounts[s]})` : s === 'all' ? `(${campaigns.length})` : ''}</button>
        ))}
      </div>

      {filtered.length > 0 ? (
        <div style={{ display: 'grid', gap: 16 }}>
          {filtered.map(c => <CampaignCard key={c.id} campaign={c} />)}
        </div>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
          No campaigns found for filter: {filter}
        </div>
      )}
    </>
  );
}

function CampaignCard({ campaign: c, compact }: { campaign: any; compact?: boolean }) {
  const statusColors: Record<string, string> = {
    active: 'var(--green)', proposed: 'var(--amber)', completed: 'var(--cyan)',
    expired: 'var(--text-muted)', failed: 'var(--red)', cancelled: 'var(--text-muted)',
  };
  const borderColor = statusColors[c.status] || 'var(--glass-border)';

  return (
    <div style={{
      padding: compact ? '12px 16px' : '16px 20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)',
      border: `1px solid var(--glass-border)`, borderLeft: `4px solid ${borderColor}`,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: borderColor }}><TypeIcon type={c.campaign_type} /></span>
          <div>
            <div style={{ fontWeight: 700, fontSize: compact ? 13 : 15 }}>{c.name}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.campaign_type?.replace(/_/g, ' ')}</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <PriorityBadge priority={c.priority} />
          <span className="badge" style={{ background: `${borderColor}22`, color: borderColor, fontSize: 10 }}>{c.status}</span>
        </div>
      </div>

      {c.reasoning && !compact && (
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '8px 0', lineHeight: 1.6, fontStyle: 'italic' }}>
          "{c.reasoning}"
        </p>
      )}

      <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
        <span>💰 {c.reward_pool?.toLocaleString()}</span>
        <span>⚡ {c.multiplier}x</span>
        <span>⏱ {c.duration_hours}h</span>
        {c.torque_primitives?.length > 0 && (
          <span>🔧 {c.torque_primitives.join(', ')}</span>
        )}
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
          {c.source === 'llm' ? '🧠 AI' : '⚡ Rule'}
        </span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════ TREASURY TAB ═══════════════════════════════════════ */
function TreasuryTab({ treasury }: { treasury: any }) {
  if (!treasury) return <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>Loading treasury data…</div>;

  const categories = treasury.categories || {};
  const catColors: Record<string, string> = {
    retention: 'var(--cyan)', supply_balancing: 'var(--amber)', referral: 'var(--green)',
    streak: 'var(--purple)', experimental: 'var(--red)',
  };

  return (
    <>
      <div className="stats-grid">
        <MetricCard icon={<Wallet size={24} />} label="Total Balance" value={`${(treasury.total_balance / 1000).toFixed(1)}K`} color="cyan" />
        <MetricCard icon={<TrendingUp size={24} />} label="Available" value={`${(treasury.available_balance / 1000).toFixed(1)}K`} color="green" />
        <MetricCard icon={<BarChart2 size={24} />} label="Total Spent" value={`${(treasury.total_spent / 1000).toFixed(1)}K`} color="amber" />
        <MetricCard icon={<Shield size={24} />} label="Emergency Reserve" value={`${(treasury.reserved_emergency / 1000).toFixed(1)}K`} color="red" />
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Budget Allocation</div>
          <div style={{ display: 'grid', gap: 12 }}>
            {Object.entries(categories).map(([cat, data]: [string, any]) => (
              <div key={cat}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{cat.replace(/_/g, ' ')}</span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {data.spent.toLocaleString()} / {data.budget.toLocaleString()} ({(data.percentage * 100)}%)
                  </span>
                </div>
                <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)' }}>
                  <div style={{
                    height: '100%', borderRadius: 3, width: `${Math.min((data.spent / Math.max(data.budget, 1)) * 100, 100)}%`,
                    background: catColors[cat] || 'var(--cyan)', transition: 'width 0.5s',
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Recent Transactions</div>
          {treasury.recent_transactions?.length > 0 ? (
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              <table><thead><tr><th>Category</th><th>Amount</th><th>Description</th></tr></thead>
                <tbody>
                  {treasury.recent_transactions.map((t: any) => (
                    <tr key={t.id}>
                      <td><span className="badge" style={{ background: 'var(--glass)', fontSize: 11 }}>{t.category}</span></td>
                      <td style={{ fontWeight: 600 }}>-{t.amount?.toLocaleString()}</td>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t.description?.slice(0, 40)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 24 }}>No transactions yet</div>
          )}
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════ RETENTION TAB ═══════════════════════════════════════ */
function RetentionTab({ retention }: { retention: any }) {
  if (!retention) return <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>Loading retention data…</div>;

  return (
    <>
      <div className="stats-grid">
        <MetricCard icon={<Users size={24} />} label="Tracked" value={retention.total_tracked} color="cyan" />
        <MetricCard icon={<AlertTriangle size={24} />} label="High Churn Risk" value={retention.high_risk} color="red" />
        <MetricCard icon={<Shield size={24} />} label="Low Risk" value={retention.low_risk} color="green" />
        <MetricCard icon={<Flame size={24} />} label="Avg Streak" value={`${retention.avg_streak_days}d`} color="amber" />
        <MetricCard icon={<Award size={24} />} label="Avg Reliability" value={`${(retention.avg_reliability * 100).toFixed(0)}%`} color="purple" />
      </div>

      {/* Risk distribution */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title">Churn Risk Distribution</div>
        <div style={{ display: 'flex', gap: 4, height: 24, borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ flex: retention.low_risk, background: 'var(--green)', transition: 'flex 0.5s' }} title={`Low: ${retention.low_risk}`} />
          <div style={{ flex: retention.medium_risk, background: 'var(--amber)', transition: 'flex 0.5s' }} title={`Medium: ${retention.medium_risk}`} />
          <div style={{ flex: retention.high_risk || 0.1, background: 'var(--red)', transition: 'flex 0.5s' }} title={`High: ${retention.high_risk}`} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)', marginTop: 8 }}>
          <span style={{ color: 'var(--green)' }}>● Low Risk ({retention.low_risk})</span>
          <span style={{ color: 'var(--amber)' }}>● Medium ({retention.medium_risk})</span>
          <span style={{ color: 'var(--red)' }}>● High Risk ({retention.high_risk})</span>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Contributors by Churn Risk</div>
        <div className="table-container">
          <table><thead><tr><th>User</th><th>Streak</th><th>Reliability</th><th>Churn Risk</th><th>Tasks</th><th>Last Active</th></tr></thead>
            <tbody>
              {retention.contributors?.map((c: any) => (
                <tr key={c.user_id}>
                  <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{c.user_id?.slice(0, 8)}…</td>
                  <td><span style={{ color: 'var(--amber)', fontWeight: 600 }}>{c.streak_days}d</span></td>
                  <td>
                    <span style={{ color: c.reliability > 0.8 ? 'var(--green)' : c.reliability > 0.5 ? 'var(--amber)' : 'var(--red)', fontWeight: 600 }}>
                      {(c.reliability * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ width: 50, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)' }}>
                        <div style={{ height: '100%', borderRadius: 2, width: `${c.churn_risk * 100}%`, background: c.churn_risk > 0.7 ? 'var(--red)' : c.churn_risk > 0.3 ? 'var(--amber)' : 'var(--green)' }} />
                      </div>
                      <span style={{ fontSize: 11 }}>{(c.churn_risk * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td>{c.total_validated}</td>
                  <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {c.last_compute ? new Date(c.last_compute).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════ HEALTH BAR ═══════════════════════════════════════ */
function HealthBar({ label, value, color, suffix }: { label: string; value: number; color: string; suffix?: string }) {
  const pct = Math.min(Math.max(value * 100, 0), 100);
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontWeight: 600, color }}>{suffix || `${pct.toFixed(0)}%`}</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)' }}>
        <div style={{ height: '100%', borderRadius: 3, width: `${pct}%`, background: color, transition: 'width 0.8s ease' }} />
      </div>
    </div>
  );
}
