from aiogram.fsm.state import State, StatesGroup


class WithdrawalStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_requisites = State()


class TicketStates(StatesGroup):
    waiting_for_message = State()

