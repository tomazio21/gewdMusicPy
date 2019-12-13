import urllib.request
import urllib.parse

def get(url, params, headers=None): 
    urlEncodedParams =  urllib.parse.urlencode(params)
    url = url + urlEncodedParams
    req = urllib.request.Request(url)
    if headers != None:
        for name, value in headers.items():
            req.add_header(name, value)
    with urllib.request.urlopen(req) as f:
        response = f.read().decode('utf-8')
        return response

def post(url, params, headers=None, json=False):
    req = urllib.request.Request(url)
    data = ''
    if json == False:
        params = urllib.parse.urlencode(params)
    if headers != None:
        for name, value in headers.items():
            req.add_header(name, value)
    data = params.encode('utf-8')
    with urllib.request.urlopen(req, data) as f:
        response = f.read().decode('utf-8')
        return response
