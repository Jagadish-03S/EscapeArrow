import hashlib,hmac,secrets,time,re
import bcrypt
from fastapi import Depends,HTTPException,Header
from sqlalchemy import select
from .config import OWNER_USER_ID,SECRET
from .db import db
from .models import User,SessionToken,Rate

def digest(v):return hmac.new(SECRET.encode(),v.encode(),hashlib.sha256).hexdigest()
def password_hash(v):
    if len(v)<8 or len(v.encode())>72:raise HTTPException(400,'Password must be 8 to 72 UTF-8 bytes')
    return bcrypt.hashpw(v.encode(),bcrypt.gensalt()).decode()
def contact(v):
    v=v.strip().lower()
    if '@' in v:
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v) or len(v)>254:raise HTTPException(400,'Enter a valid email')
    elif not re.fullmatch(r'\+[1-9]\d{7,14}',v):raise HTTPException(400,'Use phone format +919876543210')
    return v

def rate(s,key,limit=10,seconds=600):
    k=digest(key); r=s.get(Rate,k); now=time.time()
    if r and now-r.start<seconds:
        if r.count>=limit:raise HTTPException(429,'Too many attempts. Please try again later.')
        r.count+=1
    else:
        if r:r.start=now;r.count=1
        else:s.add(Rate(key=k,start=now,count=1))
    s.commit() # persist failed authentication counters too

def new_session(s,u):
    token=secrets.token_urlsafe(32)
    s.add(SessionToken(token=digest(token),user_id=u.id,expires=time.time()+86400*7))
    return {'token':token,'user':profile(u)}
def profile(u):
    return {k:getattr(u,k) for k in ('id','username','name','email','phone','gender','avatar','timezone','admin','coins','diamonds','unlocked','streak','last_play','daily_claim')}

def current(authorization:str=Header(default=''),s=Depends(db)):
    if not authorization.startswith('Bearer '):raise HTTPException(401,'Please sign in')
    t=s.get(SessionToken,digest(authorization[7:]))
    if not t or t.expires<time.time():raise HTTPException(401,'Session expired. Sign in again.')
    u=s.scalar(select(User).where(User.id==t.user_id).with_for_update())
    if not u:raise HTTPException(401,'Account unavailable')
    return u

def admin(u=Depends(current)):
    if u.id != OWNER_USER_ID:raise HTTPException(403,'Administrator access required')
    return u
