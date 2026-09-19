import os,secrets,time,re
from urllib.parse import urlencode
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import bcrypt,httpx
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from sqlalchemy import select,or_,delete
from sqlalchemy.exc import IntegrityError
from ..db import db
from ..models import User,Challenge,SessionToken,OAuth
from ..security import contact,password_hash,digest,rate,new_session,current
from ..providers import send_code
from ..config import OWNER_EMAIL,OWNER_PHONE,PUBLIC_URL
router=APIRouter(prefix='/api/auth',tags=['Accounts'])
class Start(BaseModel):
    purpose:str='login'
    contact:str
    password:str=''
    name:str=Field(default='',max_length=80)
    username:str=Field(default='',max_length=24)
    timezone:str='UTC'
class Verify(BaseModel):
    challenge_id:str
    code:str=Field(pattern=r'^\d{4}$')
    password:str=''
class GooglePoll(BaseModel):
    state:str
    key:str

def find(s,c):return s.scalar(select(User).where(or_(User.email==c,User.phone==c)))
def owner_contact(c):return c in (OWNER_EMAIL.lower(),OWNER_PHONE)
def issue(s,c,purpose,payload):
    # Invalidate older challenges, including those issued through another client.
    for old in s.scalars(select(Challenge).where(Challenge.contact==c,Challenge.used==False)):
        old.used=True
    code=f'{secrets.randbelow(10000):04d}';ch=Challenge(contact=c,purpose=purpose,payload=payload,digest=digest(code),expires=time.time()+300)
    try:send_code(c,code)
    except Exception:raise HTTPException(503,'Code delivery failed. Check provider configuration or try later.')
    s.add(ch);s.flush()
    return {'challenge_id':ch.id,'message':'Code sent. It expires in five minutes.'}

@router.post('/start')
def start(b:Start,request:Request,s=Depends(db)):
    rate(s,'ip:'+request.client.host,30)
    c=contact(b.contact);rate(s,'contact:'+c,5)
    u=find(s,c)
    if b.purpose=='signup':
        if owner_contact(c):raise HTTPException(409,'This contact is reserved for the project owner')
        if u:raise HTTPException(409,'Account already exists. Sign in instead.')
        if not re.fullmatch(r'[a-zA-Z0-9_]{3,24}',b.username):raise HTTPException(400,'Username needs 3-24 letters, numbers or underscores')
        if not b.name.strip():raise HTTPException(400,'Name is required')
        if s.scalar(select(User).where(User.username==b.username.lower())):raise HTTPException(409,'Username is taken')
        try:ZoneInfo(b.timezone)
        except (ZoneInfoNotFoundError,ValueError):raise HTTPException(400,'Invalid time zone')
        payload={'name':b.name.strip(),'username':b.username.lower(),'password':password_hash(b.password),'timezone':b.timezone}
    elif b.purpose in ('login','otp','reset'):
        if not u:raise HTTPException(404,'No user found')
        if b.purpose=='login' and (not u.password or len(b.password.encode())>72 or not bcrypt.checkpw(b.password.encode(),u.password.encode())):raise HTTPException(401,'Incorrect password')
        payload={'user_id':u.id}
    else:raise HTTPException(400,'Invalid account operation')
    return issue(s,c,b.purpose,payload)

@router.post('/verify')
def verify(b:Verify,request:Request,s=Depends(db)):
    rate(s,'verify:'+request.client.host,40)
    ch=s.scalar(select(Challenge).where(Challenge.id==b.challenge_id).with_for_update())
    if not ch or ch.used or ch.expires<time.time() or ch.tries>=5:raise HTTPException(400,'Code expired or exhausted. Request another code.')
    if not secrets.compare_digest(ch.digest,digest(b.code)):
        ch.tries+=1;s.commit();raise HTTPException(400,'Incorrect code')
    if ch.purpose=='link':raise HTTPException(400,'Verify linked contacts from your profile')
    if ch.purpose=='signup':
        if find(s,ch.contact):raise HTTPException(409,'Account already exists')
        uid=str(secrets.randbelow(900000000000)+100000000000)
        while s.get(User,uid):uid=str(secrets.randbelow(900000000000)+100000000000)
        u=User(id=uid,email=ch.contact if '@' in ch.contact else None,phone=ch.contact if '@' not in ch.contact else None,**ch.payload)
        s.add(u)
        try:s.flush()
        except IntegrityError:s.rollback();raise HTTPException(409,'Username or contact is taken; sign up again')
    elif ch.purpose=='google':
        u=find(s,ch.contact)
        if not u:
            uid=str(secrets.randbelow(900000000000)+100000000000)
            while s.get(User,uid):uid=str(secrets.randbelow(900000000000)+100000000000)
            u=User(id=uid,name=ch.payload.get('name','Player'),email=ch.contact,username='player_'+secrets.token_hex(5))
            s.add(u);s.flush()
    else:
        u=s.get(User,ch.payload['user_id'])
        if not u:raise HTTPException(404,'No user found')
        if ch.purpose=='reset':
            u.password=password_hash(b.password)
            s.execute(delete(SessionToken).where(SessionToken.user_id==u.id))
    ch.used=True
    return new_session(s,u)

@router.post('/logout')
def logout(request:Request,u=Depends(current),s=Depends(db)):
    s.execute(delete(SessionToken).where(SessionToken.token==digest(request.headers['authorization'][7:])))
    return {'ok':True}

@router.post('/guest')
def guest(request:Request,s=Depends(db)):
    rate(s,'guest:'+request.client.host,20)
    uid=str(secrets.randbelow(900000000000)+100000000000)
    while s.get(User,uid):uid=str(secrets.randbelow(900000000000)+100000000000)
    u=User(id=uid,username='guest_'+secrets.token_hex(5),name='Player')
    s.add(u);s.flush()
    return new_session(s,u)

@router.post('/google/start')
def google_start(request:Request,s=Depends(db)):
    rate(s,'google:'+request.client.host,10)
    client=os.getenv('GOOGLE_CLIENT_ID')
    if not client:raise HTTPException(503,'Google sign-in is not configured. Use email or phone.')
    state=secrets.token_urlsafe(32);key=secrets.token_urlsafe(32)
    s.add(OAuth(state=state,poll_hash=digest(key),expires=time.time()+600))
    return {'state':state,'key':key,'url':'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':client,'redirect_uri':PUBLIC_URL+'/api/auth/google/callback','response_type':'code','scope':'openid email profile','state':state,'prompt':'select_account'})}

@router.get('/google/callback',response_class=HTMLResponse)
def google_callback(state:str='',code:str='',s=Depends(db)):
    flow=s.scalar(select(OAuth).where(OAuth.state==state).with_for_update())
    if not flow or flow.used or flow.expires<time.time():raise HTTPException(400,'Expired Google sign-in')
    flow.used=True
    try:
        r=httpx.post('https://oauth2.googleapis.com/token',data={'code':code,'client_id':os.environ['GOOGLE_CLIENT_ID'],'client_secret':os.environ['GOOGLE_CLIENT_SECRET'],'redirect_uri':PUBLIC_URL+'/api/auth/google/callback','grant_type':'authorization_code'},timeout=15);r.raise_for_status()
        info=httpx.get('https://openidconnect.googleapis.com/v1/userinfo',headers={'Authorization':'Bearer '+r.json()['access_token']},timeout=15);info.raise_for_status();p=info.json()
        if not p.get('email_verified'):raise ValueError('Unverified email')
        c=contact(p['email']);rate(s,'contact:'+c,5)
        result=issue(s,c,'google',{'name':p.get('name','Player')[:80]});flow.challenge=result['challenge_id']
    except Exception:raise HTTPException(400,'Google sign-in failed; start again')
    return '<h1>Return to EscapeArrow</h1><p>Enter the four-digit code sent to your Google email.</p>'

@router.post('/google/poll')
def google_poll(b:GooglePoll,s=Depends(db)):
    flow=s.get(OAuth,b.state)
    if not flow or flow.expires<time.time() or not secrets.compare_digest(flow.poll_hash,digest(b.key)):raise HTTPException(400,'Expired sign-in')
    return {'challenge_id':flow.challenge or None}

class LinkContact(BaseModel):contact:str
@router.post('/contact/start')
def contact_start(b:LinkContact,request:Request,u=Depends(current),s=Depends(db)):
    c=contact(b.contact);rate(s,'contact:'+c,5)
    if owner_contact(c):raise HTTPException(409,'This contact is reserved for the project owner')
    # rate() commits counters; re-lock the account before its subsequent operations.
    u=s.scalar(select(User).where(User.id==u.id).with_for_update())
    if find(s,c):raise HTTPException(409,'Contact already belongs to an account')
    return issue(s,c,'link',{'user_id':u.id})
@router.post('/contact/verify')
def contact_verify(b:Verify,u=Depends(current),s=Depends(db)):
    ch=s.scalar(select(Challenge).where(Challenge.id==b.challenge_id).with_for_update())
    if not ch or ch.purpose!='link' or ch.payload.get('user_id')!=u.id or ch.used or ch.expires<time.time() or ch.tries>=5:raise HTTPException(400,'Invalid or expired code')
    if not secrets.compare_digest(ch.digest,digest(b.code)):
        ch.tries+=1;s.commit();raise HTTPException(400,'Incorrect code')
    if find(s,ch.contact):raise HTTPException(409,'Contact is already registered')
    if '@' in ch.contact:u.email=ch.contact
    else:u.phone=ch.contact
    ch.used=True
    return {'ok':True}
