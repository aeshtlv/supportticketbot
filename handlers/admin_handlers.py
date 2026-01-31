"""
Обработчики для админ-группы
Администраторы работают в группе с топиками
"""
import logging
from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ContentType

from config import ADMIN_GROUP_ID, ADMIN_IDS
from database import get_db
from services import TicketService
from database.models import TicketStatus, Ticket

router = Router()
logger = logging.getLogger(__name__)


def is_admin_group(message: Message) -> bool:
    """Проверяет, что сообщение из админ-группы"""
    if not ADMIN_GROUP_ID:
        return False
    return str(message.chat.id) == str(ADMIN_GROUP_ID)


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


@router.message(Command("close"))
async def cmd_close(message: Message, bot: Bot):
    """
    Команда /close - закрыть тикет
    
    Использование: /close в топике
    """
    if not is_admin_group(message):
        return
    
    if not is_admin(message.from_user.id):
        return
    
    # Проверяем, что команда вызвана в топике
    if not message.message_thread_id:
        await message.reply("❌ Команда /close должна быть вызвана в топике тикета.")
        return
    
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            
            # Находим тикет по topic_id
            ticket = await service.get_ticket_by_topic_id(message.message_thread_id)
            
            if not ticket:
                await message.reply("❌ Тикет не найден для этого топика.")
                return
            
            if ticket.status == TicketStatus.CLOSED:
                await message.reply("ℹ️ Тикет уже закрыт.")
                return
            
            # Закрываем тикет
            await service.close_ticket(ticket)
            
            # Обновляем название топика
            topic_name = format_topic_name_closed(ticket)
            try:
                await bot.edit_forum_topic(
                    chat_id=int(ADMIN_GROUP_ID),
                    message_thread_id=ticket.topic_id,
                    name=topic_name
                )
            except Exception as e:
                logger.error(f"Failed to update topic name: {e}")
            
            # Уведомляем пользователя
            try:
                await bot.send_message(
                    ticket.user_chat_id,
                    f"✅ Ваше обращение #{ticket.ticket_id} закрыто.\n\n"
                    f"Если у вас возникнут новые вопросы, напишите нам снова."
                )
            except Exception as e:
                logger.error(f"Failed to notify user about ticket closure: {e}")
            
            await message.reply(f"✅ Тикет #{ticket.ticket_id} закрыт. Пользователь уведомлён.")
            logger.info(f"Ticket {ticket.ticket_id} closed by admin {message.from_user.id}")
            
    except Exception as e:
        logger.error(f"Error in cmd_close: {e}", exc_info=True)
        await message.reply("❌ Ошибка при закрытии тикета.")


@router.message(F.func(is_admin_group))
async def handle_admin_message(message: Message, bot: Bot):
    """
    Обработка сообщений администраторов в топиках
    
    Логика:
    1. Игнорируем сообщения вне топиков
    2. Игнорируем служебные события форума
    3. Игнорируем команды (они обрабатываются отдельно)
    4. Пересылаем сообщение пользователю, который создал тикет
    """
    # Игнорируем сообщения вне топиков
    if not message.message_thread_id:
        logger.debug(f"Message from admin group without topic_id, ignoring")
        return
    
    # Игнорируем служебные события форума
    if message.content_type in [
        ContentType.FORUM_TOPIC_CREATED,
        ContentType.FORUM_TOPIC_CLOSED,
        ContentType.FORUM_TOPIC_REOPENED,
        ContentType.FORUM_TOPIC_EDITED,
        ContentType.GENERAL_FORUM_TOPIC_HIDDEN,
        ContentType.GENERAL_FORUM_TOPIC_UNHIDDEN,
    ]:
        return
    
    # Игнорируем команды
    if message.text and message.text.startswith("/"):
        return
    
    # Игнорируем сообщения от ботов
    if message.from_user and message.from_user.is_bot:
        return
    
    try:
        async with get_db().session_factory() as session:
            service = TicketService(session)
            
            # Находим тикет по topic_id
            ticket = await service.get_ticket_by_topic_id(message.message_thread_id)
            
            if not ticket:
                logger.warning(f"Ticket not found for topic_id={message.message_thread_id}")
                return
            
            if ticket.status == TicketStatus.CLOSED:
                logger.debug(f"Ticket {ticket.ticket_id} is closed, ignoring message")
                return
            
            # Пересылаем сообщение пользователю
            logger.info(
                f"Forwarding message from admin {message.from_user.id} "
                f"to user {ticket.user_id} (ticket {ticket.ticket_id})"
            )
            
            await forward_to_user(bot, message, ticket.user_chat_id)
            
    except Exception as e:
        logger.error(f"Error in handle_admin_message: {e}", exc_info=True)


async def forward_to_user(bot: Bot, message: Message, user_chat_id: int):
    """Пересылает сообщение пользователю"""
    try:
        from aiogram.enums import ContentType
        
        if message.content_type == ContentType.TEXT:
            await bot.send_message(user_chat_id, message.text)
        elif message.content_type == ContentType.PHOTO:
            await bot.send_photo(user_chat_id, message.photo[-1].file_id, caption=message.caption)
        elif message.content_type == ContentType.VIDEO:
            await bot.send_video(user_chat_id, message.video.file_id, caption=message.caption)
        elif message.content_type == ContentType.DOCUMENT:
            await bot.send_document(user_chat_id, message.document.file_id, caption=message.caption)
        elif message.content_type == ContentType.VOICE:
            await bot.send_voice(user_chat_id, message.voice.file_id, caption=message.caption)
        elif message.content_type == ContentType.AUDIO:
            await bot.send_audio(user_chat_id, message.audio.file_id, caption=message.caption)
        elif message.content_type == ContentType.VIDEO_NOTE:
            await bot.send_video_note(user_chat_id, message.video_note.file_id)
        elif message.content_type == ContentType.STICKER:
            await bot.send_sticker(user_chat_id, message.sticker.file_id)
        elif message.content_type == ContentType.ANIMATION:
            await bot.send_animation(user_chat_id, message.animation.file_id, caption=message.caption)
        else:
            await bot.send_message(user_chat_id, f"[Неподдерживаемый тип: {message.content_type}]")
        
        logger.info(f"✅ Successfully forwarded message to user {user_chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to forward to user {user_chat_id}: {e}", exc_info=True)


def format_topic_name_closed(ticket: Ticket) -> str:
    """Форматирует название топика для закрытого тикета"""
    username_part = f"@{ticket.username}" if ticket.username else ticket.full_name
    return f"🔴 {ticket.ticket_id} | {ticket.user_id} | {username_part}"

