import type { Category, DuplicateGroup, FileRecord } from './types';

export async function fetchTriage(category: Category): Promise<FileRecord[]> {
  const res = await fetch(`/triage/${category}`);
  if (!res.ok) throw new Error(`Failed to fetch triage: ${res.statusText}`);
  return res.json();
}

export async function postDecision(fileId: number, decision: 'keep' | 'delete'): Promise<void> {
  const res = await fetch(`/decisions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId, decision }),
  });
  if (!res.ok) throw new Error(`Failed to post decision: ${res.statusText}`);
}

export async function fetchDecisions(): Promise<{ file_id: number; decision: string; timestamp: number }[]> {
  const res = await fetch('/decisions');
  if (!res.ok) throw new Error(`Failed to fetch decisions: ${res.statusText}`);
  return res.json();
}

export async function fetchGroup(groupId: number): Promise<DuplicateGroup> {
  const res = await fetch(`/groups/${groupId}`);
  if (!res.ok) throw new Error(`Failed to fetch group: ${res.statusText}`);
  return res.json();
}
