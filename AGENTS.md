# Repository Guidelines

## Project Structure & Module Organization
Runtime code lives in `app/`: `client.py` boots the Pyrogram session, `handlers.py` routes inbound events, `message_buffer.py` debounces bursts, and `openrouter.py` plus `prompts.py` manage LLM prompts. SQLAlchemy models, CRUD helpers, and session setup live inside `database/`, writing to `tg_ai_user_bot.db`. Configuration defaults and environment lookups belong in `config.py`, while `run.py` is the single entry point for local runs and deployments. Place automation scripts under a future `scripts/` folder and mirror the package layout under `tests/` (e.g., `tests/app/test_message_buffer.py`).

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: create an isolated interpreter before installing dependencies.
- `pip install -r requirements.txt`: install the Pyrogram fork, SQLAlchemy stack, OpenRouter client, and async helpers.
- `python run.py`: launch the bot, perform Telegram login on first use, and create the SQLite database automatically.
- `python -m pytest`: execute the automated suite; append `-k handlers` for selective runs.

## Coding Style & Naming Conventions
Target Python 3.10+, four-space indentation, and explicit type hints on public helpers. Modules, functions, and files use `snake_case`, classes use `PascalCase`, and constants plus environment keys remain in `UPPER_SNAKE`. Keep OpenRouter-specific logic contained inside `openrouter.py` and generic utilities in `app/utils.py`. Prefer short docstrings describing intent rather than step-by-step instructions. When adjusting prompts, keep persona definitions in `prompts.py` and reference them by constant name (`MODE_FRIENDLY`) inside handlers.

## Testing Guidelines
Pytest is the expectation. Name files `test_<module>.py` and mirror the source tree. Mock Pyrogram clients, HTTP calls, and timers so suites remain offline-friendly. Cover buffer timing, proactive messaging toggles, and database CRUD branches before merging significant changes. Use `monkeypatch` to inject `.env` overrides when verifying `config.py` behavior. A manual smoke test (`python run.py`) is recommended whenever message handling changes.

## Commit & Pull Request Guidelines
Recent history favors short imperative subjects ("Fix key validation"), so match that voice and include a concise body explaining motivation and impact when needed. PRs should summarize the change, link related issues, describe manual/automated checks run, and call out schema or `.env` updates explicitly. Screenshots or logs are only necessary when altering user-visible Telegram behavior.

## Security & Configuration Tips
Never commit `.env`, `tg_ai_user_bot.db`, or `tg_ai_userbot.session*` artifacts. Document any new secret keys in README instructions and access them via `os.getenv` in `config.py`. When sharing example payloads, redact user identifiers and tokens, using placeholders like `123456789`.
