"""
Обработчики для пользователя
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import OPERATOR_IDS, MAX_SUBJECT_LENGTH
from database import get_db, TicketStatus
from services import TicketService
from states import UserState
from keyboards import UserKeyboards

router = Router()
logger = logging.getLogger(__name__)

SUPPORTED_CONTENT_TYPES = {"text", "photo", "document", "video", "voice", "video_note", "sticker", "animation"}


# ==================== CALLBACK HANDLERS ====================

@router.callback_query(F.data == "create_ticket")
async def cb_create_ticket(callback: CallbackQuery, state: FSMContext):
    """Начать создание тикета"""
    user_id = callback.from_user.id
    
    if user_id in OPERATOR_IDS:
        await callback.answer("Операторы не могут создавать тикеты", show_alert=True)
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        user = await service.get_or_create_user(
            telegram_id=user_id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )
        
        open_tickets = await service.get_user_open_tickets(user)
        
        if open_tickets:
            await state.update_data(pending_action="create_ticket")
            await state.set_state(UserState.CONFIRM_NEW_TICKET)
            await callback.message.edit_text(
                f"⚠️ У вас уже есть открытый тикет ({len(open_tickets)} шт.)\n"
                "Создать ещё один?",
                reply_markup=UserKeyboards.confirm_new_ticket()
            )
        else:
            await state.set_state(UserState.CREATE_TICKET_SUBJECT)
            await callback.message.edit_text(
                "✏️ Коротко опишите проблему\n"
                "(1–2 предложения)",
                reply_markup=UserKeyboards.cancel()
            )
    
    await callback.answer()


@router.callback_query(F.data == "confirm_new_ticket")
async def cb_confirm_new_ticket(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания"""
    await state.set_state(UserState.CREATE_TICKET_SUBJECT)
    await callback.message.edit_text(
        "✏️ Коротко опишите проблему\n"
        "(1–2 предложения)",
        reply_markup=UserKeyboards.cancel()
    )
    await callback.answer()


@router.callback_query(F.data == "my_tickets")
async def cb_my_tickets(callback: CallbackQuery, state: FSMContext):
    """Список тикетов"""
    async with get_db().session_factory() as session:
        service = TicketService(session)
        user = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )
        
        tickets = await service.get_user_all_tickets(user, limit=15)
        
        await state.set_state(UserState.IDLE)
        await callback.message.edit_text(
            "📂 <b>Мои обращения</b>\n\n"
            "⚪ открыт · 🟠 в работе · 🔴 ждёт ответа",
            reply_markup=UserKeyboards.tickets_list(tickets),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "closed_tickets")
async def cb_closed_tickets(callback: CallbackQuery, state: FSMContext):
    """Закрытые тикеты"""
    async with get_db().session_factory() as session:
        service = TicketService(session)
        user = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )
        
        all_tickets = await service.get_user_all_tickets(user, limit=20)
        closed = [t for t in all_tickets if t.status == TicketStatus.CLOSED]
        
        await callback.message.edit_text(
            f"📦 <b>Закрытые обращения</b> ({len(closed)})",
            reply_markup=UserKeyboards.closed_tickets_list(closed),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("view_ticket:"))
async def cb_view_ticket(callback: CallbackQuery, state: FSMContext):
    """Просмотр тикета"""
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        status_text = {
            TicketStatus.OPEN: "⚪ Открыт",
            TicketStatus.IN_PROGRESS: "🟠 В обработке",
            TicketStatus.WAITING_USER: "🟠 Ожидает вашего ответа",
            TicketStatus.CLOSED: "⚫ Закрыт"
        }.get(ticket.status, "?")
        
        operator_text = "ожидается"
        if ticket.operator:
            operator_text = f"@{ticket.operator.username}" if ticket.operator.username else "назначен"
        
        # Последние сообщения
        messages = await service.get_ticket_messages(ticket, limit=3)
        msg_preview = ""
        if messages:
            msg_preview = "\n\n💬 <b>Последние сообщения:</b>\n"
            for msg in messages[-3:]:
                sender = "👤 Вы" if not msg.is_from_operator else "👨‍💼 Оператор"
                text = msg.text[:50] + "…" if msg.text and len(msg.text) > 50 else (msg.text or f"[{msg.content_type}]")
                msg_preview += f"{sender}: {text}\n"
        
        await callback.message.edit_text(
            f"🎫 <b>{ticket.ticket_code}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>Статус:</b> {status_text}\n"
            f"👨‍💼 <b>Оператор:</b> {operator_text}\n"
            f"📅 <b>Создан:</b> {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📝 <b>Тема:</b>\n{ticket.subject}"
            f"{msg_preview}",
            reply_markup=UserKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("chat_ticket:"))
async def cb_chat_ticket(callback: CallbackQuery, state: FSMContext):
    """Войти в чат"""
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        if ticket.status == TicketStatus.CLOSED:
            await callback.answer("Тикет закрыт", show_alert=True)
            return
        
        await state.update_data(current_ticket_id=ticket.id, current_ticket_code=ticket.ticket_code)
        await state.set_state(UserState.TICKET_CHAT)
        
        await callback.message.edit_text(
            f"💬 <b>Чат тикета {ticket.ticket_code}</b>\n\n"
            f"Отправьте сообщение — оператор его получит.\n"
            f"Поддерживаются: текст, фото, видео, голосовые, файлы.",
            reply_markup=UserKeyboards.ticket_chat(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("user_history:"))
async def cb_user_history(callback: CallbackQuery, state: FSMContext):
    """История сообщений"""
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        messages = await service.get_ticket_messages(ticket, limit=25)
        
        if not messages:
            await callback.answer("Нет сообщений", show_alert=True)
            return
        
        history_text = f"📜 <b>История {ticket_code}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        
        for msg in messages:
            sender = "👤 Вы" if not msg.is_from_operator else "👨‍💼 Оператор"
            time_str = msg.created_at.strftime("%d.%m %H:%M")
            
            if msg.text:
                content = msg.text[:120] + "…" if len(msg.text) > 120 else msg.text
            else:
                type_icons = {
                    "photo": "🖼 Фото", "video": "🎥 Видео", "voice": "🎤 Голосовое",
                    "video_note": "📹 Кружок", "document": f"📎 {msg.file_name or 'Файл'}",
                    "sticker": "😀 Стикер", "animation": "🎞 GIF"
                }
                content = type_icons.get(msg.content_type, f"[{msg.content_type}]")
            
            history_text += f"<b>{sender}</b> · <i>{time_str}</i>\n{content}\n\n"
        
        if len(history_text) > 4000:
            history_text = history_text[:4000] + "\n\n… (обрезано)"
        
        await callback.message.edit_text(
            history_text,
            reply_markup=UserKeyboards.history_back(ticket_code),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("user_close:"))
async def cb_user_close(callback: CallbackQuery, state: FSMContext):
    """Запрос на закрытие"""
    ticket_code = callback.data.split(":")[1]
    
    await callback.message.edit_text(
        f"🔒 <b>Закрыть тикет {ticket_code}?</b>\n\n"
        f"Вы уверены, что хотите закрыть обращение?\n"
        f"После закрытия написать в него будет невозможно.",
        reply_markup=UserKeyboards.confirm_close(ticket_code),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_close:"))
async def cb_confirm_close(callback: CallbackQuery, state: FSMContext):
    """Подтверждение закрытия"""
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        if ticket.status == TicketStatus.CLOSED:
            await callback.answer("Уже закрыт", show_alert=True)
            return
        
        user = await service.get_user_by_telegram_id(callback.from_user.id)
        await service.update_ticket_status(ticket, TicketStatus.CLOSED, ticket.operator)
    
    await state.set_state(UserState.IDLE)
    await state.update_data(current_ticket_id=None, current_ticket_code=None)
    
    await callback.message.edit_text(
        f"✅ <b>Тикет {ticket_code} закрыт</b>\n\n"
        f"Спасибо за обращение!\n"
        f"Если проблема появится снова — создайте новый тикет.",
        reply_markup=UserKeyboards.after_ticket_closed(),
        parse_mode="HTML"
    )
    await callback.answer("✅ Закрыт")


@router.callback_query(F.data == "exit_chat")
async def cb_exit_chat(callback: CallbackQuery, state: FSMContext):
    """Выйти из чата"""
    await state.set_state(UserState.IDLE)
    await state.update_data(current_ticket_id=None, current_ticket_code=None)
    await callback.message.edit_text(
        "👋 Привет!\n"
        "Чем можем помочь?",
        reply_markup=UserKeyboards.main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена"""
    await state.set_state(UserState.IDLE)
    await state.update_data(current_ticket_id=None, current_ticket_code=None, pending_action=None)
    await callback.message.edit_text(
        "👋 Привет!\n"
        "Чем можем помочь?",
        reply_markup=UserKeyboards.main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """В главное меню"""
    await state.set_state(UserState.IDLE)
    await callback.message.edit_text(
        "👋 Привет!\n"
        "Чем можем помочь?",
        reply_markup=UserKeyboards.main_menu()
    )
    await callback.answer()


# ==================== MESSAGE HANDLERS ====================

@router.message(UserState.CREATE_TICKET_SUBJECT)
async def process_ticket_subject(message: Message, state: FSMContext):
    """Тема тикета"""
    subject = message.text
    
    if not subject or not subject.strip():
        await message.answer(
            "❌ Тема не может быть пустой.\n"
            "Опишите проблему:",
            reply_markup=UserKeyboards.cancel()
        )
        return
    
    if len(subject) > MAX_SUBJECT_LENGTH:
        await message.answer(
            f"❌ Слишком длинная тема (макс. {MAX_SUBJECT_LENGTH}).\n"
            "Опишите короче:",
            reply_markup=UserKeyboards.cancel()
        )
        return
    
    await state.update_data(ticket_subject=subject.strip())
    await state.set_state(UserState.CREATE_TICKET_MESSAGE)
    
    await message.answer(
        "📝 Опишите проблему подробнее\n"
        "Можно прислать текст, фото, видео или файл",
        reply_markup=UserKeyboards.cancel()
    )


@router.message(UserState.CREATE_TICKET_MESSAGE, F.content_type.in_(SUPPORTED_CONTENT_TYPES))
async def process_ticket_message(message: Message, state: FSMContext, bot: Bot):
    """Первое сообщение тикета"""
    data = await state.get_data()
    subject = data.get("ticket_subject")
    
    if not subject:
        await state.set_state(UserState.IDLE)
        await message.answer(
            "❌ Ошибка. Начните заново.",
            reply_markup=UserKeyboards.main_menu()
        )
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        user = await service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        
        ticket = await service.create_ticket(user, subject)
        ticket_code = ticket.ticket_code
        ticket_id = ticket.id
        
        content_type, text, file_id, file_name = extract_message_content(message)
        
        await service.add_message(
            ticket=ticket,
            sender=user,
            content_type=content_type,
            text=text,
            file_id=file_id,
            file_name=file_name,
            is_from_operator=False
        )
        
        username = f"@{user.username}" if user.username else user.full_name
    
    await state.update_data(
        current_ticket_id=ticket_id,
        current_ticket_code=ticket_code,
        ticket_subject=None
    )
    await state.set_state(UserState.TICKET_CHAT)
    
    await message.answer(
        f"✅ <b>Тикет {ticket_code} создан</b>\n\n"
        f"Оператор скоро ответит.\n"
        f"Можете писать дополнительные сообщения.",
        parse_mode="HTML"
    )
    
    await notify_operators_new_ticket(bot, ticket_code, subject, username, message)


@router.message(UserState.CREATE_TICKET_MESSAGE)
async def process_ticket_message_invalid(message: Message, state: FSMContext):
    """Неподдерживаемый тип"""
    await message.answer(
        "❌ Неподдерживаемый тип сообщения.\n"
        "Отправьте текст, фото, видео или файл.",
        reply_markup=UserKeyboards.cancel()
    )


@router.message(UserState.TICKET_CHAT, F.content_type.in_(SUPPORTED_CONTENT_TYPES))
async def process_ticket_chat_message(message: Message, state: FSMContext, bot: Bot):
    """Сообщение в чате"""
    data = await state.get_data()
    ticket_id = data.get("current_ticket_id")
    ticket_code = data.get("current_ticket_code")
    
    if not ticket_id:
        await state.set_state(UserState.IDLE)
        await message.answer(
            "❌ Тикет не найден.",
            reply_markup=UserKeyboards.main_menu()
        )
        return
    
    target_operator_ids: list[int] = []
    username = ""
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        ticket = await service.get_ticket_by_id(ticket_id)
        if not ticket or ticket.status == TicketStatus.CLOSED:
            await state.set_state(UserState.IDLE)
            await state.update_data(current_ticket_id=None, current_ticket_code=None)
            await message.answer(
                "❌ Тикет закрыт.\n"
                "Создайте новый, если нужна помощь.",
                reply_markup=UserKeyboards.no_active_ticket()
            )
            return
        
        user = await service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Ошибка пользователя")
            return
        
        username = f"@{user.username}" if user.username else user.full_name
        
        if ticket.operator and ticket.operator.telegram_id:
            target_operator_ids = [ticket.operator.telegram_id]
        else:
            target_operator_ids = list(OPERATOR_IDS)
        
        content_type, text, file_id, file_name = extract_message_content(message)
        
        await service.add_message(
            ticket=ticket,
            sender=user,
            content_type=content_type,
            text=text,
            file_id=file_id,
            file_name=file_name,
            is_from_operator=False
        )
    
    await message.answer("✉️ Отправлено")
    await forward_message_to_operators(bot, target_operator_ids, ticket_code, username, message)


@router.message(UserState.TICKET_CHAT)
async def process_ticket_chat_invalid(message: Message, state: FSMContext):
    """Неподдерживаемый тип в чате"""
    await message.answer(
        "❌ Неподдерживаемый тип сообщения.\n"
        "Отправьте текст, фото, видео или файл."
    )


@router.message(UserState.IDLE)
async def process_idle_message(message: Message, state: FSMContext):
    """Сообщение в IDLE"""
    await message.answer(
        "❌ У вас нет активных обращений",
        reply_markup=UserKeyboards.no_active_ticket()
    )


@router.message()
async def process_unknown_message(message: Message, state: FSMContext):
    """Fallback"""
    user_id = message.from_user.id
    
    if user_id in OPERATOR_IDS:
        return
    
    current_state = await state.get_state()
    
    if current_state is None:
        await state.set_state(UserState.IDLE)
        await message.answer(
            "👋 Привет!\n"
            "Чем можем помочь?",
            reply_markup=UserKeyboards.main_menu()
        )


# ==================== HELPERS ====================

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


async def notify_operators_new_ticket(bot: Bot, ticket_code: str, subject: str, username: str, message: Message):
    """Уведомление о новом тикете"""
    if not OPERATOR_IDS:
        logger.warning("OPERATOR_IDS пуст!")
        return
    
    text = (
        f"🆕 <b>Новый тикет</b>\n\n"
        f"🎫 <code>{ticket_code}</code>\n"
        f"👤 {username}\n"
        f"📝 {subject}"
    )
    
    for operator_id in OPERATOR_IDS:
        try:
            await bot.send_message(operator_id, text, parse_mode="HTML")
            await forward_content(bot, operator_id, message)
            logger.info(f"Notified operator {operator_id} about {ticket_code}")
        except Exception as e:
            logger.error(f"Failed to notify {operator_id}: {e}")


async def forward_message_to_operators(bot: Bot, operator_ids: list[int], ticket_code: str, username: str, message: Message):
    """Пересылка сообщения операторам"""
    if not operator_ids:
        logger.warning("No operators to notify!")
        return
    
    text = (
        f"💬 <b>Сообщение</b>\n"
        f"🎫 <code>{ticket_code}</code> · 👤 {username}"
    )
    
    for operator_id in operator_ids:
        try:
            await bot.send_message(operator_id, text, parse_mode="HTML")
            await forward_content(bot, operator_id, message)
        except Exception as e:
            logger.error(f"Failed to forward to {operator_id}: {e}")


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
        logger.error(f"Forward failed to {chat_id}: {e}")
