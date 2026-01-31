from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from . import models, schemas, crud

app = FastAPI(title="RippleChat API")

# =======================
# Простая OAuth2-схема
# =======================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")  # эндпоинт логина

# временное "хранилище" пользователей
USERS = {
    "ira": {"id": 1, "password": "ira-pass"},
    "mama": {"id": 2, "password": "mama-pass"},
    "seva": {"id": 3, "password": "seva-pass"},
}


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int


@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = USERS.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    # в качестве токена используем username (упрощённый вариант, как в доках)[web:601]
    return {
        "access_token": form_data.username,
        "token_type": "bearer",
        "user_id": user["id"],
    }


async def get_current_user(token: str = Depends(oauth2_scheme)):
    # token == username
    user = USERS.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# =======================
# Инициализация БД
# =======================

def init_db():
    Base.metadata.create_all(bind=engine)

    db = next(get_db())
    try:
        if not db.query(models.User).first():
            ira = models.User(name="Ира")
            mama = models.User(name="Мама")
            seva = models.User(name="Сева")
            db.add_all([ira, mama, seva])
            db.commit()

        if not db.query(models.Chat).first():
            family_chat = models.Chat(title="Семейный чат", is_group=True)
            db.add(family_chat)
            db.commit()
            db.refresh(family_chat)

            users = db.query(models.User).all()
            for u in users:
                db.add(models.ChatMember(chat_id=family_chat.id, user_id=u.id))
            db.commit()
    finally:
        db.close()


init_db()

# =======================
# Эндпоинты
# =======================

@app.get("/users/{user_id}/chats")
async def get_user_chats(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    chats = (
        db.query(models.Chat)
        .join(models.ChatMember, models.ChatMember.chat_id == models.Chat.id)
        .filter(models.ChatMember.user_id == user_id)
        .all()
    )

    return chats



@app.get("/chats/{chat_id}/messages", response_model=list[schemas.MessageOut])
async def read_chat_messages(
    chat_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    msgs = crud.get_chat_messages(db, chat_id=chat_id, limit=limit, offset=offset)
    return list(reversed(msgs))



@app.post("/chats/{chat_id}/messages", response_model=schemas.MessageOut)
def send_message(
    chat_id: int,
    payload: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    msg = crud.create_message(
        db, chat_id=chat_id, user_id=payload.user_id, text=payload.text
    )
    return msg


@app.post("/chats", response_model=schemas.ChatOut)
def create_chat_endpoint(
    payload: schemas.ChatCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    member_ids = [payload.creator_id]
    chat = crud.create_chat(db, title=payload.title, member_user_ids=member_ids)
    return chat

