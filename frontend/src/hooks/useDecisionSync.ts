import { useState, useEffect, useRef } from 'react';
import { postDecision, fetchDecisions } from '../api';

interface DecisionState {
  [fileId: number]: 'keep' | 'delete' | 'undecided';
}

export function useDecisionSync(): {
  decisions: DecisionState;
  recordDecision: (fileId: number, decision: 'keep' | 'delete') => Promise<void>;
} {
  const [decisions, setDecisions] = useState<DecisionState>({});
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    wsRef.current = ws;

    ws.onopen = async () => {
      try {
        const data = await fetchDecisions();
        const initial: DecisionState = {};
        for (const entry of data) {
          const d = entry.decision as 'keep' | 'delete' | 'undecided';
          initial[entry.file_id] = d;
        }
        setDecisions(initial);
      } catch (e) {
        console.error('Failed to load initial decisions:', e);
      }
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (Array.isArray(payload)) {
          const next: DecisionState = {};
          for (const entry of payload) {
            next[entry.file_id] = entry.decision as 'keep' | 'delete' | 'undecided';
          }
          setDecisions(next);
        } else if (payload && typeof payload === 'object' && 'file_id' in payload) {
          setDecisions(prev => ({
            ...prev,
            [payload.file_id]: payload.decision as 'keep' | 'delete' | 'undecided',
          }));
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
    };

    return () => {
      ws.close();
    };
  }, []);

  const recordDecision = async (fileId: number, decision: 'keep' | 'delete') => {
    await postDecision(fileId, decision);
  };

  return { decisions, recordDecision };
}
