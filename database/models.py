from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mode: Mapped[str] = mapped_column(String(50), default="normal")   # normal|friendly|rude|funny...
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    proactive_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dialogs: Mapped[list["Dialog"]] = relationship("Dialog", back_populates="user", cascade="all, delete-orphan")

class Dialog(Base):
    __tablename__ = "dialogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Храним компактный JSON (строка). Можно сменить на отдельную таблицу реплик.
    history_json: Mapped[str] = mapped_column(Text, default="[]")

    user: Mapped[User] = relationship("User", back_populates="dialogs")
