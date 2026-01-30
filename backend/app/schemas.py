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
