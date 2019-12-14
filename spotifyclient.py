import httputil
import base64
import re
import json
import urllib.request

urls = {
    'spotifyToken': 'https://accounts.spotify.com/api/token',
    'spotifyApi': 'https://api.spotify.com/v1/',
    'spotifyUserAuthTokenUrl': 'https://accounts.spotify.com/authorize?',
    'localRedirectCallback': 'http://127.0.0.1:5000/callback/'
}

class SpotifyClient:

    def __init__(self, clientIdAndSecret): 
        encodedIdAndSecret = bytes(clientIdAndSecret, encoding='ascii')
        b64encoded = base64.standard_b64encode(encodedIdAndSecret)
        self.clientAuthHeader = 'Basic ' + b64encoded.decode('ascii')
        self.clientCredToken = ''
        self.userAuthToken = ''
        self.clientId = clientIdAndSecret.split(':')[0]
    
    def getSpotifyClientCredToken(self):
        if not self.clientCredToken:
            headers = {'Authorization': self.clientAuthHeader}
            params = {'grant_type': 'client_credentials'}
            response = httputil.post(urls['spotifyToken'], params, headers)
            parsed = json.loads(response)
            self.clientCredToken = parsed['access_token']
        return self.clientCredToken
    
    def getSpotifyUserAuthTokenUrl(self):
        data = urllib.parse.urlencode({'client_id': self.clientId, 'response_type': 'code', 'redirect_uri': urls['localRedirectCallback'], 'scope': 'playlist-modify-public' })
        tokenUrl = urls['spotifyUserAuthTokenUrl'] + data
        print(tokenUrl)
        return tokenUrl
    
    def getSpotifyUserAuthToken(self, code=None):
        if not self.userAuthToken:
            headers = {'Authorization': self.clientAuthHeader}
            params = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': urls['localRedirectCallback']  }
            response = httputil.post(urls['spotifyToken'], params, headers) 
            parsed = json.loads(response)
            self.userAuthToken = parsed['access_token']
        return self.userAuthToken

    def querySpotifyAlbum(self, albumId):
        token = self.getSpotifyClientCredToken()
        queryUrl = urls['spotifyApi'] + 'albums/' + albumId 
        authHeader = 'Bearer ' + token
        headers = {'Authorization': authHeader}
        response = httputil.get(queryUrl, {}, headers)
        parsed = json.loads(response)
        return parsed

    def querySpotifyArtist(self, artistId):
        token = self.getSpotifyClientCredToken()
        queryUrl = urls['spotifyApi'] + 'artists/' + artistId
        authHeader = 'Bearer ' + token
        headers = {'Authorization': authHeader}
        response = httputil.get(queryUrl, {}, headers)
        parsed = json.loads(response)
        return parsed

    def querySpotifyTrack(self, trackId):
        token = self.getSpotifyClientCredToken()
        queryUrl = urls['spotifyApi'] + 'tracks/' + trackId 
        authHeader = 'Bearer ' + token
        headers = {'Authorization': authHeader}
        response = httputil.get(queryUrl, {}, headers)
        parsed = json.loads(response)
        return parsed

    def querySpotifyTracksFromAlbum(self, albumId):
        token = self.getSpotifyClientCredToken()
        ids= []
        queryUrl =  urls['spotifyApi'] +  'albums/{}/tracks'.format(albumId)
        token = self.getSpotifyClientCredToken()
        authHeader = 'Bearer ' + token
        headers = {'Authorization': authHeader}
        response = httputil.get(queryUrl, {}, headers)
        parsed = json.loads(response)
        tracks = parsed['items']
        for track in tracks:
            ids.append(track['id'])
        return ids
    
    def createSpotifyPlaylist(self, name, userId):
        token = self.getSpotifyUserAuthToken()
        print(token)
        queryUrl = urls['spotifyApi'] + 'users/{}/playlists'.format(userId)
        authHeader = 'Bearer ' + token 
        headers = {'Authorization': authHeader, 'Content-Type': 'application/json'}
        params = json.dumps({'name': name})
        response = httputil.post(queryUrl, params, headers, True)
        parsed = json.loads(response)
        playlistId = parsed['id']
        return playlistId

    def addTracksToPlaylist(self, playlistId, trackUris):
        token = self.getSpotifyUserAuthToken()
        queryUrl = urls['spotifyApi'] + 'playlists/{}/tracks'.format(playlistId)
        authHeader = 'Bearer ' + token 
        headers = {'Authorization': authHeader, 'Content-Type': 'application/json'}
        params = json.dumps({'uris': trackUris})
        response = httputil.post(queryUrl, params, headers, True)
        parsed = json.loads(response)

    def getSpotifyId(self, url):
        startIndex = url.rfind('/') + 1
        matches = re.findall('\w*', url[startIndex:])
        id = matches[0]
        return id
