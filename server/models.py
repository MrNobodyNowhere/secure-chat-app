from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
	__tablename__ = "users"

	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(64), unique=True, index=True, nullable=False)
	password_hash = Column(String(256), nullable=False)
	created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
	last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)

	sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
	received_messages = relationship("Message", back_populates="recipient", foreign_keys="Message.recipient_id")


class Message(Base):
	__tablename__ = "messages"

	id = Column(Integer, primary_key=True, index=True)
	sender_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
	recipient_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
	content = Column(Text, nullable=False)
	created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
	is_read = Column(Boolean, default=False, nullable=False)

	sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
	recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")

Index("ix_messages_pair_time", Message.sender_id, Message.recipient_id, Message.created_at)

