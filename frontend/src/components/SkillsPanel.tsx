import { useMemo, useState } from 'react';
import { LEVEL_LABELS, tierOf, type Skill, type Tier } from '../types';

interface SkillsPanelProps {
  skills: Skill[];
}

const TIERS: Array<{ id: Tier | 'all'; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'fresh', label: 'Fresh' },
  { id: 'fading', label: 'Fading' },
  { id: 'stale', label: 'Stale' },
];

export function SkillsPanel({ skills }: SkillsPanelProps) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [tier, setTier] = useState<Tier | 'all'>('all');

  const categories = useMemo(
    () => ['all', ...Array.from(new Set(skills.map((s) => s.category))).sort()],
    [skills],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return skills
      .filter((s) => (category === 'all' ? true : s.category === category))
      .filter((s) => (tier === 'all' ? true : tierOf(s.freshness) === tier))
      .filter((s) => (q ? s.name.toLowerCase().includes(q) : true))
      .sort((a, b) => a.freshness - b.freshness);
  }, [skills, query, category, tier]);

  return (
    <section className="panel" aria-labelledby="skills-h">
      <div className="panel-head">
        <div>
          <h2 id="skills-h">Skill freshness</h2>
          <p className="muted">Stalest first. A revision or new proof resets the clock.</p>
        </div>
        <span className="count-pill">{visible.length} shown</span>
      </div>

      <div className="tools">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search skills…"
          aria-label="Search skills"
        />
        <select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by category">
          {categories.map((c) => (
            <option key={c} value={c}>
              {c === 'all' ? 'All categories' : c}
            </option>
          ))}
        </select>
      </div>
      <div className="chips" role="group" aria-label="Filter by freshness">
        {TIERS.map((t) => (
          <button
            key={t.id}
            type="button"
            className="chip"
            aria-pressed={tier === t.id}
            onClick={() => setTier(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <p className="empty">No skills match these filters.</p>
      ) : (
        <ul className="skill-list">
          {visible.map((skill) => {
            const level = tierOf(skill.freshness);
            const pct = Math.round(skill.freshness * 100);
            return (
              <li key={skill.id} className="skill-row">
                <div className="skill-main">
                  <span className="skill-name">{skill.name}</span>
                  <span className="skill-meta">
                    {skill.category} · {LEVEL_LABELS[skill.level] ?? `Level ${skill.level}`} ·{' '}
                    {skill.proof_count} proof{skill.proof_count === 1 ? '' : 's'}
                  </span>
                </div>
                <div className="skill-score">
                  <span className={`tier-text ${level}`}>{pct}%</span>
                  <span className={`tag ${level}`}>{level}</span>
                </div>
                <div className="bar" aria-hidden="true">
                  <i className={level} style={{ width: `${Math.max(pct, 2)}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
