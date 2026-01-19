"""
Обработчики для оператора
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import OPERATOR_IDS
from database import get_db, TicketStatus
from services import TicketService
from states import OperatorState
from keyboards import OperatorKeyboards

router = Router()
logger = logging.getLogger(__name__)

SUPPORTED_CONTENT_TYPES = {"text", "photo", "document", "video", "voice", "video_note", "sticker", "animation"}


def is_operator(user_id: int) -> bool:
    return user_id in OPERATOR_IDS


# ==================== ГЛАВНОЕ МЕНЮ ====================

@router.callback_query(F.data == "op_refresh")
async def cb_op_refresh(callback: CallbackQuery, state: FSMContext):
    """Обновить меню оператора"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        open_count = await service.get_open_tickets_count()
        
        operator = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            is_operator=True
        )
        my_tickets = await service.get_my_tickets(operator)
        my_count = len(my_tickets)
        
        await state.set_state(OperatorState.OP_IDLE)
        await callback.message.edit_text(
            f"🎛 <b>Панель оператора</b>\n\n"
            f"📥 Открытых: <b>{open_count}</b>\n"
            f"📌 Моих: <b>{my_count}</b>",
            reply_markup=OperatorKeyboards.main_menu(open_count, my_count),
            parse_mode="HTML"
        )
    
    await callback.answer("✅ Обновлено")


@router.callback_query(F.data == "op_back_menu")
async def cb_op_back_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        open_count = await service.get_open_tickets_count()
        
        operator = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            is_operator=True
        )
        my_tickets = await service.get_my_tickets(operator)
        my_count = len(my_tickets)
        
        await state.set_state(OperatorState.OP_IDLE)
        await state.update_data(current_ticket_code=None)
        await callback.message.edit_text(
            f"🎛 <b>Панель оператора</b>\n\n"
            f"📥 Открытых: <b>{open_count}</b>\n"
            f"📌 Моих: <b>{my_count}</b>",
            reply_markup=OperatorKeyboards.main_menu(open_count, my_count),
            parse_mode="HTML"
        )
    
    await callback.answer()


# ==================== СПИСКИ ТИКЕТОВ ====================

@router.callback_query(F.data == "op_list_tickets")
async def cb_op_list_tickets(callback: CallbackQuery, state: FSMContext):
    """Список открытых тикетов"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        tickets = await service.get_all_open_tickets()
        
        if tickets:
            await state.set_state(OperatorState.OP_IDLE)
            await callback.message.edit_text(
                f"📥 <b>Открытые тикеты</b> ({len(tickets)})\n\n"
                f"⚪ new · 🟠 work · 🔴 wait",
                reply_markup=OperatorKeyboards.tickets_list(tickets),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "📭 <b>Нет открытых тикетов</b>\n\n"
                "Новые тикеты появятся здесь.",
                reply_markup=OperatorKeyboards.main_menu(0),
                parse_mode="HTML"
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("op_filter:"))
async def cb_op_filter(callback: CallbackQuery, state: FSMContext):
    """Фильтр тикетов по статусу"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    status_map = {
        "open": TicketStatus.OPEN,
        "in_progress": TicketStatus.IN_PROGRESS,
        "waiting_user": TicketStatus.WAITING_USER
    }
    
    filter_key = callback.data.split(":")[1]
    status = status_map.get(filter_key)
    
    if not status:
        await callback.answer("Неверный фильтр", show_alert=True)
        return
    
    status_names = {
        TicketStatus.OPEN: "⚪ Новые",
        TicketStatus.IN_PROGRESS: "🟠 В работе",
        TicketStatus.WAITING_USER: "🟠 Ждут ответа"
    }
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        tickets = await service.get_tickets_by_status(status)
        
        if tickets:
            await callback.message.edit_text(
                f"📋 <b>{status_names[status]}</b> ({len(tickets)})",
                reply_markup=OperatorKeyboards.tickets_list(tickets),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"📭 <b>{status_names[status]}</b>\n\nНет тикетов с таким статусом.",
                reply_markup=OperatorKeyboards.tickets_list([], show_filters=True),
                parse_mode="HTML"
            )
    
    await callback.answer()


@router.callback_query(F.data == "op_my_tickets")
async def cb_op_my_tickets(callback: CallbackQuery, state: FSMContext):
    """Мои тикеты (назначенные)"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        operator = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            is_operator=True
        )
        tickets = await service.get_my_tickets(operator)
        
        await callback.message.edit_text(
            f"📌 <b>Мои тикеты</b> ({len(tickets)})",
            reply_markup=OperatorKeyboards.my_tickets_list(tickets),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "op_archive")
async def cb_op_archive(callback: CallbackQuery, state: FSMContext):
    """Архив закрытых тикетов"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        tickets = await service.get_closed_tickets(limit=15)
        
        await callback.message.edit_text(
            f"📦 <b>Архив</b> (последние {len(tickets)})",
            reply_markup=OperatorKeyboards.archive_list(tickets),
            parse_mode="HTML"
        )
    
    await callback.answer()


# ==================== СТАТИСТИКА ====================

@router.callback_query(F.data == "op_stats")
async def cb_op_stats(callback: CallbackQuery, state: FSMContext):
    """Статистика"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        operator = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            is_operator=True
        )
        
        my_stats = await service.get_operator_stats(operator)
        global_stats = await service.get_global_stats()
        
        text = (
            f"📊 <b>Статистика</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>👤 Ваша статистика:</b>\n"
            f"├ Всего обработано: {my_stats['total']}\n"
            f"├ Закрыто: {my_stats['closed']}\n"
            f"└ В работе: {my_stats['active']}\n\n"
            f"<b>🌐 Общая статистика:</b>\n"
            f"├ Всего тикетов: {global_stats['total']}\n"
            f"├ ⚪ Открытых: {global_stats.get('open', 0)}\n"
            f"├ 🟠 В работе: {global_stats.get('in_progress', 0)}\n"
            f"├ 🟠 Ждут ответа: {global_stats.get('waiting_user', 0)}\n"
            f"└ ⚫ Закрыто: {global_stats.get('closed', 0)}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=OperatorKeyboards.stats_menu(),
            parse_mode="HTML"
        )
    
    await callback.answer()


# ==================== ПОИСК ====================

@router.callback_query(F.data == "op_search")
async def cb_op_search(callback: CallbackQuery, state: FSMContext):
    """Начать поиск тикета"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(OperatorState.OP_IDLE)
    await state.update_data(search_mode=True)
    
    await callback.message.edit_text(
        "🔍 <b>Поиск тикета</b>\n\n"
        "Введите код тикета (например: SHFT-A1B2)",
        reply_markup=OperatorKeyboards.search_cancel(),
        parse_mode="HTML"
    )
    
    await callback.answer()


# ==================== ПРОСМОТР ТИКЕТА ====================

@router.callback_query(F.data.startswith("op_view:"))
async def cb_op_view_ticket(callback: CallbackQuery, state: FSMContext):
    """Просмотр тикета"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        await state.update_data(current_ticket_code=ticket_code, search_mode=False)
        await state.set_state(OperatorState.OP_VIEW_TICKET)
        
        messages = await service.get_ticket_messages(ticket, limit=5)
        text = format_ticket_view(ticket, messages)
        
        await callback.message.edit_text(
            text,
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("op_quick_reply:"))
async def cb_op_quick_reply(callback: CallbackQuery, state: FSMContext):
    """Быстрый ответ"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    await state.update_data(current_ticket_code=ticket_code)
    await state.set_state(OperatorState.OP_REPLY)
    
    await callback.message.edit_text(
        f"✍️ <b>Ответ на {ticket_code}</b>\n\n"
        f"Отправьте сообщение пользователю.",
        reply_markup=OperatorKeyboards.reply_cancel(ticket_code),
        parse_mode="HTML"
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("op_reply:"))
async def cb_op_reply(callback: CallbackQuery, state: FSMContext):
    """Начать ответ"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    await state.update_data(current_ticket_code=ticket_code)
    await state.set_state(OperatorState.OP_REPLY)
    
    await callback.message.edit_text(
        f"✍️ <b>Ответ на {ticket_code}</b>\n\n"
        f"Отправьте сообщение пользователю.",
        reply_markup=OperatorKeyboards.reply_cancel(ticket_code),
        parse_mode="HTML"
    )
    
    await callback.answer()


# ==================== ДЕЙСТВИЯ С ТИКЕТОМ ====================

@router.callback_query(F.data.startswith("op_close:"))
async def cb_op_close(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Закрыть тикет"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    user_telegram_id = None
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        user_telegram_id = ticket.user.telegram_id
        
        operator = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            is_operator=True
        )
        
        await service.update_ticket_status(ticket, TicketStatus.CLOSED, operator)
        open_count = await service.get_open_tickets_count()
        my_tickets = await service.get_my_tickets(operator)
        my_count = len(my_tickets)
    
    if user_telegram_id:
        try:
            await bot.send_message(
                user_telegram_id,
                f"✅ <b>Обращение закрыто</b>\n\n"
                f"🎫 {ticket_code}\n\n"
                f"Спасибо за обращение! Если проблема появится снова — создайте новый тикет.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
    
    await callback.message.edit_text(
        f"🔒 Тикет <code>{ticket_code}</code> закрыт\n\n"
        f"📥 Открытых: {open_count}",
        reply_markup=OperatorKeyboards.main_menu(open_count, my_count),
        parse_mode="HTML"
    )
    await state.set_state(OperatorState.OP_IDLE)
    await callback.answer("✅ Закрыт")


@router.callback_query(F.data.startswith("op_waiting:"))
async def cb_op_waiting(callback: CallbackQuery, state: FSMContext):
    """Статус: ждём пользователя"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        operator = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            is_operator=True
        )
        
        await service.update_ticket_status(ticket, TicketStatus.WAITING_USER, operator)
        ticket = await service.get_ticket_by_code(ticket_code)
        messages = await service.get_ticket_messages(ticket, limit=5)
        text = format_ticket_view(ticket, messages)
        
        await callback.message.edit_text(
            text,
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer("✅ Ждём ответа")


@router.callback_query(F.data.startswith("op_take:"))
async def cb_op_take(callback: CallbackQuery, state: FSMContext):
    """Взять тикет"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        operator = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            is_operator=True
        )
        
        await service.update_ticket_status(ticket, TicketStatus.IN_PROGRESS, operator)
        ticket = await service.get_ticket_by_code(ticket_code)
        messages = await service.get_ticket_messages(ticket, limit=5)
        text = format_ticket_view(ticket, messages)
        
        await callback.message.edit_text(
            text,
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer("✅ Тикет ваш")


@router.callback_query(F.data.startswith("op_reopen:"))
async def cb_op_reopen(callback: CallbackQuery, state: FSMContext):
    """Переоткрыть тикет"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        operator = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            is_operator=True
        )
        
        await service.update_ticket_status(ticket, TicketStatus.IN_PROGRESS, operator)
        ticket = await service.get_ticket_by_code(ticket_code)
        messages = await service.get_ticket_messages(ticket, limit=5)
        text = format_ticket_view(ticket, messages)
        
        await callback.message.edit_text(
            text,
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer("✅ Переоткрыт")


@router.callback_query(F.data.startswith("op_priority:"))
async def cb_op_priority(callback: CallbackQuery, state: FSMContext):
    """Изменить приоритет"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    parts = callback.data.split(":")
    ticket_code = parts[1]
    priority = parts[2]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        ticket.priority = priority
        await session.commit()
        
        ticket = await service.get_ticket_by_code(ticket_code)
        messages = await service.get_ticket_messages(ticket, limit=5)
        text = format_ticket_view(ticket, messages)
        
        await callback.message.edit_text(
            text,
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    priority_text = "🔴 Срочный" if priority == "high" else "🟢 Обычный"
    await callback.answer(f"✅ Приоритет: {priority_text}")


@router.callback_query(F.data.startswith("op_history:"))
async def cb_op_history(callback: CallbackQuery, state: FSMContext):
    """История сообщений"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        messages = await service.get_ticket_messages(ticket, limit=30)
        
        if not messages:
            await callback.answer("Нет сообщений", show_alert=True)
            return
        
        history_text = f"📜 <b>История {ticket_code}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        
        for msg in messages:
            sender = "👤" if not msg.is_from_operator else "👨‍💼"
            time_str = msg.created_at.strftime("%d.%m %H:%M")
            
            if msg.text:
                content = msg.text[:150] + "…" if len(msg.text) > 150 else msg.text
            else:
                type_icons = {
                    "photo": "🖼 Фото", "video": "🎥 Видео", "voice": "🎤 Голосовое",
                    "video_note": "📹 Кружок", "document": f"📎 {msg.file_name or 'Файл'}",
                    "sticker": "😀 Стикер", "animation": "🎞 GIF"
                }
                content = type_icons.get(msg.content_type, f"[{msg.content_type}]")
            
            history_text += f"{sender} <i>{time_str}</i>\n{content}\n\n"
        
        if len(history_text) > 4000:
            history_text = history_text[:4000] + "\n\n… (обрезано)"
        
        await callback.message.edit_text(
            history_text,
            reply_markup=OperatorKeyboards.history_back(ticket_code),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("op_back_ticket:"))
async def cb_op_back_to_ticket(callback: CallbackQuery, state: FSMContext):
    """Назад к тикету"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        await state.set_state(OperatorState.OP_VIEW_TICKET)
        messages = await service.get_ticket_messages(ticket, limit=5)
        text = format_ticket_view(ticket, messages)
        
        await callback.message.edit_text(
            text,
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("op_cancel_reply:"))
async def cb_op_cancel_reply(callback: CallbackQuery, state: FSMContext):
    """Отмена ответа"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if ticket:
            await state.set_state(OperatorState.OP_VIEW_TICKET)
            messages = await service.get_ticket_messages(ticket, limit=5)
            text = format_ticket_view(ticket, messages)
            
            await callback.message.edit_text(
                text,
                reply_markup=OperatorKeyboards.ticket_view(ticket),
                parse_mode="HTML"
            )
        else:
            open_count = await service.get_open_tickets_count()
            await state.set_state(OperatorState.OP_IDLE)
            await callback.message.edit_text(
                f"🎛 <b>Панель оператора</b>\n\n📥 Открытых: <b>{open_count}</b>",
                reply_markup=OperatorKeyboards.main_menu(open_count),
                parse_mode="HTML"
            )
    
    await callback.answer()


# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================

@router.message(OperatorState.OP_REPLY, F.content_type.in_(SUPPORTED_CONTENT_TYPES))
async def process_op_reply(message: Message, state: FSMContext, bot: Bot):
    """Ответ оператора"""
    if not is_operator(message.from_user.id):
        return
    
    data = await state.get_data()
    ticket_code = data.get("current_ticket_code")
    
    if not ticket_code:
        await message.answer("❌ Сначала выберите тикет")
        await state.set_state(OperatorState.OP_IDLE)
        return
    
    user_telegram_id = None
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await message.answer("❌ Тикет не найден")
            await state.set_state(OperatorState.OP_IDLE)
            return
        
        if ticket.status == TicketStatus.CLOSED:
            await message.answer("❌ Тикет закрыт")
            await state.set_state(OperatorState.OP_IDLE)
            return
        
        user_telegram_id = ticket.user.telegram_id
        
        operator = await service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_operator=True
        )
        
        content_type, text, file_id, file_name = extract_message_content(message)
        
        await service.add_message(
            ticket=ticket,
            sender=operator,
            content_type=content_type,
            text=text,
            file_id=file_id,
            file_name=file_name,
            is_from_operator=True
        )
        
        await service.update_ticket_status(ticket, TicketStatus.IN_PROGRESS, operator)
    
    if user_telegram_id:
        try:
            await bot.send_message(
                user_telegram_id,
                f"💬 <b>Ответ от поддержки</b>\n🎫 {ticket_code}",
                parse_mode="HTML"
            )
            await forward_content(bot, user_telegram_id, message)
            await message.answer(
                f"✅ Отправлено",
                reply_markup=OperatorKeyboards.after_reply(ticket_code)
            )
        except Exception as e:
            logger.error(f"Failed to send: {e}")
            await message.answer(f"⚠️ Сохранено, но не отправлено: {e}")
    else:
        await message.answer("⚠️ Пользователь не найден")


@router.message(OperatorState.OP_REPLY)
async def process_op_reply_invalid(message: Message, state: FSMContext):
    """Неподдерживаемый тип"""
    if not is_operator(message.from_user.id):
        return
    
    data = await state.get_data()
    ticket_code = data.get("current_ticket_code", "")
    
    await message.answer(
        "❌ Неподдерживаемый тип сообщения",
        reply_markup=OperatorKeyboards.reply_cancel(ticket_code)
    )


@router.message(OperatorState.OP_IDLE)
async def process_op_idle_message(message: Message, state: FSMContext):
    """Сообщение в IDLE (возможно поиск)"""
    if not is_operator(message.from_user.id):
        return
    
    data = await state.get_data()
    
    # Режим поиска
    if data.get("search_mode") and message.text:
        search_query = message.text.strip().upper()
        
        async with get_db().session_factory() as session:
            service = TicketService(session)
            ticket = await service.search_ticket(search_query)
            
            if ticket:
                await state.update_data(search_mode=False)
                await message.answer(
                    f"✅ <b>Найден тикет</b>\n\n"
                    f"🎫 <code>{ticket.ticket_code}</code>\n"
                    f"📝 {ticket.subject[:50]}",
                    reply_markup=OperatorKeyboards.search_result(ticket.ticket_code),
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"❌ Тикет <code>{search_query}</code> не найден",
                    reply_markup=OperatorKeyboards.search_cancel(),
                    parse_mode="HTML"
                )
        return
    
    # Обычное сообщение
    async with get_db().session_factory() as session:
        service = TicketService(session)
        open_count = await service.get_open_tickets_count()
    
    await message.answer(
        "❌ Выберите тикет из списка",
        reply_markup=OperatorKeyboards.main_menu(open_count)
    )


@router.message(OperatorState.OP_VIEW_TICKET)
async def process_op_view_message(message: Message, state: FSMContext):
    """Сообщение при просмотре"""
    if not is_operator(message.from_user.id):
        return
    
    data = await state.get_data()
    ticket_code = data.get("current_ticket_code", "")
    
    await message.answer(
        "💡 Нажмите «✍️ Ответить» для ответа",
        reply_markup=OperatorKeyboards.quick_actions(ticket_code) if ticket_code else None
    )


# ==================== HELPERS ====================

def format_ticket_view(ticket, messages) -> str:
    """Форматирование карточки тикета"""
    status_info = {
        TicketStatus.OPEN: ("⚪", "Открыт"),
        TicketStatus.IN_PROGRESS: ("🟠", "В работе"),
        TicketStatus.WAITING_USER: ("🟠", "Ждём ответа"),
        TicketStatus.CLOSED: ("⚫", "Закрыт")
    }
    
    emoji, status_text = status_info.get(ticket.status, ("⚪", "?"))
    username = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
    
    operator_text = "—"
    if ticket.operator:
        operator_text = f"@{ticket.operator.username}" if ticket.operator.username else ticket.operator.full_name
    
    priority_text = "🔴 Срочный" if ticket.priority == "high" else "🟢 Обычный"
    
    text = (
        f"🎫 <b>{ticket.ticket_code}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{emoji} <b>Статус:</b> {status_text}\n"
        f"👤 <b>Клиент:</b> {username}\n"
        f"👨‍💼 <b>Оператор:</b> {operator_text}\n"
        f"🏷 <b>Приоритет:</b> {priority_text}\n"
        f"📅 <b>Создан:</b> {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"📝 <b>Тема:</b>\n{ticket.subject}\n"
    )
    
    if messages:
        text += f"\n━━━━━━━━━━━━━━━━━━\n💬 <b>Последние:</b>\n\n"
        for msg in messages[-3:]:
            sender = "👤" if not msg.is_from_operator else "👨‍💼"
            content = msg.text[:60] + "…" if msg.text and len(msg.text) > 60 else (msg.text or f"[{msg.content_type}]")
            text += f"{sender} {content}\n"
    
    return text


def extract_message_content(message: Message) -> tuple[str, str | None, str | None, str | None]:
    """Извлечение контента"""
    content_type = message.content_type
    text = None
    file_id = None
    file_name = None
    
    if content_type == "text":
        text = message.text
    elif content_type == "photo":
        file_id = message.photo[-1].file_id
        text = message.caption
    elif content_type == "document":
        file_id = message.document.file_id
        file_name = message.document.file_name
        text = message.caption
    elif content_type == "video":
        file_id = message.video.file_id
        file_name = message.video.file_name
        text = message.caption
    elif content_type == "voice":
        file_id = message.voice.file_id
        text = message.caption
    elif content_type == "video_note":
        file_id = message.video_note.file_id
    elif content_type == "sticker":
        file_id = message.sticker.file_id
    elif content_type == "animation":
        file_id = message.animation.file_id
        text = message.caption
    
    return content_type, text, file_id, file_name


async def forward_content(bot: Bot, chat_id: int, message: Message):
    """Пересылка контента"""
    try:
        ct = message.content_type
        if ct == "text":
            await bot.send_message(chat_id, message.text)
        elif ct == "photo":
            await bot.send_photo(chat_id, message.photo[-1].file_id, caption=message.caption)
        elif ct == "document":
            await bot.send_document(chat_id, message.document.file_id, caption=message.caption)
        elif ct == "video":
            await bot.send_video(chat_id, message.video.file_id, caption=message.caption)
        elif ct == "voice":
            await bot.send_voice(chat_id, message.voice.file_id, caption=message.caption)
        elif ct == "video_note":
            await bot.send_video_note(chat_id, message.video_note.file_id)
        elif ct == "sticker":
            await bot.send_sticker(chat_id, message.sticker.file_id)
        elif ct == "animation":
            await bot.send_animation(chat_id, message.animation.file_id, caption=message.caption)
    except Exception as e:
        logger.error(f"Forward failed: {e}")
