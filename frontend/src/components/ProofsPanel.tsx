import { useMemo, useState } from 'react';
import { KIND_LABELS, type Proof } from '../types';

export function ProofsPanel({ proofs }: { proofs: Proof[] }) {
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState<'all' | Proof['kind']>('all');

  const kinds = useMemo(() => {
    const counts = new Map<Proof['kind'], number>();
    proofs.forEach((p) => counts.set(p.kind, (counts.get(p.kind) ?? 0) + 1));
    return Array.from(counts.entries());
  }, [proofs]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return proofs.filter((p) => {
      if (kind !== 'all' && p.kind !== kind) return false;
      if (!q) return true;
      return (
        p.title.toLowerCase().includes(q) ||
        p.metric.toLowerCase().includes(q) ||
        p.skills.some((s) => s.toLowerCase().includes(q))
      );
    });
  }, [proofs, query, kind]);

  return (
    <section className="panel proofs-panel" aria-labelledby="proofs-h">
      <div className="panel-head">
        <div>
          <h2 id="proofs-h">Proof library</h2>
          <p className="muted">Repositories, case studies and metrics that back a skill.</p>
        </div>
        <span className="count-pill">{visible.length} / {proofs.length}</span>
      </div>

      <div className="tools">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search proofs, metrics or skills…"
          aria-label="Search proofs"
        />
        <div className="chips">
          <button type="button" className="chip" aria-pressed={kind === 'all'} onClick={() => setKind('all')}>
            All <span>{proofs.length}</span>
          </button>
          {kinds.map(([k, n]) => (
            <button key={k} type="button" className="chip" aria-pressed={kind === k} onClick={() => setKind(k)}>
              {KIND_LABELS[k]} <span>{n}</span>
            </button>
          ))}
        </div>
      </div>

      {visible.length === 0 ? (
        <p className="empty">No proofs match this filter.</p>
      ) : (
        <ul className="proof-grid">
          {visible.map((proof) => (
            <li key={proof.id} className="proof-card">
              <div className="proof-top">
                <span className={`kind kind-${proof.kind}`}>{KIND_LABELS[proof.kind]}</span>
                {!proof.link_ok && <span className="dead">dead link</span>}
              </div>
              <h3>
                {proof.url ? (
                  <a href={proof.url} target="_blank" rel="noreferrer">
                    {proof.title}
                  </a>
                ) : (
                  proof.title
                )}
              </h3>
              {proof.metric && <p className="metric">{proof.metric}</p>}
              <p className="proof-date">
                {new Date(proof.occurred_at).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                })}
              </p>
              {proof.skills.length > 0 && (
                <div className="skill-tags">
                  {proof.skills.map((skill) => (
                    <span key={skill}>{skill}</span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
