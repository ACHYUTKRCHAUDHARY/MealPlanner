import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.errors import DomainError
from app.core.middleware import RequestMiddleware, JSONFormatter
from app.db.session import session, engine
from app.api import auth, users, plans

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger('plateful')
logger.handlers = [handler]
logger.setLevel(logging.INFO)
logger.propagate = False


@asynccontextmanager
async def lifespan(app):
    settings()  # Fail early on missing database URL, JWT secret, unsafe production CORS.
    yield
    engine().dispose()


app = FastAPI(title='Plateful API', version='2.0.0',lifespan=lifespan)
app.add_middleware(RequestMiddleware)
app.add_middleware(CORSMiddleware,allow_origins=settings().origins,
    allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],
    allow_headers=['Authorization','Content-Type'],expose_headers=['X-Request-ID'])
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(plans.router)


def response(request,code,message,status):
    return JSONResponse({'error':{'code':code,'message':message,'request_id':getattr(request.state,'request_id',None)}},status_code=status)


@app.exception_handler(DomainError)
async def domain_error(request: Request,error: DomainError):
    return response(request,error.code,error.message,error.status)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request,error: RequestValidationError):
    fields = ', '.join('.'.join(map(str,e['loc'][1:])) for e in error.errors())
    return response(request,'validation_error','Check the following fields: '+fields,422)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request,error: SQLAlchemyError):
    logger.error('database_error',extra={'request_id':request.state.request_id,'error_type':type(error).__name__})
    return response(request,'database_unavailable','Database temporarily unavailable. Please retry.',503)


@app.exception_handler(HTTPException)
async def http_error(request: Request,error: HTTPException):
    return response(request,'http_error',str(error.detail),error.status_code)


@app.get('/health')
def health(db: Session = Depends(session)):
    db.execute(text('SELECT 1'))
    db.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
    if db.bind.dialect.name == 'postgresql':
        version = db.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'")).scalar_one_or_none()
        if not version:
            raise DomainError('vector_unavailable','Vector extension is missing.',503)
    return {'status':'UP'}
