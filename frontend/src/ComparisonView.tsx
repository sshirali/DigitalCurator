import { useEffect, useState } from 'react';
import { fetchGroup, postDecision } from './api';
import type { DuplicateGroup, GroupMember } from './types';

const decisionColor: Record<GroupMember['decision'], string> = {
  keep: '#2ecc71',
  delete: '#e74c3c',
  undecided: '#95a5a6',
};

interface ComparisonViewProps {
  groupId: number;
  onDecisionChange: (fileId: number, decision: 'keep' | 'delete') => void;
}

export default function ComparisonView({ groupId, onDecisionChange }: ComparisonViewProps) {
  const [group, setGroup] = useState<DuplicateGroup | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGroup(groupId)
      .then(setGroup)
      .catch((e: Error) => setError(e.message));
  }, [groupId]);

  async function applyWinner(winnerId: number) {
    if (!group) return;
    const updates: { id: number; decision: 'keep' | 'delete' }[] = group.members.map((m) => ({
      id: m.id,
      decision: m.id === winnerId ? 'keep' : 'delete',
    }));
    await Promise.all(updates.map(({ id, decision }) => postDecision(id, decision)));
    setGroup((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        winner_id: winnerId,
        members: prev.members.map((m) => ({
          ...m,
          decision: m.id === winnerId ? 'keep' : 'delete',
        })),
      };
    });
    updates.forEach(({ id, decision }) => onDecisionChange(id, decision));
  }

  if (error) return <div style={{ color: '#e74c3c', padding: 16 }}>Error: {error}</div>;
  if (!group) return <div style={{ padding: 16, color: '#888' }}>Loading…</div>;

  return (
    <div style={{ padding: 12 }}>
      {group.winner_id != null && (
        <div style={{ marginBottom: 10 }}>
          <button
            onClick={() => group.winner_id != null && applyWinner(group.winner_id)}
            style={{
              padding: '6px 16px',
              background: '#2ecc71',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: 13,
            }}
          >
            Keep Best ⭐
          </button>
        </div>
      )}
    <div style={{ display: 'flex', gap: 12, overflowX: 'auto' }}>
      {group.members.map((member) => {
        const isWinner = member.id === group.winner_id;
        const resolution =
          member.width != null && member.height != null
            ? `${member.width}×${member.height}`
            : '—';
        const sharpness =
          member.laplacian_var != null ? member.laplacian_var.toFixed(1) : '—';

        return (
          <div
            key={member.id}
            style={{
              flex: '0 0 200px',
              border: '1px solid #ddd',
              borderRadius: 6,
              overflow: 'hidden',
              background: '#fafafa',
            }}
          >
            <div style={{ position: 'relative' }}>
              <img
                src={`/thumbs/${member.id}`}
                alt="thumbnail"
                onClick={() => applyWinner(member.id)}
                style={{
                  width: '100%',
                  display: 'block',
                  aspectRatio: '1',
                  objectFit: 'cover',
                  cursor: 'pointer',
                }}
              />
              {/* Decision badge */}
              <span
                style={{
                  position: 'absolute',
                  top: 6,
                  right: 6,
                  background: decisionColor[member.decision],
                  color: '#fff',
                  fontSize: 11,
                  padding: '2px 6px',
                  borderRadius: 10,
                  textTransform: 'capitalize',
                }}
              >
                {member.decision}
              </span>
              {/* Winner star */}
              {isWinner && (
                <span
                  style={{
                    position: 'absolute',
                    top: 6,
                    left: 6,
                    fontSize: 18,
                    lineHeight: 1,
                    filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.5))',
                  }}
                  title="Candidate winner"
                >
                  ⭐
                </span>
              )}
            </div>
            <div style={{ padding: '6px 8px', fontSize: 12, color: '#555' }}>
              <div>Resolution: {resolution}</div>
              <div>Sharpness: {sharpness}</div>
            </div>
            <div style={{ display: 'flex', gap: 4, padding: '0 6px 6px' }}>
              <button
                onClick={() => onDecisionChange(member.id, 'keep')}
                style={{
                  flex: 1,
                  padding: '4px 0',
                  background: member.decision === 'keep' ? '#2ecc71' : '#ecf0f1',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: member.decision === 'keep' ? 700 : 400,
                }}
              >
                Keep
              </button>
              <button
                onClick={() => onDecisionChange(member.id, 'delete')}
                style={{
                  flex: 1,
                  padding: '4px 0',
                  background: member.decision === 'delete' ? '#e74c3c' : '#ecf0f1',
                  color: member.decision === 'delete' ? '#fff' : '#333',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: member.decision === 'delete' ? 700 : 400,
                }}
              >
                Delete
              </button>
            </div>
          </div>
        );
      })}
    </div>
    </div>
  );
}
