import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'  # Needed to search for the file by name
]

def get_user_tasks():
    # 1. Load configuration strings dynamically from GitHub Secrets/Environment
    client_secret_env = os.environ.get("CLIENT_SECRET_JSON")
    token_env = os.environ.get("TOKEN_JSON")

    if not client_secret_env or not token_env:
        raise ValueError("Missing critical environment variables: CLIENT_SECRET_JSON or TOKEN_JSON")

    # 2. Parse the strings directly into Python dictionaries
    client_config = json.loads(client_secret_env)
    token_info = json.loads(token_env)

    # 3. Initialize credentials directly from memory
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)

    # 4. Handle token refresh if expired
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            web_config = client_config.get('web', client_config.get('installed', {}))
            creds.client_id = web_config.get('client_id')
            creds.client_secret = web_config.get('client_secret')
            creds.token_uri = web_config.get('token_uri', 'https://oauth2.googleapis.com/token')
            creds.refresh(Request())
        else:
            raise Exception("Critical Error: Saved token session is entirely invalid or missing a refresh_token.")

    # 5. Connect to APIs
    tasks_service = build('tasks', 'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds) # Used to check if file exists
    
    # Get primary task list ID
    lists_results = tasks_service.tasklists().list(maxResults=10).execute()
    task_lists = lists_results.get('items', [])
    if not task_lists:
        print("No task lists found.")
        return

    target_list_id = task_lists[0]['id']

    # 6. Fetch all tasks (completed and uncompleted)
    tasks_results = tasks_service.tasks().list(
        tasklist=target_list_id, 
        maxResults=100,
        showCompleted=True,
        showHidden=True
    ).execute()
    task_items = tasks_results.get('items', [])

    # 7. Prepare the data rows for the sheet
    # First row is the header
    sheet_rows = [["Id", "Title", "Status", "Notes", "Updated"]]
    
    for task in task_items:
        sheet_rows.append([
            task.get("id", ""),
            task.get("title", ""),
            task.get("status", ""),
            task.get("notes", ""),
            task.get("updated", "")
        ])

    # 8. Find or Create the Spreadsheet named "my_tasks_list"
    spreadsheet_id = None
    query = "name = 'my_tasks_list' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    find_file = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    files = find_file.get('files', [])

    if files:
        spreadsheet_id = files[0]['id']
        print(f"[+] Found existing spreadsheet: {spreadsheet_id}")
    else:
        # Create a brand new spreadsheet with the first tab named "tasks"
        spreadsheet_body = {
            'properties': {'title': 'my_tasks_list'},
            'sheets': [{'properties': {'title': 'tasks'}}]
        }
        new_sheet = sheets_service.spreadsheets().create(body=spreadsheet_body, fields='spreadsheetId').execute()
        spreadsheet_id = new_sheet.get('spreadsheetId')
        print(f"[+] Created brand new spreadsheet: {spreadsheet_id}")

    # 9. Overwrite the spreadsheet using the 'tasks' sheet name
    # First, clear any old data that might be sitting in the sheet from previous runs
    sheets_service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range="tasks!A:E"
    ).execute()

    # Second, write the fresh rows starting from cell A1
    body = {'values': sheet_rows}
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="tasks!A1",
        valueInputOption="RAW",
        body=body
    ).execute()

    print(f"[+] Successfully wrote {len(sheet_rows) - 1} tasks to Google Sheets!")

if __name__ == '__main__':
    get_user_tasks()
