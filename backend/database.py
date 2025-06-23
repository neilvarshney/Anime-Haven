import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

DATABASE_FILE = 'anime_chatbot.db'

def initialize_database():
    """Initialize the database with all required tables."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print(f"Connected to database: {DATABASE_FILE}")

        # Create users table
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        # Create conversations table
        create_conversations_table = """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """

        # Create messages table
        create_messages_table = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        );
        """

        # Execute all table creation statements
        cursor.executescript(create_users_table + create_conversations_table + create_messages_table)
        conn.commit()
        print("Database tables created successfully.")

    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# User management functions
def create_user(username: str, email: str, password_hash: str) -> Optional[int]:
    """Create a new user and return their ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # Username or email already exists
    except sqlite3.Error as e:
        print(f"Error creating user: {e}")
        return None
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except sqlite3.Error as e:
        print(f"Error fetching user: {e}")
        return None
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[Dict]:
    """Get user by username."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except sqlite3.Error as e:
        print(f"Error fetching user: {e}")
        return None
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except sqlite3.Error as e:
        print(f"Error fetching user: {e}")
        return None
    finally:
        conn.close()

# Conversation management functions
def create_conversation(user_id: int, title: str) -> Optional[int]:
    """Create a new conversation and return its ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
            (user_id, title)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error creating conversation: {e}")
        return None
    finally:
        conn.close()

def get_user_conversations(user_id: int) -> List[Dict]:
    """Get all conversations for a user."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        )
        conversations = cursor.fetchall()
        return [dict(conv) for conv in conversations]
    except sqlite3.Error as e:
        print(f"Error fetching conversations: {e}")
        return []
    finally:
        conn.close()

def get_conversation_by_id(conversation_id: int, user_id: int) -> Optional[Dict]:
    """Get a specific conversation by ID (ensuring user ownership)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id)
        )
        conversation = cursor.fetchone()
        return dict(conversation) if conversation else None
    except sqlite3.Error as e:
        print(f"Error fetching conversation: {e}")
        return None
    finally:
        conn.close()

def update_conversation_title(conversation_id: int, user_id: int, title: str) -> bool:
    """Update conversation title."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (title, conversation_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating conversation: {e}")
        return False
    finally:
        conn.close()

def delete_conversation(conversation_id: int, user_id: int) -> bool:
    """Delete a conversation and all its messages."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting conversation: {e}")
        return False
    finally:
        conn.close()

# Message management functions
def add_message(conversation_id: int, role: str, content: str) -> Optional[int]:
    """Add a message to a conversation."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        conn.commit()
        
        # Update conversation's updated_at timestamp
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        conn.commit()
        
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding message: {e}")
        return None
    finally:
        conn.close()

def get_conversation_messages(conversation_id: int) -> List[Dict]:
    """Get all messages for a conversation."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conversation_id,)
        )
        messages = cursor.fetchall()
        return [dict(msg) for msg in messages]
    except sqlite3.Error as e:
        print(f"Error fetching messages: {e}")
        return []
    finally:
        conn.close()

def get_conversation_with_messages(conversation_id: int, user_id: int) -> Optional[Dict]:
    """Get a conversation with all its messages."""
    conversation = get_conversation_by_id(conversation_id, user_id)
    if not conversation:
        return None
    
    messages = get_conversation_messages(conversation_id)
    conversation['messages'] = messages
    return conversation 