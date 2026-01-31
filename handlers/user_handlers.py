"""
Обработчики сообщений от пользователей
"""
import logging
from aiogram import Router, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ContentType

from config import SUPPORT_CHAT_ID
from database import get_db
from services import TicketService
from database.models import TicketStatus

router = Router()
logger = logging.getLogger(__name__)


async def forward_to_support(bot: Bot, message: Message, ticket, topic_id: int = None):
    """Пересылает сообщение в чат поддержки"""
    try:
        user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        header = f"🎫 <b>{ticket.ticket_id}</b> | 👤 {user_info}"
        
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
        
        sent = None
        
        if message.content_type == ContentType.TEXT:
            sent = await bot.send_message(
                SUPPORT_CHAT_ID,
                f"{header}\n\n{message.text}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.PHOTO:
            sent = await bot.send_photo(
                SUPPORT_CHAT_ID,
                message.photo[-1].file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.VIDEO:
            sent = await bot.send_video(
                SUPPORT_CHAT_ID,
                message.video.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.DOCUMENT:
            sent = await bot.send_document(
                SUPPORT_CHAT_ID,
                message.document.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.VOICE:
            sent = await bot.send_voice(
                SUPPORT_CHAT_ID,
                message.voice.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.AUDIO:
            sent = await bot.send_audio(
                SUPPORT_CHAT_ID,
                message.audio.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.VIDEO_NOTE:
            sent = await bot.send_video_note(SUPPORT_CHAT_ID, message.video_note.file_id, message_thread_id=topic_id)
            header_msg = await bot.send_message(SUPPORT_CHAT_ID, header, reply_markup=keyboard, parse_mode="HTML", message_thread_id=topic_id)
            # Сохраняем связь для обоих сообщений
            return (sent, header_msg)  # Возвращаем оба для сохранения связей
        elif message.content_type == ContentType.STICKER:
            sent = await bot.send_sticker(SUPPORT_CHAT_ID, message.sticker.file_id, message_thread_id=topic_id)
            header_msg = await bot.send_message(SUPPORT_CHAT_ID, header, reply_markup=keyboard, parse_mode="HTML", message_thread_id=topic_id)
            # Сохраняем связь для обоих сообщений
            return (sent, header_msg)  # Возвращаем оба для сохранения связей
        elif message.content_type == ContentType.ANIMATION:
            sent = await bot.send_animation(
                SUPPORT_CHAT_ID,
                message.animation.file_id,
                caption=f"{header}\n\n{message.caption or ''}",
                reply_markup=keyboard,
                parse_mode="HTML",
                message_thread_id=topic_id
            )
        
        return sent
        
    except Exception as e:
        logger.error(f"Failed to forward message: {e}", exc_info=True)
        return None


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            welcome_text = await service.get_setting("welcome_text", "👋 Привет! Напишите ваш вопрос, и мы поможем.")
            await message.answer(welcome_text)
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}", exc_info=True)
        await message.answer("👋 Привет! Напишите ваш вопрос, и мы поможем.")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            help_text = await service.get_setting("help_text", "📖 Справка\n\nПросто напишите ваш вопрос, и оператор ответит.")
            await message.answer(help_text)
    except Exception as e:
        logger.error(f"Error in cmd_help: {e}", exc_info=True)
        await message.answer("📖 Справка\n\nПросто напишите ваш вопрос, и оператор ответит.")


@router.message(Command("close"))
async def cmd_close(message: Message):
    """Команда /close"""
    try:
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
    except Exception as e:
        logger.error(f"Error in cmd_close: {e}", exc_info=True)


@router.message(Command("reopen"))
async def cmd_reopen(message: Message):
    """Команда /reopen"""
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            user = await service.get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
            from sqlalchemy import select
            from database.models import Ticket
            
            result = await session.execute(
                select(Ticket)
                .where(Ticket.user_id == user.id, Ticket.status == TicketStatus.CLOSED)
                .order_by(Ticket.closed_at.desc())
            )
            ticket = result.scalar_one_or_none()
            
            if not ticket:
                await message.answer("❌ Нет закрытых тикетов для переоткрытия")
                return
            
            await service.reopen_ticket(ticket)
            await message.answer(f"✅ Тикет {ticket.ticket_id} переоткрыт")
    except Exception as e:
        logger.error(f"Error in cmd_reopen: {e}", exc_info=True)


@router.message()
async def handle_user_message(message: Message, bot: Bot):
    """Обработка всех сообщений от пользователей"""
    # ВАЖНО: Игнорируем сообщения из чата поддержки (они обрабатываются support_handlers)
    if SUPPORT_CHAT_ID and str(message.chat.id) == str(SUPPORT_CHAT_ID):
        return
    
    # Игнорируем служебные события форума
    forum_events = [
        ContentType.FORUM_TOPIC_CREATED,
        ContentType.FORUM_TOPIC_CLOSED,
        ContentType.FORUM_TOPIC_REOPENED,
        ContentType.FORUM_TOPIC_EDITED,
        ContentType.GENERAL_FORUM_TOPIC_HIDDEN,
        ContentType.GENERAL_FORUM_TOPIC_UNHIDDEN,
        ContentType.WRITE_ACCESS_ALLOWED,
        ContentType.USER_SHARED,
        ContentType.CHAT_SHARED,
    ]
    
    if message.content_type in forum_events:
        return
    
    # Пропускаем команды
    if message.text and message.text.startswith("/"):
        return
    
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            
            # Проверяем бан
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
            topic_mode = await service.get_setting("topic_mode", "separate")
            
            # Получаем или создаём тикет
            ticket = await service.get_or_create_ticket(user)
            topic_id = None
            
            if topic_mode == "separate":
                # Режим отдельного топика для каждого пользователя
                if not ticket.topic_id:
                    try:
                        user_info = f"@{user.username}" if user.username else user.full_name
                        topic_name = f"🟢 {ticket.ticket_id} | {user_info}"
                        
                        # Создаём топик в форуме
                        topic = await bot.create_forum_topic(
                            chat_id=int(SUPPORT_CHAT_ID),
                            name=topic_name
                        )
                        topic_id = topic.message_thread_id
                        
                        # Сохраняем topic_id в тикет
                        ticket.topic_id = topic_id
                        await session.commit()
                        logger.info(f"Created forum topic {topic_id} for ticket {ticket.ticket_id}")
                    except Exception as e:
                        logger.error(f"Failed to create forum topic: {e}", exc_info=True)
                        # Fallback: используем общий режим
                        topic_id = None
                else:
                    topic_id = ticket.topic_id
                    logger.debug(f"Using existing topic {topic_id} for ticket {ticket.ticket_id}")
            else:
                # Общий топик - topic_id = None
                topic_id = None
            
            # Пересылаем в чат поддержки
            sent_result = await forward_to_support(bot, message, ticket, topic_id)
            
            if sent_result:
                # Для video_note и sticker возвращается кортеж (медиа, заголовок)
                if isinstance(sent_result, tuple):
                    media_msg, header_msg = sent_result
                    # Сохраняем связь для обоих сообщений
                    await service.create_message_link(
                        ticket=ticket,
                        user=user,
                        user_message_id=message.message_id,
                        support_message_id=media_msg.message_id,
                        topic_id=topic_id
                    )
                    await service.create_message_link(
                        ticket=ticket,
                        user=user,
                        user_message_id=message.message_id,
                        support_message_id=header_msg.message_id,
                        topic_id=topic_id
                    )
                    logger.info(
                        f"Forwarded message from user {user.telegram_id} to support chat: "
                        f"user_msg_id={message.message_id}, media_msg_id={media_msg.message_id}, "
                        f"header_msg_id={header_msg.message_id}, topic_id={topic_id}"
                    )
                else:
                    # Обычное сообщение
                    await service.create_message_link(
                        ticket=ticket,
                        user=user,
                        user_message_id=message.message_id,
                        support_message_id=sent_result.message_id,
                        topic_id=topic_id
                    )
                    logger.info(
                        f"Forwarded message from user {user.telegram_id} to support chat: "
                        f"user_msg_id={message.message_id}, support_msg_id={sent_result.message_id}, topic_id={topic_id}"
                    )
            else:
                await message.answer("❌ Не удалось отправить сообщение в поддержку. Попробуйте позже.")
                
    except Exception as e:
        logger.error(f"Error in handle_user_message: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
