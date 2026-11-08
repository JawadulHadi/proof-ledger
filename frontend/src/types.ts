export type Tier = 'fresh' | 'fading' | 'stale';

export interface Skill {
  id: number;
  name: string;
  category: string;
  level: number;
  freshness: number;
  proof_count: number;
}

export interface Proof {
  id: number;
  title: string;
  kind: 'repo' | 'case' | 'metric';
  url: string;
  metric: string;
  occurred_at: string;
  link_ok: boolean;
  skills: string[];
}

export interface Summary {
  skills: number;
  unproven_skills: number;
  stale_skills: number;
  proofs: number;
  dead_links: number;
  applications: number;
}

export interface FunnelStage {
  status: string;
  label: string;
  n: number;
}

export interface VariantRow {
  variant: string;
  sent: number;
  responded: number;
  interviews: number;
  reply_rate: number;
}

export interface Funnel {
  stages: FunnelStage[];
  variants: VariantRow[];
}

export interface DashboardData {
  summary: Summary;
  funnel: Funnel;
  skills: Skill[];
  proofs: Proof[];
}

export const LEVEL_LABELS: Record<number, string> = {
  1: 'Learning',
  2: 'Working',
  3: 'Strong',
  4: 'Expert',
};

export const KIND_LABELS: Record<Proof['kind'], string> = {
  repo: 'Repository',
  case: 'Case study',
  metric: 'Metric',
};

export function tierOf(freshness: number): Tier {
  if (freshness >= 0.6) return 'fresh';
  if (freshness >= 0.3) return 'fading';
  return 'stale';
}
