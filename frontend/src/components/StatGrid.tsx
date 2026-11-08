import type { Summary } from '../types';

interface StatGridProps {
  summary: Summary;
}

export function StatGrid({ summary }: StatGridProps) {
  const cards = [
    { label: 'Skills tracked', value: summary.skills, tone: 'accent' },
    { label: 'Proofs linked', value: summary.proofs, tone: 'fresh' },
    { label: 'Stale skills', value: summary.stale_skills, tone: summary.stale_skills ? 'stale' : 'muted' },
    { label: 'Without proof', value: summary.unproven_skills, tone: summary.unproven_skills ? 'warn' : 'muted' },
    { label: 'Applications sent', value: summary.applications, tone: 'accent' },
    { label: 'Dead proof links', value: summary.dead_links, tone: summary.dead_links ? 'stale' : 'muted' },
  ];

  return (
    <ul className="stats" aria-label="Ledger totals">
      {cards.map((card) => (
        <li key={card.label} className={`stat tone-${card.tone}`}>
          <b>{card.value}</b>
          <span>{card.label}</span>
        </li>
      ))}
    </ul>
  );
}
