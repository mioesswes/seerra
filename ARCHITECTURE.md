# BJOKER Architecture

## Project goal

`BJOKER` is a Telegram bot built on `aiogram 3` with a casino-style interface, Telegram Stars balance, support tickets, admin notifications, and the main game mode `BLACK JACK ONLINE`.

## Product rules fixed in the project

- The external user interface does not mention internal moderation mechanics.
- The only active game is `BLACK JACK ONLINE`.
- One user can have only one active game at a time.
- Stake is deducted immediately when search starts.
- If search is canceled or expires, the stake is returned.
- A tie starts a new round with the same stake and a new deck.
- User support allows only one open ticket at a time.
- Reply keyboard menu texts are not treated as ticket messages.
- Withdrawal is a manual request; balance is deducted immediately when the request is created.

## Game rules fixed in the project

- Goal: reach 21 points or as close to it as possible.
- If the sum is above 21, it is a bust.
- Card values:
  - `6..10` by nominal value
  - `Jack = 2`
  - `Queen = 3`
  - `King = 4`
  - `Ace = 11`
- Two aces equal `21`.
- Player starts with two cards.
- The opponent side also starts with two cards.
- A new random deck is created for each new round.
- Player future cards are preselected from the deck and revealed in order when the player takes them.
- If both sides bust, the side closer to `21` wins.

## Code layout

- `app/main.py`
  - bot startup
  - router registration
  - periodic background worker
- `app/config.py`
  - environment config
- `app/common/`
  - enums and reusable text blocks
- `app/db/`
  - SQLAlchemy base, models, session factory
- `app/domain/blackjack.py`
  - pure blackjack math and deck logic
- `app/keyboards/`
  - reply and inline keyboards
- `app/renderers/`
  - text rendering for player and admin views
- `app/services/`
  - business logic for users, games, tickets, withdrawals
- `app/routers/`
  - Telegram update handlers
- `app/states/`
  - FSM groups

## Main entities

- `User`
  - Telegram identity and public data
- `Wallet`
  - current Stars balance
- `LedgerEntry`
  - immutable balance history
- `GameSession`
  - active or finished blackjack session
- `Deposit`
  - Telegram Stars top-up record
- `WithdrawalRequest`
  - manual withdrawal request
- `Ticket`
  - support ticket
- `TicketMessage`
  - ticket chat history
- `AdminLog`
  - admin actions and audit trail

## Game session state

`GameSession` stores:

- stake
- current status
- round number
- deck
- player cards
- opponent cards
- next player cards preview
- stop flags
- player/admin deadlines
- Telegram message ids for player and admin chat updates

## Status flow

- `SEARCHING`
  - stake is held
  - waiting for acceptance
- `WAITING_OPPONENT_SETUP`
  - player opening hand is generated
  - second side opening hand is being filled
- `ACTIVE`
  - both sides can continue according to the round state
- `PLAYER_WON` / `PLAYER_LOST`
  - terminal result before final persistence
- `FINISHED`
  - session closed
- `CANCELED`
  - search canceled and stake returned

## Background jobs

The bot runs a periodic worker every 10 seconds:

- checks search timeout
- checks inactivity timeout
- rerenders active game views
- re-sends a new message if editing fails

## UI strategy

- Player main screen and player cards are two separate messages.
- Admin control is a single updated message inside the admin chat.
- Message rendering is state-driven.
- If `edit_message_text` fails, a new message is sent and rebound to the session.

## Payment flow

- Top-up is based on Telegram Stars invoices with `currency="XTR"`.
- On `successful_payment`, the bot:
  - stores charge id
  - credits wallet balance
  - writes ledger entry
  - sends user receipt
  - sends admin chat log

## Withdrawal flow

- User selects a method.
- User enters amount.
- User enters requisites.
- Balance is deducted immediately.
- Admin chat receives a completion button.

## Ticket flow

- User opens a ticket from Help.
- First free-form message creates the ticket.
- While a ticket is open, free-form messages go into the ticket.
- Menu button texts are ignored by the ticket collector.

## Important next steps

- Replace placeholder premium emoji ids with real custom emoji ids.
- Add migrations.
- Add proper media group support for ticket albums.
- Add admin reply-to-ticket flow.
- Add richer styled renderers and premium emoji wrappers across all user-visible texts.
- Add tests for blackjack resolution and timeout behavior.

