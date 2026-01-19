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
        
        user = await service.get_or_create_user(
            telegram_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_operator=user_id in OPERATOR_IDS
        )
        
        if user_id in OPERATOR_IDS:
            open_count = await service.get_open_tickets_count()
            my_tickets = await service.get_my_tickets(user)
            my_count = len(my_tickets)
            
            await state.set_state(OperatorState.OP_IDLE)
            await message.answer(
                f"🎛 <b>Панель оператора</b>\n\n"
                f"📥 Открытых: <b>{open_count}</b>\n"
                f"📌 Моих: <b>{my_count}</b>",
                reply_markup=OperatorKeyboards.main_menu(open_count, my_count),
                parse_mode="HTML"
            )
        else:
            # Показываем количество активных тикетов пользователя
            open_tickets = await service.get_user_open_tickets(user)
            
            text = "👋 Привет!\nЧем можем помочь?"
            if open_tickets:
                text = f"👋 Привет!\n\n📌 У вас {len(open_tickets)} активных обращений"
            
            await state.set_state(UserState.IDLE)
            await message.answer(text, reply_markup=UserKeyboards.main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    user_id = message.from_user.id
    
    if user_id in OPERATOR_IDS:
        await message.answer(
            "📖 <b>Справка для оператора</b>\n\n"
            "<b>Команды:</b>\n"
            "/start - главное меню\n"
            "/tickets - список тикетов\n"
            "/stats - статистика\n\n"
            "<b>Возможности:</b>\n"
            "• 📥 Просмотр открытых тикетов\n"
            "• 📌 Мои тикеты (назначенные)\n"
            "• 📦 Архив закрытых\n"
            "• 🔍 Поиск по коду\n"
            "• 📊 Статистика",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "📖 <b>Справка</b>\n\n"
            "<b>Команды:</b>\n"
            "/start - главное меню\n"
            "/new - создать тикет\n"
            "/tickets - мои обращения\n\n"
            "<b>Возможности:</b>\n"
            "• Создание тикетов\n"
            "• Общение с оператором\n"
            "• Отправка фото, видео, файлов\n"
            "• Просмотр истории\n"
            "• Закрытие тикета",
            parse_mode="HTML"
        )


@router.message(Command("new"))
async def cmd_new_ticket(message: Message, state: FSMContext):
    """Команда /new"""
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
    """Команда /tickets"""
    user_id = message.from_user.id
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        if user_id in OPERATOR_IDS:
            tickets = await service.get_all_open_tickets()
            if tickets:
                await state.set_state(OperatorState.OP_IDLE)
                await message.answer(
                    f"📥 <b>Открытые тикеты</b> ({len(tickets)})\n\n"
                    f"🔵 new · 🟡 work · 🟠 wait",
                    reply_markup=OperatorKeyboards.tickets_list(tickets),
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "📭 Нет открытых тикетов",
                    reply_markup=OperatorKeyboards.main_menu(0)
                )
        else:
            user = await service.get_or_create_user(
                telegram_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
            tickets = await service.get_user_all_tickets(user)
            
            await state.set_state(UserState.IDLE)
            await message.answer(
                "📂 <b>Мои обращения</b>\n\n"
                "🔵 открыт · 🟡 в работе · 🟠 ждёт ответа",
                reply_markup=UserKeyboards.tickets_list(tickets),
                parse_mode="HTML"
            )


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    """Команда /stats (только для операторов)"""
    user_id = message.from_user.id
    
    if user_id not in OPERATOR_IDS:
        await message.answer("❌ Команда доступна только операторам")
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        operator = await service.get_or_create_user(
            telegram_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_operator=True
        )
        
        my_stats = await service.get_operator_stats(operator)
        global_stats = await service.get_global_stats()
        
        text = (
            f"📊 <b>Статистика</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>👤 Ваша статистика:</b>\n"
            f"├ Всего: {my_stats['total']}\n"
            f"├ Закрыто: {my_stats['closed']}\n"
            f"└ В работе: {my_stats['active']}\n\n"
            f"<b>🌐 Общая:</b>\n"
            f"├ Всего: {global_stats['total']}\n"
            f"├ 🔵 Открыто: {global_stats.get('open', 0)}\n"
            f"├ 🟡 В работе: {global_stats.get('in_progress', 0)}\n"
            f"├ 🟠 Ждут: {global_stats.get('waiting_user', 0)}\n"
            f"└ ⚫ Закрыто: {global_stats.get('closed', 0)}"
        )
        
        await message.answer(
            text,
            reply_markup=OperatorKeyboards.stats_menu(),
            parse_mode="HTML"
        )
