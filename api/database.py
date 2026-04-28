import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text


DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}"
    f"/{os.getenv('POSTGRES_DB')}"
)

engine = create_async_engine(DATABASE_URL,echo=False)

SessionLocal = async_sessionmaker(engine,expire_on_commit=False)



async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS videos (
         id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         title VARCHAR(255) NOT NULL,
         description TEXT DEFAULT '',
         status VARCHAR(50) DEFAULT 'processing',
         
         original_filename VARCHAR(255),
         duration_seconds INTEGER,
         file_size_bytes BIGINT,
         created_at TIMESTAMP DEFAULT NOW(),
         updated_at TIMESTAMP DEFAULT NOW()
        )
        
        """))

async def get_db():

    async with SessionLocal()  as session:
        yield session
    