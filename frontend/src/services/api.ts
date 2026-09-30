import { SourceType, ResearchRun, ResearchSummary } from '../types/research';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function createResearchRun(sourceType: SourceType, sourceInput: string): Promise<{ research_run_id: string }> {
  const res = await fetch(`${API_BASE}/api/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_type: sourceType, source_input: sourceInput.trim() })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to initiate research');
  }

  const data = await res.json();
  return {
    research_run_id: data.research_run_id || data.run_id || data.id
  };
}

export async function getResearchStatus(runId: string): Promise<ResearchRun> {
  const res = await fetch(`${API_BASE}/api/research/${runId}/status`);
  if (!res.ok) {
    throw new Error('Failed to retrieve research status');
  }
  return res.json();
}

export async function getResearchSummary(runId: string): Promise<ResearchSummary> {
  const res = await fetch(`${API_BASE}/api/research/${runId}/summary`);
  if (!res.ok) {
    throw new Error('Failed to retrieve research summary');
  }
  return res.json();
}

export async function generateGoogleDoc(runId: string): Promise<{ url: string }> {
  const res = await fetch(`${API_BASE}/api/research/${runId}/generate-google-doc`, {
    method: 'POST'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Google Docs credentials not configured');
  }
  return res.json();
}

export function getPdfDownloadUrl(runId: string): string {
  return `${API_BASE}/api/research/${runId}/report/pdf`;
}
