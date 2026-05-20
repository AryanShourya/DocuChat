from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Document(Base):
    __tablename__ = "documents"

    id:         Mapped[int]     = mapped_column(Integer,primary_key=True,autoincrement=True)
    user_id:    Mapped[str]     = mapped_column(String(128),nullable=False,index=True)
    filename:   Mapped[str]     = mapped_column(String(255),nullable=False)
    file_path:  Mapped[str]     = mapped_column(String(512),nullable=False)
    file_size:  Mapped[int]     = mapped_column(Integer,nullable=False)
    status:     Mapped[str]     = mapped_column(String(32),default="uploaded")
    created_at: Mapped[datetime]= mapped_column(DateTime,default=lambda: datetime.now(timezone.utc))

    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession",back_populates="document")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id:         Mapped[int]     = mapped_column(Integer,primary_key=True,autoincrement=True)
    user_id:    Mapped[str]     = mapped_column(String(128),nullable=False,index=True)
    document_id:Mapped[int]     = mapped_column(Integer,ForeignKey("documents.id"),nullable=False)
    created_at: Mapped[datetime]= mapped_column(DateTime,default=lambda: datetime.now(timezone.utc))

    document:   Mapped["Document"]     = relationship("Document",back_populates="chat_sessions")
    messages:   Mapped["Message"]      = relationship("Message",back_populates="session") 


class Message(Base):
    __tablename__ = "messages"

    id:         Mapped[int]     = mapped_column(Integer,primary_key=True,autoincrement=True)
    session_id: Mapped[int]     = mapped_column(Integer,ForeignKey("chat_sessions.id"),nullable=False)
    role:       Mapped[str]     = mapped_column(String(16),nullable=False)
    content:    Mapped[str]     = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime]= mapped_column(DateTime,default=lambda: datetime.now(timezone.utc))

    session: Mapped["ChatSession"] = relationship("ChatSession",back_populates="messages")