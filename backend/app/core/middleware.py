import hashlib
import json
import logging
import time
from uuid import uuid4
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.db.models import RateBucket
from app.db.session import engine

log = logging.getLogger('plateful')


class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({'timestamp':self.formatTime(record),'level':record.levelname,
                          'event':record.getMessage(), **{k:getattr(record,k) for k in
                          ('request_id','method','endpoint','status','duration_ms','error_type') if hasattr(record,k)}})


def limited(client, path):
    bucket = 'auth' if '/auth/' in path else 'planner'
    key = hashlib.sha256((client+bucket).encode()).hexdigest()
    window = int(time.time()) // 60
    table = RateBucket.__table__
    insert = pg_insert if engine().dialect.name == 'postgresql' else sqlite_insert
    with engine().begin() as db:
        db.execute(delete(table).where(table.c.window < window-2))
        stmt = insert(table).values(key=key,window=window,count=1)
        count = db.execute(stmt.on_conflict_do_update(index_elements=['key','window'],set_={'count':table.c.count+1}).returning(table.c.count)).scalar_one()
    return count > settings().rate_limit_per_minute


class RequestMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope,receive,send)
        request_id = str(uuid4())
        scope.setdefault('state',{})['request_id'] = request_id
        start = time.monotonic()
        path = scope['path']
        status = 500
        started = False
        async def wrapped_send(message):
            nonlocal status, started
            if message['type'] == 'http.response.start':
                started = True
                status = message['status']
                message.setdefault('headers',[]).extend([
                    (b'x-request-id',request_id.encode()),(b'x-content-type-options',b'nosniff'),
                    (b'cache-control',b'no-store'),(b'referrer-policy',b'no-referrer')])
            await send(message)
        async def error(code,text,status_code):
            await JSONResponse({'error':{'code':code,'message':text,'request_id':request_id}},status_code=status_code)(scope,receive,wrapped_send)
        try:
            if scope['method'] in ('POST','PUT','PATCH'):
                body = bytearray()
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    body.extend(message.get('body',b''))
                    if len(body) > 65536:
                        return await error('request_too_large','Maximum request size is 64 KiB.',413)
                    if not message.get('more_body',False):
                        break
                original_receive = receive
                delivered = False
                async def replay():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {'type':'http.request','body':bytes(body),'more_body':False}
                    return await original_receive()
                receive = replay
                if path.endswith(('/generate','/swap','/login','/register')):
                    # Trust only ASGI client identity. Configure proxy trust explicitly at deployment.
                    client = (scope.get('client') or ('unknown',0))[0]
                    if await run_in_threadpool(limited,client,path):
                        return await error('rate_limited','Too many requests. Try again in one minute.',429)
            await self.app(scope,receive,wrapped_send)
        except Exception as exc:
            log.error('request_failed',extra={'request_id':request_id,'error_type':type(exc).__name__})
            if not started:
                await error('service_unavailable','The service is temporarily unavailable.',503)
        finally:
            route = scope.get('route')
            log.info('request',extra={'request_id':request_id,'method':scope['method'],
                'endpoint':getattr(route,'path','unmatched'),'status':status,
                'duration_ms':round((time.monotonic()-start)*1000,1)})
