import urllib.request
import json
import sqlite3
import base64
from flask import Flask, render_template

app = Flask(__name__)
token = 'b5f28cd062ef01372cc0321234d8b0f5'

@app.route('/')
def loadData():
	limit = 100
	params = {'token': token, 'limit': limit}
	#data = getGroupmeData(params)
	musicRecords = appendSpotifyData([])
	return musicRecords	
	#return render_template('messages.html', messages=urls)


def getGroupmeData(params):
	spotifyUrl = 'https://open.spotify.com/'
	encodedParams = urllib.parse.urlencode(params)
	url = 'https://api.groupme.com/v3/groups/27335510/messages?%s' % encodedParams
	with urllib.request.urlopen(url) as f:
		response = f.read().decode('utf-8')
		parsed = json.loads(response)
		messages = parsed['response']['messages']
		data = []
		for mes in messages:
			text = mes['text']
			if isinstance(text, str):
				if spotifyUrl in text and 'playlist' not in text:
					messageData = [text, mes['name'], mes['created_at']]
					data.append(messageData)
		if len(messages) == params['limit']:
			params['before_id'] = messages[params['limit']-1]['id']
			data.extend(getGroupmeData(params))
		return data	

def appendSpotifyData(data):
	return getSpotifyToken()

def getSpotifyToken():
	tokenUrl = 'https://accounts.spotify.com/api/token'
	clientIdAndSecret = b'e3ec91da8dbb4f55934246932018cfa2:4cb59eece4664be88b2ebcd516e28771'
	b64encoded = base64.standard_b64encode(clientIdAndSecret)
	authHeaderValue = 'Basic ' + b64encoded.decode('ascii')
	req = urllib.request.Request(tokenUrl)
	req.add_header('Authorization', authHeaderValue)
	data = urllib.parse.urlencode({'grant_type': 'client_credentials'})
	data = data.encode('ascii')
	with urllib.request.urlopen(req, data) as f:
		print(f.read().decode('utf-8'))
		return 'we did it'

def createDB():
	conn = sqlite3.connect('gewdMusic.db')
	c = conn.cursor()
	c.execute('''CREATE TABLE music (id INTEGER PRIMARY KEY, link TEXT UNIQUE, name TEXT, date_posted INTEGER, artist TEXT, album TEXT, user text)''')
	conn.commit()
	conn.close()

def createMusicRecord(data):
	insertStmt = 'INSERT INTO music VALUES (?,?,?,?,?,?)'
	conn = sqlite3.connect('gewdMusic.db')
	c = conn.cursor()
	c.executemany(insertStmt, data)
