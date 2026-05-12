import { useEffect, useState, useCallback } from 'react';
import { useWallet, useConnection } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { LAMPORTS_PER_SOL, PublicKey, SystemProgram, Transaction } from '@solana/web3.js';
import { Wallet, ArrowUpRight, ArrowDownRight, Clock, Zap, Shield, ExternalLink } from 'lucide-react';
import { api } from '../api';

const TREASURY_ADDRESS = import.meta.env.VITE_TREASURY_WALLET || '';

export default function TreasuryPage() {
  const { publicKey, sendTransaction, connected } = useWallet();
  const { connection } = useConnection();
  const [solBalance, setSolBalance] = useState<number | null>(null);
  const [treasury, setTreasury] = useState<any>(null);
  const [history, setHistory] = useState<any>({ deposits: [], rewards: [] });
  const [depositAmount, setDepositAmount] = useState('0.1');
  const [sending, setSending] = useState(false);
  const [txResult, setTxResult] = useState<{ sig: string; success: boolean } | null>(null);

  // Load balance when wallet connects
  useEffect(() => {
    if (!publicKey || !connection) return;
    connection.getBalance(publicKey).then(b => setSolBalance(b / LAMPORTS_PER_SOL)).catch(() => {});
  }, [publicKey, connection]);

  // Load treasury and history
  useEffect(() => {
    api.getTreasury().then(setTreasury).catch(() => {});
    api.getWalletHistory().then(setHistory).catch(() => {});
    const iv = setInterval(() => {
      api.getTreasury().then(setTreasury).catch(() => {});
    }, 10000);
    return () => clearInterval(iv);
  }, []);

  const handleDeposit = useCallback(async () => {
    if (!publicKey || !connection || !TREASURY_ADDRESS) return;
    setSending(true);
    setTxResult(null);

    try {
      const amount = parseFloat(depositAmount);
      if (isNaN(amount) || amount <= 0) throw new Error('Invalid amount');

      const treasuryPubkey = new PublicKey(TREASURY_ADDRESS);
      const lamports = Math.round(amount * LAMPORTS_PER_SOL);

      const tx = new Transaction().add(
        SystemProgram.transfer({
          fromPubkey: publicKey,
          toPubkey: treasuryPubkey,
          lamports,
        })
      );

      const sig = await sendTransaction(tx, connection);
      await connection.confirmTransaction(sig, 'confirmed');

      // Record deposit on backend
      await api.depositTreasury({
        tx_signature: sig,
        amount_sol: amount,
        wallet_address: publicKey.toBase58(),
      });

      setTxResult({ sig, success: true });

      // Refresh balances
      const newBal = await connection.getBalance(publicKey);
      setSolBalance(newBal / LAMPORTS_PER_SOL);
      api.getTreasury().then(setTreasury).catch(() => {});
      api.getWalletHistory().then(setHistory).catch(() => {});
    } catch (err: any) {
      console.error('Deposit failed:', err);
      setTxResult({ sig: '', success: false });
    } finally {
      setSending(false);
    }
  }, [publicKey, connection, depositAmount, sendTransaction]);

  return (
    <>
      <div className="page-header">
        <h2>💎 Solana Treasury</h2>
        <p>Fund campaigns with SOL · Phantom Wallet · Devnet</p>
      </div>

      {/* Wallet connection */}
      <div className="card" style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>
            {connected ? '🟢 Wallet Connected' : '🔴 Wallet Not Connected'}
          </div>
          {connected && publicKey && (
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
              {publicKey.toBase58().slice(0, 8)}…{publicKey.toBase58().slice(-8)}
              {solBalance !== null && (
                <span style={{ marginLeft: 12, color: 'var(--cyan)', fontWeight: 700 }}>
                  {solBalance.toFixed(4)} SOL
                </span>
              )}
            </div>
          )}
        </div>
        <WalletMultiButton />
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon cyan"><Wallet size={24} /></div>
          <div>
            <div className="stat-value">{treasury?.sol_balance?.toFixed(4) ?? '—'}</div>
            <div className="stat-label">Treasury SOL</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><ArrowDownRight size={24} /></div>
          <div>
            <div className="stat-value">{treasury?.total_deposits?.toFixed(4) ?? '0'}</div>
            <div className="stat-label">Total Deposited</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber"><ArrowUpRight size={24} /></div>
          <div>
            <div className="stat-value">{treasury?.total_rewards_distributed?.toFixed(4) ?? '0'}</div>
            <div className="stat-label">Rewards Distributed</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon purple"><Shield size={24} /></div>
          <div>
            <div className="stat-value">{((treasury?.utilization_rate ?? 0) * 100).toFixed(1)}%</div>
            <div className="stat-label">Utilization Rate</div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Deposit Panel */}
        <div className="card">
          <div className="card-title">Fund Treasury</div>
          {connected ? (
            <div style={{ display: 'grid', gap: 16 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>Amount (SOL)</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['0.05', '0.1', '0.5', '1.0'].map(v => (
                    <button key={v} onClick={() => setDepositAmount(v)} style={{
                      padding: '6px 14px', borderRadius: 'var(--radius-sm)',
                      border: `1px solid ${depositAmount === v ? 'var(--cyan)' : 'var(--glass-border)'}`,
                      background: depositAmount === v ? 'var(--cyan-dim)' : 'var(--glass)',
                      color: depositAmount === v ? 'var(--cyan)' : 'var(--text-secondary)',
                      cursor: 'pointer', fontSize: 13, fontWeight: 600, fontFamily: 'inherit',
                    }}>{v} SOL</button>
                  ))}
                </div>
                <input
                  type="number" step="0.01" min="0.001"
                  value={depositAmount} onChange={e => setDepositAmount(e.target.value)}
                  className="form-input" style={{ marginTop: 12 }}
                />
              </div>

              {TREASURY_ADDRESS && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Treasury: <span style={{ fontFamily: 'monospace' }}>{TREASURY_ADDRESS.slice(0, 12)}…</span>
                </div>
              )}

              <button
                className="btn btn-primary"
                onClick={handleDeposit}
                disabled={sending || !TREASURY_ADDRESS}
                style={{ width: '100%', justifyContent: 'center' }}
              >
                {sending ? '⏳ Sending…' : `Deposit ${depositAmount} SOL`}
              </button>

              {!TREASURY_ADDRESS && (
                <div style={{ fontSize: 12, color: 'var(--amber)', padding: 8, background: 'var(--amber-dim)', borderRadius: 'var(--radius-sm)' }}>
                  ⚠️ Set VITE_TREASURY_WALLET in .env to enable deposits
                </div>
              )}

              {txResult && (
                <div style={{
                  padding: 12, borderRadius: 'var(--radius-sm)',
                  background: txResult.success ? 'rgba(0,200,83,0.1)' : 'rgba(255,82,82,0.1)',
                  border: `1px solid ${txResult.success ? 'var(--green)' : 'var(--red)'}`,
                }}>
                  {txResult.success ? (
                    <>
                      <div style={{ fontWeight: 700, color: 'var(--green)', marginBottom: 4 }}>✅ Deposit Confirmed!</div>
                      <a
                        href={`https://explorer.solana.com/tx/${txResult.sig}?cluster=devnet`}
                        target="_blank" rel="noopener noreferrer"
                        style={{ fontSize: 12, color: 'var(--cyan)', display: 'flex', alignItems: 'center', gap: 4 }}
                      >
                        View on Solana Explorer <ExternalLink size={12} />
                      </a>
                    </>
                  ) : (
                    <div style={{ color: 'var(--red)', fontWeight: 600 }}>❌ Transaction failed</div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
              Connect your Phantom wallet to fund the treasury
            </div>
          )}
        </div>

        {/* Transaction History */}
        <div className="card">
          <div className="card-title">Transaction History</div>
          {(history.deposits?.length > 0 || history.rewards?.length > 0) ? (
            <div style={{ display: 'grid', gap: 8, maxHeight: 350, overflowY: 'auto' }}>
              {[...(history.deposits || []), ...(history.rewards || [])]
                .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                .map((tx: any, i: number) => (
                <div key={i} style={{
                  padding: '10px 14px', background: 'var(--glass)', borderRadius: 'var(--radius-sm)',
                  borderLeft: `3px solid ${tx.type === 'deposit' ? 'var(--green)' : 'var(--amber)'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {tx.type === 'deposit' ? <ArrowDownRight size={14} style={{ color: 'var(--green)' }} /> : <ArrowUpRight size={14} style={{ color: 'var(--amber)' }} />}
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{tx.type === 'deposit' ? 'Deposit' : `Reward (${tx.tier})`}</span>
                    </div>
                    <span style={{ fontWeight: 700, color: tx.type === 'deposit' ? 'var(--green)' : 'var(--amber)' }}>
                      {tx.type === 'deposit' ? '+' : '+'}{tx.amount_sol?.toFixed(4)} SOL
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, display: 'flex', gap: 8 }}>
                    <span className={`badge ${tx.status === 'confirmed' ? 'active' : 'pending'}`} style={{ fontSize: 9 }}>{tx.status}</span>
                    {tx.tx_signature && (
                      <a href={`https://explorer.solana.com/tx/${tx.tx_signature}?cluster=devnet`}
                        target="_blank" rel="noopener noreferrer"
                        style={{ color: 'var(--cyan)', display: 'flex', alignItems: 'center', gap: 2, fontSize: 10 }}>
                        {tx.tx_signature.slice(0, 12)}… <ExternalLink size={10} />
                      </a>
                    )}
                    <span>{tx.created_at ? new Date(tx.created_at).toLocaleString() : ''}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
              <Clock size={32} style={{ opacity: 0.3, marginBottom: 8 }} /><br />
              No transactions yet
            </div>
          )}
        </div>
      </div>
    </>
  );
}
