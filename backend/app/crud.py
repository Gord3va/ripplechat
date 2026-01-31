from sqlalchemy.orm import Session
from sqlalchemy import desc
from . import models, schemas

def get_user_chats(db: Session, user_id: int):
    return (
        db.query(models.Chat)
        .join(models.ChatMember)
        .filter(models.ChatMember.user_id == user_id)
        .all()
    )

def get_chat_messages(db: Session, chat_id: int, limit: int = 50, offset: int = 0):
    q = (
        db.query(models.Message, models.User.name.label("user_name"))
        .join(models.User, models.User.id == models.Message.user_id)
        .filter(models.Message.chat_id == chat_id)
        .order_by(models.Message.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = q.all()

    result = []
    for msg, user_name in rows:
        # "подкладываем" атрибут, чтобы pydantic мог его прочитать через orm_mode
        msg.user_name = user_name
        result.append(msg)
    return result

def create_message(db: Session, chat_id: int, user_id: int, text: str):
    msg = models.Message(chat_id=chat_id, user_id=user_id, text=text)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def create_chat(db: Session, title: str, member_user_ids: list[int]) -> models.Chat:
    chat = models.Chat(title=title, is_group=True)
    db.add(chat)
    db.commit()
    db.refresh(chat)

    for uid in member_user_ids:
        db.add(models.ChatMember(chat_id=chat.id, user_id=uid))
    db.commit()

    return chat

def get_chats_for_user(db: Session, user_id: int):
    return (
        db.query(models.Chat)
        .join(models.ChatMember, models.ChatMember.chat_id == models.Chat.id)
        .filter(models.ChatMember.user_id == user_id)
        .all()
    )

def add_user_to_chat(db: Session, chat_id: int, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    exists = (
        db.query(models.ChatMember)
        .filter(
            models.ChatMember.chat_id == chat_id,
            models.ChatMember.user_id == user_id,
        )
        .first()
    )
    if exists:
        return exists

    member = models.ChatMember(chat_id=chat_id, user_id=user_id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

def get_chat_members(db: Session, chat_id: int):
    q = (
        db.query(models.ChatMember, models.User.name.label("user_name"))
        .join(models.User, models.User.id == models.ChatMember.user_id)
        .filter(models.ChatMember.chat_id == chat_id)
    )
    rows = q.all()
    result = []
    for m, user_name in rows:
        m.user_name = user_name
        result.append(m)
    return result

def get_all_users(db: Session):
    return db.query(models.User).all()
