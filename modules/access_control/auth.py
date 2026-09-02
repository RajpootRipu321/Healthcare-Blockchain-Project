"""Authentication and User Management."""

import hashlib
import secrets
import sqlite3
import os
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash

from .roles import Role, Permission, has_permission


@dataclass
class User:
    """User model for healthcare system."""

    id: str
    username: str
    email: str
    password_hash: str
    role: Role
    full_name: str = ""
    created_at: str = ""
    is_active: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary (without password)."""
        data = asdict(self)
        data['role'] = self.role.value
        del data['password_hash']
        return data

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a permission."""
        return has_permission(self.role, permission)


class AuthManager:
    """
    Authentication manager for user management.

    Handles:
    - User registration
    - Login/logout
    - Password hashing
    - Session management
    """

    def __init__(self, db_path: str = "healthcare.db"):
        """
        Initialize auth manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT,
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        conn.commit()
        conn.close()

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode())
        return f"{salt}${hash_obj.hexdigest()}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, stored_hash = password_hash.split('$')
            hash_obj = hashlib.sha256((password + salt).encode())
            return hash_obj.hexdigest() == stored_hash
        except ValueError:
            return False

    def register(self, username: str, email: str, password: str,
                 role: str = "patient", full_name: str = "") -> Optional[User]:
        """
        Register a new user.

        Args:
            username: Unique username
            email: User email
            password: Plain text password
            role: User role (patient, doctor, admin)
            full_name: Full name

        Returns:
            User object if successful, None otherwise
        """
        try:
            user_role = Role(role)
        except ValueError:
            user_role = Role.PATIENT

        user_id = secrets.token_hex(16)
        password_hash = self.hash_password(password)
        created_at = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO users (id, username, email, password_hash, role, full_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, email, password_hash, user_role.value, full_name, created_at))

            conn.commit()

            return User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                role=user_role,
                full_name=full_name,
                created_at=created_at
            )

        except sqlite3.IntegrityError as e:
            print(f"Registration failed: {e}")
            return None
        finally:
            conn.close()

    def login(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            User object if successful, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, username, email, password_hash, role, full_name, created_at, is_active
            FROM users
            WHERE (username = ? OR email = ?) AND is_active = 1
        ''', (username, username))

        row = cursor.fetchone()
        conn.close()

        if row and self.verify_password(password, row[3]):
            return User(
                id=row[0],
                username=row[1],
                email=row[2],
                password_hash=row[3],
                role=Role(row[4]),
                full_name=row[5] or "",
                created_at=row[6],
                is_active=bool(row[7])
            )

        return None

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, username, email, password_hash, role, full_name, created_at, is_active
            FROM users WHERE id = ?
        ''', (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return User(
                id=row[0],
                username=row[1],
                email=row[2],
                password_hash=row[3],
                role=Role(row[4]),
                full_name=row[5] or "",
                created_at=row[6],
                is_active=bool(row[7])
            )

        return None

    def get_all_users(self) -> List[User]:
        """Get all users."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, username, email, password_hash, role, full_name, created_at, is_active
            FROM users
        ''')

        users = []
        for row in cursor.fetchall():
            users.append(User(
                id=row[0],
                username=row[1],
                email=row[2],
                password_hash=row[3],
                role=Role(row[4]),
                full_name=row[5] or "",
                created_at=row[6],
                is_active=bool(row[7])
            ))

        conn.close()
        return users

    def get_doctors(self) -> List[User]:
        """Get all doctors."""
        return [u for u in self.get_all_users() if u.role == Role.DOCTOR]

    def update_user_role(self, user_id: str, new_role: str) -> bool:
        """Update a user's role."""
        try:
            role = Role(new_role)
        except ValueError:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users SET role = ? WHERE id = ?
        ''', (role.value, user_id))

        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users SET is_active = 0 WHERE id = ?
        ''', (user_id,))

        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0


# Flask decorators for route protection
def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator to require specific roles for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))

            user_role = session.get('user_role')
            if user_role not in [r.value if isinstance(r, Role) else r for r in roles]:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(permission: Permission):
    """Decorator to require specific permission for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))

            user_role = session.get('user_role')
            try:
                role = Role(user_role)
                if not has_permission(role, permission):
                    flash('You do not have permission to perform this action.', 'danger')
                    return redirect(url_for('dashboard'))
            except ValueError:
                flash('Invalid user role.', 'danger')
                return redirect(url_for('login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator
