from aiogram.fsm.state import StatesGroup, State

# ==== ДОХОД ====
class IncomeState(StatesGroup):
    choosing_date = State()               # выбор даты
    choosing_time = State()               # ввод времени
    choosing_category = State()           # выбор категории
    entering_amount = State()             # ввод суммы
    entering_note = State()               # комментарий

# ==== РАСХОД ====
class ExpenseState(StatesGroup):
    choosing_date = State()               # выбор даты
    choosing_time = State()               # ввод времени
    choosing_category = State()           # выбор категории
    entering_custom_category = State()    # если выбрано "другое"
    entering_amount = State()             # ввод суммы
    entering_note = State()               # комментарий

# ==== УДАЛЕНИЕ ====
class DeleteState(StatesGroup):
    choosing_date = State()              # выбор начальной даты
    entering_filter_value = State()      # выбор конечной даты
    confirming = State()                 # подтверждение удаления

# ==== ФИЛЬТР ДЛЯ ИСТОРИИ ====
class FilterState(StatesGroup):
    choosing_filter_type = State()       # выбор начальной даты
    entering_filter_value = State()      # выбор конечной даты

class AnalyticsState(StatesGroup):
    choosing_year = State()
    choosing_start_date = State()
    choosing_end_date = State()
