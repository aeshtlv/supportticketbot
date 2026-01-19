"""
Обработчики для оператора
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import OPERATOR_IDS
from database import get_db, TicketStatus
from services import TicketService
from states import OperatorState
from keyboards import OperatorKeyboards

router = Router()


# ==================== ФИЛЬТР ОПЕРАТОРА ====================

def is_operator(user_id: int) -> bool:
    """Проверка, является ли пользователь оператором"""
    return user_id in OPERATOR_IDS


# ==================== CALLBACK HANDLERS ====================

@router.callback_query(F.data == "op_list_tickets")
async def cb_op_list_tickets(callback: CallbackQuery, state: FSMContext):
    """Список тикетов для оператора"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        tickets = await service.get_all_open_tickets()
        
        if tickets:
            await state.set_state(OperatorState.OP_IDLE)
            await callback.message.edit_text(
                f"📥 Открытые тикеты ({len(tickets)}):",
                reply_markup=OperatorKeyboards.tickets_list(tickets)
            )
        else:
            await callback.message.edit_text(
                "📭 Нет открытых тикетов",
                reply_markup=OperatorKeyboards.main_menu(0)
            )
    
    await callback.answer()


@router.callback_query(F.data == "op_refresh")
async def cb_op_refresh(callback: CallbackQuery, state: FSMContext):
    """Обновить меню оператора"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        open_count = await service.get_open_tickets_count()
        
        await state.set_state(OperatorState.OP_IDLE)
        await callback.message.edit_text(
            f"👋 Панель оператора\n\n"
            f"📥 Открытых тикетов: {open_count}",
            reply_markup=OperatorKeyboards.main_menu(open_count)
        )
    
    await callback.answer("Обновлено")


@router.callback_query(F.data == "op_back_menu")
async def cb_op_back_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню оператора"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        open_count = await service.get_open_tickets_count()
        
        await state.set_state(OperatorState.OP_IDLE)
        await state.update_data(current_ticket_code=None)
        await callback.message.edit_text(
            f"👋 Панель оператора\n\n"
            f"📥 Открытых тикетов: {open_count}",
            reply_markup=OperatorKeyboards.main_menu(open_count)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("op_view:"))
async def cb_op_view_ticket(callback: CallbackQuery, state: FSMContext):
    """Просмотр тикета оператором"""
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
        
        # Сохраняем в state
        await state.update_data(current_ticket_code=ticket_code)
        await state.set_state(OperatorState.OP_VIEW_TICKET)
        
        # Формируем текст
        status_text = {
            TicketStatus.OPEN: "🔵 Открыт",
            TicketStatus.IN_PROGRESS: "🟡 В обработке",
            TicketStatus.WAITING_USER: "🟠 Ожидаем пользователя",
            TicketStatus.CLOSED: "⚫ Закрыт"
        }.get(ticket.status, "Неизвестно")
        
        username = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
        operator_name = "Не назначен"
        if ticket.operator:
            operator_name = f"@{ticket.operator.username}" if ticket.operator.username else ticket.operator.full_name
        
        await callback.message.edit_text(
            f"🎫 <b>{ticket.ticket_code}</b>\n\n"
            f"📊 <b>Статус:</b> {status_text}\n"
            f"👤 <b>Пользователь:</b> {username}\n"
            f"👨‍💼 <b>Оператор:</b> {operator_name}\n"
            f"🏷 <b>Приоритет:</b> {ticket.priority}\n\n"
            f"📝 <b>Тема:</b>\n{ticket.subject}",
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("op_reply:"))
async def cb_op_reply(callback: CallbackQuery, state: FSMContext):
    """Начать ответ на тикет"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    ticket_code = callback.data.split(":")[1]
    
    await state.update_data(current_ticket_code=ticket_code)
    await state.set_state(OperatorState.OP_REPLY)
    
    await callback.message.edit_text(
        f"✍️ <b>Ответ на тикет {ticket_code}</b>\n\n"
        f"Введите ответ пользователю:\n"
        f"(текст, фото или документ)",
        reply_markup=OperatorKeyboards.reply_cancel(),
        parse_mode="HTML"
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("op_close:"))
async def cb_op_close(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Закрыть тикет"""
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
        
        # Закрываем тикет
        await service.update_ticket_status(ticket, TicketStatus.CLOSED, operator)
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                ticket.user.telegram_id,
                f"✅ <b>Обращение закрыто</b>\n\n"
                f"🎫 {ticket.ticket_code}\n\n"
                f"Если проблема появится снова — создайте новый тикет.",
                parse_mode="HTML"
            )
        except Exception:
            pass
        
        # Обновляем меню
        open_count = await service.get_open_tickets_count()
        await callback.message.edit_text(
            f"🔒 Тикет {ticket_code} закрыт\n\n"
            f"📥 Открытых тикетов: {open_count}",
            reply_markup=OperatorKeyboards.main_menu(open_count)
        )
        await state.set_state(OperatorState.OP_IDLE)
    
    await callback.answer("Тикет закрыт")


@router.callback_query(F.data.startswith("op_waiting:"))
async def cb_op_waiting(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Установить статус "Ожидаем пользователя" """
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
        
        # Перезагружаем ticket для обновления связей
        ticket = await service.get_ticket_by_code(ticket_code)
        
        # Обновляем отображение
        status_text = "🟠 Ожидаем пользователя"
        username = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
        operator_name = f"@{operator.username}" if operator.username else operator.full_name
        
        await callback.message.edit_text(
            f"🎫 <b>{ticket.ticket_code}</b>\n\n"
            f"📊 <b>Статус:</b> {status_text}\n"
            f"👤 <b>Пользователь:</b> {username}\n"
            f"👨‍💼 <b>Оператор:</b> {operator_name}\n"
            f"🏷 <b>Приоритет:</b> {ticket.priority}\n\n"
            f"📝 <b>Тема:</b>\n{ticket.subject}",
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer("Статус обновлён")


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
        
        # Перезагружаем ticket
        ticket = await service.get_ticket_by_code(ticket_code)
        
        status_text = "🟡 В обработке"
        username = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
        operator_name = f"@{operator.username}" if operator.username else operator.full_name
        
        await callback.message.edit_text(
            f"🎫 <b>{ticket.ticket_code}</b>\n\n"
            f"📊 <b>Статус:</b> {status_text}\n"
            f"👤 <b>Пользователь:</b> {username}\n"
            f"👨‍💼 <b>Оператор:</b> {operator_name}\n"
            f"🏷 <b>Приоритет:</b> {ticket.priority}\n\n"
            f"📝 <b>Тема:</b>\n{ticket.subject}",
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer("Тикет переоткрыт")


@router.callback_query(F.data.startswith("op_history:"))
async def cb_op_history(callback: CallbackQuery, state: FSMContext):
    """Показать историю сообщений тикета"""
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
        
        messages = await service.get_ticket_messages(ticket, limit=20)
        
        if not messages:
            await callback.answer("Нет сообщений", show_alert=True)
            return
        
        history_text = f"📜 <b>История {ticket_code}</b>\n\n"
        
        for msg in messages:
            sender = "👤" if not msg.is_from_operator else "👨‍💼"
            time_str = msg.created_at.strftime("%d.%m %H:%M")
            text = msg.text or f"[{msg.content_type}]"
            if len(text) > 150:
                text = text[:150] + "..."
            history_text += f"{sender} [{time_str}]\n{text}\n\n"
        
        # Ограничиваем длину
        if len(history_text) > 4000:
            history_text = history_text[:4000] + "\n\n... (обрезано)"
        
        await callback.message.edit_text(
            history_text,
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "op_cancel_reply")
async def cb_op_cancel_reply(callback: CallbackQuery, state: FSMContext):
    """Отмена ответа"""
    if not is_operator(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    data = await state.get_data()
    ticket_code = data.get("current_ticket_code")
    
    if ticket_code:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            ticket = await service.get_ticket_by_code(ticket_code)
            
            if ticket:
                await state.set_state(OperatorState.OP_VIEW_TICKET)
                
                status_text = {
                    TicketStatus.OPEN: "🔵 Открыт",
                    TicketStatus.IN_PROGRESS: "🟡 В обработке",
                    TicketStatus.WAITING_USER: "🟠 Ожидаем пользователя",
                    TicketStatus.CLOSED: "⚫ Закрыт"
                }.get(ticket.status, "Неизвестно")
                
                username = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
                operator_name = "Не назначен"
                if ticket.operator:
                    operator_name = f"@{ticket.operator.username}" if ticket.operator.username else ticket.operator.full_name
                
                await callback.message.edit_text(
                    f"🎫 <b>{ticket.ticket_code}</b>\n\n"
                    f"📊 <b>Статус:</b> {status_text}\n"
                    f"👤 <b>Пользователь:</b> {username}\n"
                    f"👨‍💼 <b>Оператор:</b> {operator_name}\n"
                    f"🏷 <b>Приоритет:</b> {ticket.priority}\n\n"
                    f"📝 <b>Тема:</b>\n{ticket.subject}",
                    reply_markup=OperatorKeyboards.ticket_view(ticket),
                    parse_mode="HTML"
                )
                await callback.answer()
                return
    
    # Fallback - возврат в меню
    async with get_db().session_factory() as session:
        service = TicketService(session)
        open_count = await service.get_open_tickets_count()
        
        await state.set_state(OperatorState.OP_IDLE)
        await callback.message.edit_text(
            f"👋 Панель оператора\n\n"
            f"📥 Открытых тикетов: {open_count}",
            reply_markup=OperatorKeyboards.main_menu(open_count)
        )
    
    await callback.answer()


# ==================== MESSAGE HANDLERS ====================

@router.message(OperatorState.OP_REPLY, F.content_type.in_({"text", "photo", "document"}))
async def process_op_reply(message: Message, state: FSMContext, bot: Bot):
    """Обработка ответа оператора"""
    if not is_operator(message.from_user.id):
        return
    
    data = await state.get_data()
    ticket_code = data.get("current_ticket_code")
    
    if not ticket_code:
        await message.answer(
            "❌ Сначала выберите тикет",
            reply_markup=OperatorKeyboards.main_menu(0)
        )
        await state.set_state(OperatorState.OP_IDLE)
        return
    
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
        
        operator = await service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_operator=True
        )
        
        # Определяем тип контента
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
        
        # Сохраняем сообщение
        await service.add_message(
            ticket=ticket,
            sender=operator,
            content_type=content_type,
            text=text,
            file_id=file_id,
            file_name=file_name,
            is_from_operator=True
        )
        
        # Обновляем статус на IN_PROGRESS
        await service.update_ticket_status(ticket, TicketStatus.IN_PROGRESS, operator)
        
        # Отправляем пользователю
        try:
            # Уведомление
            await bot.send_message(
                ticket.user.telegram_id,
                f"💬 <b>Ответ от оператора</b>\n"
                f"🎫 {ticket.ticket_code}",
                parse_mode="HTML"
            )
            
            # Контент
            if content_type == "text":
                await bot.send_message(ticket.user.telegram_id, text)
            elif content_type == "photo":
                await bot.send_photo(ticket.user.telegram_id, file_id, caption=text)
            elif content_type == "document":
                await bot.send_document(ticket.user.telegram_id, file_id, caption=text)
            
            await message.answer("✅ Ответ отправлен пользователю")
        except Exception as e:
            await message.answer(f"⚠️ Ответ сохранён, но не удалось отправить: {e}")
        
        # Возвращаемся к просмотру тикета
        ticket = await service.get_ticket_by_code(ticket_code)
        await state.set_state(OperatorState.OP_VIEW_TICKET)
        
        status_text = "🟡 В обработке"
        username = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
        operator_name = f"@{operator.username}" if operator.username else operator.full_name
        
        await message.answer(
            f"🎫 <b>{ticket.ticket_code}</b>\n\n"
            f"📊 <b>Статус:</b> {status_text}\n"
            f"👤 <b>Пользователь:</b> {username}\n"
            f"👨‍💼 <b>Оператор:</b> {operator_name}\n"
            f"🏷 <b>Приоритет:</b> {ticket.priority}\n\n"
            f"📝 <b>Тема:</b>\n{ticket.subject}",
            reply_markup=OperatorKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )


@router.message(OperatorState.OP_REPLY)
async def process_op_reply_invalid(message: Message, state: FSMContext):
    """Неподдерживаемый тип контента при ответе"""
    if not is_operator(message.from_user.id):
        return
    
    await message.answer(
        "❌ Неподдерживаемый тип сообщения.\n"
        "Пожалуйста, отправьте текст, фото или документ.",
        reply_markup=OperatorKeyboards.reply_cancel()
    )


@router.message(OperatorState.OP_IDLE)
async def process_op_idle_message(message: Message, state: FSMContext):
    """Оператор пишет в IDLE состоянии"""
    if not is_operator(message.from_user.id):
        return
    
    await message.answer(
        "❌ Сначала выберите тикет"
    )


@router.message(OperatorState.OP_VIEW_TICKET)
async def process_op_view_message(message: Message, state: FSMContext):
    """Оператор пишет при просмотре тикета"""
    if not is_operator(message.from_user.id):
        return
    
    await message.answer(
        "❌ Нажмите «✍️ Ответить», чтобы написать пользователю"
    )

