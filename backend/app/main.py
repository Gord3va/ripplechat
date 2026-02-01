from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from . import models, schemas, crud


from .security import hash_password

from .db import SessionLocal

from .security import verify_password

from typing import cast
from .models import User



# # создаём все таблицы один раз при импорте приложения
# Base.metadata.create_all(bind=engine)


# def init_test_users():
#     db = SessionLocal()
#     try:
#         if db.query(models.User).count() == 0:
#             users = [
#                 ("ira",   "Ира",   "ira"),
#                 ("mama",  "Мама",  "mama"),
#                 ("seva",  "Сева",  "seva"),
#             ]
#             for login, display_name, raw_password in users:
#                 user = models.User(
#                     name=login,
#                     display_name=display_name,
#                     hashed_password=hash_password(raw_password),
#                 )
#                 db.add(user)
#             db.commit()
#             print("== Created test users: ira, mama, seva ==")
#     finally:
#         db.close()

# init_test_users()



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




@app.post("/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # ищем пользователя в БД по логину (name)
    user = db.query(models.User).filter(models.User.name == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )

    stored_hash = str(user.hashed_password)
    if not verify_password(form_data.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )

    # упрощённо: токен = логин, как раньше
    token = user.name

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
    }

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    # token == name (логин пользователя)
    user = db.query(models.User).filter(models.User.name == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # возвращаем такой же словарь, как раньше USERS[token]
    return {"id": user.id, "password": "", "name": user.name}

# =======================
# Инициализация БД
# =======================

# def init_db():
#     Base.metadata.create_all(bind=engine)

#     db = next(get_db())
#     try:
#         # блок с ira/mama/seva тут больше не нужен, он уже есть в init_test_users
#         if not db.query(models.Chat).first():
#             family_chat = models.Chat(title="Семейный чат", is_group=True)
#             db.add(family_chat)
#             db.commit()
#             db.refresh(family_chat)

#             users = db.query(models.User).all()
#             for u in users:
#                 db.add(models.ChatMember(chat_id=family_chat.id, user_id=u.id))
#             db.commit()
#     finally:
#         db.close()
# init_db()



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


# список всех пользователей
@app.get("/users", response_model=list[schemas.UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    users = crud.get_all_users(db)
    return users


# участники чата
@app.get("/chats/{chat_id}/members", response_model=list[schemas.ChatMemberOut])
def list_chat_members(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    members = crud.get_chat_members(db, chat_id)
    return [
        schemas.ChatMemberOut(
            chat_id=m.chat_id,
            user_id=m.user_id,
            user_name=m.user_name,
        )
        for m in members
    ]


# добавление участника
@app.post("/chats/{chat_id}/members", response_model=schemas.ChatMemberOut)
def add_chat_member(
    chat_id: int,
    payload: schemas.ChatMemberAdd,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    member = crud.add_user_to_chat(db, chat_id, payload.user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if user is None:
        # теоретически сюда не попадём, но для тайпчекера и надёжности
        raise HTTPException(status_code=404, detail="User not found")

    user_name: str = str(user.name)

    return schemas.ChatMemberOut(
        chat_id=chat_id,
        user_id=payload.user_id,
        user_name=user_name,
    )

@app.delete("/chats/{chat_id}/members/{user_id}")
def remove_chat_member(chat_id: int, user_id: int, db: Session = Depends(get_db)):
    # ищем запись участника
    member = (
        db.query(models.ChatMember)
        .filter(
            models.ChatMember.chat_id == chat_id,
            models.ChatMember.user_id == user_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this chat")

    db.delete(member)
    db.commit()
    return {"ok": True}

@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "name": user.name,
        "display_name": user.display_name or user.name,
    }

@app.put("/users/{user_id}")
def update_user_profile(
    user_id: int,
    payload: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user = cast(User, user)  # подсказываем типизатору, что это экземпляр, а не Column


    if payload.display_name is not None and payload.display_name != "":
        user.display_name = payload.display_name  # type: ignore[reportAttributeAccessIssue]

    if payload.password is not None and payload.password != "":
        user.hashed_password = hash_password(payload.password) # type: ignore[reportAttributeAccessIssue]


    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "display_name": user.display_name or user.name,
    }



@app.post("/users/{user_id}/password")
def change_password(
    user_id: int,
    payload: schemas.PasswordChange,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stored_hash = str(user.hashed_password)
    if not verify_password(payload.old_password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password",
        )

    user.hashed_password = hash_password(payload.new_password)  # type: ignore[reportAttributeAccessIssue]

    db.commit()
    return {"ok": True}



