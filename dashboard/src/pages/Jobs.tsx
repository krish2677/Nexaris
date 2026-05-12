import { useEffect, useState } from 'react';
import { Plus, ChevronDown, ChevronUp, Download, BarChart3, RefreshCw } from 'lucide-react';
import { api } from '../api';

export default function Jobs() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [progress, setProgress] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [form, setForm] = useState({
    name: '',
    template_type: 'monte_carlo',
    parameters_json: '{"seed": 42, "total_iterations": 1000000}',
    priority: 1,
    required_workers: 3,
    validation_strategy: 'duplicate',
  });

  useEffect(() => {
    api.getJobs().then(setJobs).catch(() => {});
    const interval = setInterval(() => {
      api.getJobs().then(setJobs).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createJob(form);
      setShowCreate(false);
      api.getJobs().then(setJobs).catch(() => {});
    } catch (err) {
      console.error(err);
    }
  };

  const toggleExpand = async (jobId: string) => {
    if (expanded === jobId) {
      setExpanded(null);
      return;
    }
    setExpanded(jobId);
    setProgress(null);
    setResults(null);
    try {
      const [prog, res] = await Promise.all([
        api.getJobProgress(jobId).catch(() => null),
        api.getJobResults(jobId).catch(() => null),
      ]);
      setProgress(prog);
      setResults(res);
    } catch {}
  };

  const handleDownload = async (jobId: string, format: string) => {
    try {
      const blob = await api.downloadJobResults(jobId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `output.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('Download failed: ' + err.message);
    }
  };

  const templateParams: Record<string, string> = {
    monte_carlo: '{"seed": 42, "total_iterations": 1000000}',
    dataset_stats: '{"seed": 42, "columns": 4, "total_rows": 100000}',
    matrix_compute: '{"seed": 42, "matrix_size": 512, "operation": "multiply"}',
  };

  return (
    <>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Compute Jobs</h2>
          <p>Create and monitor distributed workloads</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          <Plus size={16} /> New Job
        </button>
      </div>

      {showCreate && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-title">Create New Job</div>
          <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="form-group">
              <label>Job Name</label>
              <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Template Type</label>
              <select
                className="form-select"
                value={form.template_type}
                onChange={e => setForm({ ...form, template_type: e.target.value, parameters_json: templateParams[e.target.value] })}
              >
                <option value="monte_carlo">Monte Carlo Simulation</option>
                <option value="dataset_stats">Dataset Statistics</option>
                <option value="matrix_compute">Matrix Computation</option>
              </select>
            </div>
            <div className="form-group" style={{ gridColumn: 'span 2' }}>
              <label>Parameters (JSON)</label>
              <textarea className="form-textarea" value={form.parameters_json} onChange={e => setForm({ ...form, parameters_json: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Priority (1-10)</label>
              <input className="form-input" type="number" min={1} max={10} value={form.priority} onChange={e => setForm({ ...form, priority: +e.target.value })} />
            </div>
            <div className="form-group">
              <label>Required Workers</label>
              <input className="form-input" type="number" min={1} value={form.required_workers} onChange={e => setForm({ ...form, required_workers: +e.target.value })} />
            </div>
            <div className="form-group">
              <label>Validation Strategy</label>
              <select className="form-select" value={form.validation_strategy} onChange={e => setForm({ ...form, validation_strategy: e.target.value })}>
                <option value="duplicate">Duplicate Execution</option>
                <option value="deterministic">Deterministic</option>
                <option value="spot_check">Spot Check</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: 12, alignItems: 'end' }}>
              <button type="submit" className="btn btn-primary">Create Job</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Template</th>
                <th>Status</th>
                <th>Workers</th>
                <th>Multiplier</th>
                <th>Priority</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <>
                  <tr key={job.id} style={{ cursor: 'pointer' }} onClick={() => toggleExpand(job.id)}>
                    <td style={{ fontWeight: 600 }}>{job.name}</td>
                    <td><span className="badge pending">{job.template_type}</span></td>
                    <td><span className={`badge ${job.status}`}>{job.status}</span></td>
                    <td>{job.active_workers}/{job.required_workers}</td>
                    <td style={{ color: 'var(--amber)', fontWeight: 600 }}>{job.reward_multiplier}x</td>
                    <td>{job.priority}</td>
                    <td>{expanded === job.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</td>
                  </tr>
                  {expanded === job.id && (
                    <tr key={`${job.id}-detail`}>
                      <td colSpan={7} style={{ padding: 0 }}>
                        <div style={{ padding: 20, background: 'var(--glass)', margin: '0 8px 8px', borderRadius: 'var(--radius-sm)' }}>
                          {/* Progress */}
                          {progress && (
                            <div style={{ marginBottom: 16 }}>
                              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Task Progress</div>
                              <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                                <span>Completed: <strong style={{ color: 'var(--green)' }}>{progress.completed}</strong></span>
                                <span>Failed: <strong style={{ color: 'var(--red)' }}>{progress.failed}</strong></span>
                                <span>Total: <strong>{progress.total}</strong></span>
                                {progress.aggregation_status && (
                                  <span>Aggregation: <span className={`badge ${progress.aggregation_status === 'completed' ? 'active' : 'pending'}`}>{progress.aggregation_status}</span></span>
                                )}
                              </div>
                              {progress.total > 0 && (
                                <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
                                  <div style={{
                                    height: '100%', borderRadius: 3,
                                    width: `${(progress.completed / progress.total) * 100}%`,
                                    background: 'linear-gradient(90deg, var(--cyan), var(--green))',
                                    transition: 'width 0.5s',
                                  }} />
                                </div>
                              )}
                            </div>
                          )}

                          {/* Results preview */}
                          {results && results.metrics && (
                            <div style={{ marginBottom: 16 }}>
                              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Results Summary</div>
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 8 }}>
                                {Object.entries(results.metrics).filter(([k]) =>
                                  !['template', 'chunks_processed', 'aggregated_at', 'blocks', 'column_names', 'confidence_interval_99'].includes(k)
                                ).slice(0, 6).map(([key, val]) => (
                                  <div key={key} style={{ padding: '8px 12px', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)' }}>
                                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{key.replace(/_/g, ' ')}</div>
                                    <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'monospace', color: 'var(--cyan)' }}>
                                      {typeof val === 'number' ? (val > 1000 ? val.toLocaleString() : val.toFixed(4)) : typeof val === 'object' ? JSON.stringify(val).slice(0, 30) : String(val)}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Download buttons */}
                          {job.status === 'completed' && (
                            <div style={{ display: 'flex', gap: 8 }}>
                              <button className="btn btn-secondary" style={{ fontSize: 12 }} onClick={(e) => { e.stopPropagation(); handleDownload(job.id, 'json'); }}>
                                <Download size={12} /> JSON
                              </button>
                              <button className="btn btn-secondary" style={{ fontSize: 12 }} onClick={(e) => { e.stopPropagation(); handleDownload(job.id, 'csv'); }}>
                                <Download size={12} /> CSV
                              </button>
                              <button className="btn btn-primary" style={{ fontSize: 12 }} onClick={(e) => { e.stopPropagation(); handleDownload(job.id, 'zip'); }}>
                                <Download size={12} /> ZIP Archive
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
              {jobs.length === 0 && (
                <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 48 }}>No jobs created yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
