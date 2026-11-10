# Sistema de Indicadores Financieros SFPS (ESPOCH-DI-060)

Plataforma analítica e interactiva de indicadores financieros para el Sector Financiero Popular y Solidario (SFPS) del Ecuador (SEPS), construida bajo metodología Spec-Driven Development (SDD).

## Agent skills

### Issue tracker

Issues and specs for this repo live as markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical triage roles mapped to local issue statuses (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`GLOSSARY.md` and `docs/adr/` at the repository root). See `docs/agents/domain.md`.

---

## Technical Stack & Architecture

- **Contrato Vinculante:** OpenAPI 3.1.0 (`contracts/openapi.yaml`) auditado con Spectral (`contracts/.spectral.yaml`).
- **Motor Analítico:** Python + DuckDB procesando cubos multidimensionales Parquet en `data/processed/mart/`.
- **Backend:** FastAPI (Python 3.12) con autenticación JWT por cookies seguras HttpOnly y control de acceso RBAC.
- **Frontend:** React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui con tipado autogenerado desde OpenAPI.
- **Gobernanza:** Base de datos embebida SQLite (`data/users.db`) para el padrón de usuarios acreditados con forzado de cambio de clave en primer acceso.

## Verificación y Pruebas

- **Suite Integral (Full-Stack):** `npm run test`
- **Linting de Contrato:** `npm run contract:lint`
- **Tests Analíticos DuckDB:** `npm run etl:test`
- **Tests Backend (Pytest):** `npm run backend:test`
- **Compilación Frontend:** `npm run frontend:build`
