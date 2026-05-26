# BJOKER

Telegram bot on `aiogram 3` for the `BLACK JACK ONLINE` game flow, balance, tickets, admin notifications, and staged casino-style UI rendering.

## Quick start

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:

```bash
pip install -e .
```

3. Copy `.env.example` to `.env` and fill in the values.
4. Run:

```bash
python -m app.main
```

## Notes

- Default database is SQLite for local launch.
- Production can use PostgreSQL by changing `DATABASE_URL`.
- Telegram Stars top-up flow is wired through `sendInvoice` with `XTR`.
- The project keeps game state in the database so the bot can recover after restarts.

