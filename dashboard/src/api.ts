const API_BASE = import.meta.env.VITE_API_URL || 'https://nexaris-750648121075.europe-west1.run.app/api/v1';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('desci_token');
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  // Handle auth expiry — clear token and force re-login
  if (res.status === 401) {
    localStorage.removeItem('desci_token');
    localStorage.removeItem('desci_user_id');
    window.location.reload();
    throw new ApiError('Session expired', 401);
  }

  if (res.status === 429) {
    throw new ApiError('Rate limited — please wait', 429);
  }

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(`API error: ${res.status} ${body}`, res.status);
  }

  // Handle binary responses (downloads)
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/zip') || contentType.includes('text/csv')) {
    return res.blob() as any;
  }

  return res.json();
}

async function uploadFile(path: string, file: File): Promise<any> {
  const token = localStorage.getItem('desci_token');
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(`Upload error: ${res.status} ${body}`, res.status);
  }

  return res.json();
}

export const api = {
  // Auth
  login: async (email: string, password: string) => {
    const data = await request<{ access_token: string; user_id: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('desci_token', data.access_token);
    localStorage.setItem('desci_user_id', data.user_id);
    return data;
  },

  register: (email: string, password: string) =>
    request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  // Stats
  getStats: () => request<{
    total_users: number;
    active_devices: number;
    total_jobs: number;
    active_jobs: number;
    completed_tasks: number;
    pending_tasks: number;
    total_compute_hours: number;
    avg_reward_multiplier: number;
  }>('/stats/'),

  // Jobs
  getJobs: (mine = false) => request<any[]>(`/jobs/${mine ? '?mine=true' : ''}`),
  createJob: (job: any) =>
    request('/jobs/', { method: 'POST', body: JSON.stringify(job) }),
  getJobProgress: (jobId: string) => request<any>(`/jobs/${jobId}/progress`),
  getJobResults: (jobId: string) => request<any>(`/jobs/${jobId}/results`),
  getJobAggregates: (jobId: string) => request<any>(`/jobs/${jobId}/aggregates`),
  getJobReport: (jobId: string) => request<any>(`/jobs/${jobId}/reports`),
  downloadJobResults: (jobId: string, format: string = 'json') =>
    request<any>(`/jobs/${jobId}/download?format=${format}`),

  // Datasets
  uploadDataset: (file: File) => uploadFile('/datasets/upload', file),
  getDatasets: () => request<any[]>('/datasets/'),
  getDatasetDetail: (id: string) => request<any>(`/datasets/${id}`),
  deleteDataset: (id: string) => request('/datasets/' + id, { method: 'DELETE' }),

  // Leaderboard
  getLeaderboard: (limit = 50) =>
    request<{ leaderboard: any[] }>(`/leaderboard/?limit=${limit}`),

  // MCP
  getMCPStatus: () => request<any>('/mcp/status'),
  getMCPCampaigns: () => request<any>('/mcp/campaigns'),
  getNetworkHealth: () => request<any>('/mcp/health'),
  getRetention: () => request<any>('/mcp/retention'),

  // Campaigns Competition
  getActiveCampaigns: () => request<any>('/campaigns/active'),
  getCampaignDetail: (id: string) => request<any>(`/campaigns/${id}`),
  getCampaignLeaderboard: (id: string) => request<any>(`/campaigns/${id}/leaderboard`),
  joinCampaign: (id: string) => request<any>(`/campaigns/${id}/join`, { method: 'POST' }),

  // Treasury / Wallet
  getTreasury: () => request<any>('/treasury/balance'),
  depositTreasury: (data: { tx_signature: string; amount_sol: number; wallet_address: string; campaign_id?: string }) =>
    request<any>('/treasury/deposit', { method: 'POST', body: JSON.stringify(data) }),
  getWalletHistory: () => request<any>('/wallet/history'),
  getUserRankings: () => request<any>('/user/rankings'),

  // Health
  getHealth: () => request<{ status: string; version: string; ws_connections: number }>('/health'),
};
