import urllib.request
import json
import db
import httputil
import spotifyclient
from urllib import parse
from datetime import datetime
from flask import Flask, render_template, request

#
# globals
#

app = Flask(__name__)
groupmeToken = ''
cientId = ''
spotifyAuthHeaderValue = ''
spotifyClient = None

urls = {
    'spotify':'https://open.spotify.com/',
    'groupmeUrl': 'https://api.groupme.com/v3/groups/27335510/messages?',
}

columns = {
    'id':'id',
    'user':'user',
    'date':'date_posted',
    'artist':'artist',
    'album':'album',
    'track':'trackname'
}

with open('tokens.json') as f:
    tokens = json.load(f)
    groupmeToken = tokens['groupmeToken']
    spotifyClientIdAndSecret = tokens['spotifyClientIdAndSecret']
    spotifyClient = spotifyclient.SpotifyClient(spotifyClientIdAndSecret)

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.fromtimestamp(value).strftime('%m/%d/%Y')

#
# site routes
#

#home page
@app.route('/')
def loadData():
    sort = sanitizeSort(request.args.get('sort'))
    direction = sanitizeDirection(request.args.get('direction'))
    records = db.getMusicRecords(sort, direction)
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
    db.createDB()
    db.createMusicRecord(musicRecords)
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
    url = spotifyClient.getSpotifyUserAuthTokenUrl()
    message = 'Click the following url to initaite the authorization code flow token retrieval: <br>'
    anchor = '<a href="{}">{}</a>'.format(url, url)
    message += anchor
    return message

#after accepting permissions, spotify redirects to this route with a code, which we then use
#to make one more request to finally get our token that allows us to modify user data
@app.route('/callback/')
def callback():
    code = parse.parse_qs(parse.urlparse(request.url).query)['code'][0]
    accessToken = spotifyClient.getSpotifyUserAuthToken(code)
    return accessToken

@app.route('/playlist')
def createPlaylist():
    playlistId = spotifyClient.createSpotifyPlaylist('test5', 'tomazio21')
    uris = buildSpotifyTrackUris()
    for i in range(0, len(uris), 100):
        subset = uris[i:i+100]
        spotifyClient.addTracksToPlaylist(playlistId, subset)
    return 'tracks were all added successfully'

def buildSpotifyTrackUris():
    uris = []
    urls = db.getMusicLinks()
    for url in urls:
        if('/album/' in url[0]):
            trackIds = spotifyClient.querySpotifyTracksFromAlbum(spotifyClient.getSpotifyId(url[0]))
            for trackId in trackIds:
                uri = 'spotify:track:' + trackId
                uris.append(uri)	
        elif('/track/' in url[0]):
            uri = 'spotify:track:'+ spotifyClient.getSpotifyId(url[0])
            uris.append(uri)
    return uris

#
# home page helpers
#

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
        url = getValidSpotifyUrl(message)
        if url:
            musicId = spotifyClient.getSpotifyId(url)
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

def trimForUrl(message):
    startIndex = message.find('https')
    url = message[startIndex:].split()[0]
    return url

def getValidSpotifyUrl(message):
    text = message['text']
    if isinstance(text, str) and urls['spotify'] in text:
        url = trimForUrl(text)
        if 'album' in url or 'track' in url or 'artist' in url:
            return url
    return ''

#
# process individual groupme message for spotify link
#

def processMessage(message):
    url = getValidSpotifyUrl(message)
    if url:
        url = trimForUrl(message['text'])
        musicId = spotifyClient.getSpotifyId(url)
        messageData = [url, message['name'], message['created_at']]
        musicRecord = appendSpotifyData([messageData])
        db.createMusicRecord(musicRecord)

#
# query for spotify data with associated links and append to groupme message data
#

def appendSpotifyData(groupmeData):
    dbRecords = []
    for record in groupmeData:
        groupmeAndSpotifyData = queryAndAppendSpotifyData(record)
        if len(groupmeAndSpotifyData) != 0:
            dbRecords.append(groupmeAndSpotifyData)
    return dbRecords

def queryAndAppendSpotifyData(groupmeData):
    url = groupmeData[0]
    spotifyId = spotifyClient.getSpotifyId(url)
 
    if('/album/' in url):
        response = spotifyClient.querySpotifyAlbum(spotifyId)
        groupmeData.extend([response['artists'][0]['name'], response['name'], ''])
    elif('/artist/' in url):
        response = spotifyClient.querySpotifyArtist(spotifyId)
        groupmeData.extend([response['name'], '', ''])
    elif('/track/' in url):
        response = spotifyClient.querySpotifyTrack(spotifyId)
        groupmeData.extend([response['artists'][0]['name'], response['album']['name'], response['name']])
    
    data = tuple(groupmeData)
    return data
