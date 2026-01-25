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
    return user_id in ADMIN_IDS


class AdminStates(StatesGroup):
    EDIT_WELCOME = State()
    EDIT_HELP = State()


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
    
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            topic_mode = await service.get_setting("topic_mode", "separate")
            mode_text = "Отдельный топик для каждого" if topic_mode == "separate" else "Общий топик"
            
            await message.answer(
                f"⚙️ <b>Админ-панель</b>\n\n📁 Режим топиков: {mode_text}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Error in cmd_admin: {e}", exc_info=True)


@router.message(Command("open_tickets"))
async def cmd_open_tickets(message: Message):
    """Команда /open_tickets"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            tickets = await service.get_open_tickets()
            
            if not tickets:
                await message.answer("📭 Нет открытых тикетов")
                return
            
            text = f"📊 <b>Открытые тикеты</b> ({len(tickets)})\n\n"
            
            for ticket in tickets[:20]:
                user_info = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
                text += f"🟢 <code>{ticket.ticket_id}</code> | {user_info}\n"
            
            if len(tickets) > 20:
                text += f"\n... и ещё {len(tickets) - 20}"
            
            await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_open_tickets: {e}", exc_info=True)


@router.callback_query(F.data.startswith("admin:"))
async def handle_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка callback админ-панели"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    try:
        if callback.data == "admin:edit_welcome":
            await state.set_state(AdminStates.EDIT_WELCOME)
            await callback.message.edit_text("✏️ <b>Редактирование приветствия</b>\n\nОтправьте новый текст для команды /start:", parse_mode="HTML")
            await callback.answer()
        
        elif callback.data == "admin:edit_help":
            await state.set_state(AdminStates.EDIT_HELP)
            await callback.message.edit_text("✏️ <b>Редактирование справки</b>\n\nОтправьте новый текст для команды /help:", parse_mode="HTML")
            await callback.answer()
        
        elif callback.data == "admin:topic_mode":
            async with get_db().session_factory() as session:
                service = TicketService(session)
                current_mode = await service.get_setting("topic_mode", "separate")
                new_mode = "common" if current_mode == "separate" else "separate"
                await service.set_setting("topic_mode", new_mode)
                mode_text = "Отдельный топик для каждого" if new_mode == "separate" else "Общий топик"
                await callback.message.edit_text(f"✅ <b>Режим топиков изменён</b>\n\n📁 Текущий режим: {mode_text}", parse_mode="HTML")
            await callback.answer("✅ Режим изменён")
        
        elif callback.data == "admin:open_tickets":
            async with get_db().session_factory() as session:
                service = TicketService(session)
                tickets = await service.get_open_tickets()
                
                if not tickets:
                    await callback.message.edit_text("📭 Нет открытых тикетов")
                    await callback.answer()
                    return
                
                text = f"📊 <b>Открытые тикеты</b> ({len(tickets)})\n\n"
                for ticket in tickets[:20]:
                    user_info = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
                    text += f"🟢 <code>{ticket.ticket_id}</code> | {user_info}\n"
                
                if len(tickets) > 20:
                    text += f"\n... и ещё {len(tickets) - 20}"
                
                await callback.message.edit_text(text, parse_mode="HTML")
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in handle_admin_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(AdminStates.EDIT_WELCOME)
async def process_welcome_text(message: Message, state: FSMContext):
    """Сохранить новое приветствие"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            await service.set_setting("welcome_text", message.text)
        await state.clear()
        await message.answer("✅ Приветствие обновлено!")
    except Exception as e:
        logger.error(f"Error in process_welcome_text: {e}", exc_info=True)


@router.message(AdminStates.EDIT_HELP)
async def process_help_text(message: Message, state: FSMContext):
    """Сохранить новую справку"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            await service.set_setting("help_text", message.text)
        await state.clear()
        await message.answer("✅ Справка обновлена!")
    except Exception as e:
        logger.error(f"Error in process_help_text: {e}", exc_info=True)
