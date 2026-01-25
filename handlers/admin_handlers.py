"""
Обработчики для администраторов
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import get_db
from services import TicketService

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


class AdminStates(StatesGroup):
    """Состояния для админ-панели"""
    EDIT_WELCOME = State()
    EDIT_HELP = State()
    CHANGE_TOPIC_MODE = State()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить приветствие", callback_data="admin:edit_welcome")],
        [InlineKeyboardButton(text="✏️ Изменить справку", callback_data="admin:edit_help")],
        [InlineKeyboardButton(text="📁 Режим топиков", callback_data="admin:topic_mode")],
        [InlineKeyboardButton(text="📊 Открытые тикеты", callback_data="admin:open_tickets")]
    ])
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        topic_mode = await service.get_setting("topic_mode", "separate")
        mode_text = "Отдельный топик для каждого" if topic_mode == "separate" else "Общий топик"
        
        await message.answer(
            f"⚙️ <b>Админ-панель</b>\n\n"
            f"📁 Режим топиков: {mode_text}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin:edit_welcome")
async def cb_edit_welcome(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование приветствия"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.EDIT_WELCOME)
    await callback.message.edit_text(
        "✏️ <b>Редактирование приветствия</b>\n\n"
        "Отправьте новый текст для команды /start:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.EDIT_WELCOME)
async def process_welcome_text(message: Message, state: FSMContext):
    """Сохранить новое приветствие"""
    if not is_admin(message.from_user.id):
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        await service.set_setting("welcome_text", message.text)
    
    await state.clear()
    await message.answer("✅ Приветствие обновлено!")


@router.callback_query(F.data == "admin:edit_help")
async def cb_edit_help(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование справки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.EDIT_HELP)
    await callback.message.edit_text(
        "✏️ <b>Редактирование справки</b>\n\n"
        "Отправьте новый текст для команды /help:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.EDIT_HELP)
async def process_help_text(message: Message, state: FSMContext):
    """Сохранить новую справку"""
    if not is_admin(message.from_user.id):
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        await service.set_setting("help_text", message.text)
    
    await state.clear()
    await message.answer("✅ Справка обновлена!")


@router.callback_query(F.data == "admin:topic_mode")
async def cb_topic_mode(callback: CallbackQuery):
    """Переключение режима топиков"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        current_mode = await service.get_setting("topic_mode", "separate")
        
        new_mode = "common" if current_mode == "separate" else "separate"
        await service.set_setting("topic_mode", new_mode)
        
        mode_text = "Отдельный топик для каждого" if new_mode == "separate" else "Общий топик"
        
        await callback.message.edit_text(
            f"✅ <b>Режим топиков изменён</b>\n\n"
            f"📁 Текущий режим: {mode_text}",
            parse_mode="HTML"
        )
    
    await callback.answer("✅ Режим изменён")


@router.callback_query(F.data == "admin:open_tickets")
async def cb_open_tickets(callback: CallbackQuery):
    """Список открытых тикетов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        tickets = await service.get_open_tickets()
        
        if not tickets:
            await callback.message.edit_text("📭 Нет открытых тикетов")
            await callback.answer()
            return
        
        text = f"📊 <b>Открытые тикеты</b> ({len(tickets)})\n\n"
        
        for ticket in tickets[:20]:  # Лимит 20
            user_info = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
            status_emoji = "🟢" if ticket.status.value == "open" else "🔴"
            text += f"{status_emoji} <code>{ticket.ticket_id}</code> | {user_info}\n"
        
        if len(tickets) > 20:
            text += f"\n... и ещё {len(tickets) - 20}"
        
        await callback.message.edit_text(text, parse_mode="HTML")
    
    await callback.answer()


@router.message(Command("open_tickets"))
async def cmd_open_tickets(message: Message):
    """Команда /open_tickets"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        tickets = await service.get_open_tickets()
        
        if not tickets:
            await message.answer("📭 Нет открытых тикетов")
            return
        
        text = f"📊 <b>Открытые тикеты</b> ({len(tickets)})\n\n"
        
        for ticket in tickets[:20]:
            user_info = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
            status_emoji = "🟢" if ticket.status.value == "open" else "🔴"
            text += f"{status_emoji} <code>{ticket.ticket_id}</code> | {user_info}\n"
        
        if len(tickets) > 20:
            text += f"\n... и ещё {len(tickets) - 20}"
        
        await message.answer(text, parse_mode="HTML")

