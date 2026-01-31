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


from . import models, schemas
from sqlalchemy.orm import Session


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

