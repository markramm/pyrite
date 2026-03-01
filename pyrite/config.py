"""
Multi-KB Configuration System

Manages configuration for multiple knowledge bases with different types (events, research).
Configuration is loaded from:
1. ~/.pyrite/config.yaml (global)
2. Environment variables (overrides)
3. Individual kb.yaml files in each KB root
"""

import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv

from pyrite.utils.yaml import dump_yaml_file, load_yaml_file

logger = logging.getLogger(__name__)

load_dotenv()


class KBType(StrEnum):
    """Knowledge Base type (legacy compat — prefer string kb_type)."""

    EVENTS = "events"
    RESEARCH = "research"
    GENERIC = "generic"


@dataclass
class KBConfig:
    """Configuration for a single knowledge base."""

    name: str
    path: Path
    kb_type: str = "generic"  # Free-form string: "events", "research", "generic", etc.
    description: str = ""
    read_only: bool = False
    remote: str | None = None  # Git remote URL
    shortname: str | None = None  # Short alias for cross-KB links (e.g. "dev", "ops")
    ephemeral: bool = False  # Marks KB as temporary
    ttl: int | None = None  # TTL in seconds for ephemeral KBs
    created_at_ts: float | None = None  # Creation timestamp for TTL calculation

    # Repository reference (for multi-KB repos)
    repo: str | None = None  # Name of parent repo (if KB is inside a repo)
    repo_subpath: str = ""  # Relative path within repo (e.g., "timeline/events")

    # Loaded from kb.yaml if present
    schema: dict[str, Any] | None = None
    types: dict[str, Any] | None = None
    policies: dict[str, Any] | None = None

    # Internal cache — not serialized
    _schema_cache: Any = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self.path = Path(self.path).expanduser().resolve()
        # Accept enum or string
        if hasattr(self.kb_type, "value"):
            self.kb_type = self.kb_type.value
        self._schema_cache = None

    @property
    def kb_yaml_path(self) -> Path:
        """Path to kb.yaml config file."""
        return self.path / "kb.yaml"

    @property
    def kb_schema(self) -> "Any":
        """Lazily load and cache the KBSchema object for this KB."""
        if self._schema_cache is None:
            from .schema import KBSchema

            schema_path = self.path / "kb.yaml"
            if schema_path.exists():
                self._schema_cache = KBSchema.from_yaml(schema_path)
            else:
                self._schema_cache = KBSchema()
        return self._schema_cache

    def invalidate_schema_cache(self) -> None:
        """Clear cached KBSchema — call after kb.yaml changes."""
        self._schema_cache = None

    @property
    def local_db_path(self) -> Path:
        """Path to local SQLite index for this KB."""
        pyrite_dir = self.path / ".pyrite"
        pyrite_dir.mkdir(exist_ok=True)
        return pyrite_dir / "index.db"

    def load_kb_yaml(self) -> bool:
        """Load kb.yaml if it exists. Returns True if loaded."""
        if self.kb_yaml_path.exists():
            data = load_yaml_file(self.kb_yaml_path)
            self.schema = data.get("schema")
            self.types = data.get("types")
            self.policies = data.get("policies")
            return True
        return False

    def validate(self) -> list[str]:
        """Validate KB configuration. Returns list of errors."""
        errors = []
        if not self.path.exists():
            errors.append(f"KB path does not exist: {self.path}")
        elif not self.path.is_dir():
            errors.append(f"KB path is not a directory: {self.path}")
        return errors


@dataclass
class Repository:
    """
    Configuration for a git repository that may contain one or more KBs.

    Supports both local and remote repos, with optional GitHub OAuth for private repos.
    """

    name: str  # Unique identifier for this repo
    path: Path  # Local path where repo is/will be cloned
    remote: str | None = None  # Git remote URL (https or ssh)
    branch: str = "main"
    auto_sync: bool = True
    sync_interval: int = 3600  # seconds

    # Authentication
    auth_method: Literal["none", "ssh", "github_oauth", "token"] = "none"
    github_app_id: str | None = None  # For GitHub App auth

    # KBs defined within this repo (populated after discovery)
    kb_paths: list[str] = field(default_factory=list)  # Relative paths to KBs

    def __post_init__(self):
        self.path = Path(self.path).expanduser().resolve()

    @property
    def is_remote(self) -> bool:
        """Check if this repo has a remote."""
        return self.remote is not None

    @property
    def is_github(self) -> bool:
        """Check if this is a GitHub repo."""
        if not self.remote:
            return False
        return "github.com" in self.remote

    def validate(self) -> list[str]:
        """Validate repository configuration."""
        errors = []
        if not self.path.exists() and not self.remote:
            errors.append(f"Repository path does not exist and no remote specified: {self.path}")
        if self.auth_method == "github_oauth" and not self.is_github:
            errors.append("GitHub OAuth auth method requires a GitHub remote URL")
        return errors


@dataclass
class GitHubAuth:
    """
    GitHub OAuth configuration for accessing private repositories.

    Supports both OAuth App flow and GitHub App installation tokens.
    """

    # OAuth App credentials (for user authentication)
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_expiry: str | None = None  # ISO datetime

    # GitHub App credentials (for app-based auth)
    app_id: str | None = None
    private_key_path: Path | None = None
    installation_id: str | None = None

    # Scopes requested
    scopes: list[str] = field(default_factory=lambda: ["repo", "read:user"])

    def __post_init__(self):
        if self.private_key_path:
            self.private_key_path = Path(self.private_key_path).expanduser().resolve()

    @property
    def has_oauth_credentials(self) -> bool:
        """Check if OAuth credentials are configured."""
        return bool(self.client_id and self.client_secret)

    @property
    def has_valid_token(self) -> bool:
        """Check if we have a valid access token."""
        if not self.access_token:
            return False
        if self.token_expiry:
            from datetime import datetime

            try:
                expiry = datetime.fromisoformat(self.token_expiry.replace("Z", "+00:00"))
                if datetime.now(expiry.tzinfo) >= expiry:
                    return False
            except Exception:
                logger.warning("Failed to parse token expiry: %s", self.token_expiry, exc_info=True)
        return True

    @property
    def has_app_credentials(self) -> bool:
        """Check if GitHub App credentials are configured."""
        return bool(self.app_id and self.private_key_path and self.installation_id)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (excluding secrets for display)."""
        return {
            "client_id": self.client_id,
            "has_access_token": bool(self.access_token),
            "token_expiry": self.token_expiry,
            "app_id": self.app_id,
            "has_private_key": bool(self.private_key_path and self.private_key_path.exists()),
            "installation_id": self.installation_id,
            "scopes": self.scopes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GitHubAuth":
        """Create from dictionary."""
        return cls(
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_expiry=data.get("token_expiry"),
            app_id=data.get("app_id"),
            private_key_path=Path(data["private_key_path"])
            if data.get("private_key_path")
            else None,
            installation_id=data.get("installation_id"),
            scopes=data.get("scopes", ["repo", "read:user"]),
        )


@dataclass
class Subscription:
    """Configuration for a subscribed remote KB."""

    url: str
    local_path: Path
    auto_sync: bool = True
    sync_interval: int = 3600  # seconds
    repo: str | None = None  # Reference to parent Repository name

    def __post_init__(self):
        self.local_path = Path(self.local_path).expanduser().resolve()


@dataclass
class Settings:
    """Global application settings."""

    default_editor: str = field(default_factory=lambda: os.environ.get("EDITOR", "vim"))
    ai_provider: Literal["anthropic", "openai", "local", "stub", "none"] = "stub"
    ai_model: str = "claude-sonnet-4-20250514"
    ai_api_key: str = ""
    ai_api_base: str = ""
    summary_length: int = 280
    enable_mcp: bool = True
    index_path: Path = field(default_factory=lambda: Path.home() / ".pyrite" / "index.db")
    host: str = "127.0.0.1"
    port: int = 8088
    # Security
    cors_origins: list[str] = field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8088",
        ]
    )
    api_key: str = ""  # Empty = auth disabled (backwards-compatible)
    api_keys: list[dict[str, str]] = field(default_factory=list)  # [{key_hash, role, label}]
    rate_limit_read: str = "100/minute"
    rate_limit_write: str = "30/minute"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    search_mode: str = "keyword"
    search_backend: str = "sqlite"  # "sqlite" or "postgres"
    database_url: str = ""  # PostgreSQL connection string (for postgres backend)
    workspace_path: Path = field(default_factory=lambda: Path.home() / ".pyrite" / "repos")

    def __post_init__(self):
        self.index_path = Path(self.index_path).expanduser().resolve()
        self.workspace_path = Path(self.workspace_path).expanduser().resolve()
        # Load from environment if not set
        if not self.ai_api_key:
            self.ai_api_key = os.environ.get("OPENAI_API_KEY", "") or os.environ.get(
                "ANTHROPIC_API_KEY", ""
            )
        if not self.ai_api_base:
            self.ai_api_base = os.environ.get("OPENAI_API_BASE", "")


@dataclass
class PyriteConfig:
    """
    Root configuration for pyrite.

    Manages multiple knowledge bases, repositories, subscriptions, and global settings.

    Structure supports:
    - Multiple KBs, each can be standalone or part of a repository
    - Repositories that contain multiple KBs (e.g., CascadeSeries with timeline + research-kb)
    - GitHub OAuth for private repository access
    - Subscriptions to remote KBs
    """

    version: str = "1.0"
    knowledge_bases: list[KBConfig] = field(default_factory=list)
    repositories: list[Repository] = field(default_factory=list)
    subscriptions: list[Subscription] = field(default_factory=list)
    github_auth: GitHubAuth | None = None
    settings: Settings = field(default_factory=Settings)

    _kb_by_name: dict[str, KBConfig] = field(default_factory=dict, repr=False)
    _repo_by_name: dict[str, Repository] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild the lookup indexes."""
        self._kb_by_name = {kb.name: kb for kb in self.knowledge_bases}
        self._repo_by_name = {repo.name: repo for repo in self.repositories}

    def get_kb(self, name: str) -> KBConfig | None:
        """Get a KB by name."""
        return self._kb_by_name.get(name)

    def get_kb_by_shortname(self, shortname: str) -> KBConfig | None:
        """Get a KB by its shortname alias."""
        for kb in self.knowledge_bases:
            if kb.shortname == shortname:
                return kb
        return None

    def list_kbs(self, kb_type: str | None = None) -> list[KBConfig]:
        """List all KBs, optionally filtered by type."""
        if kb_type is None:
            return self.knowledge_bases
        # Accept enum or string
        type_str = kb_type.value if hasattr(kb_type, "value") else kb_type
        return [kb for kb in self.knowledge_bases if kb.kb_type == type_str]

    def add_kb(self, kb: KBConfig) -> None:
        """Add a KB to the registry."""
        if kb.name in self._kb_by_name:
            raise ValueError(f"KB with name '{kb.name}' already exists")
        self.knowledge_bases.append(kb)
        self._kb_by_name[kb.name] = kb

    def remove_kb(self, name: str) -> bool:
        """Remove a KB from the registry. Returns True if removed."""
        if name not in self._kb_by_name:
            return False
        kb = self._kb_by_name.pop(name)
        self.knowledge_bases.remove(kb)
        return True

    # Repository management
    def get_repo(self, name: str) -> Repository | None:
        """Get a repository by name."""
        return self._repo_by_name.get(name)

    def add_repo(self, repo: Repository) -> None:
        """Add a repository to the registry."""
        if repo.name in self._repo_by_name:
            raise ValueError(f"Repository with name '{repo.name}' already exists")
        self.repositories.append(repo)
        self._repo_by_name[repo.name] = repo

    def remove_repo(self, name: str) -> bool:
        """Remove a repository from the registry. Returns True if removed."""
        if name not in self._repo_by_name:
            return False
        repo = self._repo_by_name.pop(name)
        self.repositories.remove(repo)
        return True

    def get_kbs_in_repo(self, repo_name: str) -> list[KBConfig]:
        """Get all KBs that belong to a repository."""
        return [kb for kb in self.knowledge_bases if kb.repo == repo_name]

    def validate(self) -> dict[str, list[str]]:
        """Validate all KBs and repos. Returns dict of name -> errors."""
        results = {}
        for kb in self.knowledge_bases:
            errors = kb.validate()
            if errors:
                results[f"kb:{kb.name}"] = errors
        for repo in self.repositories:
            errors = repo.validate()
            if errors:
                results[f"repo:{repo.name}"] = errors
        return results

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, Any] = {
            "version": self.version,
            "knowledge_bases": [
                {
                    "name": kb.name,
                    "path": str(kb.path),
                    "kb_type": kb.kb_type,
                    "description": kb.description,
                    "read_only": kb.read_only,
                    **({"remote": kb.remote} if kb.remote else {}),
                    **({"repo": kb.repo} if kb.repo else {}),
                    **({"repo_subpath": kb.repo_subpath} if kb.repo_subpath else {}),
                    **({"shortname": kb.shortname} if kb.shortname else {}),
                    **({"ephemeral": kb.ephemeral} if kb.ephemeral else {}),
                    **({"ttl": kb.ttl} if kb.ttl else {}),
                    **({"created_at_ts": kb.created_at_ts} if kb.created_at_ts else {}),
                }
                for kb in self.knowledge_bases
            ],
        }

        if self.repositories:
            result["repositories"] = [
                {
                    "name": repo.name,
                    "path": str(repo.path),
                    "remote": repo.remote,
                    "branch": repo.branch,
                    "auto_sync": repo.auto_sync,
                    "sync_interval": repo.sync_interval,
                    "auth_method": repo.auth_method,
                    **({"github_app_id": repo.github_app_id} if repo.github_app_id else {}),
                    **({"kb_paths": repo.kb_paths} if repo.kb_paths else {}),
                }
                for repo in self.repositories
            ]

        result["subscriptions"] = [
            {
                "url": sub.url,
                "local_path": str(sub.local_path),
                "auto_sync": sub.auto_sync,
                "sync_interval": sub.sync_interval,
                **({"repo": sub.repo} if sub.repo else {}),
            }
            for sub in self.subscriptions
        ]

        # GitHub auth - store in separate secure file, just reference here
        if self.github_auth and self.github_auth.has_oauth_credentials:
            result["github_auth"] = {
                "configured": True,
                "has_valid_token": self.github_auth.has_valid_token,
            }

        result["settings"] = {
            "default_editor": self.settings.default_editor,
            "ai_provider": self.settings.ai_provider,
            "ai_model": self.settings.ai_model,
            "summary_length": self.settings.summary_length,
            "enable_mcp": self.settings.enable_mcp,
            "index_path": str(self.settings.index_path),
            "host": self.settings.host,
            "port": self.settings.port,
            "cors_origins": self.settings.cors_origins,
            "api_key": self.settings.api_key,
            **({"api_keys": self.settings.api_keys} if self.settings.api_keys else {}),
            "rate_limit_read": self.settings.rate_limit_read,
            "rate_limit_write": self.settings.rate_limit_write,
            "embedding_model": self.settings.embedding_model,
            "embedding_dimensions": self.settings.embedding_dimensions,
            "search_mode": self.settings.search_mode,
        }

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PyriteConfig":
        """Create from dictionary (YAML loaded)."""
        knowledge_bases = []
        for kb_data in data.get("knowledge_bases", []):
            knowledge_bases.append(
                KBConfig(
                    name=kb_data["name"],
                    path=Path(kb_data["path"]),
                    kb_type=kb_data.get("kb_type", "generic"),
                    description=kb_data.get("description", ""),
                    read_only=kb_data.get("read_only", False),
                    remote=kb_data.get("remote"),
                    repo=kb_data.get("repo"),
                    repo_subpath=kb_data.get("repo_subpath", ""),
                    shortname=kb_data.get("shortname"),
                    ephemeral=kb_data.get("ephemeral", False),
                    ttl=kb_data.get("ttl"),
                    created_at_ts=kb_data.get("created_at_ts"),
                )
            )

        repositories = []
        for repo_data in data.get("repositories", []):
            repositories.append(
                Repository(
                    name=repo_data["name"],
                    path=Path(repo_data["path"]),
                    remote=repo_data.get("remote"),
                    branch=repo_data.get("branch", "main"),
                    auto_sync=repo_data.get("auto_sync", True),
                    sync_interval=repo_data.get("sync_interval", 3600),
                    auth_method=repo_data.get("auth_method", "none"),
                    github_app_id=repo_data.get("github_app_id"),
                    kb_paths=repo_data.get("kb_paths", []),
                )
            )

        subscriptions = []
        for sub_data in data.get("subscriptions", []):
            subscriptions.append(
                Subscription(
                    url=sub_data["url"],
                    local_path=Path(sub_data["local_path"]),
                    auto_sync=sub_data.get("auto_sync", True),
                    sync_interval=sub_data.get("sync_interval", 3600),
                    repo=sub_data.get("repo"),
                )
            )

        # Load GitHub auth from secure file if referenced
        github_auth = None
        github_auth_file = CONFIG_DIR / "github_auth.yaml"
        if github_auth_file.exists():
            try:
                auth_data = load_yaml_file(github_auth_file)
                github_auth = GitHubAuth.from_dict(auth_data)
            except Exception:
                logger.warning("Failed to load GitHub auth from %s", github_auth_file, exc_info=True)

        settings_data = data.get("settings", {})
        settings = Settings(
            default_editor=settings_data.get("default_editor", os.environ.get("EDITOR", "vim")),
            ai_provider=settings_data.get("ai_provider", "stub"),
            ai_model=settings_data.get("ai_model", "claude-sonnet-4-20250514"),
            summary_length=settings_data.get("summary_length", 280),
            enable_mcp=settings_data.get("enable_mcp", True),
            index_path=Path(settings_data.get("index_path", "~/.pyrite/index.db")),
            host=settings_data.get("host", "127.0.0.1"),
            port=settings_data.get("port", 8088),
            cors_origins=settings_data.get(
                "cors_origins",
                ["http://localhost:3000", "http://localhost:5173", "http://localhost:8088"],
            ),
            api_key=settings_data.get("api_key", ""),
            api_keys=settings_data.get("api_keys", []),
            rate_limit_read=settings_data.get("rate_limit_read", "100/minute"),
            rate_limit_write=settings_data.get("rate_limit_write", "30/minute"),
            embedding_model=settings_data.get("embedding_model", "all-MiniLM-L6-v2"),
            embedding_dimensions=settings_data.get("embedding_dimensions", 384),
            search_mode=settings_data.get("search_mode", "keyword"),
        )

        return cls(
            version=data.get("version", "1.0"),
            knowledge_bases=knowledge_bases,
            repositories=repositories,
            subscriptions=subscriptions,
            github_auth=github_auth,
            settings=settings,
        )


# Global configuration paths
CONFIG_DIR = Path(os.environ.get("PYRITE_CONFIG_DIR", "~/.pyrite")).expanduser().resolve()
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def ensure_config_dir() -> Path:
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> PyriteConfig:
    """
    Load configuration from config.yaml.

    Creates default config if it doesn't exist.
    """
    ensure_config_dir()

    if CONFIG_FILE.exists():
        data = load_yaml_file(CONFIG_FILE)
        config = PyriteConfig.from_dict(data)
    else:
        # Create default config
        config = PyriteConfig()

    # Load kb.yaml for each KB
    for kb in config.knowledge_bases:
        kb.load_kb_yaml()

    return config


def save_config(config: PyriteConfig) -> None:
    """Save configuration to config.yaml."""
    ensure_config_dir()

    dump_yaml_file(config.to_dict(), CONFIG_FILE)


def auto_discover_kbs(search_paths: list[Path] | None = None) -> list[KBConfig]:
    """
    Auto-discover KBs by looking for kb.yaml files.

    Searches in:
    - Current directory and subdirectories
    - Provided search paths
    """
    if search_paths is None:
        search_paths = [Path.cwd()]

    discovered = []

    for search_path in search_paths:
        search_path = Path(search_path).expanduser().resolve()
        if not search_path.exists():
            continue

        # Look for kb.yaml files
        for kb_yaml in search_path.rglob("kb.yaml"):
            try:
                data = load_yaml_file(kb_yaml)

                name = data.get("name", kb_yaml.parent.name)
                kb_type_str = data.get("kb_type", "generic")

                kb = KBConfig(
                    name=name,
                    path=kb_yaml.parent,
                    kb_type=kb_type_str,
                    description=data.get("description", ""),
                )
                kb.schema = data.get("schema")
                kb.types = data.get("types")
                kb.policies = data.get("policies")

                discovered.append(kb)
            except Exception as e:
                logger.warning("Could not parse %s: %s", kb_yaml, e)

    return discovered


# Legacy compatibility: expose commonly used values at module level
def get_notes_dir(kb_name: str | None = None) -> Path:
    """Get notes directory for a KB (legacy compatibility)."""
    config = load_config()
    if kb_name:
        kb = config.get_kb(kb_name)
        if kb:
            return kb.path
    # Return first KB or default
    if config.knowledge_bases:
        return config.knowledge_bases[0].path
    return Path("./data/notes").resolve()


def get_db_path(kb_name: str | None = None) -> Path:
    """Get database path for a KB (legacy compatibility)."""
    config = load_config()
    if kb_name:
        kb = config.get_kb(kb_name)
        if kb:
            return kb.local_db_path
    # Return global index
    return config.settings.index_path
