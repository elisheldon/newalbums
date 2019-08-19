from flask import Flask, redirect, request, session, jsonify, render_template
import os
import requests
from concurrent.futures import ThreadPoolExecutor as PoolExecutor

app = Flask(__name__)

app.secret_key = os.environ["FLASK_SECRET_KEY"] # used to encrypt cookies
sp_id = os.environ["SP_CLIENT_ID"] # used to get spotify auth code and access tokens
sp_secret = os.environ["SP_CLIENT_SECRET"] # used to get spotify access tokens
redirect_uri = "http://localhost:5000/callback"
#redirect_uri = "https://newalbums.herokuapp.com/callback"

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template("index.html")
    else:
        auth_url = "https://accounts.spotify.com/authorize?client_id="+sp_id+"&response_type=code&redirect_uri="+redirect_uri+"&scope=user-follow-read" # gets auth code from spotify
        return redirect(auth_url)

@app.route('/load')
def load():
    artists = [] # create a blank list of artist objects
    artists_data = requests.get('https://api.spotify.com/v1/me/following?type=artist&limit=50', headers=session['headers']) # get the first page of artist objects from spotify

    if 'error' in artists_data.json():
        if artists_data.json()["error"]["message"] == "The access token expired": # if the access token has expired
            if 'refresh_token' in session: # and if we have a refresh token for the session
                auth_data = {'grant_type': 'refresh_token', 'refresh_token': session['refresh_token'], 'client_id': sp_id, 'client_secret': sp_secret}
                auth_response = requests.post('https://accounts.spotify.com/api/token', data=auth_data)  # get access and refresh tokens from spotify
                session['access_token'] = auth_response.json()['access_token']
                session['headers'] = {'Authorization': 'Bearer '+session['access_token']} # headers to use for all spotify api calls
                return redirect("/")
        return artists_data.json() # otherwise, print the error for debugging purposes
    
    for artist in artists_data.json()["artists"]["items"]:
        artists.append(artist) # add each artist object to the artists list

    if len(artists) == 0: # ensure user follows at least one artist
        return "You don't follow any artists on Spotify. Follow at least one artist, and then try again."

    for i in range(50,artists_data.json()["artists"]["total"],50): # get each subsequent page of 50 artists
        artists_data = requests.get(artists_data.json()["artists"]["next"], headers=session['headers'])
        if 'error' in artists_data.json():
            return artists_data.json()
        for artist in artists_data.json()["artists"]["items"]:
            artists.append(artist)
    
    def load_albums(artist):
        artist['newest_album'] = {'release_date':'0'} # create a placeholder newest album on artist within artists list
        albums_data = requests.get('https://api.spotify.com/v1/artists/' + artist['id'] + '/albums?include_groups=album&country=from_token&limit=50', headers=headers) # get first page of albums
        if 'error' in albums_data.json():
            return albums_data.json()

        for album in albums_data.json()['items']:
            if album['release_date'] > artist['newest_album']['release_date']: # if this album is newer than the one we currently have as newest, replace it
                artist['newest_album'] = album

        for i in range(50,albums_data.json()["total"],50): # get each subsequent page of 50 albums
            albums_data = requests.get(albums_data.json()["next"], headers=headers)
            if 'error' in albums_data.json():
                return albums_data.json()
            for album in albums_data.json()['items']:
                if album['release_date'] > artist['newest_album']['release_date']: # if this album is newer than the one we currently have as newest, replace it
                    artist['newest_album'] = album

    # load albums for each artist using concurrent workers to speed up numerous API calls
    headers = session['headers'] # load_albums cannot access session directly
    with PoolExecutor(max_workers=8) as executor:
        executor.map(load_albums, artists)

    return render_template("albums.html", artists=sorted(artists, key = lambda i: i['newest_album']['release_date'], reverse=True))

@app.route('/callback')
def callback():
    if request.args.get('error') is None:
        code = request.args.get('code') # auth code is a url parameter
        auth_data = {'grant_type': 'authorization_code','code': code, 'redirect_uri': redirect_uri, 'client_id': sp_id, 'client_secret': sp_secret}
        auth_response = requests.post('https://accounts.spotify.com/api/token', data=auth_data)  # get access and refresh tokens from spotify
        
        session['access_token'] = auth_response.json()['access_token']
        session['refresh_token'] = auth_response.json()['refresh_token']
        session['headers'] = {'Authorization': 'Bearer '+session['access_token']} # headers to use for all spotify api calls
        
        profile = requests.get('https://api.spotify.com/v1/me/', headers=session['headers'])
        session['user_id'] = profile.json()['id']
        return redirect("/")

    else:
        return request.args.get('error')

if __name__ == '__main__':
    app.run()