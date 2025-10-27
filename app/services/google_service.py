import datetime
import os.path
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES=["https://www.googleapis.com/auth/calendar"]

CLIENT_SECRET = os.getenv("CLIENT_SECRET")

class GoogleCalendar():
    def __init__(self):
        self.creds = self.get_cred()
        self.service = build("calendar", "v3", credentials=self.creds) 

    def get_now(self):
        return datetime.datetime.now(tz=datetime.timezone.utc)

    def get_cred(self):
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRET, SCOPES
                )
                creds = flow.run_local_server(port=8080)
                
        with open("token.json", "w") as token:
            token.write(creds.to_json())

        return creds
    
    def get_agenda(self):
        try:
            print("Getting the upcoming 10 events")
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=self.now,
                    maxResults=10,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            if not events:
                print("No upcoming events found.")
                return

            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                print(start, event["summary"])

        except HttpError as error:
            print(f"An error occurred: {error}")

    def get_busy(self, time_min: datetime.datetime, time_max: datetime.datetime, calendar_id: str = 'primary'):
        """
        Verifica a disponibilidade de horários no calendário dentro de um intervalo.
        """
        
        # carante que as datas têm timezone UTC
        if time_min.tzinfo is None:
            time_min = time_min.replace(tzinfo=datetime.timezone.utc)
        if time_max.tzinfo is None:
            time_max = time_max.replace(tzinfo=datetime.timezone.utc)

        # converte para ISO 8601 com o sufixo Z (obrigatório para a API)
        time_min_iso = time_min.isoformat().replace("+00:00", "Z")
        time_max_iso = time_max.isoformat().replace("+00:00", "Z")

        body = {
            "timeMin": time_min_iso,
            "timeMax": time_max_iso,
            "items": [{"id": calendar_id}]
        }

        try:
            response = self.service.freebusy().query(body=body).execute()
            busy_periods = response.get('calendars', {}).get(calendar_id, {}).get('busy', [])
            return busy_periods

        except HttpError as error:
            print(f"An error occurred while checking free/busy: {error}")
            return []

    def get_available(self, time_min: datetime.datetime, time_max: datetime.datetime, calendar_id: str = 'primary') -> list:
        """
        Verifica a disponibilidade de horários no calendário e retorna os períodos livres.
        """
        busy_periods = self.get_busy(time_min, time_max, calendar_id)

        free_periods = []

        # garante timezone UTC nos parâmetros de entrada
        if time_min.tzinfo is None:
            time_min = time_min.replace(tzinfo=datetime.timezone.utc)
        if time_max.tzinfo is None:
            time_max = time_max.replace(tzinfo=datetime.timezone.utc)

        current_time = time_min

        for busy_slot in sorted(busy_periods, key=lambda x: x['start']):
            # converte strings ISO 8601 em datetime com UTC
            busy_start = datetime.datetime.fromisoformat(
                busy_slot['start'].replace("Z", "+00:00")
            )
            busy_end = datetime.datetime.fromisoformat(
                busy_slot['end'].replace("Z", "+00:00")
            )

            # ambos são "aware", a comparação funciona normalmente
            if current_time < busy_start:
                free_periods.append({
                    "start": current_time.isoformat(),
                    "end": busy_start.isoformat()
                })

            current_time = max(current_time, busy_end)

        if current_time < time_max:
            free_periods.append({
                "start": current_time.isoformat(),
                "end": time_max.isoformat()
            })

        print(free_periods)
        return free_periods

    def create_event(self, summary:str, inicio:datetime.datetime, fim:datetime.datetime, calendar_id: str = 'primary', location: str = None, description: str = None):
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': inicio.isoformat(),
                'timeZone': inicio.tzinfo.tzname(inicio), 
            },
            'end': {
                'dateTime': fim.isoformat(),
                'timeZone': fim.tzinfo.tzname(fim),
            },
            #adicionar outras propriedades como 'attendees', 'recurrence', 'reminders', etc.
        }
        
        event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
        
        print(f"Event created: {event.get('htmlLink')}")
        
        return event
    
    