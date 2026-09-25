# AGENTS.md - dzz-bills

## Commands

```bash
uv sync              # install Python dependencies (NOT pip)
uv add <pkg>         # add a Python dependency
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000   # serve backend + built frontend
cd frontend && npm install && npm run build && cd ..          # build Vue frontend -> frontend/dist
cd frontend && npm run dev                                    # Vite dev server (proxies /api to :8000)
```

- Python 3.13+ required (enforced by `.python-version`).
- Node 22+ required to build the frontend.

## Architecture

- **Frontend**: Vue 3 + Vite + Naive UI + ECharts. Source in `frontend/src/`, build output in `frontend/dist/`.
- **Backend**: FastAPI in `backend/` (package). `backend/main.py` serves `/api/*` and the built frontend (static + SPA fallback) on one port.
- `backend/config.py` loads `.env` with `override=True`; `.env` beats system env. It is the single source of truth for paths, API key, model name.
- DB: SQLite **WAL** mode, no migrations framework (uses `_migrate()` with ALTER TABLE + silent fail).
- Each DB function opens/closes its own connection — never share connections across functions.
- API routers split by domain in `backend/routers/`: `players`, `bills`, `stats`, `settlement`, `recognize`.

## Key conventions

- All UI text is in **Chinese**.
- AI recognition via OpenAI-compatible API (default: Xiaomi MiMo `mimo-v2.5`).
- `recognize_bill()` accepts `player_names` to help the LLM match existing users (injected into the prompt).
- Game scores are stored as `win_points` (points, not money). Money conversion happens at settlement time via `price_per_point`.
- Every game session must sum to zero (zero-sum validation tolerance < 0.01).
- Image files stored at `data/images/{uuid8}_{original_filename}`; served via `GET /api/images/{filename}`.
- Frontend API client is `frontend/src/api/index.js` (axios, baseURL `/api`); image URLs via `imageUrl()`.

## Frontend layout

- Views in `frontend/src/views/`: `Dashboard.vue` (概览), `BillUpload.vue` (上传+AI), `BillRecords.vue` (记录), `Players.vue` (玩家), `Stats.vue` (统计), `Settlement.vue` (结账).
- Routing is History mode (server does SPA fallback in `backend/main.py`).
- To change the `dist` that FastAPI serves, rebuild the frontend (`npm run build`) — do not hand-edit `dist/`.

## Tests / Lint

No test infrastructure, no linter, no typechecker configured in this repo.

## CI

Push to `master` builds the multi-stage Docker image (Vue build → FastAPI) and pushes to `ghcr.io` (`.github/workflows/docker.yml`).
