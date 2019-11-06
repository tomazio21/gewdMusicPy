import urllib.request
import json
import sqlite3
import base64
import re
from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)
groupmeToken = ''
spotifyClientIdAndSecret = ''
ids = set()

with open('tokens.json') as f:
	tokens = json.load(f)
	groupmeToken = tokens['groupmeToken']	
	spotifyClientIdAndSecret = tokens['spotifyClientIdAndSecret']

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.fromtimestamp(value).strftime('%m/%d/%Y')

@app.route('/')
def loadData():
	limit = 100
	params = {'token': groupmeToken, 'limit': limit}
	#data = getGroupmeData(params)
	#musicRecords = appendSpotifyData(spotifyClientIdAndSecret, data)
	#createDB()
	#createMusicRecord(musicRecords)
	sort = sanitizeSort(request.args.get('sort'))
	direction = sanitizeDirection(request.args.get('direction'))
	records = getMusicRecords(sort, direction)
	model = buildModel(records)
	return render_template('music.html', model=model)

@app.route('/message', methods=['POST'])
def processMessage():
	body = request.json
	print(body)
	processMessage(body)
	return 'ingested'

columns = {
	'id':'id',
	'user':'user',
	'date':'date_posted',
	'artist':'artist',
	'album':'album',
	'track':'trackname'
}

def buildModel(records):
	routes = {}
	for k, v in columns.items():
		routes[k] = buildRoute(k)
	model = {}
	model['routes'] = routes
	model['records'] = records
	return model

def buildRoute(name):
	direction = 'asc'
	if name in request.url and direction in request.url:
		direction = 'desc'
	return '/?sort={}&direction={}'.format(name, direction)

def sanitizeSort(sort):
    return columns.get(sort, 'id')

def sanitizeDirection(direction):
	if direction == 'desc':
		return 'DESC'
	else:
		return 'ASC'
	
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
					url = trimForUrl(text)
					musicId = getSpotifyId(url)
					if musicId not in ids:
						ids.add(musicId)
						messageData = [url, mes['name'], mes['created_at']]
						data.append(messageData)
		if len(messages) == params['limit']:
			params['before_id'] = messages[params['limit']-1]['id']
			data.extend(getGroupmeData(params))
		return data	

def processMessage(message):	
	spotifyUrl = 'https://open.spotify.com/'
	text = message['text']
	if isinstance(text, str):
		if spotifyUrl in text and 'playlist' not in text:
			url = trimForUrl(text)
			musicId = getSpotifyId(url)
			messageData = [url, mes['name'], mes['created_at']]
			musicRecord = appendSpotifyData(spotifyClientIdAndSecret, [messageData])
			createMusicRecord(musicRecord)

def appendSpotifyData(token, groupmeData):
	dbRecords = []
	authToken = getSpotifyToken(token)
	for record in groupmeData:
		groupmeAndSpotifyData = queryAndAppendSpotifyData(record, authToken)
		if len(groupmeAndSpotifyData) != 0:
			dbRecords.append(groupmeAndSpotifyData)
	return dbRecords

def queryAndAppendSpotifyData(groupmeData, token):
	url = groupmeData[0]
	data = ()
	if('/album/' in url):
		data = querySpotifyAlbum(groupmeData, token)
	elif('/artist/' in url):
		data = querySpotifyArtist(groupmeData, token)
	elif('/track/' in url):
		data = querySpotifyTrack(groupmeData, token)
	return data

def querySpotifyAlbum(groupmeData, token):
	queryUrl = "https://api.spotify.com/v1/albums/" + getSpotifyId(groupmeData[0])
	authHeader = 'Bearer ' + token
	req = urllib.request.Request(queryUrl)
	req.add_header('Authorization', authHeader)
	with urllib.request.urlopen(req) as f:
		response = f.read().decode('utf-8')
		parsed = json.loads(response)
		groupmeData.extend([parsed['artists'][0]['name'], parsed['name'], ''])
	return tuple(groupmeData)

def querySpotifyArtist(groupmeData, token):
	queryUrl = "https://api.spotify.com/v1/artists/" + getSpotifyId(groupmeData[0])
	authHeader = 'Bearer ' + token
	req = urllib.request.Request(queryUrl)
	req.add_header('Authorization', authHeader)
	with urllib.request.urlopen(req) as f:
		response = f.read().decode('utf-8')
		parsed = json.loads(response)
		groupmeData.extend([parsed['name'], '', ''])
	return tuple(groupmeData)

def querySpotifyTrack(groupmeData, token):
	queryUrl = "https://api.spotify.com/v1/tracks/" + getSpotifyId(groupmeData[0])
	authHeader = 'Bearer ' + token
	req = urllib.request.Request(queryUrl)
	req.add_header('Authorization', authHeader)
	with urllib.request.urlopen(req) as f:
		response = f.read().decode('utf-8')
		parsed = json.loads(response)
		groupmeData.extend([parsed['artists'][0]['name'], parsed['album']['name'], parsed['name']])
	return tuple(groupmeData)

def getSpotifyId(url):
	startIndex = url.rfind('/') + 1
	matches = re.findall('\w*', url[startIndex:])
	id = matches[0]
	return id

def trimForUrl(message):
	startIndex = message.find('https')
	url = message[startIndex:].split()[0]
	return url

def getSpotifyToken(token):
	tokenUrl = 'https://accounts.spotify.com/api/token'
	clientIdAndSecret = bytes(token, encoding='ascii')
	b64encoded = base64.standard_b64encode(clientIdAndSecret)
	authHeaderValue = 'Basic ' + b64encoded.decode('ascii')
	req = urllib.request.Request(tokenUrl)
	req.add_header('Authorization', authHeaderValue)
	data = urllib.parse.urlencode({'grant_type': 'client_credentials'})
	data = data.encode('ascii')
	with urllib.request.urlopen(req, data) as f:
		response = f.read().decode('utf-8')
		parsed = json.loads(response)
		return parsed['access_token']

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
	print('all the records have been inserted')
	conn.close()

def getMusicRecords(column, direction):
	conn = sqlite3.connect('gewdMusic.db')
	c = conn.cursor()
	c.execute('SELECT * FROM music ORDER BY {0} {1}'.format(column, direction))
	records = c.fetchall()
	return records
