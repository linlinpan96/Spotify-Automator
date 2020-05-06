# Automatically sync liked videos from youtube to a spotify playlist
# Inspiration credit to https://github.com/TheComeUpCode

import json
import requests
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import youtube_dl

from exceptions import ResponseException
from spotify_info import spotify_username, spotify_token

class SyncVideos:

    def __init__(self):
        self.youtube_client = self.get_yt_client()
        self.all_video_info = {};

    # Get the Youtube Client
    def get_yt_client(self):
        
        # Copied from Youtube DATA api
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()

        # Get the client
        youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        return youtube;
    
    # Get the liked videos from YouTube client
    def get_liked_videos(self):
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            mine=True
        )
        response = request.execute()

        # Get video information
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(item["id"])

            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)
            song_name = video["track"]
            artist = video["artist"]

            # Create dictionary of all important info of liked songs
            self.all_video_info[video_title] = {
                "youtube_url" : youtube_url,
                "song_name" : song_name,
                "artist" : artist,

                # Get Spotify uri
                "spotify_uri" : self.get_spotify_uri(song_name)
            }

    def create_playlist():
        request_body = json.dumps({
            "name" : "Youtube Liked Songs",
            "description" : "Songs I liked from Youtube",
            "public" : True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_username)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json();

        return response_json["id"]
    
    def get_spotify_uri(self, track):
        
        query = "https://api.spotify.com/v1/search?q={}&type=track%2Cartist&limit=10&offset=5".format(
            track
        )

        response = requests.get(
            query,
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json();
        songs = response_json["tracks"]["items"]

        # Get the first result (should be correct one)
        uri = songs[0]["uri"]

    def add_song_to_playlist(self):

        # Populate songs into dictionary
        self.get_liked_videos();
        
        URIs = []
        for song,info in self.all_video_info:
            URIs.append(info["spotify_uri"])

        # Create new playlist
        playlist_id = self.create_playlist();

        # Add song into playlist
        request_data = json.dumps(URIs)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)

        response = requests.post(
            query,
            data = request_data,
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        # Check for valid response
        if response.status_code != 200:
            raise ResponseException(response.status_code)

        response_json = response.json()
        return response_json

if __name__ == '__main__':
    cp = SyncVideos()
    cp.add_song_to_playlist