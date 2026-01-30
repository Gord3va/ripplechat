from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


from .db import Base, engine, get_db
from . import models, schemas, crud

from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from . import models, schemas, crud

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer  # form для /login
from pydantic import BaseModel

from typing import List
from fastapi import Depends

app = FastAPI(title="RippleChat API")

security = HTTPBearer()
API_TOKEN = "super-secret-token-123" #cупертокен

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")  # /login

# временно: храним пользователей и пароли в памяти
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
    # в качестве токена можно использовать username или сгенерированную строку
    return {
        "access_token": form_data.username,
        "token_type": "bearer",
        "user_id": user["id"],
    }

def get_current_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth scheme",
        )
    if credentials.credentials != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )
    return credentials.credentials

async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = USERS.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def init_db():
    # создать таблицы, если их нет
    Base.metadata.create_all(bind=engine)

    # засев: если нет пользователей/чатов — создаём
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


@app.get("/users/{user_id}/chats")
async def get_user_chats(
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    # дальше — как у тебя сейчас: достаём чаты из БД для этого user_id


@app.get("/users/{user_id}/chats")
async def get_user_chats(user_id: int, current_user=Depends(get_current_user)):
    chats = repo.get_chats_for_user(user_id)
    if chats is None:
        chats = []
    return chats


@app.get("/chats/{chat_id}/messages", response_model=list[schemas.MessageOut])
def read_chat_messages(
    chat_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    token: str = Depends(get_current_token),
):
    msgs = crud.get_chat_messages(db, chat_id=chat_id, limit=limit, offset=offset)
    return list(reversed(msgs))  # чтобы новые были внизу


@app.post("/chats/{chat_id}/messages", response_model=schemas.MessageOut)
def send_message(
    chat_id: int,
    payload: schemas.MessageCreate,
    db: Session = Depends(get_db),
    token: str = Depends(get_current_token),
):
    # можно добавить проверки chat_id/user_id, но пока минимально
    msg = crud.create_message(
        db, chat_id=chat_id, user_id=payload.user_id, text=payload.text
    )
    return msg


@app.post("/chats", response_model=schemas.ChatOut)
def create_chat_endpoint(
    payload: schemas.ChatCreate,
    db: Session = Depends(get_db),
    token: str = Depends(get_current_token),
):
    print("CREATE_CHAT_ENDPOINT CALLED", payload)

    # только создатель — участник чата
    member_ids = [payload.creator_id]

    chat = crud.create_chat(db, title=payload.title, member_user_ids=member_ids)
    return chat

