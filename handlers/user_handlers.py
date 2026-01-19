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

# Поддерживаемые типы контента
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
    """Подтверждение создания нового тикета при наличии открытого"""
    await state.set_state(UserState.CREATE_TICKET_SUBJECT)
    await callback.message.edit_text(
        "✏️ Коротко опишите проблему\n"
        "(1–2 предложения)",
        reply_markup=UserKeyboards.cancel()
    )
    await callback.answer()


@router.callback_query(F.data == "my_tickets")
async def cb_my_tickets(callback: CallbackQuery, state: FSMContext):
    """Показать список тикетов пользователя"""
    async with get_db().session_factory() as session:
        service = TicketService(session)
        user = await service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )
        
        tickets = await service.get_user_all_tickets(user)
        
        if tickets:
            await state.set_state(UserState.IDLE)
            await callback.message.edit_text(
                "📂 Ваши обращения:",
                reply_markup=UserKeyboards.tickets_list(tickets)
            )
        else:
            await callback.message.edit_text(
                "📭 У вас пока нет обращений",
                reply_markup=UserKeyboards.main_menu()
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("view_ticket:"))
async def cb_view_ticket(callback: CallbackQuery, state: FSMContext):
    """Просмотр тикета пользователем"""
    ticket_code = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_code(ticket_code)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        status_text = {
            TicketStatus.OPEN: "🔵 Открыт",
            TicketStatus.IN_PROGRESS: "🟡 В обработке",
            TicketStatus.WAITING_USER: "🟠 Ожидает вашего ответа",
            TicketStatus.CLOSED: "⚫ Закрыт"
        }.get(ticket.status, "Неизвестно")
        
        await callback.message.edit_text(
            f"🎫 <b>{ticket.ticket_code}</b>\n\n"
            f"📝 <b>Тема:</b> {ticket.subject}\n"
            f"📊 <b>Статус:</b> {status_text}\n"
            f"📅 <b>Создан:</b> {ticket.created_at.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=UserKeyboards.ticket_view(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("chat_ticket:"))
async def cb_chat_ticket(callback: CallbackQuery, state: FSMContext):
    """Войти в чат тикета"""
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
        
        # Сохраняем ticket_id в state
        await state.update_data(current_ticket_id=ticket.id, current_ticket_code=ticket.ticket_code)
        await state.set_state(UserState.TICKET_CHAT)
        
        # Показываем историю последних сообщений
        messages = await service.get_ticket_messages(ticket, limit=10)
        
        history_text = ""
        if messages:
            history_text = "\n\n📜 <b>Последние сообщения:</b>\n"
            for msg in messages[-5:]:
                sender = "👤 Вы" if not msg.is_from_operator else "👨‍💼 Оператор"
                text = msg.text or f"[{msg.content_type}]"
                if len(text) > 100:
                    text = text[:100] + "..."
                history_text += f"\n{sender}: {text}"
        
        await callback.message.edit_text(
            f"💬 <b>Чат тикета {ticket.ticket_code}</b>\n\n"
            f"Отправьте сообщение — оператор его получит.\n"
            f"Поддерживаются: текст, фото, видео, голосовые, файлы."
            f"{history_text}",
            reply_markup=UserKeyboards.ticket_chat(ticket),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "exit_chat")
async def cb_exit_chat(callback: CallbackQuery, state: FSMContext):
    """Выйти из чата тикета"""
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
    """Отмена текущего действия"""
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
    """Вернуться в главное меню"""
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
    """Обработка темы тикета"""
    subject = message.text
    
    if not subject or not subject.strip():
        await message.answer(
            "❌ Тема не может быть пустой.\n"
            "Пожалуйста, опишите проблему:",
            reply_markup=UserKeyboards.cancel()
        )
        return
    
    if len(subject) > MAX_SUBJECT_LENGTH:
        await message.answer(
            f"❌ Тема слишком длинная (макс. {MAX_SUBJECT_LENGTH} символов).\n"
            "Пожалуйста, опишите проблему короче:",
            reply_markup=UserKeyboards.cancel()
        )
        return
    
    # Сохраняем тему и переходим к сообщению
    await state.update_data(ticket_subject=subject.strip())
    await state.set_state(UserState.CREATE_TICKET_MESSAGE)
    
    await message.answer(
        "📝 Опишите проблему подробнее\n"
        "Можно прислать текст, фото, видео или файл",
        reply_markup=UserKeyboards.cancel()
    )


@router.message(UserState.CREATE_TICKET_MESSAGE, F.content_type.in_(SUPPORTED_CONTENT_TYPES))
async def process_ticket_message(message: Message, state: FSMContext, bot: Bot):
    """Обработка первого сообщения тикета"""
    data = await state.get_data()
    subject = data.get("ticket_subject")
    
    if not subject:
        await state.set_state(UserState.IDLE)
        await message.answer(
            "❌ Произошла ошибка. Начните заново.",
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
        
        # Создаём тикет
        ticket = await service.create_ticket(user, subject)
        ticket_code = ticket.ticket_code
        ticket_id = ticket.id
        
        # Извлекаем данные из сообщения
        content_type, text, file_id, file_name = extract_message_content(message)
        
        # Добавляем первое сообщение
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
    
    # Сохраняем в state и переводим в режим чата
    await state.update_data(
        current_ticket_id=ticket_id,
        current_ticket_code=ticket_code,
        ticket_subject=None
    )
    await state.set_state(UserState.TICKET_CHAT)
    
    await message.answer(
        f"✅ Тикет <b>{ticket_code}</b> создан\n\n"
        f"Оператор скоро ответит.\n"
        f"Вы можете писать сюда дополнительные сообщения.",
        parse_mode="HTML"
    )
    
    # Уведомляем операторов (вне сессии БД)
    await notify_operators_new_ticket(bot, ticket_code, subject, username, message)


@router.message(UserState.CREATE_TICKET_MESSAGE)
async def process_ticket_message_invalid(message: Message, state: FSMContext):
    """Неподдерживаемый тип контента при создании тикета"""
    await message.answer(
        "❌ Неподдерживаемый тип сообщения.\n"
        "Отправьте текст, фото, видео, голосовое или файл.",
        reply_markup=UserKeyboards.cancel()
    )


@router.message(UserState.TICKET_CHAT, F.content_type.in_(SUPPORTED_CONTENT_TYPES))
async def process_ticket_chat_message(message: Message, state: FSMContext, bot: Bot):
    """Сообщение в чате тикета"""
    data = await state.get_data()
    ticket_id = data.get("current_ticket_id")
    ticket_code = data.get("current_ticket_code")
    
    if not ticket_id:
        await state.set_state(UserState.IDLE)
        await message.answer(
            "❌ Произошла ошибка. Тикет не найден.",
            reply_markup=UserKeyboards.main_menu()
        )
        return
    
    # Собираем данные для уведомления ДО работы с БД
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
                "Если проблема появится снова — создайте новый тикет.",
                reply_markup=UserKeyboards.no_active_ticket()
            )
            return
        
        user = await service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Ошибка пользователя")
            return
        
        username = f"@{user.username}" if user.username else user.full_name
        
        # Определяем кому отправлять
        if ticket.operator and ticket.operator.telegram_id:
            target_operator_ids = [ticket.operator.telegram_id]
        else:
            target_operator_ids = list(OPERATOR_IDS)
        
        # Извлекаем данные из сообщения
        content_type, text, file_id, file_name = extract_message_content(message)
        
        # Добавляем сообщение в БД
        await service.add_message(
            ticket=ticket,
            sender=user,
            content_type=content_type,
            text=text,
            file_id=file_id,
            file_name=file_name,
            is_from_operator=False
        )
    
    await message.answer("✉️ Сообщение отправлено")
    
    # Уведомляем оператора (вне сессии БД)
    await forward_message_to_operators(bot, target_operator_ids, ticket_code, username, message)


@router.message(UserState.TICKET_CHAT)
async def process_ticket_chat_invalid(message: Message, state: FSMContext):
    """Неподдерживаемый тип контента в чате"""
    await message.answer(
        "❌ Неподдерживаемый тип сообщения.\n"
        "Отправьте текст, фото, видео, голосовое или файл."
    )


# ==================== EDGE CASE: Пользователь пишет без активного тикета ====================

@router.message(UserState.IDLE)
async def process_idle_message(message: Message, state: FSMContext):
    """Пользователь пишет в IDLE состоянии"""
    await message.answer(
        "❌ У вас нет активных обращений",
        reply_markup=UserKeyboards.no_active_ticket()
    )


@router.message()
async def process_unknown_message(message: Message, state: FSMContext):
    """Обработка сообщений без состояния (fallback)"""
    user_id = message.from_user.id
    
    # Пропускаем операторов
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
    """Извлекает контент из сообщения"""
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
    """Уведомить операторов о новом тикете"""
    if not OPERATOR_IDS:
        logger.warning("OPERATOR_IDS is empty! No one to notify.")
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
            # Пересылаем оригинальное сообщение
            await forward_content(bot, operator_id, message)
            logger.info(f"Notified operator {operator_id} about new ticket {ticket_code}")
        except Exception as e:
            logger.error(f"Failed to notify operator {operator_id}: {e}")


async def forward_message_to_operators(bot: Bot, operator_ids: list[int], ticket_code: str, username: str, message: Message):
    """Переслать сообщение операторам"""
    if not operator_ids:
        logger.warning("No operators to notify!")
        return
    
    text = (
        f"💬 <b>Сообщение в тикете</b>\n"
        f"🎫 <code>{ticket_code}</code> | 👤 {username}"
    )
    
    for operator_id in operator_ids:
        try:
            await bot.send_message(operator_id, text, parse_mode="HTML")
            await forward_content(bot, operator_id, message)
        except Exception as e:
            logger.error(f"Failed to forward message to operator {operator_id}: {e}")


async def forward_content(bot: Bot, chat_id: int, message: Message):
    """Пересылает контент сообщения"""
    try:
        content_type = message.content_type
        
        if content_type == "text":
            await bot.send_message(chat_id, message.text)
        elif content_type == "photo":
            await bot.send_photo(chat_id, message.photo[-1].file_id, caption=message.caption)
        elif content_type == "document":
            await bot.send_document(chat_id, message.document.file_id, caption=message.caption)
        elif content_type == "video":
            await bot.send_video(chat_id, message.video.file_id, caption=message.caption)
        elif content_type == "voice":
            await bot.send_voice(chat_id, message.voice.file_id, caption=message.caption)
        elif content_type == "video_note":
            await bot.send_video_note(chat_id, message.video_note.file_id)
        elif content_type == "sticker":
            await bot.send_sticker(chat_id, message.sticker.file_id)
        elif content_type == "animation":
            await bot.send_animation(chat_id, message.animation.file_id, caption=message.caption)
    except Exception as e:
        logger.error(f"Failed to forward content to {chat_id}: {e}")
