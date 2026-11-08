import type { DashboardData, Funnel, Proof, Skill, Summary } from './types';

const API_ROOT = '/api/v1';

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: { Accept: 'application/json' },
    signal,
  });
  if (!response.ok) {
    throw new Error(`${path} failed (${response.status} ${response.statusText})`);
  }
  return (await response.json()) as T;
}

/** All four public endpoints in parallel; any failure rejects the whole refresh. */
export async function fetchDashboard(signal?: AbortSignal): Promise<DashboardData> {
  const [summary, funnel, skills, proofs] = await Promise.all([
    getJson<Summary>('/summary/', signal),
    getJson<Funnel>('/funnel/', signal),
    getJson<Skill[]>('/skills/', signal),
    getJson<Proof[]>('/proofs/', signal),
  ]);
  return { summary, funnel, skills, proofs };
}
