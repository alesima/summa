# summa

[![Python](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-43%20passing-brightgreen.svg)](#development)
[![Code style: ruff](https://img.shields.io/badge/code%20style-clean-black.svg)](#)

Terminal personal finance tracker with AI. Open source, local data (SQLite).

## Installation

```bash
cd ~/Projects/summa
uv sync
```

## Quick start

```bash
uv run summa init
uv run summa account add "Checking"
uv run summa tx add 45.90 "Lunch"            # expense
uv run summa tx add 3000 "Salary" --income    # income
uv run summa tx import statement.csv --categorize
uv run summa tx categorize --apply
uv run summa report monthly 2026-11
uv run summa budget set Food 2026-11 500
uv run summa budget show 2026-11
uv run summa ask "how much did I spend on food this month?"
uv run summa plan --goal "save 20%"
uv run summa review
uv run summa chart spending
uv run summa export out.csv
uv run summa dashboard
```

## AI setup (OpenAI o4-mini)

1. Create a key at https://platform.openai.com/api-keys
2. Save it in `~/.summa/.env` (or as an environment variable):

```
OPENAI_API_KEY=sk-...
SUMMA_AI_MODEL=o4-mini
```

Optional: use another provider/model:

```
SUMMA_AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
SUMMA_AI_MODEL=claude-haiku-4-5-20251001
```

Or an OpenAI-compatible endpoint (local Ollama, etc.):

```
SUMMA_AI_BASE_URL=http://localhost:11434/v1
SUMMA_AI_MODEL=llama3.1
```

## Conversation language

```bash
summa lang en          # English
summa lang pt-BR       # Portuguese (Brazil)
summa lang             # show current
```

Or set `SUMMA_LANGUAGE=en` in the environment.

## Multi-currency

Accounts store their own currency. Set exchange rates and view conversions:

```bash
summa fx set USD BRL 5.20
summa fx list
```

## Global shortcut

```bash
uv tool install --editable ~/Projects/summa
summa --help
```

## Project structure

- `src/summa/cli.py` — commands
- `src/summa/db.py` — SQLite schema
- `src/summa/repo.py` — data access
- `src/summa/ai.py` — LLM integration
- `src/summa/importers.py` — CSV/OFX parsers
- `src/summa/i18n.py` — language helpers
- `src/summa/charts.py` — terminal charts
- `src/summa/tui.py` — Textual dashboard
- `tests/` — test suite

## Development

```bash
make install   # install deps
make test      # run tests
make lint      # compile check
make clean     # remove artifacts
```
