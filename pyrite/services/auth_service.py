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

    # ── Invite codes ──────────────────────────────────────────────

    def create_invite_code(
        self, created_by: str, role: str = "write", note: str = "", expires_hours: int | None = None
    ) -> dict:
        """Generate a new invite code. Only admins should call this."""
        code = secrets.token_urlsafe(16)
        now = datetime.now(UTC).isoformat()
        expires_at = None
        if expires_hours:
            expires_at = (datetime.now(UTC) + timedelta(hours=expires_hours)).isoformat()
        self.db.execute_write_sql(
            """INSERT INTO invite_code (code, created_by, created_at, expires_at, role, note)
            VALUES (:code, :created_by, :now, :expires_at, :role, :note)""",
            {"code": code, "created_by": created_by, "now": now,
             "expires_at": expires_at, "role": role, "note": note},
        )
        return {"code": code, "role": role, "expires_at": expires_at, "note": note}

    def list_invite_codes(self) -> list[dict]:
        """List all invite codes with usage status."""
        return self.db.execute_sql(
            "SELECT code, created_by, created_at, expires_at, used_by, used_at, role, note FROM invite_code ORDER BY created_at DESC"
        )

    def validate_invite_code(self, code: str) -> dict | None:
        """Validate an invite code. Returns code info or None if invalid."""
        rows = self.db.execute_sql(
            "SELECT * FROM invite_code WHERE code = :code", {"code": code}
        )
        if not rows:
            return None
        row = rows[0]
        if row.get("used_by"):
            return None  # Already used
        if row.get("expires_at"):
            try:
                expires = datetime.fromisoformat(row["expires_at"])
                if datetime.now(UTC) > expires:
                    return None  # Expired
            except (ValueError, TypeError):
                pass
        return row

    def _redeem_invite_code(self, code: str, username: str) -> str:
        """Mark an invite code as used. Returns the role from the code."""
        now = datetime.now(UTC).isoformat()
        self.db.execute_write_sql(
            "UPDATE invite_code SET used_by = :username, used_at = :now WHERE code = :code",
            {"username": username, "now": now, "code": code},
        )
        rows = self.db.execute_sql(
            "SELECT role FROM invite_code WHERE code = :code", {"code": code}
        )
        return rows[0]["role"] if rows else "read"

    def delete_invite_code(self, code: str) -> bool:
        """Delete an unused invite code."""
        rows = self.db.execute_sql(
            "SELECT used_by FROM invite_code WHERE code = :code", {"code": code}
        )
        if not rows:
            return False
        if rows[0].get("used_by"):
            raise ValueError("Cannot delete a used invite code")
        self.db.execute_write_sql(
            "DELETE FROM invite_code WHERE code = :code", {"code": code}
        )
        return True

    # ── Registration ──────────────────────────────────────────────

    def register(self, username: str, password: str, display_name: str | None = None,
                 invite_code: str | None = None) -> dict:
        """Create a new local user.

        First registered user gets 'admin' role; subsequent users get role from
        invite code (or 'read' default).
        Raises ValueError if username is taken, registration is disabled, or
        invite code is required but invalid.
        """
        if not self.config.allow_registration:
            raise ValueError("Registration is disabled")

        # Validate invite code if required
        invite_role = None
        if self.config.require_invite_code:
            if not invite_code:
                raise ValueError("An invite code is required to register")
            code_info = self.validate_invite_code(invite_code)
            if not code_info:
                raise ValueError("Invalid or expired invite code")
            invite_role = code_info.get("role", "write")

        if not username or not password:
            raise ValueError("Username and password are required")

        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Check if username exists
        rows = self.db.execute_sql(
            "SELECT id FROM local_user WHERE username = :username",
            {"username": username},
        )
        if rows:
            raise ValueError("Username already taken")

        # First user gets admin role; invite code overrides default role
        count_rows = self.db.execute_sql("SELECT COUNT(*) AS cnt FROM local_user")
        count = count_rows[0]["cnt"] if count_rows else 0
        if count == 0:
            role = "admin"
        elif invite_role:
            role = invite_role
        else:
            role = "read"

        password_hash = self._hash_password(password)
        now = datetime.now(UTC).isoformat()

        self.db.execute_write_sql(
            """INSERT INTO local_user
            (username, display_name, password_hash, role, auth_provider, created_at, updated_at)
            VALUES (:username, :display_name, :password_hash, :role, 'local', :now, :now2)""",
            {
                "username": username,
                "display_name": display_name,
                "password_hash": password_hash,
                "role": role,
                "now": now,
                "now2": now,
            },
        )

        # Redeem invite code if one was used
        if invite_code and invite_role:
            self._redeem_invite_code(invite_code, username)

        rows = self.db.execute_sql(
            "SELECT id FROM local_user WHERE username = :username",
            {"username": username},
        )
        user_id = rows[0]["id"]

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
        rows = self.db.execute_sql(
            "SELECT id, username, display_name, password_hash, role, auth_provider, avatar_url"
            " FROM local_user WHERE username = :username",
            {"username": username},
        )
        if not rows:
            raise ValueError("Invalid username or password")

        row = rows[0]
        user_id = row["id"]
        uname = row["username"]
        display_name = row["display_name"]
        password_hash = row["password_hash"]
        role = row["role"]
        auth_provider = row["auth_provider"]
        avatar_url = row["avatar_url"]

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

        self.db.execute_write_sql(
            """INSERT INTO session (token_hash, user_id, created_at, expires_at, last_used)
            VALUES (:token_hash, :user_id, :created_at, :expires_at, :last_used)""",
            {
                "token_hash": token_hash,
                "user_id": user_id,
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "last_used": now.isoformat(),
            },
        )

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
        rows = self.db.execute_sql(
            "SELECT id, username, display_name, role, avatar_url"
            " FROM local_user WHERE auth_provider = :provider AND provider_id = :provider_id",
            {"provider": profile.provider, "provider_id": profile.provider_id},
        )

        now = datetime.now(UTC).isoformat()

        if rows:
            row = rows[0]
            user_id = row["id"]
            username = row["username"]
            display_name = row["display_name"]
            existing_role = row["role"]
            # Update avatar and display name
            self.db.execute_write_sql(
                "UPDATE local_user SET avatar_url = :avatar_url, display_name = :display_name,"
                " updated_at = :now WHERE id = :user_id",
                {
                    "avatar_url": profile.avatar_url,
                    "display_name": profile.display_name or display_name,
                    "now": now,
                    "user_id": user_id,
                },
            )
            role = existing_role  # preserve existing role
        else:
            # 4. New user — handle username conflict with local users
            username = profile.username
            conflict = self.db.execute_sql(
                "SELECT id FROM local_user WHERE username = :username",
                {"username": username},
            )
            if conflict:
                username = f"{profile.provider}:{profile.username}"

            # First OAuth user gets admin if no users exist at all
            count_rows = self.db.execute_sql("SELECT COUNT(*) AS cnt FROM local_user")
            count = count_rows[0]["cnt"] if count_rows else 0
            if count == 0:
                role = "admin"

            self.db.execute_write_sql(
                """INSERT INTO local_user
                (username, display_name, password_hash, role, auth_provider, provider_id,
                 avatar_url, created_at, updated_at)
                VALUES (:username, :display_name, '', :role, :provider, :provider_id,
                 :avatar_url, :now, :now2)""",
                {
                    "username": username,
                    "display_name": profile.display_name,
                    "role": role,
                    "provider": profile.provider,
                    "provider_id": profile.provider_id,
                    "avatar_url": profile.avatar_url,
                    "now": now,
                    "now2": now,
                },
            )
            id_rows = self.db.execute_sql(
                "SELECT id FROM local_user WHERE username = :username",
                {"username": username},
            )
            user_id = id_rows[0]["id"]

        # 5. Create session
        self._enforce_max_sessions(user_id)
        raw_token, token_hash = self._generate_token()
        now_dt = datetime.now(UTC)
        expires_at = now_dt + timedelta(hours=self.config.session_ttl_hours)
        self.db.execute_write_sql(
            """INSERT INTO session (token_hash, user_id, created_at, expires_at, last_used)
            VALUES (:token_hash, :user_id, :created_at, :expires_at, :last_used)""",
            {
                "token_hash": token_hash,
                "user_id": user_id,
                "created_at": now_dt.isoformat(),
                "expires_at": expires_at.isoformat(),
                "last_used": now_dt.isoformat(),
            },
        )

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

        # Probabilistic cleanup (1 in 20 calls)
        if secrets.randbelow(20) == 0:
            self._cleanup_expired()

        rows = self.db.execute_sql(
            """SELECT s.id, s.user_id, s.expires_at,
                      u.username, u.display_name, u.role, u.auth_provider, u.avatar_url
            FROM session s JOIN local_user u ON s.user_id = u.id
            WHERE s.token_hash = :token_hash""",
            {"token_hash": token_hash},
        )

        if not rows:
            return None

        row = rows[0]
        session_id = row["id"]
        user_id = row["user_id"]
        expires_at = row["expires_at"]
        username = row["username"]
        display_name = row["display_name"]
        role = row["role"]
        auth_provider = row["auth_provider"]
        avatar_url = row["avatar_url"]

        # Check expiry
        if datetime.fromisoformat(expires_at) < datetime.now(UTC):
            self.db.execute_write_sql(
                "DELETE FROM session WHERE id = :session_id",
                {"session_id": session_id},
            )
            return None

        # Update last_used
        self.db.execute_write_sql(
            "UPDATE session SET last_used = :last_used WHERE id = :session_id",
            {"last_used": datetime.now(UTC).isoformat(), "session_id": session_id},
        )

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
        rowcount = self.db.execute_write_sql(
            "DELETE FROM session WHERE token_hash = :token_hash",
            {"token_hash": token_hash},
        )
        return rowcount > 0

    def logout_all(self, user_id: int) -> int:
        """Delete all sessions for a user. Returns count deleted."""
        return self.db.execute_write_sql(
            "DELETE FROM session WHERE user_id = :user_id",
            {"user_id": user_id},
        )

    def get_user(self, user_id: int) -> dict | None:
        """Get user by ID."""
        rows = self.db.execute_sql(
            "SELECT id, username, display_name, role, auth_provider, avatar_url"
            " FROM local_user WHERE id = :user_id",
            {"user_id": user_id},
        )
        if not rows:
            return None
        return rows[0]

    def set_role(self, user_id: int, role: str) -> bool:
        """Set user role. Returns True if user found."""
        if role not in ("read", "write", "admin"):
            raise ValueError(f"Invalid role: {role}")
        rowcount = self.db.execute_write_sql(
            "UPDATE local_user SET role = :role, updated_at = :now WHERE id = :user_id",
            {"role": role, "now": datetime.now(UTC).isoformat(), "user_id": user_id},
        )
        return rowcount > 0

    def _cleanup_expired(self) -> int:
        """Delete expired sessions."""
        now = datetime.now(UTC).isoformat()
        deleted = self.db.execute_write_sql(
            "DELETE FROM session WHERE expires_at < :now", {"now": now}
        )
        if deleted:
            logger.debug("Cleaned up %d expired sessions", deleted)
        return deleted

    def _enforce_max_sessions(self, user_id: int) -> None:
        """Delete oldest sessions if user has too many."""
        count_rows = self.db.execute_sql(
            "SELECT COUNT(*) AS cnt FROM session WHERE user_id = :user_id",
            {"user_id": user_id},
        )
        count = count_rows[0]["cnt"] if count_rows else 0

        if count >= self.config.max_sessions_per_user:
            # Delete oldest sessions to make room
            excess = count - self.config.max_sessions_per_user + 1
            self.db.execute_write_sql(
                """DELETE FROM session WHERE id IN (
                    SELECT id FROM session WHERE user_id = :user_id
                    ORDER BY created_at ASC LIMIT :excess
                )""",
                {"user_id": user_id, "excess": excess},
            )

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
        if user_id is not None:
            # Check if global admin
            rows = self.db.execute_sql(
                "SELECT role FROM local_user WHERE id = :user_id",
                {"user_id": user_id},
            )
            if rows and rows[0]["role"] == "admin":
                return "admin"

            # Check explicit KB grant
            perm_rows = self.db.execute_sql(
                "SELECT role FROM kb_permission WHERE user_id = :user_id AND kb_name = :kb_name",
                {"user_id": user_id, "kb_name": kb_name},
            )
            if perm_rows:
                return perm_rows[0]["role"]

            # KB default_role
            if kb_default_role is not None and kb_default_role != "none":
                return kb_default_role

            # Fall back to user's global role
            if rows:
                # If KB is private (default_role="none"), deny unless explicit grant
                if kb_default_role == "none":
                    return None
                return rows[0]["role"]

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
        now = datetime.now(UTC).isoformat()
        self.db.execute_write_sql(
            """INSERT INTO kb_permission (user_id, kb_name, role, granted_by, created_at)
            VALUES (:user_id, :kb_name, :role, :granted_by, :now)
            ON CONFLICT(user_id, kb_name) DO UPDATE SET role = :role2, granted_by = :granted_by2, created_at = :now2""",
            {
                "user_id": user_id,
                "kb_name": kb_name,
                "role": role,
                "granted_by": granted_by,
                "now": now,
                "role2": role,
                "granted_by2": granted_by,
                "now2": now,
            },
        )

    def revoke_kb_permission(self, user_id: int, kb_name: str) -> bool:
        """Revoke a per-KB permission. Returns True if found."""
        rowcount = self.db.execute_write_sql(
            "DELETE FROM kb_permission WHERE user_id = :user_id AND kb_name = :kb_name",
            {"user_id": user_id, "kb_name": kb_name},
        )
        return rowcount > 0

    def list_kb_permissions(self, kb_name: str) -> list[dict]:
        """List all permission grants for a KB."""
        return self.db.execute_sql(
            """SELECT kp.user_id, u.username, kp.role, kp.granted_by, kp.created_at
            FROM kb_permission kp
            JOIN local_user u ON kp.user_id = u.id
            WHERE kp.kb_name = :kb_name
            ORDER BY kp.created_at""",
            {"kb_name": kb_name},
        )

    def list_users(self) -> list[dict]:
        """List all local users (excluding password hashes)."""
        return self.db.execute_sql(
            "SELECT id, username, display_name, role, auth_provider, avatar_url "
            "FROM local_user ORDER BY username"
        )

    def get_user_kb_permissions(self, user_id: int) -> dict[str, str]:
        """Get all explicit KB grants for a user. Returns {kb_name: role}."""
        rows = self.db.execute_sql(
            "SELECT kb_name, role FROM kb_permission WHERE user_id = :user_id",
            {"user_id": user_id},
        )
        return {r["kb_name"]: r["role"] for r in rows}

    # =====================================================================
    # GitHub Token Management
    # =====================================================================

    @staticmethod
    def _get_encryption_key() -> bytes | None:
        """Get encryption key from environment. Returns None if not configured."""
        import base64
        import hashlib
        import os

        raw_key = os.environ.get("PYRITE_ENCRYPTION_KEY")
        if not raw_key:
            return None
        # Derive a 32-byte Fernet-compatible key from the raw secret
        key_bytes = hashlib.sha256(raw_key.encode()).digest()
        return base64.urlsafe_b64encode(key_bytes)

    @staticmethod
    def _encrypt_token(token: str, key: bytes) -> str:
        """Encrypt a token string using Fernet symmetric encryption."""
        from cryptography.fernet import Fernet

        f = Fernet(key)
        return f.encrypt(token.encode()).decode()

    @staticmethod
    def _decrypt_token(encrypted: str, key: bytes) -> str:
        """Decrypt a Fernet-encrypted token string."""
        from cryptography.fernet import Fernet

        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()

    def store_github_token(self, user_id: int, token: str, scopes: str = "public_repo") -> None:
        """Store a GitHub access token for a user. Encrypts if PYRITE_ENCRYPTION_KEY is set."""
        key = self._get_encryption_key()
        stored_value = self._encrypt_token(token, key) if key else token

        self.db.execute_write_sql(
            "UPDATE local_user SET github_access_token = :token, github_token_scopes = :scopes,"
            " updated_at = :now WHERE id = :user_id",
            {
                "token": stored_value,
                "scopes": scopes,
                "now": datetime.now(UTC).isoformat(),
                "user_id": user_id,
            },
        )

    def get_github_token_for_user(self, user_id: int) -> tuple[str | None, str | None]:
        """Get GitHub token and scopes for a user. Decrypts if encrypted. Returns (token, scopes)."""
        rows = self.db.execute_sql(
            "SELECT github_access_token, github_token_scopes FROM local_user WHERE id = :user_id",
            {"user_id": user_id},
        )
        if not rows or not rows[0]["github_access_token"]:
            scopes = rows[0]["github_token_scopes"] if rows else None
            return None, scopes

        raw_token = rows[0]["github_access_token"]
        scopes = rows[0]["github_token_scopes"]
        key = self._get_encryption_key()
        if key:
            try:
                return self._decrypt_token(raw_token, key), scopes
            except Exception:
                # Token may be stored as plaintext from before encryption was enabled
                return raw_token, scopes
        return raw_token, scopes

    def clear_github_token(self, user_id: int) -> bool:
        """Remove stored GitHub token. Returns True if user found."""
        rowcount = self.db.execute_write_sql(
            "UPDATE local_user SET github_access_token = NULL, github_token_scopes = NULL,"
            " updated_at = :now WHERE id = :user_id",
            {"now": datetime.now(UTC).isoformat(), "user_id": user_id},
        )
        return rowcount > 0

    def create_user_ephemeral_kb(self, user_id: int, ephemeral_service, name: str | None = None) -> dict:
        """Create an ephemeral KB for a user with per-KB admin grant.

        Checks ephemeral_min_tier, ephemeral_max_per_user limits.
        Raises ValueError on policy violation.
        """
        # Check user tier against ephemeral_min_tier
        rows = self.db.execute_sql(
            "SELECT role, ephemeral_kb_count FROM local_user WHERE id = :user_id",
            {"user_id": user_id},
        )
        if not rows:
            raise ValueError("User not found")

        user_role = rows[0]["role"]
        current_count = rows[0]["ephemeral_kb_count"] or 0

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
        kb = ephemeral_service.create_ephemeral_kb(
            name, ttl=ttl, description=f"Ephemeral KB for user {user_id}"
        )

        # Set KB as private by default
        kb.default_role = "none"

        # Grant creator admin on the KB
        now = datetime.now(UTC).isoformat()
        self.db.execute_write_sql(
            """INSERT INTO kb_permission (user_id, kb_name, role, granted_by, created_at)
            VALUES (:user_id, :kb_name, 'admin', :granted_by, :now)""",
            {"user_id": user_id, "kb_name": name, "granted_by": user_id, "now": now},
            commit=False,
        )

        # Increment ephemeral_kb_count
        self.db.execute_write_sql(
            "UPDATE local_user SET ephemeral_kb_count = ephemeral_kb_count + 1"
            " WHERE id = :user_id",
            {"user_id": user_id},
        )

        return {
            "name": kb.name,
            "path": str(kb.path),
            "ephemeral": True,
            "ttl": ttl,
        }
