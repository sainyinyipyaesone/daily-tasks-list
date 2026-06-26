import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/tasks']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_CACHE_FILE = 'token.json'  # <--- Where your login session stays saved

def get_user_tasks():
    creds = None
    
    # 1. Check if we already logged in previously
    if os.path.exists(TOKEN_CACHE_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_CACHE_FILE, SCOPES)
        
    # 2. If there are no valid credentials available, let them login or refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[+] Token expired. Refreshing silently in the background...")
            creds.refresh(Request())
        else:
            print("[!] No saved session found. Starting browser login...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, scopes=SCOPES
            )
            creds = flow.run_local_server(host='localhost', port=8080, open_browser=False, access_type='offline', prompt='consent')
            
        # 3. Save the credentials for the next run
        with open(TOKEN_CACHE_FILE, 'w') as token_file:
            token_file.write(creds.to_json())

    print(f"\n[+] Active Access Token: {creds.token}\n")

    # 4. Run your API call
    service = build('tasks', 'v1', credentials=creds)
    results = service.tasklists().list(maxResults=10).execute()
    for item in results.get('items', []):
        print(f"- {item['title']} (ID: {item['id']})")

if __name__ == '__main__':
    get_user_tasks()
