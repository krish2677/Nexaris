import { useEffect, useState, useCallback } from 'react';
import { Database, Upload, FileText, Trash2, Eye, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../api';

export default function Datasets() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);

  const load = useCallback(() => {
    api.getDatasets().then(setDatasets).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(`Uploading ${file.name}...`);
    try {
      await api.uploadDataset(file);
      setUploadProgress('Upload complete!');
      load();
      setTimeout(() => setUploadProgress(''), 3000);
    } catch (err: any) {
      setUploadProgress(`Error: ${err.message}`);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const toggleDetail = async (id: string) => {
    if (expanded === id) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(id);
    try {
      const d = await api.getDatasetDetail(id);
      setDetail(d);
    } catch { setDetail(null); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this dataset?')) return;
    try {
      await api.deleteDataset(id);
      load();
    } catch {}
  };

  const formatBytes = (b: number) => {
    if (b < 1024) return `${b} B`;
    if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
    return `${(b / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Research Datasets</h2>
          <p>Upload and manage datasets for distributed computation</p>
        </div>
        <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
          <Upload size={16} /> Upload Dataset
          <input type="file" accept=".csv,.json,.jsonl,.parquet" onChange={handleUpload} style={{ display: 'none' }} disabled={uploading} />
        </label>
      </div>

      {uploadProgress && (
        <div className="card" style={{ marginBottom: 16, padding: '12px 20px', background: uploading ? 'var(--cyan-dim)' : 'var(--green-dim)', border: `1px solid ${uploading ? 'var(--cyan)' : 'var(--green)'}40` }}>
          <span style={{ color: uploading ? 'var(--cyan)' : 'var(--green)' }}>{uploadProgress}</span>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Format</th>
                <th>Rows</th>
                <th>Size</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map(ds => (
                <>
                  <tr key={ds.id}>
                    <td style={{ fontWeight: 600 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Database size={14} style={{ color: 'var(--cyan)' }} />
                        {ds.filename}
                      </div>
                    </td>
                    <td><span className="badge pending">{ds.format}</span></td>
                    <td>{ds.row_count?.toLocaleString()}</td>
                    <td>{formatBytes(ds.size_bytes)}</td>
                    <td><span className={`badge ${ds.upload_status === 'ready' ? 'active' : 'pending'}`}>{ds.upload_status}</span></td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{new Date(ds.created_at).toLocaleDateString()}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: 12 }} onClick={() => toggleDetail(ds.id)}>
                          {expanded === ds.id ? <ChevronUp size={12} /> : <Eye size={12} />}
                        </button>
                        <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: 12, color: 'var(--red)' }} onClick={() => handleDelete(ds.id)}>
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expanded === ds.id && detail && (
                    <tr key={`${ds.id}-detail`}>
                      <td colSpan={7} style={{ padding: 0 }}>
                        <div style={{ padding: 20, background: 'var(--glass)', margin: '0 8px 8px' , borderRadius: 'var(--radius-sm)' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                            <div>
                              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Columns</div>
                              <div style={{ fontWeight: 600 }}>{detail.column_metadata?.column_count ?? 'N/A'}</div>
                            </div>
                            <div>
                              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Chunks</div>
                              <div style={{ fontWeight: 600 }}>{detail.chunks?.length ?? 0}</div>
                            </div>
                          </div>
                          {detail.column_metadata?.columns && (
                            <div>
                              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Column Names</div>
                              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                {detail.column_metadata.columns.map((c: string, i: number) => (
                                  <span key={i} className="badge pending" style={{ fontSize: 11 }}>
                                    {c} ({detail.column_metadata.dtypes?.[i] || '?'})
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
              {datasets.length === 0 && (
                <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 48 }}>
                  <Database size={32} style={{ marginBottom: 12, opacity: 0.3 }} /><br />
                  No datasets uploaded yet. Upload CSV, JSON, or Parquet files.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
