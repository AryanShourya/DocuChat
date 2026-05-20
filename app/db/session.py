from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# The engine
engine = create_async_engine(
    url= settings.DATABASE_URL,
    echo=settings.DEBUG,
)

# session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_comit=False,
)

# Base class
class Base(DeclarativeBase):
    pass 

#Dependency - routes call this to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise 



