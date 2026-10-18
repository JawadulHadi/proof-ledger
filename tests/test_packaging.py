import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_dependencies_match_requirements():
    # Vercel installs from pyproject.toml; Docker and Render install from requirements.txt.
    pyproject = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    requirements = [
        line.strip()
        for line in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.startswith('#')
    ]
    assert pyproject['project']['dependencies'] == requirements
