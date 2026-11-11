# summa — Project Specification

> Terminal personal finance tracker with AI. Open source, local-first (SQLite).

## 1. Overview

`summa` is a command-line application for personal finance management. It runs
locally, stores data in SQLite, and integrates with LLM/decision models for
categorization, Q&A, planning and review.

- **Language:** Python 3.14+
- **Package manager:** uv
- **CLI framework:** Typer + Rich
- **Storage:** SQLite (via stdlib `sqlite3`)
- **AI:** OpenAI-compatible chat completions (provider-agnostic) + optional JEV
- **TUI:** Textual
- **Tests:** pytest (46 tests)

## 2. Architecture

Layered architecture (dependencies point inward):

```
cli (commands/)  ->  services/  ->  repo.py  ->  db.py
                  ->  ai.py / adapters/  ->  ports/
                  ->  importers.py, charts.py, tui.py, i18n.py
```

- `db.py` — schema + connection helpers.
- `repo.py` — data access (CRUD). No business logic beyond SQL.
- `models.py` — Pydantic models + cents helpers.
- `services/` — business logic (import, decisions).
- `commands/` — one Typer module per domain, each exposes `register(app)`.
- `cli.py` — thin aggregator: creates `app`, registers all command modules.
- `console.py` — shared Rich console.
- `ai.py` — provider-agnostic LLM client.
- `ports/` — protocols (e.g. `DecisionModel`).
- `adapters/` — implementations (LLM, JEV).
- `importers.py` — CSV/OFX/PDF parsers.
- `charts.py` — terminal charts.
- `tui.py` — Textual dashboard.
- `i18n.py` — language helpers.

## 3. Data Model

See `docs/DATA_MODEL.md`.

Core tables: `accounts`, `categories`, `transactions`, `budgets`, `settings`,
`fx_rates`, `token_usage`.

Amounts are stored as **integer cents** (signed: income positive, expense
negative) to avoid floating point errors.

## 4. Command Reference

See `docs/COMMANDS.md`.

Top-level commands: `init`, `lang`, `export`, `import`, `dashboard`, `ask`,
`chat`, `plan`, `review`, `usage`, plus sub-apps `account`, `category`, `tx`,
`budget`, `report`, `chart`, `fx`.

## 5. AI Integration

- Provider-agnostic: single OpenAI-compatible client (`ai._client()`).
- Config via env: `SUMMA_AI_PROVIDER`, `SUMMA_AI_MODEL`, `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, `SUMMA_AI_BASE_URL`.
- Default OpenAI model: `gpt-5.6-terra`.
- Capabilities: categorization (`categorize_transactions`), Q&A
  (`answer_question`), and free-form chat (`chat`).
- Token usage recorded in `token_usage` table; view with `summa usage`.

### Decision service (optional JEV)
- Port: `ports.decision.DecisionModel`.
- Adapters: `adapters.llm_decision.LLMDecisionModel` (default),
  `adapters.jev.JEVDecisionModel` (optional).
- Factory: `services.decision_service.get_decision_model()` with fallback.
- Config: `SUMMA_DECISION_PROVIDER` (`auto`/`jev`/`llm`), `JEV_API_KEY`,
  `JEV_API_URL`, `JEV_MODEL`.

## 6. Importers

- `parse_csv`: heuristic column detection (date, description, amount or
  debit/credit).
- `parse_ofx`: STMTTRN blocks.
- `parse_pdf`: text extraction + line heuristics.
- `parse_statement`: auto-detect by extension/content.
- Dedup on import; transfer detection for credit card payments.

## 7. Configuration

- `SUMMA_HOME`: data directory (default `~/.summa`).
- `.env` loaded from cwd and `~/.summa/.env`.
- Settings stored in `settings` table (e.g. `language`).

## 8. Testing

- `pytest` with fixtures in `tests/conftest.py`.
- `SUMMA_HOME` redirected to temp dir per test.
- 46 tests covering db, repo, importers, CLI, AI, decision service.

## 9. Development

```bash
make install   # uv sync
make test      # pytest
make lint      # compile check
make clean     # remove artifacts
```

## 10. Extension Points

- Add a new command: create module in `commands/`, implement `register(app)`,
  import + register in `cli.py`.
- Add a new importer: implement `parse_x(path)` in `importers.py`, wire into
  `parse_statement`.
- Add a new decision backend: implement `DecisionModel`, register in
  `services.decision_service`.
- Add a new language: add code to `i18n.SUPPORTED`.
