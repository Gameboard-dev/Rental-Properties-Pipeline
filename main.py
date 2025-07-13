from scripts.compile import compile_sql
from scripts.entity import render_entity_relationship_diagram
from scripts.load import load
from settings import SQL_PATH

training, testing, addresses = load()

'''
sql: str = compile_sql([training, testing])

with open(SQL_PATH, "w", encoding="utf-8") as file: 
    file.write(sql)

render_entity_relationship_diagram()
'''