# Changelog

All notable changes to Proof Ledger. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The project has no version tags yet, so
past entries are grouped by merged pull request and date.

Every change adds an entry under **Unreleased** in the same pull request: what changed for someone
running or deploying the app, not a list of files.

## [Unreleased]

### Added
- Vercel deployment on the Python runtime: `vercel.json` (build command, 30 s function limit,
  bundle exclusions), `vercel-build.sh`, `.python-version` (3.12), `.vercelignore`, and the
  entrypoint pinned in `pyproject.toml` (`[tool.vercel]`).
- Production builds on Vercel run `migrate`, `seed_demo` and a one-time `createsuperuser`. Preview
  builds only collect static files and never touch the database.
- `docs/deployment.md`: setup, environment variables, how Vercel changes settings, limits and
  troubleshooting.
- `tests/test_settings.py` covering the Vercel and default settings paths.
- This changelog.
- `sync_github` flags: `--include-forks`, `--include-archived`, and `--prune` (deletes proofs for
  repos GitHub no longer lists, such as renamed or deleted ones).

### Changed
- On Vercel (`VERCEL` set), `DEBUG` defaults to off, the production, branch and deployment
  hostnames are added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`, and database connections
  aren't kept between requests (`CONN_MAX_AGE` 0; override with `DB_CONN_MAX_AGE`).
- On Vercel, a missing `DATABASE_URL` stops startup with a clear error. It no longer falls back to
  SQLite, which can't write to the read-only filesystem.
- README "Deploy" section now covers Vercel, with Render and Docker kept as fallbacks.
- `sync_github` now reads every repo the account owns. With `GITHUB_TOKEN` set it uses the
  authenticated `/user/repos` endpoint, so private repos count too; without a token it still sees
  public repos only. It prints how many repos it found and how many it skipped as forks or archived,
  so a short count is explained instead of silent.

## 2026-10-12: Dashboard motion and review fixes (#3)

### Added
- Half-life map: every skill plotted on one normalized decay curve, with fresh, fading and stale bands
  and a "no proof" column.
- Live "points fading a day" total and ticker, a filterable proof list with kind chips, and motion
  (scroll reveal, count-ups, the "revived" animation after Mark revised) in `motion.js`. All of it
  respects `prefers-reduced-motion`.
- `sync_github` pages through every public repo (up to 1,000) and also links skills by each repo's
  primary language.

### Fixed
- Dashboard template tags that a formatter had split across lines, which made `/` fail with
  `TemplateSyntaxError` and printed raw `{{ ... }}` text.
- Removed `Skill` fields that clashed with the `Proof.skills` relation and the query annotations.
- The half-life map no longer crashes when many skills share a column, keeps "no proof" pins inside
  the chart, and colours each pin to match its band.
- Funnel bars render at their width again.
- Sections stay visible if `motion.js` fails to load or throws.
- The dashboard no longer loads private `star_answer` drafts, and the decay ticker pauses when it's
  off-screen or the tab is hidden.

## 2026-10-12: Notes (#2)

### Added
- First `NOTES.md` entries (mistakes and their fixes).

## 2026-10-11: Deploy scripts (#1)

### Fixed
- Render runs `build.sh` and `start.sh` through `sh`, so a lost executable bit can't break a deploy.

## 2026-10-11: Initial release

### Added
- Django dashboard for skills, the proof behind them and freshness decay, plus the job-application
  funnel, reply rate by resume variant and weekly snapshots.
- Unfold admin, read-only throttled API (`/api/v1/`), and the `seed_demo`, `sync_github`,
  `link_check` and `weekly_digest` commands.
- Render blueprint, Dockerfile and docker-compose, and GitHub Actions CI (ruff and pytest with 85%
  coverage).
