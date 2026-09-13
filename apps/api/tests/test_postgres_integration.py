"""Real PostgreSQL tests; each test owns a fresh schema in a local test DB only."""
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.inference import InferenceOutcome
from app.models import Alarm, AlarmState, Telemetry
from app.schemas import TelemetryIn
from app.services import acknowledge_alarm, persist_inferences, process_telemetry


@pytest_asyncio.fixture
async def session():
    url = os.getenv('OILWELL_TEST_DATABASE_URL')
    if not url: pytest.skip('requires isolated local PostgreSQL: OILWELL_TEST_DATABASE_URL')
    parsed = make_url(url)
    if parsed.host not in {'127.0.0.1', 'localhost'} or parsed.database != 'oilwell_test':
        pytest.fail('integration tests require localhost/oilwell_test, never a deployed database')
    schema = 'test_' + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as conn: await conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine = create_async_engine(url, connect_args={'server_settings': {'search_path': schema}})
    try:
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as value: yield value
    finally:
        await engine.dispose()
        async with admin.begin() as conn: await conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        await admin.dispose()


def packet(sequence):
    return TelemetryIn.model_validate({'device_id': 'test-edge', 'well_id': 'test-well',
        'timestamp': '2017-01-01T00:00:00Z', 'sequence': sequence,
        'measurements': {name: 1.0 for name in ('P_PDG','P_TPT','T_TPT','P_MON_CKP','T_JUS_CKP','P_JUS_CKGL','QGL')}})


def outcome(label='Severe Slugging', mode='active', score=0.9, status='predicted'):
    return InferenceOutcome(status=status, model_type='xgboost' if mode == 'active' else 'tcn', model_mode=mode,
        window_start=datetime(2017,1,1,tzinfo=UTC), window_end=datetime(2017,1,1,tzinfo=UTC)+timedelta(seconds=179),
        model_version='test-v1', predicted_class=label, confidence=0.9, anomaly_score=score,
        feature_schema_version='3w-7v-window-stats-v1')


async def insert_result(session, sequence, outcomes):
    row = await process_telemetry(session, packet(sequence))
    assert row is not None
    return await persist_inferences(session, row, outcomes, 0.5, 2, 3)


async def inference_telemetry_model_mode_constraint(session):
    result = await session.execute(text("""
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
        WHERE constraint_row.conname = 'uq_inference_telemetry_model_mode'
            AND constraint_row.conrelid = to_regclass(
                format('%I.%I', current_schema(), 'inference_results')
            )
        GROUP BY constraint_row.oid, constraint_row.conindid,
            constraint_row.contype, table_row.relname
    """))
    row = result.mappings().one_or_none()
    return None if row is None else dict(row)


async def test_bigint_dedup_and_replay_receipt_heartbeat(session):
    from app.models import EdgeDevice
    large = 1_789_214_000_000_000
    assert await process_telemetry(session, packet(large)) is not None
    assert await process_telemetry(session, packet(large)) is None
    assert await process_telemetry(session, packet(large + 1)) is not None
    assert len((await session.scalars(select(Telemetry))).all()) == 2
    device = await session.get(EdgeDevice, 'test-edge')
    assert (datetime.now(UTC) - device.last_heartbeat).total_seconds() < 5


async def test_alarm_confirmation_shadow_isolation_recovery_and_rearm(session):
    _, alarm = await insert_result(session, 1, [outcome('Normal', score=0), outcome(mode='shadow')])
    assert alarm is None
    assert not (await session.scalars(select(Alarm))).all()
    _, alarm = await insert_result(session, 2, [outcome()])
    assert alarm is None
    _, alarm = await insert_result(session, 3, [outcome()])
    assert alarm is not None
    alarm_id = alarm.id
    assert (await acknowledge_alarm(session, alarm_id)).status == 'ACKNOWLEDGED'
    for seq in range(4,7): await insert_result(session, seq, [outcome(score=0.2)])
    assert (await session.get(Alarm, alarm_id)).status == 'ACKNOWLEDGED'
    for seq in range(7,10): await insert_result(session, seq, [outcome('Normal', score=0)])
    assert (await session.get(Alarm, alarm_id)).status == 'RESOLVED'
    assert (await session.get(Alarm, alarm_id)).resolved_at is not None
    await insert_result(session, 10, [outcome()])
    _, second = await insert_result(session, 11, [outcome()])
    assert second is not None and second.id != alarm_id


async def test_gap_breaks_consecutive_alarm_evidence(session):
    await insert_result(session, 1, [outcome()])
    await insert_result(session, 2, [outcome(status='warming_up')])
    _, alarm = await insert_result(session, 3, [outcome()])
    assert alarm is None


async def test_diagnostic_http_audit_has_no_alarm_or_mqtt_side_effects(session, monkeypatch, tmp_path):
    import app.main as main
    from app.config import Settings
    from app.diagnostics import ControlledDiagnosticService, KnowledgeBase
    from app.database import get_session
    from app.models import DiagnosticRecord
    import json
    records, _ = await insert_result(session, 1, [outcome(), outcome(mode='shadow')])
    async def supplied_session(): yield session
    async def forbidden(*args, **kwargs): pytest.fail('diagnosis published an MQTT control command')
    monkeypatch.setattr(main.bridge, 'publish_command', forbidden)
    main.app.dependency_overrides[get_session] = supplied_session
    service = ControlledDiagnosticService(Settings(explainability_dir=tmp_path))
    monkeypatch.setattr(main, 'diagnostic_service', service)
    state = await session.get(AlarmState, 'test-well')
    baseline = (state.abnormal_streak, state.normal_streak, state.armed, state.active_alarm_id)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
            response = await client.post('/api/wells/test-well/diagnostics', json={'inference_id': records[0].id})
            assert response.status_code == 201
            assert response.json()['evidence_status'] == 'degraded'
            response = await client.post('/api/wells/test-well/diagnostics', json={'inference_id': records[1].id})
            assert response.json()['evidence_status'] == 'refused'
            records[0].confidence = 0.3
            await session.commit()
            response = await client.post('/api/wells/test-well/diagnostics', json={'inference_id': records[0].id})
            assert response.json()['evidence_status'] == 'refused'
            assert response.json()['degradation_reasons']
            history = await client.get('/api/wells/test-well/diagnostics')
            assert len(history.json()) == 3
        await session.refresh(state)
        assert baseline == (state.abnormal_streak, state.normal_streak, state.armed, state.active_alarm_id)
        assert not (await session.scalars(select(Alarm))).all()
        assert len((await session.scalars(select(DiagnosticRecord))).all()) == 3
    finally:
        main.app.dependency_overrides.clear()


async def test_existing_integer_sequence_schema_upgrades_idempotently(session):
    from app.database import migrate_schema
    await session.execute(text('ALTER TABLE telemetry ALTER COLUMN sequence TYPE INTEGER'))
    await session.commit()
    connection = await session.connection()
    await migrate_schema(connection)
    await migrate_schema(connection)
    kind = await session.scalar(text("SELECT data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='telemetry' AND column_name='sequence'"))
    assert kind == 'bigint'
    await session.commit()
    assert await process_telemetry(session, packet(1_789_214_000_000_000)) is not None


async def test_existing_inference_unique_constraint_is_preserved_across_startups(session):
    from app.database import migrate_schema

    before = await inference_telemetry_model_mode_constraint(session)
    assert before is not None
    assert before == {
        'constraint_oid': before['constraint_oid'],
        'backing_index_oid': before['backing_index_oid'],
        'constraint_type': 'u',
        'table_name': 'inference_results',
        'columns': ['telemetry_id', 'model_mode'],
    }
    connection = await session.connection()
    await migrate_schema(connection)
    after_first_startup = await inference_telemetry_model_mode_constraint(session)
    await migrate_schema(connection)
    after_second_startup = await inference_telemetry_model_mode_constraint(session)

    assert after_first_startup == before
    assert after_second_startup == before


async def test_missing_inference_unique_constraint_is_created_once(session):
    from app.database import migrate_schema

    await session.execute(text(
        'ALTER TABLE inference_results '
        'DROP CONSTRAINT uq_inference_telemetry_model_mode'
    ))
    await session.commit()
    assert await inference_telemetry_model_mode_constraint(session) is None

    connection = await session.connection()
    await migrate_schema(connection)
    after_first_startup = await inference_telemetry_model_mode_constraint(session)
    assert after_first_startup['constraint_type'] == 'u'
    assert after_first_startup['table_name'] == 'inference_results'
    assert after_first_startup['columns'] == ['telemetry_id', 'model_mode']

    await migrate_schema(connection)
    after_second_startup = await inference_telemetry_model_mode_constraint(session)
    assert after_second_startup == after_first_startup


async def test_incompatible_inference_unique_constraint_fails_closed(session):
    from app.database import migrate_schema

    await session.execute(text(
        'ALTER TABLE inference_results '
        'DROP CONSTRAINT uq_inference_telemetry_model_mode'
    ))
    await session.execute(text(
        'ALTER TABLE inference_results '
        'ADD CONSTRAINT uq_inference_telemetry_model_mode '
        'UNIQUE (telemetry_id, model_type)'
    ))
    await session.commit()
    before = await inference_telemetry_model_mode_constraint(session)

    connection = await session.connection()
    with pytest.raises(RuntimeError, match='incompatible existing constraint'):
        await migrate_schema(connection)
    assert await inference_telemetry_model_mode_constraint(session) == before
    await session.rollback()
    assert await inference_telemetry_model_mode_constraint(session) == before


async def test_history_filters_are_bounded_and_use_source_time(session, monkeypatch):
    import app.main as main
    from app.database import get_session
    await insert_result(session, 1, [outcome()])
    async def supplied_session(): yield session
    main.app.dependency_overrides[get_session] = supplied_session
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
            response = await client.get('/api/wells/test-well/telemetry', params={'start':'2018-01-01T00:00:00Z'})
            assert response.json() == []
            response = await client.get('/api/wells/test-well/inference', params={'event_class':'Severe Slugging','mode':'active'})
            assert len(response.json()) == 1
            response = await client.get('/api/wells/test-well/telemetry', params={'limit':5001})
            assert response.status_code == 422
            response = await client.get('/api/wells/test-well/telemetry', params={'start':'2018-01-01T00:00:00Z','end':'2017-01-01T00:00:00Z'})
            assert response.status_code == 422
    finally: main.app.dependency_overrides.clear()
