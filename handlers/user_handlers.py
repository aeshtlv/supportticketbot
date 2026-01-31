"""
Обработчики сообщений от пользователей
Пользователи пишут боту в личные сообщения
"""
import logging
import asyncio
from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramRetryAfter

from config import ADMIN_GROUP_ID
from database import get_db
from database.models import Ticket, TicketStatus
from services import TicketService
from utils import rate_limiter

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    await message.answer(
        "👋 Привет! Я бот поддержки shftsecure.\n\n"
        "Напишите ваш вопрос, и мы обязательно поможем!"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    await message.answer(
        "📖 Справка\n\n"
        "Просто напишите ваш вопрос, и администратор ответит вам.\n"
        "Все сообщения обрабатываются в порядке очереди."
    )


@router.message()
async def handle_user_message(message: Message, bot: Bot):
    """
    Обработка всех сообщений от пользователей
    
    Логика:
    1. Проверка на спам (rate limiting)
    2. Проверяем, есть ли у пользователя открытый тикет
    3. Если есть - отправляем сообщение в существующий топик
    4. Если нет - проверяем закрытый тикет и переоткрываем или создаём новый
    """
    # Пропускаем команды
    if message.text and message.text.startswith("/"):
        return
    
    # Защита от спама
    is_allowed, wait_seconds = await rate_limiter.check_rate_limit(message.from_user.id)
    if not is_allowed:
        await message.answer(
            f"⏳ Слишком много сообщений. Подождите {wait_seconds} секунд."
        )
        return
    
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            
            user_id = message.from_user.id
            user_chat_id = message.chat.id
            
            # Проверяем, есть ли открытый тикет
            ticket = await service.get_open_ticket_by_user(user_id)
            
            if ticket:
                # Тикет существует - отправляем в существующий топик
                logger.info(f"Adding message to existing ticket {ticket.ticket_id} (topic_id={ticket.topic_id})")
                
                if not ticket.topic_id:
                    logger.error(f"Ticket {ticket.ticket_id} has no topic_id!")
                    await message.answer("❌ Ошибка: тикет не привязан к топику. Обратитесь к администратору.")
                    return
                
                # Отправляем сообщение в топик с обработкой flood control
                await send_message_to_topic_safe(bot, message, ticket.topic_id)
                
            else:
                # Проверяем, есть ли закрытый тикет для переоткрытия
                last_ticket = await service.get_last_ticket_by_user(user_id)
                
                if last_ticket and last_ticket.status == TicketStatus.CLOSED and last_ticket.topic_id:
                    # Переоткрываем закрытый тикет
                    logger.info(f"Reopening closed ticket {last_ticket.ticket_id} (topic_id={last_ticket.topic_id})")
                    
                    await service.reopen_ticket(last_ticket)
                    
                    # Обновляем название топика
                    topic_name = format_topic_name(last_ticket)
                    try:
                        await bot.edit_forum_topic(
                            chat_id=int(ADMIN_GROUP_ID),
                            message_thread_id=last_ticket.topic_id,
                            name=topic_name
                        )
                    except Exception as e:
                        logger.error(f"Failed to update topic name: {e}")
                    
                    # Отправляем сообщение в переоткрытый топик
                    await send_message_to_topic_safe(bot, message, last_ticket.topic_id)
                    
                    await message.answer(
                        "✅ Ваше обращение получено. Мы как можно быстрее постараемся решить вашу проблему.\n\n"
                        "💡 Вы можете дополнить свой запрос новыми сообщениями."
                    )
                    
                else:
                    # Создаём новый тикет
                    logger.info(f"Creating new ticket for user {user_id}")
                    
                    ticket = await service.create_ticket(
                        user_id=user_id,
                        user_chat_id=user_chat_id,
                        username=message.from_user.username,
                        full_name=message.from_user.full_name
                    )
                    
                    # Создаём топик в админ-группе
                    topic_name = format_topic_name(ticket)
                    
                    try:
                        topic = await bot.create_forum_topic(
                            chat_id=int(ADMIN_GROUP_ID),
                            name=topic_name
                        )
                        topic_id = topic.message_thread_id
                        
                        # Сохраняем topic_id в тикет
                        await service.set_topic_id(ticket, topic_id)
                        logger.info(f"Created topic {topic_id} for ticket {ticket.ticket_id}")
                        
                        # Отправляем информацию о профиле пользователя и закрепляем
                        profile_info = await send_user_profile_info(bot, ticket, topic_id)
                        
                        if profile_info:
                            try:
                                # В aiogram 3.x pin_chat_message не поддерживает message_thread_id напрямую
                                # Используем прямой вызов API
                                from aiogram.methods import PinChatMessage
                                
                                await bot(PinChatMessage(
                                    chat_id=int(ADMIN_GROUP_ID),
                                    message_id=profile_info.message_id,
                                    message_thread_id=topic_id
                                ))
                                logger.info(f"Pinned profile info message in topic {topic_id}")
                            except Exception as e:
                                logger.warning(f"Failed to pin message (may not be supported): {e}")
                        
                        # Отправляем первое сообщение в топик
                        await send_message_to_topic_safe(bot, message, topic_id)
                        
                        await message.answer(
                            "✅ Ваше обращение получено. Мы как можно быстрее постараемся решить вашу проблему.\n\n"
                            "💡 Вы можете дополнить свой запрос новыми сообщениями."
                        )
                        
                    except Exception as e:
                        logger.error(f"Failed to create forum topic: {e}", exc_info=True)
                        await message.answer("❌ Не удалось создать обращение. Попробуйте позже.")
                    
    except Exception as e:
        logger.error(f"Error in handle_user_message: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


async def send_user_profile_info(bot: Bot, ticket: Ticket, topic_id: int) -> Message | None:
    """Отправляет информацию о профиле пользователя в топик"""
    try:
        from config import ADMIN_GROUP_ID
        
        username_part = f"@{ticket.username}" if ticket.username else ticket.full_name
        user_link = f"tg://user?id={ticket.user_id}"
        
        profile_text = (
            f"👤 <b>Информация о пользователе</b>\n\n"
            f"🆔 <b>User ID:</b> <code>{ticket.user_id}</code>\n"
            f"👤 <b>Имя:</b> <a href=\"{user_link}\">{username_part}</a>\n"
            f"🎫 <b>Тикет:</b> <code>{ticket.ticket_id}</code>\n"
            f"📅 <b>Создан:</b> {ticket.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
        
        msg = await bot.send_message(
            ADMIN_GROUP_ID,
            profile_text,
            parse_mode="HTML",
            message_thread_id=topic_id,
            disable_web_page_preview=True
        )
        
        return msg
        
    except Exception as e:
        logger.error(f"Failed to send user profile info: {e}", exc_info=True)
        return None


async def send_message_to_topic_safe(bot: Bot, message: Message, topic_id: int):
    """
    Отправляет сообщение в топик с обработкой flood control и задержками
    """
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            await send_message_to_topic(bot, message, topic_id)
            return
        except TelegramRetryAfter as e:
            wait_time = e.retry_after
            logger.warning(f"Flood control: waiting {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Failed to send message to topic {topic_id}: {e}", exc_info=True)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise


async def send_message_to_topic(bot: Bot, message: Message, topic_id: int):
    """Отправляет сообщение в топик админ-группы"""
    try:
        from config import ADMIN_GROUP_ID
        from aiogram.enums import ContentType
        
        # Небольшая задержка между сообщениями для защиты от flood
        await asyncio.sleep(0.1)
        
        if message.content_type == ContentType.TEXT:
            await bot.send_message(
                ADMIN_GROUP_ID,
                message.text,
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.PHOTO:
            await bot.send_photo(
                ADMIN_GROUP_ID,
                message.photo[-1].file_id,
                caption=message.caption,
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.VIDEO:
            await bot.send_video(
                ADMIN_GROUP_ID,
                message.video.file_id,
                caption=message.caption,
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.DOCUMENT:
            await bot.send_document(
                ADMIN_GROUP_ID,
                message.document.file_id,
                caption=message.caption,
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.VOICE:
            await bot.send_voice(
                ADMIN_GROUP_ID,
                message.voice.file_id,
                caption=message.caption,
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.AUDIO:
            await bot.send_audio(
                ADMIN_GROUP_ID,
                message.audio.file_id,
                caption=message.caption,
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.VIDEO_NOTE:
            await bot.send_video_note(
                ADMIN_GROUP_ID,
                message.video_note.file_id,
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.STICKER:
            await bot.send_sticker(
                ADMIN_GROUP_ID,
                message.sticker.file_id,
                message_thread_id=topic_id
            )
        elif message.content_type == ContentType.ANIMATION:
            await bot.send_animation(
                ADMIN_GROUP_ID,
                message.animation.file_id,
                caption=message.caption,
                message_thread_id=topic_id
            )
        else:
            await bot.send_message(
                ADMIN_GROUP_ID,
                f"[Неподдерживаемый тип: {message.content_type}]",
                message_thread_id=topic_id
            )
            
    except Exception as e:
        logger.error(f"Failed to send message to topic {topic_id}: {e}", exc_info=True)
        raise


def format_topic_name(ticket: Ticket) -> str:
    """Форматирует название топика"""
    username_part = f"@{ticket.username}" if ticket.username else ticket.full_name
    status_emoji = "🟢" if ticket.status == TicketStatus.OPEN else "🔴"
    return f"{status_emoji} {ticket.ticket_id} | {ticket.user_id} | {username_part}"
