import sqlite3
import os
import json

DATABASE_FILE = 'history.db'

def initialize_database():
    conn = None # Initialize connection to None
    try:
        # Connect to the database. If it doesn't exist, it will be created.
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print(f"Connected to database: {DATABASE_FILE}")

        # Define your SQL statements for creating tables
        # Using triple quotes allows for multi-line SQL strings
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY,
            messages TEXT
        );
        """

        # Execute the SQL script to create tables
        # executescript() handles multiple statements separated by semicolons
        cursor.executescript(create_tables_sql)

        # Commit the changes to save the table structures
        conn.commit()
        print("Tables created or already exist.")

    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")

    finally:
        # Ensure the connection is closed even if an error occurs
        if conn:
            conn.close()
            print("Database connection closed.")

# --- Functions for Database Interaction ---
def get_db_connection():
    """
    Returns a new connection object to the database.
    Sets row_factory for easy column access by name.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name (e.g., row['username'])
    return conn


def get_user_by_id(user_id):
    """
    Fetches a single user row by their ID and returns it as a JSON string.
    Returns a JSON string of the user data, or None if not found.
    """
    conn = get_db_connection()
    if conn is None:
        return None # Could not establish database connection

    cursor = conn.cursor()
    user_json = None # Initialize to None

    try:
        # Use a placeholder (?) for the ID in the SQL query
        # Pass the ID as a tuple to the execute method
        cursor.execute("SELECT id, messages FROM history WHERE id = ?", (user_id,))
        user_row = cursor.fetchone() # fetchone() retrieves the next row as a sqlite3.Row object

        if user_row:
            # Convert the sqlite3.Row object to a Python dictionary
            user_dict = dict(user_row)
            
            # Convert the dictionary to a JSON string
            # `indent=4` makes the JSON output more readable (pretty-printed)
            user_json = json.dumps(user_dict, indent=4)
            print("added user")
        else:
            # If no user is found, user_json remains None
            pass # No user found, return None as per the docstring (implicit)

    except sqlite3.Error as e:
        print(f"Error fetching user by ID {user_id}: {e}")
    except TypeError as e:
        # This might happen if row_factory is not set correctly and user_row is a tuple
        print(f"Error converting row to dict (is row_factory set?): {e}")
    finally:
        if conn: # Ensure connection is closed even if an error occurs
            conn.close()
            
    return user_json

def add_user(messages: str):
    conn = get_db_connection()
    if conn is None:
        return None # Could not establish database connection

    cursor = conn.cursor()
    new_user_id = None

    try:
        # Insert the new user data into the history table
        cursor.execute("INSERT INTO history (messages) VALUES (?)", (messages,))
        conn.commit() # Commit the changes to save them to the database
        new_user_id = cursor.lastrowid # Get the ID of the last inserted row
    except sqlite3.Error as e:
        print(f"Error adding new user: {e}")
        conn.rollback() # Rollback changes if an error occurs
    finally:
        if conn:
            conn.close()
    
    return new_user_id 

if __name__ == "__main__":
    print("history.py is running directly!")