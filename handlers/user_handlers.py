"""
Обработчики сообщений от пользователей
Пользователи пишут боту в личные сообщения
"""
import logging
from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command

from config import ADMIN_GROUP_ID
from database import get_db
from database.models import Ticket
from services import TicketService

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
    1. Проверяем, есть ли у пользователя открытый тикет
    2. Если есть - отправляем сообщение в существующий топик
    3. Если нет - создаём новый тикет и новый топик
    """
    # Пропускаем команды
    if message.text and message.text.startswith("/"):
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
                
                # Отправляем сообщение в топик
                await send_message_to_topic(bot, message, ticket.topic_id)
                
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
                    
                    # Отправляем первое сообщение в топик
                    await send_message_to_topic(bot, message, topic_id)
                    
                    await message.answer("✅ Ваше обращение создано. Администратор скоро ответит.")
                    
                except Exception as e:
                    logger.error(f"Failed to create forum topic: {e}", exc_info=True)
                    await message.answer("❌ Не удалось создать обращение. Попробуйте позже.")
                    
    except Exception as e:
        logger.error(f"Error in handle_user_message: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


async def send_message_to_topic(bot: Bot, message: Message, topic_id: int):
    """Отправляет сообщение в топик админ-группы"""
    try:
        from config import ADMIN_GROUP_ID
        from aiogram.enums import ContentType
        
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
    return f"{ticket.ticket_id} | {ticket.user_id} | {username_part}"
