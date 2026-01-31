from pydantic import BaseModel
from datetime import datetime

class MessageBase(BaseModel):
    text: str


class MessageCreate(MessageBase):
    user_id: int


class MessageOut(MessageBase):
    id: int
    chat_id: int
    user_id: int
    text: str
    created_at: datetime

    class Config:
        orm_mode = True


class ChatCreate(BaseModel):
    title: str
    creator_id: int


class ChatOut(BaseModel):
    id: int
    title: str

    class Config:
        orm_mode = True


class ChatMemberAdd(BaseModel):
    user_id: int


class ChatMemberOut(BaseModel):
    chat_id: int
    user_id: int
    user_name: str

    class Config:
        orm_mode = True


class UserOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True