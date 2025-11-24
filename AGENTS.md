# Repository Guidelines

## Project Structure & Module Organization
Runtime code resides in `app/`: `client.py` wires Pyrogram, `handlers.py` and `message_buffer.py` coordinate chat logic, while `openrouter.py` and `prompts.py` encapsulate LLM traffic. Shared helpers belong in `app/utils.py`. Persistence lives in `database/` (`models.py`, `crud.py`, `session.py`), and SQLite data is written to `tg_ai_user_bot.db`. Configuration defaults and env lookups are centralized in `config.py`; `run.py` stays the single entry point. Tests should mirror this layout under `tests/` (for example, `tests/app/test_handlers.py`). Assets or diagrams referenced in docs belong near `README.md`.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: set up an isolated interpreter before touching dependencies.
- `pip install -r requirements.txt`: installs the Pyrogram fork, OpenRouter client, SQLAlchemy, and asyncio helpers.
- `python run.py`: starts the bot locally, creates the SQLite database if missing, and prompts for Telegram login on first run.
- `python -m pytest`: executes all automated tests; append `-k message_buffer` for focused runs.

## Coding Style & Naming Conventions
Target Python 3.10+, 4-space indentation, and type hints on public helpers. Functions, modules, and files use `snake_case`; classes use `PascalCase`; constants and environment keys use `UPPER_SNAKE`. Keep OpenRouter-specific logic isolated to `openrouter.py` so providers remain interchangeable. Use concise docstrings describing intent, and prefer refactoring shared routines into `app/utils.py` rather than duplicating logic.

## Testing Guidelines
Pytest is the default framework. Name files `test_<module>.py`, mirror the package tree, and rely on fixtures to mock Pyrogram clients or HTTP calls. Avoid live OpenRouter or Telegram traffic by stubbing responses. Cover buffer timing, proactive message toggles, and CRUD branches before merging; a light smoke run of `python run.py` is expected when handlers change. Patch environment variables with `monkeypatch` to validate `config.py`.

## Commit & Pull Request Guidelines
History uses short imperative subjects (e.g., `Fix key validation`), so match that tone and describe motivations plus side effects in the body when necessary. Every PR should include a summary, mention manual or automated test commands executed, flag schema or `.env` updates, and reference related issues. Screenshots or log excerpts are required only when altering user-visible behavior.

## Security & Configuration Tips
Never commit `.env`, database dumps, or `tg_ai_userbot.session*`. Store new secret names in README instructions and always read them with `os.getenv`. Use placeholder IDs (`123456789`) in docs and strip sensitive text from debug output before attaching it to issues.
