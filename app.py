from flask import Flask, redirect, request
import os # for environment variables
import requests

app = Flask(__name__)

sp_id = os.environ["SP_CLIENT_ID"]
sp_secret = os.environ["SP_CLIENT_SECRET"]
#redirect_uri = "http://localhost:5000/auth0"
redirect_uri = "https://newalbums.herokuapp.com/auth0"

@app.route('/')
def index():
    auth_url = "https://accounts.spotify.com/authorize?client_id="+sp_id+"&response_type=code&redirect_uri="+redirect_uri+"&scope=user-follow-read"
    return redirect(auth_url)

@app.route('/auth0')
def auth0():
    if request.args.get('error') is None:
        code = request.args.get('code')
        payload = {'grant_type': 'authorization_code','code': code, 'redirect_uri': redirect_uri, 'client_id': sp_id, 'client_secret': sp_secret}
        auth_response = requests.post("https://accounts.spotify.com/api/token", data=payload)
        #return auth_response.json()["access_token"]

        access_token = auth_response.json()["access_token"]
        headers = {'Authorization': 'Bearer '+access_token}
        me = requests.get("https://api.spotify.com/v1/me/following?type=artist", headers=headers)
        return me.json()

    else:
        return request.args.get('error')

if __name__ == '__main__':
    app.run()