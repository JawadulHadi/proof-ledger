"""Vercel builds from pyproject.toml, Render and Docker from requirements.txt. Keep them in step."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_dependencies_match_requirements():
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']
    requirements = [
        line.strip() for line in (ROOT / 'requirements.txt').read_text().splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]
    assert sorted(project['dependencies']) == sorted(requirements)
