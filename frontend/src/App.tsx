import { FreshnessChart } from './components/FreshnessChart';
import { FunnelPanel, VariantsPanel } from './components/FunnelPanel';
import { Header } from './components/Header';
import { ProofsPanel } from './components/ProofsPanel';
import { SkillsPanel } from './components/SkillsPanel';
import { StatGrid } from './components/StatGrid';
import { useDashboard } from './useDashboard';

export default function App() {
  const { data, error, loading, updatedAt, refresh } = useDashboard();

  return (
    <>
      <Header updatedAt={updatedAt} loading={loading} onRefresh={refresh} />
      <main>
        {error && (
          <div className="alert" role="alert">
            <strong>Could not refresh.</strong> {error}
            {data && ' Showing the last successful snapshot.'}
            <button type="button" className="ghost" onClick={refresh}>
              Retry
            </button>
          </div>
        )}

        {!data ? (
          <div className="loading-grid" aria-busy="true" aria-label="Loading dashboard">
            <div className="skeleton tall" />
            <div className="skeleton" />
            <div className="skeleton" />
            <div className="skeleton" />
          </div>
        ) : (
          <>
            <section className="hero">
              <div className="hero-copy">
                <p className="eyebrow">Live dashboard</p>
                <h1>Skills fade. Proof keeps them fresh.</h1>
                <p className="lede">
                  Every skill loses freshness the longer it goes without a revision or new proof. A
                  repo, case study or metric resets the clock. This view is served by the React +
                  TypeScript client on top of the Django REST API.
                </p>
              </div>
              <div className="panel chart-panel">
                <div className="panel-head">
                  <div>
                    <h2>Freshness curve</h2>
                    <p className="muted">One point per skill, freshest to stalest.</p>
                  </div>
                </div>
                <FreshnessChart skills={data.skills} />
              </div>
            </section>

            <StatGrid summary={data.summary} />

            {data.summary.unproven_skills > 0 && (
              <p className="banner" role="note">
                <b>
                  {data.summary.unproven_skills} skill
                  {data.summary.unproven_skills === 1 ? '' : 's'} without proof.
                </b>{' '}
                Link a repo, case study or metric so the claim is backed.
              </p>
            )}

            <div className="main-grid">
              <SkillsPanel skills={data.skills} />
              <div className="side-col">
                <FunnelPanel funnel={data.funnel} />
                <VariantsPanel variants={data.funnel.variants} />
              </div>
            </div>

            <ProofsPanel proofs={data.proofs} />
          </>
        )}
      </main>
      <footer>
        <span>Proof Ledger · Django + React/TypeScript</span>
        <span>
          <a href="/">Classic dashboard</a> · <a href="/admin/">Admin</a> ·{' '}
          <a href="/api/v1/">REST API</a>
        </span>
      </footer>
    </>
  );
}
