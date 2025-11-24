# Repository Guidelines

## Project Structure & Module Organization
Bot runtime lives in `app/`: `client.py` wires Pyrogram, `handlers.py` orchestrates conversations, `message_buffer.py` smooths bursts, and `openrouter.py` plus `prompts.py` manage LLM personas. Shared helpers stay in `app/utils.py`. Persistence code (`models.py`, `crud.py`, `session.py`) is contained in `database/`, writing to `tg_ai_user_bot.db`. Configuration defaults and env lookups belong in `config.py`, and `run.py` is the only entry point. Keep diagrams or specs near `README.md`. Place automated checks in `tests/`, mirroring the package layout (`tests/app/test_handlers.py`).

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: set up an isolated interpreter before installing dependencies.
- `pip install -r requirements.txt`: pull in the Pyrogram fork, SQLAlchemy stack, and OpenRouter client.
- `python run.py`: launch the bot locally, perform Telegram login on first run, and auto-create the SQLite DB.
- `python -m pytest`: execute the test suite; add `-k message_buffer` or a file path for focused runs.

## Coding Style & Naming Conventions
Use Python 3.10+, 4-space indentation, and type hints on public helpers. Files, modules, and functions follow `snake_case`; classes use `PascalCase`; constants and environment keys use `UPPER_SNAKE`. Keep provider-specific logic confined to `openrouter.py` so alternatives can be swapped easily. Prefer extracting reusable helpers into `app/utils.py` instead of duplicating handler logic. Docstrings should describe intent in one concise sentence.

## Testing Guidelines
Pytest is the standard harness. Name files `test_<module>.py`, mirror the source tree, and mock Pyrogram clients or HTTP requests so suites remain offline-friendly. Cover message buffering, proactive toggles, and database CRUD paths whenever they change. Use `monkeypatch` to inject `.env` overrides when validating `config.py`. Run a quick smoke test (`python run.py`) after altering handlers or startup wiring.

## Commit & Pull Request Guidelines
History favors short imperative subjects ("Fix key validation"), so adopt the same tone and add a brief body when context is needed. Each PR should summarize behavior changes, list manual/automated checks (`python run.py`, `python -m pytest`), flag schema or `.env` updates, and link any related issues. Screenshots or logs are only necessary when Telegram-facing behavior or prompts change.

## Security & Configuration Tips
Do not commit `.env`, `tg_ai_user_bot.db`, or `tg_ai_userbot.session*`. Document new secret names in README instructions and access them via `os.getenv` in `config.py`. Use placeholder IDs such as `123456789` when sharing examples, and scrub user data from logs before attaching them to issues.
