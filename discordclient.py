import httputil
import json


urls = {
    'discordHttpApi': 'https://discord.com/api/v10/'
}


class DiscordClient:

    def __init__(self, token):
        self.token = token

    def getChannelMessages(self, channelId, before):
        queryUrl = urls['discordHttpApi'] + \
            'channels/' + channelId + '/messages' + \
            '?limit=100' + before
        headers = {
            'Authorization': 'Bot ' + self.token,
            'User-Agent': 'DiscordBot'
        }
        response = httputil.get(queryUrl, {}, headers)
        print(response.getheaders())
        parsed = json.loads(response.read().decode('utf-8'))
        return parsed

    def getChannelHistory(self, channelId):
        messages = []
        jsonResponse = self.getChannelMessages(channelId, '')
        messages.extend(jsonResponse)
        while len(jsonResponse) == 100:
            before = '&before=' + jsonResponse[-1]['id']
            jsonResponse = self.getChannelMessages(channelId, before)
            messages.extend(jsonResponse)
        return messages
