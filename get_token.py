import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/tasks']

def get_user_tasks():
    # 1. Load configuration strings dynamically from GitHub Secrets/Environment
    client_secret_env = os.environ.get("CLIENT_SECRET_JSON")
    token_env = os.environ.get("TOKEN_JSON")

    if not client_secret_env or not token_env:
        raise ValueError("Missing critical environment variables: CLIENT_SECRET_JSON or TOKEN_JSON")

    # 2. Parse the strings directly into Python dictionaries
    client_config = json.loads(client_secret_env)
    token_info = json.loads(token_env)

    # 3. Initialize credentials directly from the memory info
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)

    # 4. If the short-term access token is expired, refresh it silently in-memory
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            web_config = client_config.get('web', client_config.get('installed', {}))
            creds.client_id = web_config.get('client_id')
            creds.client_secret = web_config.get('client_secret')
            creds.token_uri = web_config.get('token_uri', 'https://oauth2.googleapis.com/token')
            
            creds.refresh(Request())
        else:
            raise Exception("Critical Error: Saved token session is entirely invalid or missing a refresh_token.")

    # 5. Connect to Google Tasks API
    tasks_service = build('tasks', 'v1', credentials=creds)
    
    # Get all task lists to find the primary list ID
    lists_results = tasks_service.tasklists().list(maxResults=10).execute()
    task_lists = lists_results.get('items', [])

    if not task_lists:
        print(json.dumps({"error": "No task lists found."}, indent=2))
        return

    # Target your primary list
    target_list_id = task_lists[0]['id']
    target_list_title = task_lists[0]['title']

    # 6. Fetch tasks with parameters to include completed items and high limits
    tasks_results = tasks_service.tasks().list(
        tasklist=target_list_id, 
        maxResults=100,
        showCompleted=True,  # Crucial: brings back checked items
        showHidden=True      # Crucial: brings back hidden subtasks/cleared items
    ).execute()
    
    task_items = tasks_results.get('items', [])

    # 7. Format everything into a single structured JSON output
    output_data = {
        "task_list_title": target_list_title,
        "task_list_id": target_list_id,
        "total_tasks_found": len(task_items),
        "tasks": []
    }

    for task in task_items:
        output_data["tasks"].append({
            "id": task.get("id"),
            "title": task.get("title"),
            "status": task.get("status"),  # Will show 'needsAction' or 'completed'
            "notes": task.get("notes", ""),
            "updated": task.get("updated", "")
        })

    # Print pure JSON output to the GitHub Action log window
    print(json.dumps(output_data, indent=2))

if __name__ == '__main__':
    get_user_tasks()
