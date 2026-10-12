# Proof Ledger

A Django admin dashboard that tracks your skills, the proof behind each one, and your job-search
funnel. Skills lose freshness over time (a configurable half-life), so the dashboard always shows
what to revise next.

## Architecture

```mermaid
flowchart LR
    subgraph Users["Who uses it"]
        Visitor["Visitor"]
        Staff["Staff user"]
        You["You, from the shell"]
    end

    subgraph Django["Django project · config/urls.py"]
        Dash["/ · views.dashboard<br/>skills sorted by freshness, funnel"]
        Revise["POST /skills/:pk/revise/<br/>staff only, returns row partial"]
        Admin["/admin/ · Unfold ModelAdmin<br/>freshness badge, mark_revised action,<br/>dashboard_callback"]
        API["/api/v1/ · DRF, read-only<br/>skills, proofs, summary<br/>(star_answer never exposed)"]
        Agg["core/dashboard.py<br/>annotate last_proof + proof_count<br/>(no N+1)"]
        Cmds["manage.py commands<br/>seed_demo · sync_github · weekly_digest"]
    end

    Visitor --> Dash & API
    Staff --> Revise & Admin
    You --> Cmds
    Dash & Admin & Cmds --> Agg

    subgraph Models["core/models.py"]
        Skill["Skill<br/>freshness = exp(-ln2 · days / half_life)"]
        Proof["Proof<br/>repo / case / metric"]
        Note["RevisionNote"]
        Variant["ResumeVariant"]
        App["Application<br/>saved → applied → replied →<br/>interview → offer / rejected"]
        Snap["MetricSnapshot (weekly)"]
        Proof -- "M2M" --> Skill
        Note -- "FK" --> Skill
        App -- "FK" --> Variant
    end

    Agg & API & Revise --> Models
    Models --> DB[("SQLite by default<br/>PostgreSQL 16 when POSTGRES_DB set")]

    Cmds -- "sync_github: repos → Proof,<br/>topics matched to Skill names" --> GH[("GitHub REST API<br/>/users/GITHUB_USER/repos")]
```

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

- Public dashboard: [http://localhost:8000/](http://localhost:8000/)
- Admin: [http://localhost:8000/admin/](http://localhost:8000/admin/)
- API: [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/) (read-only)

Or with Postgres: `docker compose up`.

## Commands

| Command                  | What it does                                                                                                                                                                                |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `seed_demo`              | Creates starter skills (with GitHub topic aliases) and resume variants. Edit levels to be honest.                                                                                           |
| `sync_github`            | Pulls all your public repos (paginated) as Proof rows and links skills by repo topic and primary language. Forks and archived repos are skipped. Set`GITHUB_USER`, optional `GITHUB_TOKEN`. |
| `link_check`             | Requests every proof URL and flags dead links (`link_ok`), shown on the dashboard and admin.                                                                                                |
| `weekly_digest [--save]` | Prints a markdown plan: stale skills, unproven skills, funnel, reply rate per resume variant, next actions.`--save` stores this week's numbers as a `MetricSnapshot`.                       |

## What the dashboard shows

- **Public page (`/`)**: the interactive decay curve (with a Play button), totals with a live
  "points fading a day" ticker, a banner for skills with no proof, the half-life map, every skill by
  freshness (staff can mark one revised in place with HTMX), every proof with a filter and kind chips,
  the application funnel and reply rate by resume variant.
- **Half-life map**: every skill plotted on one curve by half-lives idle (`0.5 ** n`), so skills with
  different half-lives compare directly and the fresh/fading/stale bands are fixed. Skills with no
  revision or proof sit in a "no proof" column. Hover or focus a pin for its name; click to jump to its row.
- **Motion**: sections reveal on scroll, bars sweep in, totals count up. Mark revised refills the bar,
  counts the percent up, floats a +N chip and slides the skill's pin back to the top of the map. All of
  it is skipped under `prefers-reduced-motion`, and the page is complete without JavaScript.
- **Admin home**: the same numbers for you, plus the five skills to revise next and weekly snapshots.
- **API (`/api/v1/`)**: `skills/`, `proofs/`, `summary/` and `funnel/`, read-only, throttled, and the
  summary and funnel cached for 60 seconds.

### Topic-to-skill mapping

A repo topic proves a skill when it equals the skill's name (lowercased, spaces as dashes) or one of
its `github_topics`, for example `LLM integration` with `llm, agents`. Edit them in the admin.

## Quality

```bash
ruff check .
pytest --cov=core --cov-fail-under=85
```

Every change also adds an entry under **Unreleased** in `CHANGELOG.md` and updates the docs it
affects (this README, `docs/`, and `NOTES.md` for mistakes). The pull request template has a
checklist for it.

## Design notes

- Freshness is `exp(-ln2 * days / half_life)`, tested with frozen time.
- Admin querysets annotate the last proof date, so the list view has no N+1 queries (tested).
- The API never exposes `star_answer`, your private interview drafts (tested).
- "Responded" means replied, interview or offer; "sent" is anything past saved. Reply rate is per resume variant.
- Weekly snapshots count applications by `applied_on` week, so they can be re-saved without double counting.
- Marking a skill revised from the public page needs a logged-in staff user.

## Deploy (free)

**Vercel** (Python runtime) with a **Neon** Postgres database. The full guide is in
[docs/deployment.md](docs/deployment.md); the short version:

1. Create a Neon project in AWS `us-east-1` and copy its **pooled** connection string.
2. Import the repo in Vercel. `vercel.json` sets the build (`vercel-build.sh`) and the function
   (`config/wsgi.py`).
3. Set `SECRET_KEY` and `DATABASE_URL` (Production and Preview), plus `DJANGO_SUPERUSER_*`
   (Production) to create the admin user on the first production build.
4. Push to `main`. Production builds migrate and seed; preview builds never touch the schema.

`DEBUG` defaults to off on Vercel and the `*.vercel.app` hostnames are allowed automatically.
`render.yaml` and the `Dockerfile` are kept as fallbacks; see the guide.

## Roadmap

- [x] Link-check command for proof URLs
- [x] Topic-to-skill mapping (`Skill.github_topics`)
- [ ] Scheduled `link_check` and `sync_github` (needs a cron host or a CI secret for the database)
- [ ] LLM-drafted STAR answers through a provider gateway
- [ ] React rebuild of the dashboard (`proof-ledger-ui`)

See `CHANGELOG.md` for what changed in each release and `NOTES.md` for mistakes made and fixed.
