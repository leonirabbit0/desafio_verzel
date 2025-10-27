import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("app/config/firebase_token.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

