#!/usr/bin/env python3
from trawler import db

print('(Re)Creating database...')
db.drop_all()
db.create_all()
print('Done.')