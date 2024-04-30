from typing import AsyncGenerator

from sqlalchemy.pool import NullPool

from sqlalchemy.orm import sessionmaker, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


from src.settings import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

#ссылка для подключения БД постгре
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

#асинхронный движок create_async_engine
engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=True)#echo нужен для записи логово в консоли от запросов sql

Base = declarative_base()

#это асинхронная сессия БД
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

#это функция для асинхронного запуска. 
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
        





