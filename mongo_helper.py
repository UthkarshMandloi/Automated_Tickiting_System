# mongo_helper.py
# This file contains a helper class for interacting with the MongoDB database.

from pymongo import MongoClient
# Import column names from your config file to ensure consistency
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME, COL_NAME, COL_EMAIL

class MongoDBClient:
    def __init__(self):
        """Initializes the connection to the MongoDB database and collection."""
        try:
            if not MONGO_DB_NAME:
                raise ValueError("MONGO_DB_NAME is not set.")
            if not MONGO_COLLECTION_NAME:
                raise ValueError("MONGO_COLLECTION_NAME is not set.")
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[MONGO_DB_NAME]
            self.collection = self.db[MONGO_COLLECTION_NAME]
            # Test the connection on initialization
            self.client.admin.command('ping')
            print("[MongoDB] Connection successful.")
        except Exception as e:
            print(f"[MongoDB] ERROR: Could not connect to MongoDB: {e}")
            exit(1)

    def find_attendee_by_email_and_name(self, email: str, name: str):
        """
        Finds a single attendee document by matching both their email and name,
        using the specific column headers defined in config.py.
        """
        query = {
            COL_EMAIL: email,
            COL_NAME: name
        }
        return self.collection.find_one(query)

    def insert_full_attendee(self, attendee_data: dict):
        """
        Inserts a new attendee document into the collection.
        The data is passed as a complete dictionary.
        """
        self.collection.insert_one(attendee_data)
        print(f"[MongoDB] Inserted new attendee: {attendee_data.get('Name')} ({attendee_data.get('attendee_id')})")

    # --- NEW: Generic function to update any field for an attendee ---
    def update_attendee_field(self, attendee_id: str, field_name: str, new_value: str):
        """
        Updates a specific field for a given attendee ID.
        This is used to update ticket status, email status, etc.
        """
        self.collection.update_one(
            {"attendee_id": attendee_id},
            {"$set": {field_name: new_value}}
        )
        print(f"[MongoDB] Updated '{field_name}' for {attendee_id} → {new_value}")

    def get_attendee(self, attendee_id: str):
        """Retrieves a single attendee document by their unique attendee_id."""
        return self.collection.find_one({"attendee_id": attendee_id})
    
    def find_attendees_by_query(self, query: dict):
        """
        Finds attendees based on a flexible query.
        To get all attendees, pass an empty dictionary: {}.
        """
        # The .find() method returns a cursor, so we convert it to a list
        return list(self.collection.find(query))