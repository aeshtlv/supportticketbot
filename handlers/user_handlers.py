"""
Обработчики сообщений от пользователей
"""
import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import SUPPORT_CHAT_ID, ADMIN_IDS
from database import get_db
from services import TicketService
from database.models import TicketStatus

router = Router()
logger = logging.getLogger(__name__)


async def forward_to_support(bot: Bot, message: Message, ticket, topic_id: int = None):
    """Пересылает сообщение в чат поддержки"""
    try:
        # Формируем текст с информацией о тикете
        user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        header = f"🎫 <b>{ticket.ticket_id}</b> | 👤 {user_info}"
        
        # Клавиатура с действиями
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔴 Закрыть" if ticket.status == TicketStatus.OPEN else "🟢 Открыть",
                    callback_data=f"toggle_ticket:{ticket.ticket_id}"
                ),
                InlineKeyboardButton(
                    text="⛔ Забанить" if not ticket.user.is_banned else "✅ Разбанить",
                    callback_data=f"toggle_ban:{ticket.user.telegram_id}"
                )
            ]
        ])
        
        # Пересылаем сообщение
        if message.content_type == "text":
            sent = await bot.send_message(
                SUPPORT_CHAT_ID,
                f"{header}\n\n{message.text}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == "photo":
            sent = await bot.send_photo(
                SUPPORT_CHAT_ID,
                message.photo[-1].file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == "video":
            sent = await bot.send_video(
                SUPPORT_CHAT_ID,
                message.video.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == "document":
            sent = await bot.send_document(
                SUPPORT_CHAT_ID,
                message.document.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == "voice":
            sent = await bot.send_voice(
                SUPPORT_CHAT_ID,
                message.voice.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == "audio":
            sent = await bot.send_audio(
                SUPPORT_CHAT_ID,
                message.audio.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == "video_note":
            sent = await bot.send_video_note(
                SUPPORT_CHAT_ID,
                message.video_note.file_id,
                message_thread_id=topic_id
            )
            # Отправляем отдельно заголовок для video_note
            sent_header = await bot.send_message(
                SUPPORT_CHAT_ID,
                header,
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
            return sent_header
        elif message.content_type == "sticker":
            sent = await bot.send_sticker(
                SUPPORT_CHAT_ID,
                message.sticker.file_id,
                message_thread_id=topic_id
            )
            sent_header = await bot.send_message(
                SUPPORT_CHAT_ID,
                header,
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
            return sent_header
        elif message.content_type == "animation":
            sent = await bot.send_animation(
                SUPPORT_CHAT_ID,
                message.animation.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        else:
            # Для других типов отправляем как документ
            sent = await bot.send_message(
                SUPPORT_CHAT_ID,
                f"{header}\n\n[Неподдерживаемый тип: {message.content_type}]",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        
        return sent
        
    except Exception as e:
        logger.error(f"Failed to forward message: {e}")
        return None


@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
    """Команда /start"""
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        # Получаем текст приветствия
        welcome_text = await service.get_setting("welcome_text", "👋 Привет! Напишите ваш вопрос, и мы поможем.")
        
        await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help(message: Message, bot: Bot):
    """Команда /help"""
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        # Получаем текст справки
        help_text = await service.get_setting("help_text", "📖 Справка\n\nПросто напишите ваш вопрос, и оператор ответит.")
        
        await message.answer(help_text)


@router.message(Command("close"))
async def cmd_close(message: Message, bot: Bot):
    """Команда /close - закрыть свой тикет"""
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        user = await service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        
        ticket = await service.get_user_ticket(user)
        
        if not ticket:
            await message.answer("❌ У вас нет открытых тикетов")
            return
        
        await service.close_ticket(ticket)
        await message.answer(f"✅ Тикет {ticket.ticket_id} закрыт")


@router.message(Command("reopen"))
async def cmd_reopen(message: Message, bot: Bot):
    """Команда /reopen - переоткрыть тикет"""
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        user = await service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        
        # Ищем последний закрытый тикет
        from sqlalchemy import select
        from database.models import Ticket
        
        result = await session.execute(
            select(Ticket)
            .where(
                Ticket.user_id == user.id,
                Ticket.status == TicketStatus.CLOSED
            )
            .order_by(Ticket.closed_at.desc())
        )
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            await message.answer("❌ Нет закрытых тикетов для переоткрытия")
            return
        
        await service.reopen_ticket(ticket)
        await message.answer(f"✅ Тикет {ticket.ticket_id} переоткрыт")


@router.message()
async def handle_user_message(message: Message, bot: Bot):
    """Обработка всех сообщений от пользователей"""
    # Пропускаем команды
    if message.text and message.text.startswith("/"):
        return
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        # Проверяем, не забанен ли пользователь
        user = await service.get_user_by_telegram_id(message.from_user.id)
        if user and user.is_banned:
            await message.answer("❌ Вы заблокированы и не можете отправлять сообщения.")
            return
        
        # Создаём/получаем пользователя
        user = await service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        
        # Определяем режим топиков
        topic_mode = await service.get_setting("topic_mode", "separate")  # separate или common
        
        # Получаем или создаём тикет
        ticket = await service.get_or_create_ticket(user)
        topic_id = None
        
        if topic_mode == "separate":
            # Режим отдельного топика
            if not ticket.topic_id:
                # Создаём новый топик в форуме
                try:
                    user_info = f"@{user.username}" if user.username else user.full_name
                    topic_name = f"🎫 {ticket.ticket_id} | {user_info}"
                    
                    topic = await bot.create_forum_topic(
                        chat_id=int(SUPPORT_CHAT_ID),
                        name=topic_name
                    )
                    topic_id = topic.message_thread_id
                    ticket.topic_id = topic_id
                    await session.commit()
                except Exception as e:
                    logger.error(f"Failed to create forum topic: {e}")
                    # Fallback: используем общий режим
                    topic_id = None
            else:
                topic_id = ticket.topic_id
        else:
            # Общий топик - topic_id = None
            topic_id = None
        
        # Пересылаем в чат поддержки
        sent_message = await forward_to_support(bot, message, ticket, topic_id)
        
        if sent_message:
            # Сохраняем связь
            await service.create_message_link(
                ticket=ticket,
                user=user,
                user_message_id=message.message_id,
                support_message_id=sent_message.message_id,
                topic_id=topic_id
            )
        else:
            await message.answer("❌ Не удалось отправить сообщение в поддержку. Попробуйте позже.")
