# AGENTS.md - dzz-bills

## Commands

```bash
uv sync              # install dependencies (NOT pip)
uv add <pkg>         # add a dependency
uv run streamlit run app.py   # start dev server on :8501
```

- `config.py` loads `.env` with `override=True`; `.env` beats system env.
- Python 3.13+ required (enforced by `.python-version`).

## Architecture

Streamlit multi-page app: `app.py` is `/`, `pages/` files auto-register as sidebar pages.
Prefix filenames with numbers to control ordering (e.g. `1_账单上传.py`).

- DB: SQLite WAL mode, no migrations framework (uses `_migrate()` with ALTER TABLE + silent fail).
- Each function opens/closes its own connection -- never share connections across functions.
- `config.py` is the single source of truth for paths, API key, model name.

## Key conventions

- All UI text is in **Chinese**.
- AI recognition via OpenAI-compatible API (default: Xiaomi MiMo `mimo-v2.5`).
- `recognize_bill()` accepts `player_names` param to help LLM match existing users (injected into prompt).
- `st.session_state` is the only persistent state across reruns.
- `st.set_page_config()` must be the very first Streamlit command on each page.
- Game scores are stored as `win_points` (not money). Money conversion happens at settlement time via `price_per_point`.
- Every game session must sum to zero (zero-sum validation < 0.01 tolerance).
- Image files stored at `data/images/{uuid8}_{original_filename}`.

## Tests / Lint

No test infrastructure, no linter, no typechecker configured in this repo.

## CI

Push to `master` builds and pushes Docker image to `ghcr.io` (`.github/workflows/docker.yml`).
