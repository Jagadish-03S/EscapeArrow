from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DATABASE_URL
class Base(DeclarativeBase): pass
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={'check_same_thread':False, 'timeout':30} if DATABASE_URL.startswith('sqlite') else {})
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_setup(conn, record):
        conn.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine, expire_on_commit=False)
def db():
    with Session() as s:
        # Serialize local writes too; PostgreSQL uses row locks in auth dependency.
        if DATABASE_URL.startswith('sqlite'):
            s.connection().exec_driver_sql('BEGIN IMMEDIATE')
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
