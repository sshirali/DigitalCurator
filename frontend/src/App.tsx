import { useState, useEffect, useCallback } from 'react';
import type { Category, FileRecord } from './types';
import { fetchTriage } from './api';
import ThumbnailCard from './ThumbnailCard';
import { useDecisionSync } from './hooks/useDecisionSync';
import SettingsPanel from './SettingsPanel';

const TABS: { label: string; category: Category }[] = [
  { label: 'Duplicates', category: 'duplicates' },
  { label: 'Screenshots', category: 'screenshots' },
  { label: 'Blurry', category: 'blurry' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<Category>('duplicates');
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const { decisions, recordDecision } = useDecisionSync();

  const loadTab = useCallback(async (category: Category) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTriage(category);
      setFiles(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTab(activeTab);
  }, [activeTab, loadTab]);

  const handleDecision = async (fileId: number, decision: 'keep' | 'delete') => {
    await recordDecision(fileId, decision);
    setFiles(prev =>
      prev.map(f => (f.id === fileId ? { ...f, decision } : f))
    );
  };

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 960, margin: '0 auto', padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, margin: 0 }}>Digital Curator</h1>
        <button
          onClick={() => setShowSettings(s => !s)}
          aria-label="Open settings"
          style={{
            padding: '6px 14px',
            border: '1px solid #ccc',
            borderRadius: 4,
            background: showSettings ? '#f0f0f0' : '#fff',
            cursor: 'pointer',
            fontSize: 14,
            color: '#333',
          }}
        >
          ⚙ Settings
        </button>
      </div>

      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}

      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '2px solid #ddd', marginBottom: 16 }}>
        {TABS.map(({ label, category }) => (
          <button
            key={category}
            onClick={() => setActiveTab(category)}
            style={{
              padding: '8px 20px',
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              fontWeight: activeTab === category ? 700 : 400,
              borderBottom: activeTab === category ? '2px solid #3498db' : '2px solid transparent',
              marginBottom: -2,
              color: activeTab === category ? '#3498db' : '#555',
              fontSize: 15,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading && <p style={{ color: '#888' }}>Loading…</p>}
      {error && <p style={{ color: '#e74c3c' }}>Error: {error}</p>}

      {!loading && !error && files.length === 0 && (
        <p style={{ color: '#27ae60', fontSize: 18, textAlign: 'center', marginTop: 48 }}>
          All clean!
        </p>
      )}

      {!loading && !error && files.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: 12,
          }}
        >
          {files.map(file => (
            <ThumbnailCard
              key={file.id}
              file={{ ...file, decision: decisions[file.id] ?? file.decision }}
              onDecision={handleDecision}
            />
          ))}
        </div>
      )}
    </div>
  );
}
