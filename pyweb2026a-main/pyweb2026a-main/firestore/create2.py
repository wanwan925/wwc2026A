import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

doc = {
  "name": "吳菀秦2",
  "mail": "n0975755006@gmail.com",
  "lab": 555
}

doc_ref = db.collection("靜宜資管2026a")
doc_ref.add(doc)
