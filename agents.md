# Project: AI Task Planner

## Technology Stack
- Python 3.12
- FastAPI
- SQLAlchemy 2.x (async)
- PostgreSQL
- Keycloak (OIDC)
- uv
- pytest
- Docker Compose

## Architecture
- Use a modular monolith.
- Separate API, business logic and persistence.
- Use dependency injection.
- Do not introduce new frameworks without approval.

## Development Rules
- Manage dependencies exclusively through uv.
- Do not use pip directly.
- Write tests for new functionality.
- Use type annotations.
- Do not modify database schema without Alembic migrations.

## Workflow
- Before implementing a non-trivial task, propose a plan.
- Explain significant architectural decisions.
- Run relevant tests after implementation.
- Report changes and test results.
- Do not install dependencies without approval.
