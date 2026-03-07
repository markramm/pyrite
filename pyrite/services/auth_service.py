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

from ..config import AuthConfig, OAuthProviderConfig
from ..services.oauth_providers import OAuthProfile
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


class AuthService:
    """Manages local user authentication and session tokens."""

    def __init__(self, db: PyriteDB, auth_config: AuthConfig):
        self.db = db
        self.config = auth_config

    def register(self, username: str, password: str, display_name: str | None = None) -> dict:
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
        row = conn.execute("SELECT id FROM local_user WHERE username = ?", (username,)).fetchone()
        if row:
            raise ValueError("Username already taken")

        # First user gets admin role
        count = conn.execute("SELECT COUNT(*) FROM local_user").fetchone()[0]
        role = "admin" if count == 0 else "read"

        password_hash = self._hash_password(password)
        now = datetime.now(UTC).isoformat()

        conn.execute(
            """INSERT INTO local_user
            (username, display_name, password_hash, role, auth_provider, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'local', ?, ?)""",
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
            "auth_provider": "local",
            "avatar_url": None,
        }

    def login(self, username: str, password: str) -> tuple[dict, str]:
        """Authenticate user and create session.

        Returns (user_dict, raw_token). Raises ValueError on bad credentials.
        """
        conn = self.db._raw_conn

        row = conn.execute(
            "SELECT id, username, display_name, password_hash, role, auth_provider, avatar_url"
            " FROM local_user WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            raise ValueError("Invalid username or password")

        user_id, uname, display_name, password_hash, role, auth_provider, avatar_url = row

        # Block password login for OAuth-only users
        if auth_provider != "local":
            raise ValueError("This account uses external authentication")

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
            "auth_provider": auth_provider,
            "avatar_url": avatar_url,
        }
        return user, raw_token

    def oauth_login(
        self, profile: OAuthProfile, provider_config: OAuthProviderConfig
    ) -> tuple[dict, str]:
        """Create or update an OAuth user and return (user_dict, raw_token).

        Raises ValueError if the user's orgs don't match allowed_orgs.
        """
        conn = self.db._raw_conn

        # 1. Check org restrictions
        if provider_config.allowed_orgs:
            if not set(profile.orgs) & set(provider_config.allowed_orgs):
                raise ValueError("Your GitHub account is not a member of an allowed organization")

        # 2. Determine role from org_tier_map or default_tier
        role = provider_config.default_tier
        if provider_config.org_tier_map:
            role_priority = {"read": 0, "write": 1, "admin": 2}
            for org in profile.orgs:
                mapped = provider_config.org_tier_map.get(org)
                if mapped and role_priority.get(mapped, -1) > role_priority.get(role, -1):
                    role = mapped

        # 3. Look up existing OAuth user
        row = conn.execute(
            "SELECT id, username, display_name, role, avatar_url"
            " FROM local_user WHERE auth_provider = ? AND provider_id = ?",
            (profile.provider, profile.provider_id),
        ).fetchone()

        now = datetime.now(UTC).isoformat()

        if row:
            user_id, username, display_name, existing_role, _ = row
            # Update avatar and display name
            conn.execute(
                "UPDATE local_user SET avatar_url = ?, display_name = ?, updated_at = ? WHERE id = ?",
                (profile.avatar_url, profile.display_name or display_name, now, user_id),
            )
            conn.commit()
            role = existing_role  # preserve existing role
        else:
            # 4. New user — handle username conflict with local users
            username = profile.username
            conflict = conn.execute(
                "SELECT id FROM local_user WHERE username = ?", (username,)
            ).fetchone()
            if conflict:
                username = f"{profile.provider}:{profile.username}"

            # First OAuth user gets admin if no users exist at all
            count = conn.execute("SELECT COUNT(*) FROM local_user").fetchone()[0]
            if count == 0:
                role = "admin"

            conn.execute(
                """INSERT INTO local_user
                (username, display_name, password_hash, role, auth_provider, provider_id,
                 avatar_url, created_at, updated_at)
                VALUES (?, ?, '', ?, ?, ?, ?, ?, ?)""",
                (
                    username,
                    profile.display_name,
                    role,
                    profile.provider,
                    profile.provider_id,
                    profile.avatar_url,
                    now,
                    now,
                ),
            )
            conn.commit()
            user_id = conn.execute(
                "SELECT id FROM local_user WHERE username = ?", (username,)
            ).fetchone()[0]

        # 5. Create session
        self._enforce_max_sessions(user_id)
        raw_token, token_hash = self._generate_token()
        now_dt = datetime.now(UTC)
        expires_at = now_dt + timedelta(hours=self.config.session_ttl_hours)
        conn.execute(
            """INSERT INTO session (token_hash, user_id, created_at, expires_at, last_used)
            VALUES (?, ?, ?, ?, ?)""",
            (token_hash, user_id, now_dt.isoformat(), expires_at.isoformat(), now_dt.isoformat()),
        )
        conn.commit()

        user = {
            "id": user_id,
            "username": username,
            "display_name": profile.display_name,
            "role": role,
            "auth_provider": profile.provider,
            "avatar_url": profile.avatar_url,
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
            """SELECT s.id, s.user_id, s.expires_at,
                      u.username, u.display_name, u.role, u.auth_provider, u.avatar_url
            FROM session s JOIN local_user u ON s.user_id = u.id
            WHERE s.token_hash = ?""",
            (token_hash,),
        ).fetchone()

        if not row:
            return None

        session_id, user_id, expires_at, username, display_name, role, auth_provider, avatar_url = (
            row
        )

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
            "auth_provider": auth_provider,
            "avatar_url": avatar_url,
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
            "SELECT id, username, display_name, role, auth_provider, avatar_url"
            " FROM local_user WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "display_name": row[2],
            "role": row[3],
            "auth_provider": row[4],
            "avatar_url": row[5],
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

    # =====================================================================
    # Per-KB Permissions
    # =====================================================================

    def get_kb_role(
        self, user_id: int | None, kb_name: str, kb_default_role: str | None = None
    ) -> str | None:
        """Resolve effective role for a user on a KB.

        Resolution chain:
        1. Global admin always returns "admin"
        2. Explicit kb_permission grant
        3. KB default_role
        4. User global role
        5. Anonymous tier (when user_id is None)
        """
        conn = self.db._raw_conn

        if user_id is not None:
            # Check if global admin
            row = conn.execute("SELECT role FROM local_user WHERE id = ?", (user_id,)).fetchone()
            if row and row[0] == "admin":
                return "admin"

            # Check explicit KB grant
            row = conn.execute(
                "SELECT role FROM kb_permission WHERE user_id = ? AND kb_name = ?",
                (user_id, kb_name),
            ).fetchone()
            if row:
                return row[0]

            # KB default_role
            if kb_default_role is not None and kb_default_role != "none":
                return kb_default_role

            # Fall back to user's global role
            row = conn.execute("SELECT role FROM local_user WHERE id = ?", (user_id,)).fetchone()
            if row:
                # If KB is private (default_role="none"), deny unless explicit grant
                if kb_default_role == "none":
                    return None
                return row[0]

        # Anonymous user
        if kb_default_role is not None and kb_default_role != "none":
            return kb_default_role
        if kb_default_role == "none":
            return None
        return self.config.anonymous_tier

    def grant_kb_permission(self, user_id: int, kb_name: str, role: str, granted_by: int) -> None:
        """Grant or update a per-KB permission."""
        if role not in ("read", "write", "admin"):
            raise ValueError(f"Invalid role: {role}")
        conn = self.db._raw_conn
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """INSERT INTO kb_permission (user_id, kb_name, role, granted_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, kb_name) DO UPDATE SET role = ?, granted_by = ?, created_at = ?""",
            (user_id, kb_name, role, granted_by, now, role, granted_by, now),
        )
        conn.commit()

    def revoke_kb_permission(self, user_id: int, kb_name: str) -> bool:
        """Revoke a per-KB permission. Returns True if found."""
        conn = self.db._raw_conn
        cursor = conn.execute(
            "DELETE FROM kb_permission WHERE user_id = ? AND kb_name = ?",
            (user_id, kb_name),
        )
        conn.commit()
        return cursor.rowcount > 0

    def list_kb_permissions(self, kb_name: str) -> list[dict]:
        """List all permission grants for a KB."""
        conn = self.db._raw_conn
        rows = conn.execute(
            """SELECT kp.user_id, u.username, kp.role, kp.granted_by, kp.created_at
            FROM kb_permission kp
            JOIN local_user u ON kp.user_id = u.id
            WHERE kp.kb_name = ?
            ORDER BY kp.created_at""",
            (kb_name,),
        ).fetchall()
        return [
            {
                "user_id": r[0],
                "username": r[1],
                "role": r[2],
                "granted_by": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]

    def list_users(self) -> list[dict]:
        """List all local users (excluding password hashes)."""
        conn = self.db._raw_conn
        rows = conn.execute(
            "SELECT id, username, display_name, role, auth_provider, avatar_url "
            "FROM local_user ORDER BY username"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_user_kb_permissions(self, user_id: int) -> dict[str, str]:
        """Get all explicit KB grants for a user. Returns {kb_name: role}."""
        conn = self.db._raw_conn
        rows = conn.execute(
            "SELECT kb_name, role FROM kb_permission WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    # =====================================================================
    # GitHub Token Management
    # =====================================================================

    def store_github_token(
        self, user_id: int, token: str, scopes: str = "public_repo"
    ) -> None:
        """Store a GitHub access token for a user."""
        conn = self.db._raw_conn
        conn.execute(
            "UPDATE local_user SET github_access_token = ?, github_token_scopes = ?, updated_at = ? WHERE id = ?",
            (token, scopes, datetime.now(UTC).isoformat(), user_id),
        )
        conn.commit()

    def get_github_token_for_user(self, user_id: int) -> tuple[str | None, str | None]:
        """Get GitHub token and scopes for a user. Returns (token, scopes)."""
        conn = self.db._raw_conn
        row = conn.execute(
            "SELECT github_access_token, github_token_scopes FROM local_user WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None, None
        return row[0], row[1]

    def clear_github_token(self, user_id: int) -> bool:
        """Remove stored GitHub token. Returns True if user found."""
        conn = self.db._raw_conn
        cursor = conn.execute(
            "UPDATE local_user SET github_access_token = NULL, github_token_scopes = NULL, updated_at = ? WHERE id = ?",
            (datetime.now(UTC).isoformat(), user_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def create_user_ephemeral_kb(self, user_id: int, kb_service, name: str | None = None) -> dict:
        """Create an ephemeral KB for a user with per-KB admin grant.

        Checks ephemeral_min_tier, ephemeral_max_per_user limits.
        Raises ValueError on policy violation.
        """
        conn = self.db._raw_conn

        # Check user tier against ephemeral_min_tier
        row = conn.execute(
            "SELECT role, ephemeral_kb_count FROM local_user WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            raise ValueError("User not found")

        user_role, current_count = row[0], row[1] or 0

        tier_levels = {"read": 0, "write": 1, "admin": 2}
        min_tier = self.config.ephemeral_min_tier
        if tier_levels.get(user_role, -1) < tier_levels.get(min_tier, 99):
            raise ValueError(
                f"Insufficient tier: requires '{min_tier}', your role is '{user_role}'"
            )

        # Check per-user limit
        if current_count >= self.config.ephemeral_max_per_user:
            raise ValueError(f"Ephemeral KB limit reached ({self.config.ephemeral_max_per_user})")

        # Generate name if not provided
        if not name:
            name = f"ephemeral-{user_id}-{secrets.token_hex(4)}"

        ttl = self.config.ephemeral_default_ttl
        kb = kb_service.create_ephemeral_kb(
            name, ttl=ttl, description=f"Ephemeral KB for user {user_id}"
        )

        # Set KB as private by default
        kb.default_role = "none"

        # Grant creator admin on the KB
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """INSERT INTO kb_permission (user_id, kb_name, role, granted_by, created_at)
            VALUES (?, ?, 'admin', ?, ?)""",
            (user_id, name, user_id, now),
        )

        # Increment ephemeral_kb_count
        conn.execute(
            "UPDATE local_user SET ephemeral_kb_count = ephemeral_kb_count + 1 WHERE id = ?",
            (user_id,),
        )
        conn.commit()

        return {
            "name": kb.name,
            "path": str(kb.path),
            "ephemeral": True,
            "ttl": ttl,
        }
