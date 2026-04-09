import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models import Base
from dotenv import load_dotenv

load_dotenv()

# URL для подключения к базе в Docker
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/clickup_db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    """Создает таблицы в базе данных, если их еще нет"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)