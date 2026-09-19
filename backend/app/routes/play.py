import time
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from ..db import db
from ..models import Attempt,Reward
from ..security import current,profile
from ..game import generate,blocked,rating,payout,tier
router=APIRouter(prefix='/api',tags=['Game and rewards'])
class Start(BaseModel):level:int=Field(ge=1,le=1000000)
class Move(BaseModel):arrow_id:int;request_id:str=Field(min_length=8,max_length=64)
class Collect(BaseModel):collect:bool

def today(u):return datetime.now(ZoneInfo(u.timezone)).date()
def grant(s,u,key,coins=0,diamonds=0):
    if s.scalar(select(Reward).where(Reward.user_id==u.id,Reward.key==key)):return False
    s.add(Reward(user_id=u.id,key=key,coins=coins,diamonds=diamonds));u.coins+=coins;u.diamonds+=diamonds
    s.flush();return True

def public(a):
    return {k:getattr(a,k) for k in ('id','level','board','lives','collisions','purchases','status','started','seconds','stars','reward')}|{'tier':tier(a.level),'server_now':time.time(),'payout':payout(a.level,a.seconds)}
def owned(s,u,id):
    a=s.get(Attempt,id)
    if not a or a.user_id!=u.id:raise HTTPException(404,'Attempt not found')
    return a

def expire(a):
    if a.status in ('playing','exhausted') and time.time()-a.started>86400:
        a.status='abandoned';a.finished=time.time();a.seconds=a.finished-a.started

def register_day(s,u):
    d=today(u);last=u.last_play
    if last==str(d):return
    # Never move rewards backwards if time zone or clock changes.
    if last and last>str(d):return
    u.streak=u.streak+1 if last==str(d-timedelta(days=1)) else 1
    u.last_play=str(d)
    if u.streak%7==0:grant(s,u,'streak:'+str(d),50,20)

@router.get('/me')
def me(u=Depends(current),s=Depends(db)):
    d=today(u)
    p=profile(u)
    if u.last_play and u.last_play<str(d-timedelta(days=1)):p['streak']=0
    return p|{'local_day':str(d),'daily_available':u.last_play==str(d) and u.daily_claim!=str(d)}

@router.post('/heartbeat')
def heartbeat(u=Depends(current)):
    u.seen=time.time();return {'ok':True}

@router.post('/daily/claim')
def daily(u=Depends(current),s=Depends(db)):
    d=str(today(u))
    if u.last_play!=d:raise HTTPException(400,'Start a level to claim today’s coins')
    grant(s,u,'daily:'+d,2);u.daily_claim=d
    return profile(u)

@router.get('/levels')
def levels(offset:int=0,u=Depends(current),s=Depends(db)):
    offset=max(0,min(offset,1000000))
    attempts=list(s.scalars(select(Attempt).where(Attempt.user_id==u.id,Attempt.level>offset,Attempt.level<=offset+30,Attempt.status=='complete')))
    return [{'level':n,'tier':tier(n),'unlocked':n<=u.unlocked,'best_stars':max([a.stars for a in attempts if a.level==n],default=0),'best_seconds':min([a.seconds for a in attempts if a.level==n],default=None)} for n in range(offset+1,offset+31)]

@router.get('/attempts/active')
def active(u=Depends(current),s=Depends(db)):
    a=s.scalar(select(Attempt).where(Attempt.user_id==u.id,Attempt.status.in_(['playing','exhausted'])).order_by(Attempt.started.desc()))
    if a:expire(a)
    return public(a) if a and a.status!='abandoned' else None

@router.post('/attempts')
def start(b:Start,u=Depends(current),s=Depends(db)):
    if b.level>u.unlocked:raise HTTPException(403,'Complete the previous level with at least 1.5 stars')
    for old in s.scalars(select(Attempt).where(Attempt.user_id==u.id,Attempt.status.in_(['playing','exhausted']))):
        old.status='abandoned';old.finished=time.time();old.seconds=old.finished-old.started
    register_day(s,u);u.seen=time.time()
    a=Attempt(user_id=u.id,level=b.level,board=generate(b.level));s.add(a);s.flush();return public(a)

@router.post('/attempts/{id}/move')
def move(id:str,b:Move,u=Depends(current),s=Depends(db)):
    a=owned(s,u,id);expire(a)
    if any(e.get('request_id')==b.request_id for e in a.events):return public(a)|{'duplicate':True}
    if a.status!='playing':raise HTTPException(409,'This attempt cannot accept moves')
    arrows=a.board['arrows'];arrow=next((x for x in arrows if x['id']==b.arrow_id),None)
    if not arrow:raise HTTPException(400,'Arrow already removed or not found')
    collision=blocked(arrow,arrows,a.board['size']);now=time.time()
    if collision:
        a.collisions+=1;a.lives-=1
        if a.lives==0:a.status='exhausted'
    else:
        a.board={**a.board,'arrows':[x for x in arrows if x['id']!=arrow['id']]}
        if not a.board['arrows']:
            a.status='complete';a.finished=now;a.seconds=round(now-a.started,2);a.stars=rating(a.seconds,a.collisions,a.level)
            if a.stars>=1.5:u.unlocked=max(u.unlocked,a.level+1)
    a.events=a.events+[{'request_id':b.request_id,'arrow':b.arrow_id,'collision':collision,'time':now}]
    u.seen=now
    return public(a)|{'collision':collision}

@router.post('/attempts/{id}/life')
def life(id:str,u=Depends(current),s=Depends(db)):
    a=owned(s,u,id);expire(a)
    if a.status!='exhausted' or a.purchases>=3:raise HTTPException(400,'No extra life available')
    price=[10,25,35][a.purchases]
    if u.coins<price:raise HTTPException(400,'Not enough coins. Restart for five free lives.')
    grant(s,u,'life:'+id+':'+str(a.purchases),-price);a.purchases+=1;a.lives=1;a.status='playing'
    return public(a)

@router.post('/attempts/{id}/reward')
def reward(id:str,b:Collect,u=Depends(current),s=Depends(db)):
    a=owned(s,u,id)
    if a.status!='complete':raise HTTPException(400,'Finish the level first')
    if a.reward=='pending':
        a.reward='collected' if b.collect else 'declined'
        if b.collect:grant(s,u,'level:'+id,**payout(a.level,a.seconds))
    return profile(u)

@router.post('/attempts/{id}/exit')
def leave(id:str,u=Depends(current),s=Depends(db)):
    a=owned(s,u,id)
    if a.status in ('playing','exhausted'):
        a.status='abandoned';a.finished=time.time();a.seconds=a.finished-a.started
    return {'ok':True}

@router.get('/history')
def history(u=Depends(current),s=Depends(db)):
    return [public(a) for a in s.scalars(select(Attempt).where(Attempt.user_id==u.id).order_by(Attempt.started.desc()).limit(100))]

@router.get('/wallet')
def wallet(u=Depends(current),s=Depends(db)):
    return [{'key':r.key,'coins':r.coins,'diamonds':r.diamonds,'created':r.created} for r in s.scalars(select(Reward).where(Reward.user_id==u.id).order_by(Reward.created.desc()).limit(100))]
