interface HeaderProps {
  updatedAt: Date | null;
  loading: boolean;
  onRefresh: () => void;
}

export function Header({ updatedAt, loading, onRefresh }: HeaderProps) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          PL
        </span>
        <div>
          <strong>Proof Ledger</strong>
          <small>Skills fade. Proof keeps them fresh.</small>
        </div>
      </div>
      <nav className="topnav" aria-label="Sections">
        <a href="/">Classic view</a>
        <a href="/admin/">Admin</a>
        <a href="/api/v1/" target="_blank" rel="noreferrer">
          API
        </a>
        <button type="button" className="ghost" onClick={onRefresh} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </nav>
      <p className="stamp" aria-live="polite">
        {updatedAt
          ? `Updated ${updatedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
          : 'Loading live data…'}
      </p>
    </header>
  );
}
