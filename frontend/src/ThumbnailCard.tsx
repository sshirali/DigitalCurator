import type { FileRecord } from './types';

const decisionColor: Record<FileRecord['decision'], string> = {
  keep: '#2ecc71',
  delete: '#e74c3c',
  undecided: '#95a5a6',
};

interface ThumbnailCardProps {
  file: FileRecord;
  onDecision: (id: number, decision: 'keep' | 'delete') => void;
}

export default function ThumbnailCard({ file, onDecision }: ThumbnailCardProps) {
  return (
    <div
      style={{
        border: '1px solid #ddd',
        borderRadius: 6,
        overflow: 'hidden',
        background: '#fafafa',
      }}
    >
      <div style={{ position: 'relative' }}>
        <img
          src={`/thumbs/${file.id}`}
          alt="thumbnail"
          style={{ width: '100%', display: 'block', aspectRatio: '1', objectFit: 'cover' }}
        />
        {/* Decision badge: gray=undecided, green=keep, red=delete */}
        <span
          style={{
            position: 'absolute',
            top: 6,
            right: 6,
            background: decisionColor[file.decision],
            color: '#fff',
            fontSize: 11,
            padding: '2px 6px',
            borderRadius: 10,
            textTransform: 'capitalize',
          }}
        >
          {file.decision}
        </span>
      </div>
      <div style={{ display: 'flex', gap: 4, padding: 6 }}>
        <button
          onClick={() => onDecision(file.id, 'keep')}
          style={{
            flex: 1,
            padding: '4px 0',
            background: file.decision === 'keep' ? '#2ecc71' : '#ecf0f1',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 12,
            fontWeight: file.decision === 'keep' ? 700 : 400,
          }}
        >
          Keep
        </button>
        <button
          onClick={() => onDecision(file.id, 'delete')}
          style={{
            flex: 1,
            padding: '4px 0',
            background: file.decision === 'delete' ? '#e74c3c' : '#ecf0f1',
            color: file.decision === 'delete' ? '#fff' : '#333',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 12,
            fontWeight: file.decision === 'delete' ? 700 : 400,
          }}
        >
          Delete
        </button>
      </div>
    </div>
  );
}
