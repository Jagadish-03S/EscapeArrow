import os,tempfile,time
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
os.environ['OTP_MODE']='console'
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import Session
from app.models import User,Attempt,Challenge,Reward
from app.game import generate,blocked,rating
from app.security import new_session
from app.routes.play import register_day,today
from datetime import timedelta
import pytest
@pytest.fixture
def client():
    with TestClient(app) as c:yield c
@pytest.fixture
def player(client):
    import secrets
    with Session() as s:
        u=User(id=str(secrets.randbelow(900000000000)+100000000000),username='u'+secrets.token_hex(5),name='Tester',email=secrets.token_hex(5)+'@example.com',coins=100)
        s.add(u);s.flush();token=new_session(s,u)['token'];s.commit();uid=u.id
    return {'Authorization':'Bearer '+token},uid

def test_generator_solvable():
    for level in [1,5,10,11,20,30,31,80,1000]:
        for seed in range(20):
            b=generate(level,seed);arrows=b['arrows'][:]
            assert len({(a['x'],a['y']) for a in arrows})==len(arrows)
            while arrows:
                legal=[a for a in arrows if not blocked(a,arrows,b['size'])]
                assert legal, (level,seed)
                arrows.remove(legal[0])
def solve(c,h,a):
    import uuid
    while a['board']['arrows']:
        b=a['board'];x=next(x for x in b['arrows'] if not blocked(x,b['arrows'],b['size']))
        r=c.post('/api/attempts/'+a['id']+'/move',headers=h,json={'arrow_id':x['id'],'request_id':str(uuid.uuid4())});assert r.status_code==200,r.text;a=r.json()
    return a

def test_completion_unlock_and_idempotent_reward(client,player):
    h,uid=player
    assert client.post('/api/attempts',headers=h,json={'level':2}).status_code==403
    a=client.post('/api/attempts',headers=h,json={'level':1}).json();a=solve(client,h,a)
    assert a['stars']==5 and a['status']=='complete'
    for _ in range(2):r=client.post('/api/attempts/'+a['id']+'/reward',headers=h,json={'collect':True})
    assert r.json()['coins']==105 and r.json()['diamonds']==3 and r.json()['unlocked']==2

def test_five_collisions_prices_duplicate_and_limit(client,player):
    h,uid=player;a=client.post('/api/attempts',headers=h,json={'level':1}).json()
    with Session() as s:
        row=s.get(Attempt,a['id']);row.board={'size':3,'arrows':[{'id':0,'x':0,'y':0,'dx':1,'dy':0},{'id':1,'x':1,'y':0,'dx':0,'dy':1}]};s.commit()
    for n in range(5):
        r=client.post('/api/attempts/'+a['id']+'/move',headers=h,json={'arrow_id':0,'request_id':'request-'+str(n)});assert r.status_code==200
    assert r.json()['lives']==0 and r.json()['status']=='exhausted'
    r=client.post('/api/attempts/'+a['id']+'/move',headers=h,json={'arrow_id':0,'request_id':'request-4'});assert r.json()['collisions']==5
    for i in range(3):
        assert client.post('/api/attempts/'+a['id']+'/life',headers=h).status_code==200
        client.post('/api/attempts/'+a['id']+'/move',headers=h,json={'arrow_id':0,'request_id':'purchased-'+str(i)})
    assert client.post('/api/attempts/'+a['id']+'/life',headers=h).status_code==400
    assert client.get('/api/me',headers=h).json()['coins']==30

def test_low_rating_blocks_unlock_and_decline(client,player):
    h,uid=player;a=client.post('/api/attempts',headers=h,json={'level':1}).json()
    with Session() as s:r=s.get(Attempt,a['id']);r.started=time.time()-400;s.commit()
    a=solve(client,h,a);assert a['stars']<1.5
    assert client.get('/api/me',headers=h).json()['unlocked']==1
    client.post('/api/attempts/'+a['id']+'/reward',headers=h,json={'collect':False})
    r=client.post('/api/attempts/'+a['id']+'/reward',headers=h,json={'collect':True});assert r.json()['coins']==100

def test_daily_and_streak(client,player):
    h,uid=player
    assert client.post('/api/daily/claim',headers=h).status_code==400
    with Session() as s:
        u=s.get(User,uid);u.streak=6;u.last_play=str(today(u)-timedelta(days=1));s.commit()
    client.post('/api/attempts',headers=h,json={'level':1})
    for _ in range(2):r=client.post('/api/daily/claim',headers=h)
    assert r.json()['coins']==152 and r.json()['diamonds']==20 and r.json()['streak']==7
    with Session() as s:
        u=s.get(User,uid);u.last_play=str(today(u)-timedelta(days=2));register_day(s,u);assert u.streak==1;s.commit()

def test_access_control(client,player):
    h,uid=player;assert client.get('/api/admin/players',headers=h).status_code==403
    assert client.get('/api/me').status_code==401
    assert client.post('/api/attempts/missing/life',headers=h).status_code==404

def test_guest_can_start_without_account(client):
    r=client.post('/api/auth/guest');assert r.status_code==200
    h={'Authorization':'Bearer '+r.json()['token']}
    assert r.json()['user']['name']=='Player'
    assert client.get('/api/levels',headers=h).status_code==200
    assert client.post('/api/attempts',headers=h,json={'level':1}).status_code==200

def test_only_configured_owner_can_access_admin(client,monkeypatch):
    monkeypatch.setattr('app.routes.admin.OWNER_EMAIL','owner@test.example')
    monkeypatch.setattr('app.routes.admin.OWNER_PHONE','+919876543210')
    monkeypatch.setattr('app.routes.admin.OWNER_PASSWORD','OwnerPass123')
    assert client.post('/api/admin/login',json={'contact':'player@test.example','password':'OwnerPass123'}).status_code==401
    r=client.post('/api/admin/login',json={'contact':'owner@test.example','password':'OwnerPass123'});assert r.status_code==200
    assert client.get('/api/admin/overview',headers={'Authorization':'Bearer '+r.json()['token']}).status_code==200

def test_otp_replay_and_fail_limit(client,monkeypatch):
    codes=[];monkeypatch.setattr('app.routes.auth.send_code',lambda c,v:codes.append(v))
    b={'purpose':'signup','contact':'signup@example.com','username':'signup_test','name':'New Player','password':'StrongPass123','timezone':'Asia/Kolkata'}
    r=client.post('/api/auth/start',json=b);assert r.status_code==200,r.text;id=r.json()['challenge_id']
    r=client.post('/api/auth/verify',json={'challenge_id':id,'code':codes[-1]});assert r.status_code==200
    assert client.post('/api/auth/verify',json={'challenge_id':id,'code':codes[-1]}).status_code==400
    r=client.post('/api/auth/start',json={'purpose':'otp','contact':b['contact']});id=r.json()['challenge_id'];wrong='0000' if codes[-1]!='0000' else '0001'
    for _ in range(5):assert client.post('/api/auth/verify',json={'challenge_id':id,'code':wrong}).status_code==400
    assert client.post('/api/auth/verify',json={'challenge_id':id,'code':codes[-1]}).status_code==400

def test_reset_revokes_existing_sessions(client,monkeypatch):
    codes=[];monkeypatch.setattr('app.routes.auth.send_code',lambda c,v:codes.append(v))
    b={'purpose':'signup','contact':'reset@example.com','username':'reset_test','name':'Reset Player','password':'StrongPass123'}
    id=client.post('/api/auth/start',json=b).json()['challenge_id'];r=client.post('/api/auth/verify',json={'challenge_id':id,'code':codes[-1]}).json();h={'Authorization':'Bearer '+r['token']}
    id=client.post('/api/auth/start',json={'purpose':'reset','contact':b['contact']}).json()['challenge_id']
    assert client.post('/api/auth/verify',json={'challenge_id':id,'code':codes[-1],'password':'NewStrongPass123'}).status_code==200
    assert client.get('/api/me',headers=h).status_code==401

def test_linked_contact_requires_correct_route_and_owner(client,player,monkeypatch):
    h,uid=player;codes=[];monkeypatch.setattr('app.routes.auth.send_code',lambda c,v:codes.append(v))
    r=client.post('/api/auth/contact/start',headers=h,json={'contact':'+919999999999'});assert r.status_code==200,r.text
    body={'challenge_id':r.json()['challenge_id'],'code':codes[-1]}
    assert client.post('/api/auth/verify',json=body).status_code==400
    assert client.post('/api/auth/contact/verify',headers=h,json=body).status_code==200
    assert client.get('/api/me',headers=h).json()['phone']=='+919999999999'
