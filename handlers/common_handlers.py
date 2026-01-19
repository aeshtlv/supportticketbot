"""
Общие обработчики (start, help)
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import OPERATOR_IDS
from database import get_db
from services import TicketService
from states import UserState, OperatorState
from keyboards import UserKeyboards, OperatorKeyboards

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start - точка входа"""
    user_id = message.from_user.id
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        # Создаём/обновляем пользователя
        user = await service.get_or_create_user(
            telegram_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_operator=user_id in OPERATOR_IDS
        )
        
        # Проверяем, оператор ли это
        if user_id in OPERATOR_IDS:
            open_count = await service.get_open_tickets_count()
            await state.set_state(OperatorState.OP_IDLE)
            await message.answer(
                f"👋 Привет, оператор!\n\n"
                f"📥 Новых тикетов: {open_count}",
                reply_markup=OperatorKeyboards.main_menu(open_count)
            )
        else:
            await state.set_state(UserState.IDLE)
            await message.answer(
                "👋 Привет!\n"
                "Чем можем помочь?",
                reply_markup=UserKeyboards.main_menu()
            )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    user_id = message.from_user.id
    
    if user_id in OPERATOR_IDS:
        await message.answer(
            "📖 <b>Справка для оператора</b>\n\n"
            "/start - главное меню\n"
            "/tickets - список тикетов\n\n"
            "Выберите тикет из списка, чтобы:\n"
            "• Ответить пользователю\n"
            "• Изменить статус\n"
            "• Закрыть обращение",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "📖 <b>Справка</b>\n\n"
            "/start - главное меню\n"
            "/new - создать новый тикет\n"
            "/tickets - мои обращения\n\n"
            "Вы можете создать тикет и переписываться "
            "с оператором прямо в боте.",
            parse_mode="HTML"
        )


@router.message(Command("new"))
async def cmd_new_ticket(message: Message, state: FSMContext):
    """Команда /new - быстрое создание тикета"""
    user_id = message.from_user.id
    
    if user_id in OPERATOR_IDS:
        await message.answer("❌ Операторы не могут создавать тикеты")
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        user = await service.get_or_create_user(
            telegram_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        
        open_tickets = await service.get_user_open_tickets(user)
        
        if open_tickets:
            await state.update_data(pending_action="create_ticket")
            await state.set_state(UserState.CONFIRM_NEW_TICKET)
            await message.answer(
                f"⚠️ У вас уже есть открытый тикет ({len(open_tickets)} шт.)\n"
                "Создать ещё один?",
                reply_markup=UserKeyboards.confirm_new_ticket()
            )
        else:
            await state.set_state(UserState.CREATE_TICKET_SUBJECT)
            await message.answer(
                "✏️ Коротко опишите проблему\n"
                "(1–2 предложения)",
                reply_markup=UserKeyboards.cancel()
            )


@router.message(Command("tickets"))
async def cmd_tickets(message: Message, state: FSMContext):
    """Команда /tickets - список тикетов"""
    user_id = message.from_user.id
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        if user_id in OPERATOR_IDS:
            # Для оператора - все открытые тикеты
            tickets = await service.get_all_open_tickets()
            if tickets:
                await state.set_state(OperatorState.OP_IDLE)
                await message.answer(
                    f"📥 Открытые тикеты ({len(tickets)}):",
                    reply_markup=OperatorKeyboards.tickets_list(tickets)
                )
            else:
                await message.answer("📭 Нет открытых тикетов")
        else:
            # Для пользователя - его тикеты
            user = await service.get_or_create_user(
                telegram_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
            tickets = await service.get_user_all_tickets(user)
            
            if tickets:
                await state.set_state(UserState.IDLE)
                await message.answer(
                    "📂 Ваши обращения:",
                    reply_markup=UserKeyboards.tickets_list(tickets)
                )
            else:
                await message.answer(
                    "📭 У вас пока нет обращений",
                    reply_markup=UserKeyboards.main_menu()
                )

