# This File will transform comma-separated values file as follows (hopefully it will at least):
#
# Input format  :Album1,Artist1
#               :Album2,Artist2
#
# Output format :Album1,Artist1,AlbumLink1
#               :Album2,Artist2,AlbumLink2
#
# More on CSV format (I had to look it up lol): https://en.wikipedia.org/wiki/Comma-separated_values
import csv
import json

with open('tokens.json') as f:
	tokens = json.load(f)
	spotifyAuthToken = tokens['spotifyAuthToken']

def getSpotifyLink(album, artist):
    print(album + ", " + artist) # Why is the output slightly fucked up?
    # Example query: "https://api.spotify.com/v1/search?q=album%3Aarrival%20artist%3Aabba&type=album"
    # Need to add header with auth token or some shit.. fuck the web and its "security"
    endpoint = 'https://api.spotify.com/v1/search'


if __name__ == '__main__':
    # HARD coded for now...
    # TODO parse input for path.
    # TODO2 File tracking item for this!
    with open('C:\\Users\\Chaz\\projects\\gewMusicPy\\toplists\\ToddTopAlbums2019.csv') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in spamreader:
            getSpotifyLink(row[0], row[1])