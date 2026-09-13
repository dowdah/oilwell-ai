"""Explicit local-only integration check, never pointed at deployed services.

Requires API localhost:8001, isolated test DB, broker localhost:18884, and
qa-edge-controlled with the selected real Parquet. Writes ignored evidence.
Baseline model output is used for wiring checks, never model acceptance.
"""
import asyncio, json, time
from pathlib import Path
import httpx, websockets

BASE='http://127.0.0.1:8001'
DEVICE='qa-edge-controlled'
INSTANCE='0/WELL-00001_20170201010207.parquet'
OUT=Path('docs/.local/phase-1-5-completion/mqtt-chain.json')

async def main():
    samples=[]; inferences=[]; commands=[]
    async with httpx.AsyncClient(base_url=BASE, timeout=5) as api, websockets.connect('ws://127.0.0.1:8001/ws') as socket:
        async def collect():
            async for raw in socket:
                event=json.loads(raw); p=event['payload']
                if event['event']=='telemetry' and p['device_id']==DEVICE:samples.append((time.monotonic(),p))
                if event['event']=='inference' and p['well_id']=='WELL-00001':inferences.append(p)
        collector=asyncio.create_task(collect())
        async def until(check, timeout=30):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                if collector.done():
                    raise RuntimeError('WebSocket collector failed') from collector.exception()
                if check():return
                await asyncio.sleep(.1)
            raise AssertionError('condition timed out')
        async def command(name, expected='applied', **params):
            started=time.monotonic()
            response=await api.post(f'/api/replay/{DEVICE}/commands',json={'command':name,**params}); response.raise_for_status()
            body=response.json(); deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                devices=(await api.get('/api/edge-devices')).json()
                device=next((row for row in devices if row['id']==DEVICE),None)
                ack=(device or {}).get('metrics',{}).get('last_command',{})
                if ack.get('command_id')==body['command_id']:
                    assert ack['status']==expected,(name,ack)
                    commands.append({'command':name,'params':params,'ack':ack,'round_trip_ms':round((time.monotonic()-started)*1000,2)})
                    return
                await asyncio.sleep(.1)
            raise AssertionError(f'no acknowledgement: {name}')
        try:
            assert (await api.get('/api/health')).json()['mqtt_connected']
            await command('STOP')
            await command('LOAD_INSTANCE',instance=INSTANCE)
            await command('SET_SPEED',speed=10)
            await command('START')
            await until(lambda:len(samples)>=40)
            ten=list(samples)
            await command('LOAD_INSTANCE',expected='rejected',instance=INSTANCE)
            await command('PAUSE')
            await asyncio.sleep(.3); paused=len(samples);await asyncio.sleep(1)
            assert len(samples)==paused,'telemetry continued while paused'
            await command('SET_SPEED',speed=20)
            await command('START')
            await until(lambda:len(samples)>=205)
            await command('STOP')
            await until(lambda:sum(x.get('status')=='predicted' for x in inferences)>=6)
            await asyncio.sleep(.3); stopped=len(samples);await asyncio.sleep(.5)
            assert len(samples)==stopped,'telemetry continued after STOP'
            before=max(p['sequence'] for _,p in samples)
            await command('START');await until(lambda:len(samples)>=stopped+10);await command('STOP')
            assert all(p['sequence']>before for _,p in samples[stopped:])
            sequences=[p['sequence'] for _,p in samples]
            assert len(sequences)==len(set(sequences))
            predicted=[p for p in inferences if p.get('status')=='predicted']
            pairs={}
            for p in predicted:pairs.setdefault((p['window_start'],p['window_end']),set()).add(p['model_mode'])
            assert sum(v=={'active','shadow'} for v in pairs.values())>=3
            history=(await api.get('/api/wells/WELL-00001/telemetry',params={'limit':5000})).json()
            assert set(sequences)<=set(p['sequence'] for p in history)
            report={'scope':'isolated local MQTT TCP, actual source parquet and baseline models; not TLS/Pi/deployment/model-quality acceptance','commands':commands,'telemetry_messages':len(samples),'predictions':len(predicted),'paired_model_windows':sum(v=={'active','shadow'} for v in pairs.values()),'ten_x_observed_hz':(len(ten)-1)/(ten[-1][0]-ten[0][0]),'twenty_x_observed_hz':(stopped-paused-1)/(samples[stopped-1][0]-samples[paused][0]),'pause_stable':True,'stop_stable':True,'sequence_unique_and_restart_monotonic':True,'database_contains_all_received_sequences':True}
            OUT.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='commands'},indent=2))
        finally:
            try:await command('STOP')
            finally:collector.cancel();await asyncio.gather(collector,return_exceptions=True)

if __name__ == '__main__':
    asyncio.run(main())
