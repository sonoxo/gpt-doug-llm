import sqlite3

conn = sqlite3.connect('example.db')
conn.row_factory = sqlite3.Row

def create_table():
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)')
    conn.commit()

create_table()