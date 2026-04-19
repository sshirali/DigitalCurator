import { useState } from 'react';

interface SettingsPanelProps {
  onClose: () => void;
}

export default function SettingsPanel({ onClose }: SettingsPanelProps) {
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleWipe = async () => {
    const confirmed = window.confirm(
      'Are you sure you want to wipe all app data? This will delete the database and all cached thumbnails. This action cannot be undone.'
    );
    if (!confirmed) return;

    try {
      const res = await fetch('/wipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: 'WIPE' }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || res.statusText);
      }

      setStatus('success');
      setTimeout(() => window.location.reload(), 1500);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Unknown error');
      setStatus('error');
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Settings"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        width: 320,
        height: '100%',
        background: '#fff',
        boxShadow: '-2px 0 12px rgba(0,0,0,0.15)',
        padding: 24,
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Settings</h2>
        <button
          onClick={onClose}
          aria-label="Close settings"
          style={{
            background: 'none',
            border: 'none',
            fontSize: 20,
            cursor: 'pointer',
            color: '#555',
            lineHeight: 1,
          }}
        >
          ✕
        </button>
      </div>

      <hr style={{ margin: 0, borderColor: '#eee' }} />

      <div>
        <h3 style={{ margin: '0 0 8px', fontSize: 15, color: '#333' }}>Danger Zone</h3>
        <p style={{ margin: '0 0 12px', fontSize: 13, color: '#666' }}>
          Permanently removes the local database and all cached thumbnails. Original image files are not affected.
        </p>
        <button
          onClick={handleWipe}
          disabled={status === 'success'}
          style={{
            padding: '10px 16px',
            background: '#e74c3c',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: status === 'success' ? 'default' : 'pointer',
            fontWeight: 600,
            fontSize: 14,
            opacity: status === 'success' ? 0.6 : 1,
          }}
        >
          Wipe App Data
        </button>
      </div>

      {status === 'success' && (
        <p role="status" style={{ color: '#27ae60', fontWeight: 600, margin: 0 }}>
          App data wiped successfully
        </p>
      )}

      {status === 'error' && (
        <p role="alert" style={{ color: '#e74c3c', margin: 0 }}>
          Error: {errorMsg}
        </p>
      )}
    </div>
  );
}
