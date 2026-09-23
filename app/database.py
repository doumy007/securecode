from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with engine.begin() as conn:
            for col, col_type in [("git_username", "VARCHAR(255)"), ("git_token", "VARCHAR(512)"), ("nombre", "VARCHAR(255)"), ("tipo", "VARCHAR(20)"), ("frameworks", "JSON"), ("git_url", "VARCHAR(1024)"), ("updated_at", "DATETIME")]:
                try:
                    await conn.execute(text(f"ALTER TABLE sc_auditorias ADD COLUMN {col} {col_type}"))
                except Exception:
                    pass
    except Exception as e:
        import logging
        logging.getLogger("securecode").warning(f"init_db (no crítico): {e}")
