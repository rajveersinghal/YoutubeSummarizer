# backend/db.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "spectra_ai")

try:
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    print(f"✅ Connected to MongoDB: {MONGODB_DB_NAME}")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    db = None
    