import time
import secrets
from datetime import datetime,timezone,timedelta
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy import select,func,case
from ..db import db
from ..config import OWNER_EMAIL,OWNER_PASSWORD,OWNER_PHONE,OWNER_USER_ID
from ..security import admin,contact,new_session,profile
from ..models import User,Attempt,Review,Reward
router=APIRouter(prefix='/api/admin',tags=['Administrator'])
class OwnerLogin(BaseModel):
    contact:str
    password:str
@router.post('/login')
def owner_login(b:OwnerLogin,s=Depends(db)):
    c=contact(b.contact)
    if not secrets.compare_digest(c,OWNER_EMAIL.lower()) and not secrets.compare_digest(c,OWNER_PHONE):
        raise HTTPException(401,'Invalid owner credentials')
    if not secrets.compare_digest(b.password,OWNER_PASSWORD):raise HTTPException(401,'Invalid owner credentials')
    u=s.get(User,OWNER_USER_ID)
    if not u:
        u=User(id=OWNER_USER_ID,username='owner',name='Project Owner',email=OWNER_EMAIL.lower(),phone=OWNER_PHONE,admin=True)
        s.add(u);s.flush()
    return new_session(s,u)
@router.get('/overview')
def overview(a=Depends(admin),s=Depends(db)):
    total=s.scalar(select(func.count(User.id)))
    online=s.scalar(select(func.count(User.id)).where(User.seen>time.time()-90))
    completed=s.scalar(select(func.count(Attempt.id)).where(Attempt.status=='complete'))
    avg=s.scalar(select(func.avg(Attempt.seconds)).where(Attempt.status=='complete')) or 0
    avgstars=s.scalar(select(func.avg(Attempt.stars)).where(Attempt.status=='complete')) or 0
    avg_review=s.scalar(select(func.avg(Review.stars))) or 0
    states=dict(s.execute(select(Attempt.status,func.count()).group_by(Attempt.status)).all())
    tiers=[]
    for label,lo,hi in [('easy',1,10),('moderate',11,30),('hard',31,1000000)]:
        count,seconds,stars=s.execute(select(func.count(),func.avg(Attempt.seconds),func.avg(Attempt.stars)).where(Attempt.status=='complete',Attempt.level>=lo,Attempt.level<=hi)).one()
        tiers.append({'tier':label,'completions':count,'seconds':round(seconds or 0,1),'stars':round(stars or 0,1)})
    days=[]
    for n in range(6,-1,-1):
        d=(datetime.now(timezone.utc)-timedelta(days=n)).replace(hour=0,minute=0,second=0,microsecond=0)
        count=s.scalar(select(func.count()).select_from(Attempt).where(Attempt.started>=d.timestamp(),Attempt.started<d.timestamp()+86400))
        days.append({'day':d.strftime('%d %b'),'attempts':count})
    return {'players':total,'online':online,'completed':completed,'avg_seconds':round(avg,1),'avg_stars':round(avgstars,2),'avg_review':round(avg_review,2),'states':states,'tiers':tiers,'days':days}
@router.get('/players')
def players(q:str='',offset:int=0,a=Depends(admin),s=Depends(db)):
    query=select(User).order_by(User.created.desc()).offset(max(0,offset)).limit(50)
    if q:query=query.where((User.username.contains(q[:80]))|(User.id==q)|(User.email.contains(q[:80])))
    return [profile(u)|{'created':u.created,'seen':u.seen} for u in s.scalars(query)]
@router.get('/players/{id}')
def player(id:str,a=Depends(admin),s=Depends(db)):
    u=s.get(User,id)
    if not u:raise HTTPException(404,'Player not found')
    attempts=[{'level':x.level,'status':x.status,'seconds':x.seconds,'stars':x.stars,'collisions':x.collisions,'started':x.started} for x in s.scalars(select(Attempt).where(Attempt.user_id==id).order_by(Attempt.started.desc()).limit(200))]
    return {'profile':profile(u),'attempts':attempts}
@router.get('/reviews')
def reviews(offset:int=0,a=Depends(admin),s=Depends(db)):
    rows=s.execute(select(Review,User.username).join(User,Review.user_id==User.id).order_by(Review.updated.desc()).offset(max(0,offset)).limit(50))
    return [{'user_id':r.user_id,'username':name,'stars':r.stars,'text':r.text,'updated':r.updated} for r,name in rows]
