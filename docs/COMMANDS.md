# Command Reference

## Top-level

| Command | Description |
|---|---|
| `init` | Initialize the database. |
| `lang [code]` | View or set conversation language. |
| `export <path>` | Export transactions to CSV. |
| `import <file>` | Import a bank statement (CSV/OFX/PDF). |
| `dashboard` | Launch the TUI dashboard. |
| `ask "<question>"` | Ask a natural-language question (AI). |
| `chat` | Interactive chat (REPL). |
| `plan` | Generate a financial plan (AI). |
| `review` | Monthly review with AI insights. |
| `usage` | Show AI token usage and cost estimate. |
| `memory` | Manage persistent AI memory/notes. |
| `graph` | Manage knowledge graph (triples). |

## account
- `account add <name> [--type] [--currency]`
- `account list`
- `account remove <name>`

## category
- `category list [--kind]`
- `category add <name> [--kind]`

## tx
- `tx add <amount> <desc> [--account] [--date] [--category] [--income] [--notes]`
- `tx list [--account] [--category] [--start] [--end] [--uncategorized] [--limit]`
- `tx delete <id>`
- `tx import <file> [--account] [--dry-run] [--categorize]`
- `tx categorize [--limit] [--apply]`

## budget
- `budget set <category> <month> <amount>`
- `budget show <month>`

## report
- `report summary [--start] [--end]`
- `report monthly <month>`

## chart
- `chart spending [--month]`
- `chart trend [--months]`

## memory
- `memory add <key> <value> [--scope]`
- `memory list [--scope]`
- `memory remove <key>`

## graph
- `graph add <subject> <predicate> <object> [--confidence]`
- `graph list [--subject] [--predicate] [--object]`
- `graph query <subject>`
- `graph remove <subject> <predicate> <object>`

## fx
- `fx set <base> <quote> <rate>`
- `fx list`
