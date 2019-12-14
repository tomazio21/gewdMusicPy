import sqlite3

def createDB():
    conn = sqlite3.connect('gewdMusic.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE music (id INTEGER PRIMARY KEY, link TEXT UNIQUE, user text, date_posted INTEGER, artist TEXT, album TEXT, trackname TEXT)''')
    conn.commit()
    conn.close()

def createMusicRecord(musicRecords):
    insertStmt = 'INSERT INTO music (link, user, date_posted, artist, album, trackname) VALUES (?,?,?,?,?,?)'
    conn = sqlite3.connect('gewdMusic.db')
    c = conn.cursor()
    c.executemany(insertStmt, musicRecords)
    conn.commit()
    conn.close()

def getMusicRecords(column, direction):
    conn = sqlite3.connect('gewdMusic.db')
    c = conn.cursor()
    c.execute('SELECT * FROM music ORDER BY {0} {1}'.format(column, direction))
    records = c.fetchall()
    return records

def getMusicLinks():
    conn = sqlite3.connect('gewdMusic.db')
    c = conn.cursor()
    c.execute('SELECT link FROM music')
    records = c.fetchall()
    return records
