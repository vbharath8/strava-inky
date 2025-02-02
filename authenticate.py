# Followed steps from https://towardsdatascience.com/using-the-strava-api-and-pandas-to-explore-your-activity-data-d94901d9bfde
import requests
import urllib3
import os
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_strava_access_token()-> str:

    auth_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': os.getenv("STRAVA_CLIENT_ID"),
        'client_secret': os.getenv("STRAVA_CLIENT_SECRET"),
        'refresh_token': os.getenv("STRAVA_REFRESH_TOKEN"),
        'grant_type': "refresh_token",
        'f': 'json'
    }
    print("Requesting Token...\n")
    res = requests.post(auth_url, data=payload, verify=False)
    access_token = res.json()['access_token']
    return  access_token

