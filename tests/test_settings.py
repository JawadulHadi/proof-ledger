"""Host-specific settings. Each test re-imports config.settings under a patched environment.

Reloading the module doesn't touch django.conf.settings, which Django already built from the
original import, so the rest of the suite is unaffected.
"""
import importlib

import pytest

import config.settings

VERCEL_ENV = {
    'VERCEL': '1',
    'SECRET_KEY': 'test-secret',
    'DATABASE_URL': 'postgres://u:p@db.example.com:5432/proof',
    'VERCEL_PROJECT_PRODUCTION_URL': 'proof-ledger.vercel.app',
    'VERCEL_URL': 'proof-ledger-abc123.vercel.app',
}


@pytest.fixture
def load_settings(monkeypatch):
    for var in ('VERCEL', 'DEBUG', 'DATABASE_URL', 'DB_CONN_MAX_AGE', 'RENDER_EXTERNAL_HOSTNAME',
                'VERCEL_PROJECT_PRODUCTION_URL', 'VERCEL_BRANCH_URL', 'VERCEL_URL', 'POSTGRES_DB'):
        monkeypatch.delenv(var, raising=False)

    def load(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return importlib.reload(config.settings)

    yield load
    monkeypatch.undo()
    importlib.reload(config.settings)


def test_vercel_hostnames_are_allowed_and_trusted_for_csrf(load_settings):
    s = load_settings(**VERCEL_ENV)

    assert {'proof-ledger.vercel.app', 'proof-ledger-abc123.vercel.app'} <= set(s.ALLOWED_HOSTS)
    assert 'https://proof-ledger.vercel.app' in s.CSRF_TRUSTED_ORIGINS


def test_vercel_defaults_debug_off_and_drops_persistent_connections(load_settings):
    s = load_settings(**VERCEL_ENV)

    assert s.DEBUG is False
    assert s.DATABASES['default']['CONN_MAX_AGE'] == 0


def test_conn_max_age_can_be_overridden(load_settings):
    s = load_settings(**VERCEL_ENV, DB_CONN_MAX_AGE='60')

    assert s.DATABASES['default']['CONN_MAX_AGE'] == 60


def test_vercel_without_database_url_fails_loudly(load_settings):
    env = {k: v for k, v in VERCEL_ENV.items() if k != 'DATABASE_URL'}

    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        load_settings(**env)


def test_render_and_local_defaults_are_unchanged(load_settings):
    s = load_settings(DATABASE_URL=VERCEL_ENV['DATABASE_URL'])

    assert s.DEBUG is True
    assert s.DATABASES['default']['CONN_MAX_AGE'] == 600
