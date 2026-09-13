from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


INFERENCE_TELEMETRY_MODEL_MODE_CONSTRAINT = "uq_inference_telemetry_model_mode"
INFERENCE_TELEMETRY_MODEL_MODE_COLUMNS = ("telemetry_id", "model_mode")


async def ensure_inference_telemetry_model_mode_constraint(conn) -> None:
    """Create the inference uniqueness constraint once, or fail closed on drift."""
    result = await conn.execute(
        text(
            """
            SELECT
                constraint_row.oid::bigint AS constraint_oid,
                constraint_row.conindid::bigint AS backing_index_oid,
                constraint_row.contype::text AS constraint_type,
                table_row.relname AS table_name,
                array_agg(attribute_row.attname ORDER BY key_column.ordinality) AS columns
            FROM pg_constraint AS constraint_row
            JOIN pg_class AS table_row ON table_row.oid = constraint_row.conrelid
            JOIN LATERAL unnest(constraint_row.conkey) WITH ORDINALITY
                AS key_column(attnum, ordinality) ON TRUE
            JOIN pg_attribute AS attribute_row
                ON attribute_row.attrelid = constraint_row.conrelid
                AND attribute_row.attnum = key_column.attnum
            WHERE constraint_row.conname = :constraint_name
                AND constraint_row.conrelid = to_regclass(
                    format('%I.%I', current_schema(), 'inference_results')
                )
            GROUP BY constraint_row.oid, constraint_row.conindid,
                constraint_row.contype, table_row.relname
            """
        ),
        {"constraint_name": INFERENCE_TELEMETRY_MODEL_MODE_CONSTRAINT},
    )
    constraint = result.mappings().one_or_none()
    if constraint is None:
        await conn.execute(
            text(
                "ALTER TABLE inference_results "
                "ADD CONSTRAINT uq_inference_telemetry_model_mode "
                "UNIQUE (telemetry_id, model_mode)"
            )
        )
        return

    actual_columns = tuple(constraint["columns"])
    if (
        constraint["constraint_type"] != "u"
        or constraint["table_name"] != "inference_results"
        or actual_columns != INFERENCE_TELEMETRY_MODEL_MODE_COLUMNS
    ):
        raise RuntimeError(
            "incompatible existing constraint "
            f"{INFERENCE_TELEMETRY_MODEL_MODE_CONSTRAINT}: expected UNIQUE "
            "on inference_results(telemetry_id, model_mode), found "
            f"type={constraint['constraint_type']!r}, "
            f"table={constraint['table_name']!r}, columns={actual_columns!r}; "
            "refusing to modify the existing constraint"
        )


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
        await ensure_inference_telemetry_model_mode_constraint(conn)
        await conn.execute(text("ALTER TABLE diagnostic_records ADD COLUMN IF NOT EXISTS evidence_status VARCHAR(16) NOT NULL DEFAULT 'complete'"))
        await conn.execute(text("ALTER TABLE diagnostic_records ADD COLUMN IF NOT EXISTS degradation_reasons JSONB NOT NULL DEFAULT '[]'::jsonb"))
