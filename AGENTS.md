# Repository Guidelines

## Project Structure & Module Organization
All runtime logic sits in `app/`: `client.py` wires Pyrogram, `handlers.py` manages chat flow, `message_buffer.py` debounces bursts, and `openrouter.py`/`prompts.py` encapsulate LLM calls. Shared helpers belong in `app/utils.py`. Persistence lives inside `database/` (`models.py`, `crud.py`, `session.py`) and writes to `tg_ai_user_bot.db`. Configuration defaults and environment lookups stay in `config.py`, while `run.py` is the single entry point. Keep docs or diagrams beside `README.md` and mirror the package layout when adding tests under `tests/` (e.g., `tests/app/test_message_buffer.py`).

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: create an isolated interpreter before touching dependencies.
- `pip install -r requirements.txt`: install the Pyrogram fork, OpenRouter client, SQLAlchemy, and async helpers.
- `python run.py`: start the bot locally, trigger Telegram login on first run, and auto-create the SQLite database.
- `python -m pytest`: execute automated tests; append `-k handlers` or a path for focused runs.

## Coding Style & Naming Conventions
Target Python 3.10+, 4-space indentation, and explicit type hints for public helpers. Modules and functions use `snake_case`, classes use `PascalCase`, and constants/environment keys use `UPPER_SNAKE`. Keep provider-specific logic inside `openrouter.py` to maintain swapability, and move shared routines into `app/utils.py` rather than duplicating them. Docstrings should briefly describe intent, and persona tweaks belong in `prompts.py` referenced via constants such as `MODE_FRIENDLY`.

## Testing Guidelines
Pytest is the standard harness. Name files `test_<module>.py`, mirror the source tree, and mock Pyrogram clients or HTTP calls to remain offline-friendly. Cover message buffering, proactive toggles, and CRUD paths before merging. Use `monkeypatch` to inject `.env` overrides when verifying `config.py`, and run a smoke test via `python run.py` whenever handlers or client wiring change.

## Commit & Pull Request Guidelines
Git history favors short imperative subjects ("Fix key validation"), so follow that voice. PRs should summarize the change, list manual/automated checks (`python run.py`, `python -m pytest`), call out schema or `.env` updates, and link related issues. Provide screenshots or logs only when Telegram-facing output changes.

## Security & Configuration Tips
Never commit `.env`, `tg_ai_user_bot.db`, or `tg_ai_userbot.session*`. Document new secrets in README instructions and read them via `os.getenv`. Use placeholders such as `123456789` in docs and redact identifiers from logs shared in issues.
