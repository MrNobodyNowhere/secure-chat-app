from datetime import datetime
from pydantic import BaseModel, Field
from typing import List


class UserCreate(BaseModel):
	username: str = Field(min_length=3, max_length=64)
	password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
	id: int
	username: str
	created_at: datetime
	last_seen: datetime

	class Config:
		from_attributes = True


class Token(BaseModel):
	access_token: str
	token_type: str = "bearer"


class TokenData(BaseModel):
	user_id: int
	username: str


class MessageCreate(BaseModel):
	recipient_id: int
	content: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
	id: int
	sender_id: int
	recipient_id: int
	content: str
	created_at: datetime
	is_read: bool

	class Config:
		from_attributes = True


class ChatHistory(BaseModel):
	with_user_id: int
	messages: List[MessageOut]

