# Repository Guidelines

## Project Structure & Module Organization
Runtime logic lives in `app/`: `client.py` wires Pyrogram, `handlers.py` coordinates conversations, `message_buffer.py` smooths bursts, and `openrouter.py` plus `prompts.py` own LLM personas. Shared helpers belong in `app/utils.py`. Persistence and migration helpers are under `database/` (`models.py`, `crud.py`, `session.py`), writing to `tg_ai_user_bot.db`. Configuration defaults reside in `config.py`, while `run.py` is the single entry point for local runs and deployments. Keep docs or assets near `README.md`, and mirror the package tree under `tests/` (e.g., `tests/app/test_message_buffer.py`).

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: prepare an isolated interpreter before installing dependencies.
- `pip install -r requirements.txt`: install Pyrogram fork, SQLAlchemy, dotenv, and OpenRouter client libraries.
- `python run.py`: start the bot, trigger Telegram login on first use, and auto-create the SQLite database.
- `python -m pytest`: run the automated suite; append `-k handlers` or `tests/app/test_handlers.py::test_smoke` for focused runs.

## Coding Style & Naming Conventions
Use Python 3.10+, 4-space indentation, and explicit type hints on public helpers. Files, modules, and functions follow `snake_case`; classes use `PascalCase`; constants/environment keys use `UPPER_SNAKE`. Keep provider-specific logic inside `openrouter.py`, push reusable routines into `app/utils.py`, and keep prompts centralized in `prompts.py` referenced via constants (e.g., `MODE_FRIENDLY`). Docstrings should briefly describe intent rather than implementation details.

## Testing Guidelines
Pytest is the preferred framework. Name tests `test_<module>.py`, mirror the source tree, and mock Pyrogram clients or HTTP calls so suites remain offline-friendly. Validate message buffering, proactive messaging toggles, and database CRUD behavior before merging. Use `monkeypatch` to inject `.env` overrides when verifying `config.py`, and perform a smoke run with `python run.py` whenever handlers or messaging flows change.

## Commit & Pull Request Guidelines
Git history favors short imperative subjects ("Fix key validation"), so match that tone and include concise bodies describing motivation and impact when necessary. Each PR should summarize the change, list manual or automated checks (`python run.py`, `python -m pytest`), flag schema or `.env` updates, and link related issues. Attach screenshots or logs only when user-visible Telegram behavior changes.

## Security & Configuration Tips
Never commit `.env`, `tg_ai_user_bot.db`, or `tg_ai_userbot.session*`. Document new secrets in README instructions and access them via `os.getenv`. Use placeholders such as `123456789` when sharing sample payloads and scrub identifiers from logs before attaching them to issues.
