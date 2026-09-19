import time, secrets
from sqlalchemy import String, Integer, Float, Boolean, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
class User(Base):
    __tablename__='users'
    id: Mapped[str]=mapped_column(String(12),primary_key=True)
    username: Mapped[str]=mapped_column(String(24),unique=True)
    name: Mapped[str]=mapped_column(String(80))
    email: Mapped[str|None]=mapped_column(String(254),unique=True,nullable=True)
    phone: Mapped[str|None]=mapped_column(String(20),unique=True,nullable=True)
    password: Mapped[str]=mapped_column(String(128),default='')
    gender: Mapped[str]=mapped_column(String(30),default='Prefer not to say')
    avatar: Mapped[str]=mapped_column(String,default='')
    timezone: Mapped[str]=mapped_column(String(64),default='UTC')
    admin: Mapped[bool]=mapped_column(Boolean,default=False)
    coins: Mapped[int]=mapped_column(Integer,default=0)
    diamonds: Mapped[int]=mapped_column(Integer,default=0)
    unlocked: Mapped[int]=mapped_column(Integer,default=1)
    streak: Mapped[int]=mapped_column(Integer,default=0)
    last_play: Mapped[str]=mapped_column(String(10),default='')
    daily_claim: Mapped[str]=mapped_column(String(10),default='')
    created: Mapped[float]=mapped_column(Float,default=time.time)
    seen: Mapped[float]=mapped_column(Float,default=time.time)
class SessionToken(Base):
    __tablename__='sessions'
    token: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'))
    expires: Mapped[float]=mapped_column(Float)
class Challenge(Base):
    __tablename__='challenges'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=lambda:secrets.token_urlsafe(24))
    contact: Mapped[str]=mapped_column(String(254),index=True)
    purpose: Mapped[str]=mapped_column(String(20))
    digest: Mapped[str]=mapped_column(String(64))
    payload: Mapped[dict]=mapped_column(JSON,default=dict)
    tries: Mapped[int]=mapped_column(Integer,default=0)
    expires: Mapped[float]=mapped_column(Float)
    created: Mapped[float]=mapped_column(Float,default=time.time)
    used: Mapped[bool]=mapped_column(Boolean,default=False)
class Rate(Base):
    __tablename__='rate_limits'
    key: Mapped[str]=mapped_column(String(64),primary_key=True)
    start: Mapped[float]=mapped_column(Float)
    count: Mapped[int]=mapped_column(Integer,default=1)
class Attempt(Base):
    __tablename__='attempts'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=lambda:secrets.token_urlsafe(18))
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    level: Mapped[int]=mapped_column(Integer)
    board: Mapped[dict]=mapped_column(JSON)
    lives: Mapped[int]=mapped_column(Integer,default=5)
    collisions: Mapped[int]=mapped_column(Integer,default=0)
    purchases: Mapped[int]=mapped_column(Integer,default=0)
    status: Mapped[str]=mapped_column(String(20),default='playing')
    started: Mapped[float]=mapped_column(Float,default=time.time)
    finished: Mapped[float|None]=mapped_column(Float,nullable=True)
    seconds: Mapped[float]=mapped_column(Float,default=0)
    stars: Mapped[float]=mapped_column(Float,default=0)
    reward: Mapped[str]=mapped_column(String(20),default='pending')
    events: Mapped[list]=mapped_column(JSON,default=list)
class Reward(Base):
    __tablename__='rewards'
    __table_args__=(UniqueConstraint('user_id','key'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'))
    key: Mapped[str]=mapped_column(String(100))
    coins: Mapped[int]=mapped_column(Integer,default=0)
    diamonds: Mapped[int]=mapped_column(Integer,default=0)
    created: Mapped[float]=mapped_column(Float,default=time.time)
class Review(Base):
    __tablename__='reviews'
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    stars: Mapped[int]=mapped_column(Integer)
    text: Mapped[str]=mapped_column(String(2000),default='')
    updated: Mapped[float]=mapped_column(Float,default=time.time)
class OAuth(Base):
    __tablename__='oauth_flows'
    state: Mapped[str]=mapped_column(String(64),primary_key=True)
    poll_hash: Mapped[str]=mapped_column(String(64))
    expires: Mapped[float]=mapped_column(Float)
    challenge: Mapped[str]=mapped_column(String(64),default='')
    used: Mapped[bool]=mapped_column(Boolean,default=False)
