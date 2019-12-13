import urllib.request
import json
import sqlite3
import base64
import re
from flask import Flask, render_template, request
from datetime import datetime
import httputil
from urllib import parse

#
# globals
#

app = Flask(__name__)
groupmeToken = ''
cientId = ''
spotifyAuthHeaderValue = ''

urls = {
    'spotify':'https://open.spotify.com/',
    'spotifyToken': 'https://accounts.spotify.com/api/token',
    'spotifyApi': 'https://api.spotify.com/v1/',
    'spotifyUserAuthTokenUrl': 'https://accounts.spotify.com/authorize?',
    'groupmeUrl': 'https://api.groupme.com/v3/groups/27335510/messages?',
    'localRedirectCallback': 'http://127.0.0.1:5000/callback/'
}

with open('tokens.json') as f:
    tokens = json.load(f)
    groupmeToken = tokens['groupmeToken']
    spotifyClientIdAndSecret = tokens['spotifyClientIdAndSecret']
    clientId = tokens['clientId']
    clientIdAndSecret = bytes(spotifyClientIdAndSecret, encoding='ascii')
    b64encoded = base64.standard_b64encode(clientIdAndSecret)
    spotifyAuthHeaderValue = 'Basic ' + b64encoded.decode('ascii')

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.fromtimestamp(value).strftime('%m/%d/%Y')

@app.route('/token')
def token():
    return getSpotifyClientCredToken()


#
# site routes
#

#home page
@app.route('/')
def loadData():
    sort = sanitizeSort(request.args.get('sort'))
    direction = sanitizeDirection(request.args.get('direction'))
    records = getMusicRecords(sort, direction)
    model = buildModel(records)
    return render_template('music.html', model=model)

#callback groupme calls on message post in gewdMusic chat
@app.route('/message', methods=['GET'])
def processMessage():
    body = request.get_json()
    processMessage(body)
    return 'ok', 200

#
# generate latest db from groupme messages
#

@app.route('/db', methods=['GET'])
def generateDb():
    limit = 100
    params = {'token': groupmeToken, 'limit': limit}
    spotifyIds = set()
    data = getGroupmeData(params, spotifyIds)
    data.reverse()
    musicRecords = appendSpotifyData(data)
    createDB()
    createMusicRecord(musicRecords)
    return 'the db was created successfully'

#
# playlist creation
#

#this kicks off the auth flow to get the token, click this link which will take you
#to a spotify login if your login cookie isnt saved which after logging in will show
#you a permissions screen to authorize a token for your account. after a redirect the token will
#will be displayed
@app.route('/spotifyAuth', methods=['GET'])
def spotifyAuth():
    url = getSpotifyUserAuthTokenUrl(clientId)
    msg = 'Click the following url to initaite the authorization code flow token retrieval: {}'.format(url)
    return msg

#after accepting permissions, spotify redirects to this route with a code, which we then use
#to make one more request to finally get our token that allows us to modify user data
@app.route('/callback/')
def callback():
    code = parse.parse_qs(parse.urlparse(request.url).query)['code'][0]
    headers = {'Authorization': spotifyAuthHeaderValue}
    params = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': urls['localRedirectCallback']  }
    response = httputil.post(urls['spotifyToken'], params, headers) 
    parsed = json.loads(response)
    accessToken = parsed['access_token']
    print(accessToken)
    return accessToken

@app.route('/playlist')
def createPlaylist():
    playlistId = createSpotifyPlaylist('test4', 'tomazio21')
    uris = buildSpotifyTrackUris()
    for i in range(0, len(uris), 100):
        subset = uris[i:i+100]
        queryUrl = urls['spotifyApi'] + 'playlists/{}/tracks'.format(playlistId)
        authHeader = 'Bearer ' + 'BQDpbaXyvTQ61PN2HxYAJ2MJgZIhPmhnyOBxULbugLzTq4DMNagdE2nQ6AuOUSVTsq8DiNAuXPqE6kF0zONyIDbdBoxzizssGA0ifnLHYTPsOhCa3oFECEWDd6ENbjXpUCnSruF46wwR5lxmpRiG5GPhFF8f7FG24ybAluxA3poV3LXC'
        headers = {'Authorization': authHeader, 'Content-Type': 'application/json'}
        params = json.dumps({'uris': subset})
        response = httputil.post(queryUrl, params, headers, True)
        parsed = json.loads(response)
    return 'tracks were all added successfully'

def createSpotifyPlaylist(name, userId):
    queryUrl = urls['spotifyApi'] + 'users/{}/playlists'.format(userId)
    authHeader = 'Bearer ' + 'BQDpbaXyvTQ61PN2HxYAJ2MJgZIhPmhnyOBxULbugLzTq4DMNagdE2nQ6AuOUSVTsq8DiNAuXPqE6kF0zONyIDbdBoxzizssGA0ifnLHYTPsOhCa3oFECEWDd6ENbjXpUCnSruF46wwR5lxmpRiG5GPhFF8f7FG24ybAluxA3poV3LXC'
    headers = {'Authorization': authHeader, 'Content-Type': 'application/json'}
    params = json.dumps({'name': name})
    response = httputil.post(queryUrl, params, headers, True)
    parsed = json.loads(response)
    playlistId = parsed['id']
    return playlistId

def buildSpotifyTrackUris():
    uris = []
    urls = getMusicLinks()
    token = getSpotifyClientCredToken()
    for url in urls:
        if('/album/' in url[0]):
            trackIds = querySpotifyTracksFromAlbum(getSpotifyId(url[0]))
            for trackId in trackIds:
                uri = 'spotify:track:' + trackId
                uris.append(uri)	
        elif('/track/' in url[0]):
            uri = 'spotify:track:'+ getSpotifyId(url[0])
            uris.append(uri)
    return uris

#
# home page helpers
#

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
    if direction == 'asc':
        return 'ASC'
    else:
        return 'DESC'

#
# query and comb through groupme messages for valid spotify links
#
	
def getGroupmeData(params, ids):
    response = httputil.get(urls['groupmeUrl'], params)
    parsed = json.loads(response)
    messages = parsed['response']['messages']
    data = []
    for message in messages:
        if isValidSpotifyLink(message):
            url = trimForUrl(message['text'])
            musicId = getSpotifyId(url)
            if musicId not in ids:
                ids.add(musicId)
                messageData = [url, message['name'], message['created_at']]
                data.append(messageData)
    if len(messages) == params['limit']:
        params['before_id'] = messages[params['limit']-1]['id']
        data.extend(getGroupmeData(params, ids))
    return data

#
#url/id parsing
#

def getSpotifyId(url):
    startIndex = url.rfind('/') + 1
    matches = re.findall('\w*', url[startIndex:])
    id = matches[0]
    return id

def trimForUrl(message):
    startIndex = message.find('https')
    url = message[startIndex:].split()[0]
    return url

def isValidSpotifyLink(message):
    text = message['text']
    if isinstance(text, str) and urls['spotify'] in text:
        url = trimForUrl(text)
        if 'album' in url or 'track' in url or 'artist' in url:
            return True
    return False

#
# process individual groupme message for spotify link
#

def processMessage(message):	
    if isValidSpotifyLink(message): 
        url = trimForUrl(message['text'])
        musicId = getSpotifyId(url)
        messageData = [url, message['name'], message['created_at']]
        musicRecord = appendSpotifyData([messageData])
        createMusicRecord(musicRecord)

#
# query for spotify data with associated links and append to groupme message data
#

def appendSpotifyData(groupmeData):
    dbRecords = []
    authToken = getSpotifyClientCredToken()
    for record in groupmeData:
        groupmeAndSpotifyData = queryAndAppendSpotifyData(record, authToken)
        if len(groupmeAndSpotifyData) != 0:
            dbRecords.append(groupmeAndSpotifyData)
    return dbRecords

#
# spotify api query helpers
#

def queryAndAppendSpotifyData(groupmeData, token):
    url = groupmeData[0]
    data = ()
   
    if('/album/' in url):
        response = querySpotifyAlbum(groupmeData, token)
        groupmeData.extend([response['artists'][0]['name'], response['name'], ''])
    elif('/artist/' in url):
        response = querySpotifyArtist(groupmeData, token)
        groupmeData.extend([response['name'], '', ''])
    elif('/track/' in url):
        response = querySpotifyTrack(groupmeData, token)
        groupmeData.extend([response['artists'][0]['name'], response['album']['name'], response['name']])
    
    data = tuple(groupmeData)
    if len(data) == 3:
        print(data)
    return data

def querySpotifyAlbum(groupmeData, token):
    queryUrl = urls['spotifyApi'] + 'albums/' + getSpotifyId(groupmeData[0])
    authHeader = 'Bearer ' + token
    headers = {'Authorization': authHeader}
    response = httputil.get(queryUrl, {}, headers)
    parsed = json.loads(response)
    return parsed

def querySpotifyArtist(groupmeData, token):
    queryUrl = urls['spotifyApi'] + 'artists/' + getSpotifyId(groupmeData[0])
    authHeader = 'Bearer ' + token
    headers = {'Authorization': authHeader}
    response = httputil.get(queryUrl, {}, headers)
    parsed = json.loads(response)
    return parsed

def querySpotifyTrack(groupmeData, token):
    queryUrl = urls['spotifyApi'] + 'tracks/' + getSpotifyId(groupmeData[0])
    authHeader = 'Bearer ' + token
    headers = {'Authorization': authHeader}
    response = httputil.get(queryUrl, {}, headers)
    parsed = json.loads(response)
    return parsed

def querySpotifyTracksFromAlbum(albumId):
    ids= []
    queryUrl =  urls['spotifyApi'] +  'albums/{}/tracks'.format(albumId)
    token = getSpotifyClientCredToken()
    authHeader = 'Bearer ' + token
    headers = {'Authorization': authHeader}
    response = httputil.get(queryUrl, {}, headers)
    parsed = json.loads(response)
    tracks = parsed['items']
    for track in tracks:
        ids.append(track['id'])
    return ids

#
#token retrieval methods
#

def getSpotifyClientCredToken():
    headers = {'Authorization': spotifyAuthHeaderValue}
    params = {'grant_type': 'client_credentials'}
    response = httputil.post(urls['spotifyToken'], params, headers)
    parsed = json.loads(response)
    return parsed['access_token']

def getSpotifyUserAuthTokenUrl(clientId):
    data = urllib.parse.urlencode({'client_id': clientId, 'response_type': 'code', 'redirect_uri': urls['localRedirectCallback'], 'scope': 'playlist-modify-public' })
    tokenUrl = urls['spotifyUserAuthTokenUrl'] + data
    print(tokenUrl)
    return tokenUrl

#
#db
#

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

def getMusicLinks():
    conn = sqlite3.connect('gewdMusic.db')
    c = conn.cursor()
    c.execute('SELECT link FROM music')
    records = c.fetchall()
    return records
