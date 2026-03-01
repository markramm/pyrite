"""
Authentication Service for Web UI

Provides local username/password authentication with session tokens.
Uses bcrypt for password hashing and SHA-256 hashed opaque tokens for sessions.
"""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt as _bcrypt

from ..config import AuthConfig
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


class AuthService:
    """Manages local user authentication and session tokens."""

    def __init__(self, db: PyriteDB, auth_config: AuthConfig):
        self.db = db
        self.config = auth_config

    def register(
        self, username: str, password: str, display_name: str | None = None
    ) -> dict:
        """Create a new local user.

        First registered user gets 'admin' role; subsequent users get 'read'.
        Raises ValueError if username is taken or registration is disabled.
        """
        if not self.config.allow_registration:
            raise ValueError("Registration is disabled")

        if not username or not password:
            raise ValueError("Username and password are required")

        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        conn = self.db._raw_conn

        # Check if username exists
        row = conn.execute(
            "SELECT id FROM local_user WHERE username = ?", (username,)
        ).fetchone()
        if row:
            raise ValueError("Username already taken")

        # First user gets admin role
        count = conn.execute("SELECT COUNT(*) FROM local_user").fetchone()[0]
        role = "admin" if count == 0 else "read"

        password_hash = self._hash_password(password)
        now = datetime.now(UTC).isoformat()

        conn.execute(
            """INSERT INTO local_user (username, display_name, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (username, display_name, password_hash, role, now, now),
        )
        conn.commit()

        user_id = conn.execute(
            "SELECT id FROM local_user WHERE username = ?", (username,)
        ).fetchone()[0]

        return {
            "id": user_id,
            "username": username,
            "display_name": display_name,
            "role": role,
        }

    def login(self, username: str, password: str) -> tuple[dict, str]:
        """Authenticate user and create session.

        Returns (user_dict, raw_token). Raises ValueError on bad credentials.
        """
        conn = self.db._raw_conn

        row = conn.execute(
            "SELECT id, username, display_name, password_hash, role FROM local_user WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            raise ValueError("Invalid username or password")

        user_id, uname, display_name, password_hash, role = row

        if not self._verify_password(password, password_hash):
            raise ValueError("Invalid username or password")

        # Enforce max sessions per user
        self._enforce_max_sessions(user_id)

        # Create session
        raw_token, token_hash = self._generate_token()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=self.config.session_ttl_hours)

        conn.execute(
            """INSERT INTO session (token_hash, user_id, created_at, expires_at, last_used)
            VALUES (?, ?, ?, ?, ?)""",
            (token_hash, user_id, now.isoformat(), expires_at.isoformat(), now.isoformat()),
        )
        conn.commit()

        user = {
            "id": user_id,
            "username": uname,
            "display_name": display_name,
            "role": role,
        }
        return user, raw_token

    def verify_session(self, token: str) -> dict | None:
        """Look up session by SHA-256(token).

        Returns user dict or None if expired/invalid. Updates last_used.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        conn = self.db._raw_conn

        # Probabilistic cleanup (1 in 20 calls)
        if secrets.randbelow(20) == 0:
            self._cleanup_expired()

        row = conn.execute(
            """SELECT s.id, s.user_id, s.expires_at, u.username, u.display_name, u.role
            FROM session s JOIN local_user u ON s.user_id = u.id
            WHERE s.token_hash = ?""",
            (token_hash,),
        ).fetchone()

        if not row:
            return None

        session_id, user_id, expires_at, username, display_name, role = row

        # Check expiry
        if datetime.fromisoformat(expires_at) < datetime.now(UTC):
            conn.execute("DELETE FROM session WHERE id = ?", (session_id,))
            conn.commit()
            return None

        # Update last_used
        conn.execute(
            "UPDATE session SET last_used = ? WHERE id = ?",
            (datetime.now(UTC).isoformat(), session_id),
        )
        conn.commit()

        return {
            "id": user_id,
            "username": username,
            "display_name": display_name,
            "role": role,
        }

    def logout(self, token: str) -> bool:
        """Delete session by token. Returns True if found."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        conn = self.db._raw_conn
        cursor = conn.execute("DELETE FROM session WHERE token_hash = ?", (token_hash,))
        conn.commit()
        return cursor.rowcount > 0

    def logout_all(self, user_id: int) -> int:
        """Delete all sessions for a user. Returns count deleted."""
        conn = self.db._raw_conn
        cursor = conn.execute("DELETE FROM session WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount

    def get_user(self, user_id: int) -> dict | None:
        """Get user by ID."""
        conn = self.db._raw_conn
        row = conn.execute(
            "SELECT id, username, display_name, role FROM local_user WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "display_name": row[2],
            "role": row[3],
        }

    def set_role(self, user_id: int, role: str) -> bool:
        """Set user role. Returns True if user found."""
        if role not in ("read", "write", "admin"):
            raise ValueError(f"Invalid role: {role}")
        conn = self.db._raw_conn
        cursor = conn.execute(
            "UPDATE local_user SET role = ?, updated_at = ? WHERE id = ?",
            (role, datetime.now(UTC).isoformat(), user_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def _cleanup_expired(self) -> int:
        """Delete expired sessions."""
        conn = self.db._raw_conn
        now = datetime.now(UTC).isoformat()
        cursor = conn.execute("DELETE FROM session WHERE expires_at < ?", (now,))
        conn.commit()
        deleted = cursor.rowcount
        if deleted:
            logger.debug("Cleaned up %d expired sessions", deleted)
        return deleted

    def _enforce_max_sessions(self, user_id: int) -> None:
        """Delete oldest sessions if user has too many."""
        conn = self.db._raw_conn
        count = conn.execute(
            "SELECT COUNT(*) FROM session WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

        if count >= self.config.max_sessions_per_user:
            # Delete oldest sessions to make room
            excess = count - self.config.max_sessions_per_user + 1
            conn.execute(
                """DELETE FROM session WHERE id IN (
                    SELECT id FROM session WHERE user_id = ?
                    ORDER BY created_at ASC LIMIT ?
                )""",
                (user_id, excess),
            )
            conn.commit()

    def _hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()

    def _verify_password(self, password: str, pw_hash: str) -> bool:
        """Verify password against bcrypt hash."""
        return _bcrypt.checkpw(password.encode(), pw_hash.encode())

    def _generate_token(self) -> tuple[str, str]:
        """Generate a session token. Returns (raw_token, sha256_hash)."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        return raw_token, token_hash
