"""
공용 Google OAuth 인증 헬퍼 (Calendar + Sheets 겸용)

check_calendar_overlap.py, fetch_send_history.py 등 여러 스크립트가
이 모듈의 get_service()를 공유해서 같은 credentials.json / token.json을 쓴다.
스코프를 하나 더 추가해야 하면 아래 SCOPES 리스트에만 추가하면 됨
(단, 기존 token.json은 새 스코프 동의가 안 된 상태라 삭제 후 재인증 필요).
"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def get_credentials():
    creds = None
    try:
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    except FileNotFoundError:
        pass

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return creds


def get_service(api_name: str, api_version: str):
    """예: get_service('calendar', 'v3'), get_service('sheets', 'v4')"""
    creds = get_credentials()
    return build(api_name, api_version, credentials=creds)
