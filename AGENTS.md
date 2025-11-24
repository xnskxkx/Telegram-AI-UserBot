# Repository Guidelines

## Project Structure & Module Organization
Runtime code lives in `app/`: `client.py` wires Pyrogram, `handlers.py` routes events, `message_buffer.py` smooths bursts, and `openrouter.py` plus `prompts.py` encapsulate LLM personas. Shared helpers belong in `app/utils.py`. Persistence and session helpers reside in `database/` (`models.py`, `crud.py`, `session.py`), writing to `tg_ai_user_bot.db`. Configuration defaults and env lookups are in `config.py`, while `run.py` is the single entry point. Keep diagrams or docs near `README.md`, and mirror this structure under `tests/` (e.g., `tests/app/test_message_buffer.py`).

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: prepare an isolated interpreter before installing deps.
- `pip install -r requirements.txt`: install Pyrogram fork, SQLAlchemy, dotenv, and OpenRouter client.
- `python run.py`: start the bot locally, trigger Telegram login on first run, and auto-create the SQLite DB.
- `python -m pytest`: execute the automated suite; append `-k handlers` or a file path to focus on specific modules.

## Coding Style & Naming Conventions
Use Python 3.10+, 4-space indentation, and concise type hints for public helpers. Files, modules, and functions use `snake_case`; classes use `PascalCase`; constants/environment keys use `UPPER_SNAKE`. Keep provider-specific logic confined to `openrouter.py` and reusable helpers in `app/utils.py`. Docstrings should describe intent in a single sentence, and prompts must stay centralized in `prompts.py` referenced via constants like `MODE_FRIENDLY`.

## Testing Guidelines
Pytest is the standard harness. Name files `test_<module>.py`, mirror the source tree, and mock Pyrogram clients or HTTP calls so suites remain offline-friendly. Cover message buffering, proactive toggles, and CRUD paths before merging. Use `monkeypatch` to inject `.env` overrides when verifying `config.py`, and run a smoke test (`python run.py`) after touching handlers or startup wiring.

## Commit & Pull Request Guidelines
Git history favors short imperative subjects ("Fix key validation"), so match that voice. PRs should summarize behavior changes, list manual/automated checks (`python run.py`, `python -m pytest`), flag schema or `.env` updates, and link related issues. Provide screenshots or logs only when Telegram-facing behavior changes.

## Security & Configuration Tips
Never commit `.env`, `tg_ai_user_bot.db`, or `tg_ai_userbot.session*`. Document new secrets in README instructions and access them via `os.getenv`. Use placeholders such as `123456789` when sharing sample payloads, and scrub identifiers from logs before attaching them to issues.
