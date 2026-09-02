"""
Chat Module for Healthcare Blockchain System

Lets a patient and a doctor message each other, but only once a
consultation relationship exists between them (i.e. the patient has
approved that doctor's access request via the Consent Center).

This module owns its own table (chat_messages) and is deliberately
decoupled from ConsentManager -- callers are expected to verify the
patient/doctor connection (e.g. via ConsentManager.check_access) BEFORE
calling send_message. This module does not re-check consent itself so
it stays simple and testable; the app layer is the enforcement point.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional


class ChatManager:
    """
    Manages direct messages between connected patients and doctors.

    Messages are never hard-deleted, so the table doubles as a chat log
    for audit purposes.
    """

    def __init__(self, db_path: str = "healthcare.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the chat_messages table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_read INTEGER DEFAULT 0
            )
        ''')

        # Speeds up "conversation between A and B" lookups.
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chat_sender_receiver
            ON chat_messages (sender_id, receiver_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chat_receiver_sender
            ON chat_messages (receiver_id, sender_id)
        ''')

        conn.commit()
        conn.close()

    @staticmethod
    def _row_to_dict(row) -> Dict:
        return {
            'id': row[0],
            'sender_id': row[1],
            'receiver_id': row[2],
            'message': row[3],
            'created_at': row[4],
            'is_read': bool(row[5]),
        }

    def send_message(self, sender_id: str, receiver_id: str, message: str) -> Optional[Dict]:
        """
        Store a new message. Caller must have already verified the
        sender/receiver are connected (active consent between them).

        Returns the stored message dict, or None if message was empty.
        """
        message = (message or "").strip()
        if not message:
            return None

        # Keep messages to a sane size (this is a chat, not file transfer).
        message = message[:4000]

        created_at = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO chat_messages (sender_id, receiver_id, message, created_at, is_read)
            VALUES (?, ?, ?, ?, 0)
        ''', (sender_id, receiver_id, message, created_at))

        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        return {
            'id': new_id,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'message': message,
            'created_at': created_at,
            'is_read': False,
        }

    def get_conversation(self, user_a: str, user_b: str, limit: int = 200) -> List[Dict]:
        """Get the full (most recent `limit`) messages between two users, oldest first."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM (
                SELECT * FROM chat_messages
                WHERE (sender_id = ? AND receiver_id = ?)
                   OR (sender_id = ? AND receiver_id = ?)
                ORDER BY id DESC
                LIMIT ?
            ) sub
            ORDER BY id ASC
        ''', (user_a, user_b, user_b, user_a, limit))

        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]

    def get_messages_since(self, user_a: str, user_b: str, since_id: int = 0) -> List[Dict]:
        """Get messages between two users newer than since_id, oldest first. Used for polling."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM chat_messages
            WHERE ((sender_id = ? AND receiver_id = ?)
                OR (sender_id = ? AND receiver_id = ?))
              AND id > ?
            ORDER BY id ASC
        ''', (user_a, user_b, user_b, user_a, since_id))

        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]

    def get_last_message(self, user_a: str, user_b: str) -> Optional[Dict]:
        """Get the most recent message in a conversation, if any."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM chat_messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY id DESC
            LIMIT 1
        ''', (user_a, user_b, user_b, user_a))

        row = cursor.fetchone()
        conn.close()
        return self._row_to_dict(row) if row else None

    def mark_read(self, reader_id: str, other_user_id: str) -> int:
        """Mark all messages sent TO reader_id FROM other_user_id as read."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE chat_messages
            SET is_read = 1
            WHERE receiver_id = ? AND sender_id = ? AND is_read = 0
        ''', (reader_id, other_user_id))

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected

    def get_unread_count(self, reader_id: str, other_user_id: str) -> int:
        """Unread message count from a specific sender."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM chat_messages
            WHERE receiver_id = ? AND sender_id = ? AND is_read = 0
        ''', (reader_id, other_user_id))

        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_total_unread(self, reader_id: str) -> int:
        """Total unread messages across all conversations for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM chat_messages
            WHERE receiver_id = ? AND is_read = 0
        ''', (reader_id,))

        count = cursor.fetchone()[0]
        conn.close()
        return count