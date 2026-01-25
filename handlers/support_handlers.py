"""
Обработчики для чата поддержки (Reply на сообщения)
"""
import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery

from config import SUPPORT_CHAT_ID, ADMIN_IDS
from database import get_db
from services import TicketService
from database.models import TicketStatus

router = Router()
logger = logging.getLogger(__name__)


async def forward_to_user(bot: Bot, message: Message, user_telegram_id: int):
    """Пересылает ответ пользователю"""
    try:
        if message.content_type == "text":
            await bot.send_message(user_telegram_id, message.text)
        elif message.content_type == "photo":
            await bot.send_photo(
                user_telegram_id,
                message.photo[-1].file_id,
                caption=message.caption
            )
        elif message.content_type == "video":
            await bot.send_video(
                user_telegram_id,
                message.video.file_id,
                caption=message.caption
            )
        elif message.content_type == "document":
            await bot.send_document(
                user_telegram_id,
                message.document.file_id,
                caption=message.caption
            )
        elif message.content_type == "voice":
            await bot.send_voice(
                user_telegram_id,
                message.voice.file_id,
                caption=message.caption
            )
        elif message.content_type == "audio":
            await bot.send_audio(
                user_telegram_id,
                message.audio.file_id,
                caption=message.caption
            )
        elif message.content_type == "video_note":
            await bot.send_video_note(user_telegram_id, message.video_note.file_id)
        elif message.content_type == "sticker":
            await bot.send_sticker(user_telegram_id, message.sticker.file_id)
        elif message.content_type == "animation":
            await bot.send_animation(
                user_telegram_id,
                message.animation.file_id,
                caption=message.caption
            )
        else:
            await bot.send_message(user_telegram_id, f"[Неподдерживаемый тип: {message.content_type}]")
    except Exception as e:
        logger.error(f"Failed to forward to user {user_telegram_id}: {e}")


@router.message()
async def handle_support_reply(message: Message, bot: Bot):
    """Обработка Reply в чате поддержки"""
    # Проверяем, что сообщение из чата поддержки
    if not SUPPORT_CHAT_ID or str(message.chat.id) != str(SUPPORT_CHAT_ID):
        return
    
    # Проверяем, что это ответ на сообщение
    if not message.reply_to_message:
        return
    
    reply_to = message.reply_to_message
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        
        # Ищем связь по ID сообщения
        link = await service.get_message_link_by_support_id(reply_to.message_id)
        
        if not link:
            # Может быть это ответ на заголовок (для video_note, sticker)
            # Ищем по топику, если есть
            if message.message_thread_id:
                from sqlalchemy import select
                from database.models import Ticket
                
                result = await session.execute(
                    select(Ticket).where(Ticket.topic_id == message.message_thread_id)
                )
                ticket = result.scalar_one_or_none()
                
                if ticket:
                    # Отправляем пользователю
                    await forward_to_user(bot, message, ticket.user.telegram_id)
            return
        
        # Отправляем ответ пользователю
        await forward_to_user(bot, message, link.user.telegram_id)


@router.callback_query(F.data.startswith("toggle_ticket:"))
async def cb_toggle_ticket(callback: CallbackQuery, bot: Bot):
    """Переключение статуса тикета"""
    ticket_id = callback.data.split(":")[1]
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_id(ticket_id)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        if ticket.status == TicketStatus.OPEN:
            await service.close_ticket(ticket)
            status_emoji = "🔴"
            status_text = "закрыт"
        else:
            await service.reopen_ticket(ticket)
            status_emoji = "🟢"
            status_text = "открыт"
        
        # Обновляем название топика, если используется отдельный топик
        if ticket.topic_id:
            try:
                user_info = f"@{ticket.user.username}" if ticket.user.username else ticket.user.full_name
                topic_name = f"{status_emoji} {ticket.ticket_id} | {user_info}"
                await bot.edit_forum_topic(
                    chat_id=int(SUPPORT_CHAT_ID),
                    message_thread_id=ticket.topic_id,
                    name=topic_name
                )
            except Exception as e:
                logger.error(f"Failed to update topic name: {e}")
        
        # Обновляем кнопку
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
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
        
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except:
            pass
        
        await callback.answer(f"✅ Тикет {status_text}")


@router.callback_query(F.data.startswith("toggle_ban:"))
async def cb_toggle_ban(callback: CallbackQuery, bot: Bot):
    """Переключение бана пользователя"""
    user_telegram_id = int(callback.data.split(":")[1])
    
    async with get_db().session_factory() as session:
        service = TicketService(session)
        user = await service.get_user_by_telegram_id(user_telegram_id)
        
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        if user.is_banned:
            await service.unban_user(user)
            action = "разбанен"
        else:
            await service.ban_user(user)
            action = "забанен"
        
        # Обновляем кнопку
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from database.models import Ticket
        
        # Находим тикет пользователя
        from sqlalchemy import select
        result = await session.execute(
            select(Ticket)
            .where(Ticket.user_id == user.id)
            .order_by(Ticket.created_at.desc())
        )
        ticket = result.scalar_one_or_none()
        
        if ticket:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔴 Закрыть" if ticket.status == TicketStatus.OPEN else "🟢 Открыть",
                        callback_data=f"toggle_ticket:{ticket.ticket_id}"
                    ),
                    InlineKeyboardButton(
                        text="⛔ Забанить" if not user.is_banned else "✅ Разбанить",
                        callback_data=f"toggle_ban:{user.telegram_id}"
                    )
                ]
            ])
            
            try:
                await callback.message.edit_reply_markup(reply_markup=keyboard)
            except:
                pass
        
        await callback.answer(f"✅ Пользователь {action}")

