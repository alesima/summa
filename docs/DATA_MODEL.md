# Data Model

SQLite schema (see `src/summa/db.py`). All amounts in **integer cents**.

## accounts
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT UNIQUE | |
| type | TEXT | checking, savings, credit, cash, investment |
| currency | TEXT | ISO code, default BRL |
| created_at | TEXT | |

## categories
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT UNIQUE | |
| kind | TEXT | expense, income, transfer |
| parent_id | INTEGER FK | optional hierarchy |

Default categories seeded on `init`: Moradia, Alimentação, Transporte, Saúde,
Educação, Lazer, Compras, Assinaturas, Contas/Serviços, Outros (expense);
Salário, Freelance, Investimentos, Outras receitas (income); Transferência
(transfer).

## transactions
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| account_id | INTEGER FK | cascade delete |
| date | TEXT | ISO YYYY-MM-DD |
| amount_cents | INTEGER | signed |
| description | TEXT | |
| category_id | INTEGER FK | nullable |
| notes | TEXT | nullable |
| raw | TEXT | original imported line |
| created_at / updated_at | TEXT | |

Indexes: `idx_tx_date`, `idx_tx_account`, `idx_tx_category`.

## budgets
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| category_id | INTEGER FK | |
| month | TEXT | YYYY-MM |
| amount_cents | INTEGER | |
| UNIQUE(category_id, month) | | |

## settings
| Column | Type | Notes |
|---|---|---|
| key | TEXT PK | e.g. `language` |
| value | TEXT | |

## fx_rates
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| base_currency | TEXT | |
| quote_currency | TEXT | |
| rate | REAL | |
| updated_at | TEXT | |
| UNIQUE(base_currency, quote_currency) | | |

## token_usage
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| model | TEXT | |
| prompt_tokens | INTEGER | |
| completion_tokens | INTEGER | |
| total_tokens | INTEGER | |
| created_at | TEXT | |
