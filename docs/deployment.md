# Deployment

Proof Ledger deploys to **Vercel** (Python runtime) with a **Neon** Postgres database. The Render
blueprint is still in the repo as a fallback (see [Render](#render-fallback) below).

| Piece | Where | Config |
| --- | --- | --- |
| Web app | Vercel Function running Django through `config/wsgi.py` | `vercel.json`, `pyproject.toml` (`[tool.vercel]`), `.python-version` |
| Build | Vercel build step | `vercel-build.sh` |
| Static files | WhiteNoise, from `staticfiles/` inside the function bundle | `config/settings.py` (`STORAGES`) |
| Database | Neon Postgres (free tier doesn't expire) | `DATABASE_URL` |

## How a Vercel deploy works

1. Vercel detects Django from `manage.py` and installs `requirements.txt` with Python 3.12
   (`.python-version`).
2. `vercel-build.sh` runs (`buildCommand` in `vercel.json`):
   - `collectstatic` writes hashed, compressed files to `staticfiles/`.
   - **Production builds only** (`VERCEL_ENV=production`): `migrate`, `seed_demo`, and a one-time
     `createsuperuser` from the `DJANGO_SUPERUSER_*` variables. Preview builds never touch the
     schema.
3. Requests go to one function, `config.wsgi:application`, which can run for up to 30 seconds
   (`maxDuration`). Tests, docs and the Render/Docker files are left out of the bundle
   (`excludeFiles`).

Vercel has no long-running server, so there is no `start.sh` step. Anything `start.sh` does on
Render happens at build time on Vercel.

## First-time setup

1. **Database.** Create a Neon project in the same region as your Vercel functions.
   `vercel.json` pins the functions to São Paulo (`"regions": ["gru1"]`) because the live Neon
   project is in AWS `sa-east-1`. If you use a Neon project elsewhere, change `regions` to the
   nearest Vercel region, or every query crosses a continent. Copy the **pooled** connection
   string, the one whose host contains `-pooler`.
2. **Project.** In Vercel: Add New, Project, import `JawadulHadi/proof-ledger`. Leave the framework,
   build and output settings at their defaults; `vercel.json` sets them.
3. **Environment variables.** Under Settings, Environment Variables, add:

   | Variable | Environments | Value |
   | --- | --- | --- |
   | `SECRET_KEY` | Production, Preview | A long random string, e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `DATABASE_URL` | Production, Preview | The Neon pooled connection string |
   | `GITHUB_USER` | Production, Preview | `JawadulHadi` |
   | `GITHUB_TOKEN` | Production | Optional; lets `sync_github` include private repos and raises the API rate limit |
   | `DJANGO_SUPERUSER_USERNAME` | Production | Admin login created on the first production build |
   | `DJANGO_SUPERUSER_EMAIL` | Production | Admin email |
   | `DJANGO_SUPERUSER_PASSWORD` | Production | Admin password |
   | `ALLOWED_HOSTS` | Production | Only for a custom domain, e.g. `proof.example.com` |

   You don't need to set `DEBUG` (it defaults to off on Vercel) or the `*.vercel.app` hostnames
   (`config/settings.py` reads them from Vercel's system variables).
4. **Deploy.** Push to `main` for production. Every other branch and pull request gets a preview URL.
5. **Check it.** Open `/`, `/api/v1/`, `/admin/`, and a static file such as
   `/static/core/dashboard.css`. All should return 200.

### From the CLI

```bash
npm i -g vercel
vercel link                 # once: creates .vercel/ (git-ignored)
vercel env pull .env.local  # optional: the project's variables, for local runs
vercel                      # preview deploy
vercel --prod               # production deploy
```

## Settings that change on Vercel

`config/settings.py` sets `ON_VERCEL` from the `VERCEL` variable Vercel provides, and then:

| Setting | On Vercel | Elsewhere | Why |
| --- | --- | --- | --- |
| `DEBUG` default | off | on | A missing variable must never turn debug pages on in production |
| `ALLOWED_HOSTS` | adds `VERCEL_PROJECT_PRODUCTION_URL`, `VERCEL_BRANCH_URL`, `VERCEL_URL` | unchanged | Production, branch and per-deployment URLs all work without hand-editing |
| `CSRF_TRUSTED_ORIGINS` | `https://` + each allowed host | same | Admin login and HTMX posts work on every Vercel URL |
| `CONN_MAX_AGE` | `0` | `600` | Serverless instances don't keep a connection between requests; Neon's pooler does the pooling. Override with `DB_CONN_MAX_AGE`. |
| No `DATABASE_URL` | fails at startup | falls back to SQLite | The deployed filesystem is read-only, so SQLite can't work |

## Limits and trade-offs

- **Previews share the database.** If `DATABASE_URL` is set for Preview, preview deployments read and
  write the production database (they never migrate it). To isolate them, install the Neon
  integration from the Vercel Marketplace, which creates a database branch per preview.
- **Migrations run before the new code goes live.** Keep migrations additive (add columns and tables;
  drop them in a later release) so the running deployment keeps working while a build migrates.
- **Cold starts.** The first request after an idle period imports Django, which takes about a second.
  That's still faster than a free Render instance waking from sleep.
- **No background work.** Requests stop at `maxDuration` (30 s). `sync_github`, `link_check` and
  `weekly_digest` still run from your shell against `DATABASE_URL`:

  ```bash
  vercel env pull .env.local
  set -a; . ./.env.local; set +a
  python manage.py sync_github --prune   # GITHUB_TOKEN set: counts private repos too
  ```

  Scheduling them is on the roadmap. Options are Vercel Cron (once a day on the Hobby plan, calling
  a protected endpoint) or a scheduled GitHub Actions workflow.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| Build fails with `set DATABASE_URL on Vercel` | `DATABASE_URL` is missing for that environment (Production or Preview). Add it and redeploy. |
| Build fails with `set SECRET_KEY when DEBUG is off` | `SECRET_KEY` is missing for that environment. |
| `400 Bad Request` on a custom domain | Add the domain to `ALLOWED_HOSTS`. |
| `403 CSRF verification failed` on admin login | Same: the host has to be in `ALLOWED_HOSTS` to be trusted for CSRF. |
| `500` with `Missing staticfiles manifest entry` | `collectstatic` didn't run. Check that the build log shows `vercel-build.sh` and the "static files copied" line. |
| Admin user not created | The `DJANGO_SUPERUSER_*` variables must be set for **Production**; they're only used on production builds. |

## Render (fallback)

`render.yaml` is a Render Blueprint for a free Python web service. `build.sh` installs and collects
static files; `start.sh` migrates, seeds, creates the admin user once, then runs gunicorn. In Render:
New, Blueprint, pick this repo, then set `DATABASE_URL` and the `DJANGO_SUPERUSER_*` values.
`SECRET_KEY` is generated, and Render's hostname is added to `ALLOWED_HOSTS`. Free instances sleep
after about 15 minutes idle.

The `Dockerfile` (and `docker-compose.yml` with Postgres 16) runs the same `start.sh` anywhere that
runs containers.
