from contextlib import asynccontextmanager
from pathlib import Path
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .db import Base,engine
from . import models
from .routes import auth,play,profile,admin
ROOT=Path(__file__).resolve().parents[2]
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield
app=FastAPI(title='EscapeArrow API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('ALLOWED_ORIGINS','http://localhost:8000,https://localhost,http://localhost').split(','),allow_methods=['GET','POST','PATCH'],allow_headers=['Authorization','Content-Type'])
@app.middleware('http')
async def headers(request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    if request.url.path.startswith('/api'):response.headers['Cache-Control']='no-store'
    return response
@app.get('/health')
def health():return {'status':'ok'}
for r in (auth,play,profile,admin):app.include_router(r.router)
app.mount('/admin',StaticFiles(directory=ROOT/'admin',html=True),name='admin')
app.mount('/',StaticFiles(directory=ROOT/'client',html=True),name='player')
