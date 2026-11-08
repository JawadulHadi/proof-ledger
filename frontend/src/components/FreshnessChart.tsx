import { useMemo } from 'react';
import type { Skill } from '../types';

const W = 640;
const H = 190;
const PAD = { top: 14, right: 12, bottom: 26, left: 34 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

/** Every skill as a point, ranked from freshest to stalest, with the two tier thresholds. */
export function FreshnessChart({ skills }: { skills: Skill[] }) {
  const sorted = useMemo(
    () => [...skills].sort((a, b) => b.freshness - a.freshness),
    [skills],
  );

  if (sorted.length === 0) {
    return <p className="empty">No skills yet. Run <code>manage.py seed_demo</code>.</p>;
  }

  const x = (i: number) => PAD.left + (sorted.length === 1 ? PLOT_W / 2 : (i / (sorted.length - 1)) * PLOT_W);
  const y = (v: number) => PAD.top + (1 - v) * PLOT_H;
  const points = sorted.map((s, i) => `${x(i).toFixed(1)},${y(s.freshness).toFixed(1)}`).join(' ');
  const area = `${PAD.left},${y(0)} ${points} ${PAD.left + PLOT_W},${y(0)}`;

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Freshness by skill, freshest to stalest">
        <defs>
          <linearGradient id="freshnessFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.35" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0.6, 0.3].map((v) => (
          <g key={v}>
            <line className="grid" x1={PAD.left} x2={PAD.left + PLOT_W} y1={y(v)} y2={y(v)} />
            <text x={PAD.left - 6} y={y(v) + 4} textAnchor="end">
              {Math.round(v * 100)}%
            </text>
          </g>
        ))}
        <line className="grid" x1={PAD.left} x2={PAD.left + PLOT_W} y1={y(0)} y2={y(0)} />
        <polygon points={area} fill="url(#freshnessFill)" />
        <polyline points={points} className="freshness-line" />
        {sorted.map((s, i) => (
          <circle
            key={s.id}
            cx={x(i)}
            cy={y(s.freshness)}
            r={4.5}
            className={`dot tier-${s.freshness >= 0.6 ? 'fresh' : s.freshness >= 0.3 ? 'fading' : 'stale'}`}
          >
            <title>{`${s.name}: ${Math.round(s.freshness * 100)}% fresh`}</title>
          </circle>
        ))}
        <text x={PAD.left} y={H - 6}>
          freshest
        </text>
        <text x={PAD.left + PLOT_W} y={H - 6} textAnchor="end">
          stalest
        </text>
      </svg>
    </div>
  );
}
