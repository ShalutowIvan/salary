from sqlalchemy import Integer, String, TIMESTAMP, ForeignKey, Float, Boolean, Text, DateTime, text

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base



class User(Base):
    __tablename__ = "user"    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(256))    
    time_create_user: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    email: Mapped[str] = mapped_column(String(length=256), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(length=256), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)#при регистрации запрашивать секретный код, если его ввести, то ты будешь суперюзером. Он будет с полными правами и видеть все данные. 

    #связи
    token: Mapped["Token"] = relationship(back_populates="user")
    worker: Mapped["Worker"] = relationship(back_populates="user")
    salary_increase_date: Mapped["Salary_increase_date"] = relationship(back_populates="user")

    
    

class Token(Base):
    __tablename__ = "token"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    refresh_token = mapped_column(String(length=320), unique=True, index=True, nullable=False)

    #связи
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))    
    user: Mapped["User"] = relationship(back_populates="token")




