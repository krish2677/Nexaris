import { useEffect, useState } from 'react';
import { FileText, Download, BarChart3, RefreshCw } from 'lucide-react';
import { api } from '../api';

export default function ResearchOutputs() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getJobs(true).then(setJobs).catch(() => {});
  }, []);

  const completedJobs = jobs.filter(j => j.status === 'completed');

  const loadResults = async (jobId: string) => {
    setSelectedJob(jobId);
    setLoading(true);
    try {
      const [res, rep] = await Promise.all([
        api.getJobResults(jobId).catch(() => null),
        api.getJobReport(jobId).catch(() => null),
      ]);
      setResults(res);
      setReport(rep);
    } catch {}
    setLoading(false);
  };

  const handleDownload = async (jobId: string, format: string) => {
    try {
      const blob = await api.downloadJobResults(jobId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `desci_output.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('Download failed: ' + err.message);
    }
  };

  const metrics = results?.metrics || results || {};
  const template = metrics?.template || report?.template_type || '';

  return (
    <>
      <div className="page-header">
        <h2>Research Outputs</h2>
        <p>View results, download reports, and inspect analytics from completed jobs</p>
      </div>

      <div className="grid-2">
        {/* Job selector */}
        <div className="card">
          <div className="card-title">Completed Jobs</div>
          {completedJobs.length > 0 ? (
            <div style={{ display: 'grid', gap: 8, maxHeight: 400, overflowY: 'auto' }}>
              {completedJobs.map(job => (
                <button
                  key={job.id}
                  onClick={() => loadResults(job.id)}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '12px 16px', background: selectedJob === job.id ? 'var(--cyan-dim)' : 'var(--glass)',
                    borderRadius: 'var(--radius-sm)', border: selectedJob === job.id ? '1px solid var(--cyan)' : '1px solid transparent',
                    cursor: 'pointer', width: '100%', textAlign: 'left', color: 'inherit',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>{job.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{job.template_type}</div>
                  </div>
                  <span className="badge active">completed</span>
                </button>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 32 }}>
              No completed jobs yet
            </div>
          )}
        </div>

        {/* Results panel */}
        <div className="card">
          <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Results</span>
            {selectedJob && (
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => handleDownload(selectedJob, 'json')}>
                  <Download size={12} /> JSON
                </button>
                <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => handleDownload(selectedJob, 'csv')}>
                  <Download size={12} /> CSV
                </button>
                <button className="btn btn-primary" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => handleDownload(selectedJob, 'zip')}>
                  <Download size={12} /> ZIP
                </button>
              </div>
            )}
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
              <RefreshCw size={24} className="spin" /> Loading...
            </div>
          ) : selectedJob && metrics ? (
            <div style={{ display: 'grid', gap: 16 }}>
              {/* Monte Carlo Results */}
              {template === 'monte_carlo' && (
                <>
                  <MetricRow label="Pi Estimate" value={metrics.probability_estimate?.toFixed(10)} highlight />
                  <MetricRow label="Total Samples" value={metrics.total_samples?.toLocaleString()} />
                  <MetricRow label="Standard Error" value={metrics.standard_error?.toExponential(4)} />
                  <MetricRow label="Estimator Variance" value={metrics.estimator_variance?.toExponential(6)} />
                  {metrics.confidence_interval_95 && (
                    <MetricRow
                      label="95% CI"
                      value={`[${metrics.confidence_interval_95.lower?.toFixed(8)}, ${metrics.confidence_interval_95.upper?.toFixed(8)}]`}
                    />
                  )}
                  {metrics.confidence_interval_99 && (
                    <MetricRow
                      label="99% CI"
                      value={`[${metrics.confidence_interval_99.lower?.toFixed(8)}, ${metrics.confidence_interval_99.upper?.toFixed(8)}]`}
                    />
                  )}
                  <MetricRow label="Chunks Processed" value={metrics.chunks_processed} />
                </>
              )}

              {/* Dataset Stats Results */}
              {template === 'dataset_stats' && (
                <>
                  <MetricRow label="Total Rows" value={metrics.total_rows?.toLocaleString()} highlight />
                  <MetricRow label="Columns" value={metrics.columns} />
                  {metrics.global_means && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Column Statistics</div>
                      <div className="table-container">
                        <table style={{ fontSize: 13 }}>
                          <thead>
                            <tr>
                              <th>Column</th>
                              <th>Mean</th>
                              <th>Std Dev</th>
                              <th>Min</th>
                              <th>Max</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(metrics.column_names || []).map((name: string, i: number) => (
                              <tr key={i}>
                                <td style={{ fontWeight: 600 }}>{name}</td>
                                <td>{metrics.global_means?.[i]?.toFixed(4)}</td>
                                <td>{metrics.global_stddevs?.[i]?.toFixed(4)}</td>
                                <td>{metrics.global_mins?.[i]?.toFixed(4)}</td>
                                <td>{metrics.global_maxs?.[i]?.toFixed(4)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Matrix Results */}
              {template === 'matrix_compute' && (
                <>
                  <MetricRow label="Rows Processed" value={metrics.total_rows_processed?.toLocaleString()} highlight />
                  <MetricRow label="Block Sum" value={metrics.total_block_sum?.toFixed(4)} />
                  <MetricRow label="Global Mean" value={metrics.global_mean?.toFixed(6)} />
                  <MetricRow label="Row Variance" value={metrics.row_sum_variance?.toFixed(4)} />
                  <MetricRow label="Row Std Dev" value={metrics.row_sum_stddev?.toFixed(4)} />
                  <MetricRow label="Blocks" value={metrics.block_count} />
                </>
              )}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 32 }}>
              <FileText size={32} style={{ marginBottom: 12, opacity: 0.3 }} /><br />
              Select a completed job to view results
            </div>
          )}
        </div>
      </div>

      {/* Analysis section */}
      {report?.analysis && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-title">
            <BarChart3 size={16} style={{ display: 'inline', marginRight: 8 }} />
            Analysis Summary
          </div>
          <div style={{ display: 'grid', gap: 12 }}>
            {report.analysis.conclusion && (
              <div style={{ padding: '12px 16px', background: 'var(--cyan-dim)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(0,229,255,0.2)' }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Conclusion</div>
                <div style={{ fontWeight: 600 }}>{report.analysis.conclusion}</div>
              </div>
            )}
            {report.analysis.precision && (
              <MetricRow label="Precision" value={report.analysis.precision} />
            )}
            {report.analysis.convergence && (
              <MetricRow label="Convergence" value={report.analysis.convergence} />
            )}
            {report.analysis.relative_error !== undefined && (
              <MetricRow label="Relative Error" value={(report.analysis.relative_error * 100).toFixed(6) + '%'} />
            )}
          </div>
        </div>
      )}
    </>
  );
}

function MetricRow({ label, value, highlight }: { label: string; value: any; highlight?: boolean }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '10px 14px', background: 'var(--glass)', borderRadius: 'var(--radius-sm)',
    }}>
      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{label}</span>
      <span style={{
        fontWeight: highlight ? 700 : 600,
        fontSize: highlight ? 18 : 14,
        color: highlight ? 'var(--cyan)' : 'var(--text-primary)',
        fontFamily: 'monospace',
      }}>{value ?? '—'}</span>
    </div>
  );
}
