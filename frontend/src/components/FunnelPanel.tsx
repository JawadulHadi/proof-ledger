import type { Funnel, FunnelStage, VariantRow } from '../types';

function maxOf(stages: FunnelStage[]) {
  return Math.max(1, ...stages.map((s) => s.n));
}

export function FunnelPanel({ funnel }: { funnel: Funnel }) {
  const top = maxOf(funnel.stages);
  return (
    <section className="panel" aria-labelledby="funnel-h">
      <div className="panel-head">
        <div>
          <h2 id="funnel-h">Application funnel</h2>
          <p className="muted">Every stage, including empty ones.</p>
        </div>
      </div>
      <ul className="funnel-list">
        {funnel.stages.map((stage, index) => {
          const previous = index > 0 ? funnel.stages[index - 1].n : null;
          const stepRate =
            previous && previous > 0 ? Math.round((stage.n / previous) * 100) : null;
          return (
            <li key={stage.status}>
              <div className="funnel-label">
                <span>{stage.label}</span>
                <span className="funnel-n">
                  {stage.n}
                  {stepRate !== null && <small> · {stepRate}%</small>}
                </span>
              </div>
              <div className="bar" aria-hidden="true">
                <i className="stage" style={{ width: `${Math.max((stage.n / top) * 100, 1)}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function VariantsPanel({ variants }: { variants: VariantRow[] }) {
  return (
    <section className="panel" aria-labelledby="variants-h">
      <div className="panel-head">
        <div>
          <h2 id="variants-h">Resume variants</h2>
          <p className="muted">Which headline gets answers.</p>
        </div>
      </div>
      {variants.length === 0 ? (
        <p className="empty">No resume variants yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Variant</th>
                <th className="num">Sent</th>
                <th className="num">Replied</th>
                <th className="num">Interviews</th>
                <th>Reply rate</th>
              </tr>
            </thead>
            <tbody>
              {variants.map((row) => (
                <tr key={row.variant}>
                  <td className="variant-name">{row.variant}</td>
                  <td className="num">{row.sent}</td>
                  <td className="num">{row.responded}</td>
                  <td className="num">{row.interviews}</td>
                  <td>
                    <div className="rate">
                      <div className="bar" aria-hidden="true">
                        <i className="fresh" style={{ width: `${Math.round(row.reply_rate * 100)}%` }} />
                      </div>
                      <span>{Math.round(row.reply_rate * 100)}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
