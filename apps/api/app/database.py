from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(get_settings().database_url, pool_pre_ping=True, pool_size=5, max_overflow=0)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def migrate_schema(conn) -> None:
    """Idempotent additive upgrades; keep BIGINT when rolling application code back."""
    # The phase-2 table allowed only one result per telemetry point. Upgrade existing
    # PostgreSQL deployments before persisting active and shadow results together.
    if conn.dialect.name == "postgresql":
        await conn.execute(text("ALTER TABLE alarms ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ"))
        sequence_type = await conn.scalar(text("SELECT data_type FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'telemetry' AND column_name = 'sequence'"))
        if sequence_type == "integer":
            await conn.execute(text("ALTER TABLE telemetry ALTER COLUMN sequence TYPE BIGINT"))
        await conn.execute(text("ALTER TABLE inference_results DROP CONSTRAINT IF EXISTS uq_inference_telemetry"))
        await conn.execute(text("ALTER TABLE inference_results ADD COLUMN IF NOT EXISTS model_type VARCHAR(32) NOT NULL DEFAULT 'xgboost'"))
        await conn.execute(text("ALTER TABLE inference_results ADD COLUMN IF NOT EXISTS model_mode VARCHAR(16) NOT NULL DEFAULT 'active'"))
        await conn.execute(text("ALTER TABLE inference_results DROP CONSTRAINT IF EXISTS uq_inference_telemetry_model_mode"))
        await conn.execute(text("ALTER TABLE inference_results ADD CONSTRAINT uq_inference_telemetry_model_mode UNIQUE (telemetry_id, model_mode)"))
        await conn.execute(text("ALTER TABLE diagnostic_records ADD COLUMN IF NOT EXISTS evidence_status VARCHAR(16) NOT NULL DEFAULT 'complete'"))
        await conn.execute(text("ALTER TABLE diagnostic_records ADD COLUMN IF NOT EXISTS degradation_reasons JSONB NOT NULL DEFAULT '[]'::jsonb"))
