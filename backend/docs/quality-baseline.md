# Backend CI quality baseline

The backend quality workflow runs on Python 3.12 for backend-related pushes and
pull requests. It uses only the approved tools pinned in
`requirements-dev.txt`. The default pytest configuration excludes PostgreSQL,
migration, and concurrency categories, so CI requires no database credentials.

## Local setup

From the `backend` directory, create or activate a Python 3.12 virtual
environment and install:

```powershell
python -m pip install -r requirements-dev.txt
python -m pip check
```

## Required gates

Run the same commands used by CI:

```powershell
python -m ruff format --check .
python -m ruff check .
python -m mypy app test_support
python -m pytest --cov=app --cov-branch --cov-report=term-missing --cov-fail-under=90
python -m pip_audit -r requirements.txt --strict
python -m bandit -r app test_support -c pyproject.toml -ll
```

The thresholds are explicit:

- Ruff formatting must require no changes.
- Ruff linting must report zero selected-rule violations.
- mypy must report zero errors in `app` and `test_support`.
- branch-aware application coverage must be at least 90 percent.
- pip-audit must report zero known vulnerabilities in runtime dependencies.
- Bandit must report zero medium- or high-severity findings in application and
  PostgreSQL test-support code.

PostgreSQL, migration, and concurrency tests remain separately approval-gated
and are not part of this credential-free CI baseline.
