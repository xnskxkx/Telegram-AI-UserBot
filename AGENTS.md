# Repository Guidelines

## Project Structure & Module Organization
Runtime logic lives in `app/`: `client.py` bootstraps Pyrogram, `handlers.py` drives conversation flow, `message_buffer.py` debounces bursts, and `openrouter.py` with `prompts.py` manages LLM exchanges. Shared helpers belong in `app/utils.py`. Persistence sits inside `database/` (models, CRUD utilities, and session factory), while SQLite data stores in `tg_ai_user_bot.db`. Defaults and feature flags are centralized in `config.py`, and `run.py` remains the single entry point. Keep contributor docs in `README.md`, and mirror the package layout under `tests/` (e.g., `tests/app/test_handlers.py`).

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: provision an isolated interpreter before modifying dependencies.
- `pip install -r requirements.txt`: install Pyrogram fork, OpenRouter client, SQLAlchemy, and other runtime libraries.
- `python run.py`: launch the bot, trigger Telegram login on first run, and create the SQLite database automatically.
- `python -m pytest`: execute test suites; append `-k buffer` or `tests/app/test_message_buffer.py::test_flush` for targeted runs.

## Coding Style & Naming Conventions
Target Python 3.10+, 4-space indentation, and concise type hints on public helpers. Functions and modules follow `snake_case`, classes use `PascalCase`, and constants/environment keys stay in `UPPER_SNAKE`. Favor short, action-oriented commit subjects and docstrings that provide one-sentence intent. Keep OpenRouter-specific logic confined to `openrouter.py` so alternate providers remain pluggable, and prefer composable helpers inside `app.utils` over inlined logic in handlers.

## Testing Guidelines
Pytest is the primary harness. Name files `test_<module>.py` and mirror the package tree. Mock Pyrogram clients, OpenRouter responses, and timeouts so suites stay offline-friendly. Add regression tests covering buffer timing, proactive messaging toggles, and CRUD branches inside `database/`. When validating configuration, use `monkeypatch` to inject `.env` overrides and assert that `config.py` falls back correctly.

## Commit & Pull Request Guidelines
Git history favors short imperative subjects (e.g., `Fix key validation`). Follow that style, include a concise body when behavior changes, and mention schema migrations or `.env` additions explicitly. Each PR should summarize the problem, outline manual or automated checks (`python run.py`, `python -m pytest`), and link relevant issues. Attach logs or screenshots only when altering user-visible Telegram behavior.

## Security & Configuration Tips
Never commit `.env`, `tg_ai_user_bot.db`, or `tg_ai_userbot.session*`. Store new secrets in README instructions only, and read them via `os.getenv` within `config.py`. Prefer placeholders (e.g., `123456789`) in docs and sanitize sample payloads before sharing traces in issues.
