"""Initialize the EscapeArrow database."""
import argparse
from app.db import Base,engine
p=argparse.ArgumentParser();p.add_argument('command',choices=['init-db']);a=p.parse_args()
Base.metadata.create_all(engine)
