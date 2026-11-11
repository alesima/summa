# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Token usage tracking (`summa usage`) with optional cost estimate.
- Persistent AI memory: `summa memory add/list/remove` and multi-turn chat with history.
- Monthly salary-based budget planning: `summa budget plan`.
- Streaming chat responses (ChatGPT-style) with preloader in `summa chat`.
- Knowledge graph (triples): `summa graph add/list/query/remove/sync/show/clear/stats/alias`, auto-populated from data, merchant normalization, aliases, injected into AI context.

## [0.1.0] - 2026-11-10

### Added
- Initial release of `summa`, a terminal personal finance tracker with AI.
- CLI commands: `init`, `account`, `category`, `tx`, `budget`, `report`, `ask`, `chat`, `plan`, `review`.
- SQLite local storage (`~/.summa/summa.db`) with accounts, categories, transactions, budgets, settings.
- Default category seeding (expense/income).
- Bank statement importers for CSV, OFX and PDF (multi-page, with content-stream fallback).
- Document-level deduplication on import (SHA-256), with `--force` to re-import.
- AI integration (OpenAI / Anthropic / OpenAI-compatible endpoints) for categorization, Q&A, planning and review.
- Conversation language selection (`summa lang`, `SUMMA_LANGUAGE`).
- Multi-currency support: per-account currency, exchange rates (`summa fx`), auto transfer detection and dedup on import.
- Terminal charts (`summa chart spending|trend`).
- CSV export (`summa export`).
- Interactive TUI dashboard (`summa dashboard`).
- Top-level `summa import` command.
- Provider-agnostic AI via OpenAI-compatible client.
- Optional JEV (TypeSafe System One) decision adapter with LLM fallback (`SUMMA_DECISION_PROVIDER`).
- Modular command architecture (`commands/`) and service layer (`services/`).
- Test suite (46 tests) covering db, repo, importers, CLI, AI and decision service.
- `Makefile`, `.env.example`, MIT license, README with badges.

### Changed
- Refactored CLI from a single monolithic file into domain command modules.
- All documentation and descriptions translated to English.

[Unreleased]: https://github.com/alesima/summa/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/alesima/summa/releases/tag/v0.1.0
