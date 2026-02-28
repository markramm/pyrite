"""
pyrite CLI

Command-line interface for managing knowledge bases.
Split into submodules for maintainability:
- kb_commands: Knowledge base management (list, add, remove, discover, validate)
- index_commands: Search index management (build, sync, stats, embed, health)
- search_commands: Search command with file fallback
- repo_commands: Repository collaboration (subscribe, fork, sync, unsubscribe, status)
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..config import (
    CONFIG_FILE,
    Repository,
    auto_discover_kbs,
    load_config,
    save_config,
)
from ..exceptions import PyriteError, ValidationError
from ..services.kb_service import KBService
from ..storage.database import PyriteDB
from .collection_commands import collections_app
from .extension_commands import extension_app
from .index_commands import index_app
from .init_command import init_kb
from .kb_commands import kb_app
from .qa_commands import qa_app
from .repo_commands import repo_collab_app
from .search_commands import register_search_command

app = typer.Typer(
    name="pyrite",
    help="Multi-KB research infrastructure for citizen journalists and AI agents",
    no_args_is_help=True,
)
console = Console()


def _get_svc():
    """Create a KBService instance for CLI commands."""
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    return KBService(config, db), db


# Register sub-apps
app.add_typer(kb_app, name="kb")
app.add_typer(index_app, name="index")
app.add_typer(collections_app, name="collections")
app.add_typer(qa_app, name="qa")

# Repository management — collaboration app with subscribe/fork/sync/unsubscribe/status/list
# Plus legacy add/remove commands added below
app.add_typer(repo_collab_app, name="repo")

# Extension management
app.add_typer(extension_app, name="extension")

# Init command (headless KB init)
app.command("init")(init_kb)

# Authentication commands
auth_app = typer.Typer(help="Authentication (GitHub OAuth)")
app.add_typer(auth_app, name="auth")

# Register search command
register_search_command(app)

# Register plugin CLI commands
try:
    from ..plugins import get_registry

    for name, command in get_registry().get_all_cli_commands():
        if hasattr(command, "registered_commands"):
            # It's a Typer app — register as sub-app
            app.add_typer(command, name=name)
        else:
            # It's a single command callback
            app.command(name)(command)
except Exception:
    pass  # Plugin loading shouldn't break the CLI


# =============================================================================
# Get command
# =============================================================================


def _format_output(data: dict, fmt: str) -> str | None:
    """Format data using the format registry. Returns None for default (rich) output."""
    if fmt == "rich":
        return None
    from ..formats import format_response

    content, _ = format_response(data, fmt)
    return content


@app.command("get")
def get_entry(
    entry_id: str = typer.Argument(..., help="Entry ID"),
    kb_name: str | None = typer.Option(None, "--kb", "-k", help="KB to search in"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Get a specific entry by ID."""
    svc, db = _get_svc()
    try:
        result = svc.get_entry(entry_id, kb_name=kb_name)

        if not result:
            console.print(f"[red]Error:[/red] Entry '{entry_id}' not found")
            raise typer.Exit(1)

        formatted = _format_output(result, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        console.print(f"\n[bold cyan]{result.get('title', '')}[/bold cyan]")
        console.print(
            f"[dim]KB: {result.get('kb_name', '')} | Type: {result.get('entry_type', '')} | ID: {result.get('id', '')}[/dim]\n"
        )

        summary = result.get("summary")
        if summary:
            console.print(f"[italic]{summary}[/italic]\n")

        body = result.get("body", "")
        if body:
            console.print(body)

        sources = result.get("sources", [])
        if sources:
            console.print(f"\n[bold]Sources ({len(sources)}):[/bold]")
            for src in sources:
                if isinstance(src, dict):
                    console.print(f"  • {src.get('title', '')}: {src.get('url', '')}")
                else:
                    console.print(f"  • {src.title}: {src.url}")
    finally:
        db.close()


# =============================================================================
# Create command
# =============================================================================


@app.command("create")
def create_entry(
    kb_name: str = typer.Option(None, "--kb", "-k", help="Target knowledge base"),
    entry_type: str = typer.Option("note", "--type", "-t", help="Entry type"),
    title: str = typer.Option(None, "--title", help="Entry title"),
    body: str = typer.Option("", "--body", "-b", help="Entry body text"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags"),
    date: str = typer.Option("", "--date", "-d", help="Date (YYYY-MM-DD, for events)"),
    importance: int = typer.Option(5, "--importance", "-i", help="Importance (1-10)"),
    field: list[str] | None = typer.Option(None, "--field", "-f", help="Extra field as key=value"),
    link: list[str] | None = typer.Option(
        None, "--link", "-l", help="Link to target entry (format: target-id or target-id:relation)"
    ),
    body_file: Path | None = typer.Option(None, "--body-file", help="Read body from file"),
    stdin: bool = typer.Option(False, "--stdin", help="Read body from stdin"),
    template: bool = typer.Option(False, "--template", help="Output entry skeleton to stdout"),
):
    """Create a new entry in a knowledge base."""
    from ..schema import CORE_TYPES, generate_entry_id
    from ..utils.yaml import dump_yaml

    # Template mode: output a skeleton and exit
    if template:
        fm: dict = {
            "id": "",
            "type": entry_type,
            "title": title or "Your Title Here",
            "tags": [],
        }
        # Add type-specific fields as empty values
        type_info = CORE_TYPES.get(entry_type, {})
        for field_name, field_type in type_info.get("fields", {}).items():
            if field_name in ("tags", "links"):
                continue
            if "list" in field_type:
                fm[field_name] = []
            elif field_type == "int":
                fm[field_name] = 0
            else:
                fm[field_name] = ""
        typer.echo(f"---\n{dump_yaml(fm)}\n---\n\nYour content here.")
        return

    # Require title for non-template mode
    if title is None:
        console.print("[red]Error:[/red] --title is required (unless using --template)")
        raise typer.Exit(1)

    # Require kb for non-template mode
    if kb_name is None:
        console.print("[red]Error:[/red] --kb is required (unless using --template)")
        raise typer.Exit(1)

    # Body resolution: --stdin > --body-file > --body
    if stdin:
        import sys

        body = sys.stdin.read()
    elif body_file:
        if not body_file.exists():
            console.print(f"[red]Error:[/red] Body file not found: {body_file}")
            raise typer.Exit(1)
        body = body_file.read_text(encoding="utf-8")

    # Extract YAML frontmatter from body content (--body-file or --stdin)
    _file_meta: dict = {}
    if body and body.startswith("---"):
        _fm_end = body.find("---", 3)
        if _fm_end > 0:
            from pyrite.utils.yaml import load_yaml

            _parsed = load_yaml(body[3:_fm_end])
            if _parsed and isinstance(_parsed, dict):
                for _k, _v in _parsed.items():
                    if _k not in ("id", "type", "title"):
                        _file_meta[_k] = _v
                body = body[_fm_end + 3 :].strip()

    entry_id = generate_entry_id(title)

    extra: dict = {**_file_meta}
    if date:
        extra["date"] = date
    if importance != 5:
        extra["importance"] = importance
    if tags:
        extra["tags"] = [t.strip() for t in tags.split(",")]

    # Parse --field key=value pairs
    if field:
        for fv in field:
            if "=" not in fv:
                console.print(f"[red]Error:[/red] --field must be key=value, got '{fv}'")
                raise typer.Exit(1)
            k, v = fv.split("=", 1)
            try:
                v = int(v)
            except ValueError:
                pass
            extra[k] = v

    svc, db = _get_svc()
    try:
        entry = svc.create_entry(kb_name, entry_id, title, entry_type, body, **extra)
        console.print(f"[green]Created:[/green] {entry.id}")
        console.print(f"[dim]Type: {entry.entry_type}[/dim]")

        # Add links after creation
        if link:
            for link_spec in link:
                if ":" in link_spec:
                    target, relation = link_spec.split(":", 1)
                else:
                    target, relation = link_spec, "related_to"
                try:
                    svc.add_link(entry.id, kb_name, target.strip(), relation.strip())
                    console.print(f"  [dim]Linked to {target} ({relation})[/dim]")
                except (PyriteError, ValueError) as e:
                    console.print(f"  [yellow]Link failed:[/yellow] {e}")
    except (PyriteError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.close()


# =============================================================================
# Add command
# =============================================================================


@app.command("add")
def add_entry(
    file_path: Path = typer.Argument(..., help="Path to markdown file with frontmatter"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Target knowledge base"),
    validate_only: bool = typer.Option(False, "--validate-only", help="Validate without saving"),
):
    """Add a markdown file to a knowledge base.

    Reads a markdown file with YAML frontmatter, validates it, copies it to the
    correct KB subdirectory, and indexes it.

    Frontmatter must include 'type' and 'title'. If 'id' is missing, it is
    generated from the title.
    """
    if not file_path.exists():
        console.print(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(1)

    svc, db = _get_svc()
    try:
        entry, result = svc.add_entry_from_file(
            kb_name, file_path, validate_only=validate_only
        )

        # Show warnings
        for warning in result.get("warnings", []):
            console.print(f"[yellow]Warning:[/yellow] {warning}")

        if validate_only:
            errors = result.get("errors", [])
            if errors:
                for err in errors:
                    console.print(f"[red]Error:[/red] {err}")
                raise typer.Exit(1)
            console.print(f"[green]Valid:[/green] {entry.id}")
            console.print(f"[dim]Type: {entry.entry_type}[/dim]")
        else:
            console.print(f"[green]Added:[/green] {entry.id}")
            console.print(f"[dim]Type: {entry.entry_type}[/dim]")
    except ValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except PyriteError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.close()


# =============================================================================
# Update command
# =============================================================================


@app.command("update")
def update_entry(
    entry_id: str = typer.Argument(..., help="Entry ID to update"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    title: str = typer.Option(None, "--title", help="New title"),
    body: str = typer.Option(None, "--body", "-b", help="New body text"),
    tags: str = typer.Option(None, "--tags", help="New comma-separated tags"),
    importance: int = typer.Option(None, "--importance", "-i", help="New importance (1-10)"),
):
    """Update an existing entry."""
    updates = {}
    if title is not None:
        updates["title"] = title
    if body is not None:
        updates["body"] = body
    if importance is not None:
        updates["importance"] = importance
    if tags is not None:
        updates["tags"] = [t.strip() for t in tags.split(",")]

    svc, db = _get_svc()
    try:
        entry = svc.update_entry(entry_id, kb_name, **updates)
        console.print(f"[green]Updated:[/green] {entry.id}")
    except (PyriteError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.close()


# =============================================================================
# Delete command
# =============================================================================


@app.command("delete")
def delete_entry(
    entry_id: str = typer.Argument(..., help="Entry ID to delete"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete an entry from a knowledge base."""
    if not force:
        if not typer.confirm(f"Delete entry '{entry_id}' from KB '{kb_name}'?"):
            raise typer.Abort()

    svc, db = _get_svc()
    try:
        deleted = svc.delete_entry(entry_id, kb_name)
        if not deleted:
            console.print(f"[red]Error:[/red] Entry '{entry_id}' not found")
            raise typer.Exit(1)
        console.print(f"[green]Deleted:[/green] {entry_id}")
    except (PyriteError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.close()


# =============================================================================
# Link command
# =============================================================================


@app.command("link")
def link_entries(
    source: str = typer.Argument(..., help="Source entry ID"),
    target: str = typer.Argument(..., help="Target entry ID"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Source KB name"),
    relation: str = typer.Option("related_to", "--relation", "-r", help="Relationship type"),
    target_kb: str | None = typer.Option(None, "--target-kb", help="Target KB (if different)"),
    note: str = typer.Option("", "--note", "-n", help="Note about the link"),
    bidirectional: bool = typer.Option(False, "--bidi", help="Create link in both directions"),
):
    """Create a link between two entries."""
    svc, db = _get_svc()
    try:
        svc.add_link(source, kb_name, target, relation, target_kb=target_kb, note=note)
        tkb = target_kb or kb_name
        console.print(f"[green]Linked:[/green] {source} --[{relation}]--> {target} (in {tkb})")

        if bidirectional:
            from ..schema import get_inverse_relation

            inverse = get_inverse_relation(relation)
            svc.add_link(target, tkb, source, inverse, target_kb=kb_name, note=note)
            console.print(f"[green]Linked:[/green] {target} --[{inverse}]--> {source} (in {kb_name})")
    except (PyriteError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        db.close()


# =============================================================================
# List command (top-level KB listing)
# =============================================================================


@app.command("list")
def list_kbs(
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """List all knowledge bases."""
    svc, db = _get_svc()
    try:
        kbs = svc.list_kbs()

        if not kbs:
            console.print("[yellow]No knowledge bases configured.[/yellow]")
            return

        formatted = _format_output({"kbs": kbs, "total": len(kbs)}, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        table = Table(title="Knowledge Bases")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="dim")
        table.add_column("Entries", justify="right")
        table.add_column("Path", style="dim")

        for kb in kbs:
            table.add_row(
                kb["name"], kb.get("type", ""), str(kb.get("entries", 0)), kb.get("path", "")
            )

        console.print(table)
    finally:
        db.close()


# =============================================================================
# Timeline command
# =============================================================================


@app.command("timeline")
def timeline(
    date_from: str = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    date_to: str = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    min_importance: int = typer.Option(1, "--min-importance", help="Minimum importance (1-10)"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Query timeline events."""
    svc, db = _get_svc()
    try:
        results = svc.get_timeline(
            date_from=date_from,
            date_to=date_to,
            min_importance=min_importance,
        )
        results = results[:limit]

        if not results:
            console.print("[yellow]No timeline events found.[/yellow]")
            return

        formatted = _format_output({"count": len(results), "events": results}, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        table = Table(title="Timeline Events")
        table.add_column("Date", style="cyan")
        table.add_column("Title")
        table.add_column("Imp", justify="right", style="dim")
        table.add_column("KB", style="dim")

        for evt in results:
            table.add_row(
                evt.get("date", ""),
                evt.get("title", ""),
                str(evt.get("importance", "")),
                evt.get("kb_name", ""),
            )

        console.print(table)
    finally:
        db.close()


# =============================================================================
# Tags command
# =============================================================================


@app.command("tags")
def tags_cmd(
    kb_name: str = typer.Option(None, "--kb", "-k", help="Filter by KB"),
    prefix: str = typer.Option(None, "--prefix", "-p", help="Filter tags by prefix"),
    limit: int = typer.Option(100, "--limit", "-n", help="Max tags to show"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """List tags with counts."""
    svc, db = _get_svc()
    try:
        tag_list = svc.get_tags(kb_name=kb_name, limit=limit)

        # Apply prefix filter
        if prefix:
            tag_list = [t for t in tag_list if t.get("name", "").startswith(prefix)]

        if not tag_list:
            console.print("[yellow]No tags found.[/yellow]")
            return

        formatted = _format_output({"tags": tag_list, "count": len(tag_list)}, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        title = f"Tags (prefix: {prefix})" if prefix else "Tags"
        table = Table(title=title)
        table.add_column("Tag", style="cyan")
        table.add_column("Count", justify="right")

        for tag in tag_list:
            table.add_row(tag.get("name", ""), str(tag.get("count", 0)))

        console.print(table)
    finally:
        db.close()


# =============================================================================
# Backlinks command
# =============================================================================


@app.command("backlinks")
def backlinks_cmd(
    entry_id: str = typer.Argument(..., help="Entry ID to find backlinks for"),
    kb_name: str = typer.Option(..., "--kb", "-k", help="Knowledge base name"),
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Find entries that link to a given entry."""
    svc, db = _get_svc()
    try:
        links = svc.get_backlinks(entry_id, kb_name)

        if not links:
            console.print(f"[yellow]No backlinks found for '{entry_id}'.[/yellow]")
            return

        formatted = _format_output(
            {"entry_id": entry_id, "entries": links, "total": len(links)}, output_format
        )
        if formatted is not None:
            typer.echo(formatted)
            return

        table = Table(title=f"Backlinks to {entry_id}")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Type", style="dim")
        table.add_column("Relation", style="dim")

        for link in links:
            table.add_row(
                link.get("id", ""),
                link.get("title", ""),
                link.get("entry_type", ""),
                link.get("relation", ""),
            )

        console.print(table)
    finally:
        db.close()


# =============================================================================
# Config command
# =============================================================================


@app.command("config")
def show_config():
    """Show current configuration."""
    console.print(f"[bold]Config file:[/bold] {CONFIG_FILE}")
    console.print(f"[bold]Exists:[/bold] {CONFIG_FILE.exists()}")

    if CONFIG_FILE.exists():
        config = load_config()
        console.print(f"\n[bold]Knowledge Bases:[/bold] {len(config.knowledge_bases)}")
        console.print(f"[bold]Subscriptions:[/bold] {len(config.subscriptions)}")
        console.print(f"[bold]AI Provider:[/bold] {config.settings.ai_provider}")


# =============================================================================
# Serve command
# =============================================================================


@app.command("serve")
def serve(
    host: str = typer.Option(None, "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(None, "--port", "-p", help="Port to bind to"),
    dev: bool = typer.Option(
        False, "--dev", help="API-only mode (frontend dev server runs separately on :5173)"
    ),
    build: bool = typer.Option(False, "--build", help="Run npm build before serving"),
):
    """Start the Pyrite web server.

    By default, serves the built web app from web/dist/ and the API.
    Use --dev when developing the frontend (Vite dev server on :5173, API on :8088).
    """
    import subprocess

    import uvicorn

    config = load_config()
    host = host or config.settings.host or "127.0.0.1"
    port = port or config.settings.port or 8088

    web_dir = Path(__file__).parent.parent.parent / "web"
    dist_dir = web_dir / "dist"

    if build and web_dir.is_dir():
        console.print("[dim]Building frontend...[/dim]")
        result = subprocess.run(
            ["npm", "run", "build"], cwd=str(web_dir), capture_output=True, text=True
        )
        if result.returncode != 0:
            console.print(f"[red]Build failed:[/red]\n{result.stderr}")
            raise typer.Exit(1)
        console.print("[green]Frontend built successfully.[/green]")

    if dev:
        console.print(f"[dim]Starting API server at http://{host}:{port} (dev mode)[/dim]")
        console.print("[dim]Run 'cd web && npm run dev' for the frontend.[/dim]")
    elif dist_dir.is_dir():
        console.print(f"[dim]Starting Pyrite at http://{host}:{port}[/dim]")
    else:
        console.print(f"[dim]Starting API server at http://{host}:{port}[/dim]")
        console.print(
            "[yellow]No web/dist/ found — run 'pyrite serve --build' or "
            "'cd web && npm run build' first.[/yellow]"
        )

    from ..server.api import create_app

    application = create_app()
    uvicorn.run(application, host=host, port=port)


# =============================================================================
# Legacy Repository Commands (add/remove for local repos)
# =============================================================================


@repo_collab_app.command("add")
def repo_add(
    path: Path = typer.Argument(..., help="Path to the repository"),
    name: str | None = typer.Option(None, "--name", "-n", help="Name for the repo"),
    remote: str | None = typer.Option(None, "--remote", "-r", help="Git remote URL"),
    auth_method: str = typer.Option(
        "none", "--auth", "-a", help="Auth method (none/ssh/github_oauth/token)"
    ),
    discover: bool = typer.Option(
        True, "--discover/--no-discover", help="Auto-discover KBs in repo"
    ),
):
    """Add a local repository to the registry."""
    config = load_config()

    path = path.expanduser().resolve()
    repo_name = name or path.name

    if config.get_repo(repo_name):
        console.print(f"[red]Error:[/red] Repository '{repo_name}' already exists")
        raise typer.Exit(1)

    repo = Repository(
        name=repo_name,
        path=path,
        remote=remote,
        auth_method=auth_method,  # type: ignore
    )

    config.add_repo(repo)

    if discover and path.exists():
        discovered = auto_discover_kbs([path])
        for kb in discovered:
            if not config.get_kb(kb.name):
                kb.repo = repo_name
                kb.repo_subpath = str(kb.path.relative_to(path))
                config.add_kb(kb)
                console.print(f"  [green]Discovered KB:[/green] {kb.name} ({kb.kb_type})")

    save_config(config)
    console.print(f"[green]Added repository:[/green] {repo_name}")


@repo_collab_app.command("remove")
def repo_remove(
    name: str = typer.Argument(..., help="Name of the repository"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove a repository from the registry."""
    config = load_config()

    repo = config.get_repo(name)
    if not repo:
        console.print(f"[red]Error:[/red] Repository '{name}' not found")
        raise typer.Exit(1)

    kbs = config.get_kbs_in_repo(name)

    if not force:
        msg = f"Remove repository '{name}'?"
        if kbs:
            msg += f" ({len(kbs)} KBs will also be removed)"
        if not typer.confirm(msg):
            raise typer.Abort()

    for kb in kbs:
        config.remove_kb(kb.name)

    config.remove_repo(name)
    save_config(config)

    console.print(f"[green]Removed:[/green] {name}")
    if kbs:
        console.print(f"[dim]Also removed {len(kbs)} KB(s)[/dim]")


# =============================================================================
# Authentication Commands
# =============================================================================


@auth_app.command("status")
def auth_status(
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Check GitHub authentication status."""
    from ..github_auth import check_github_auth

    valid, message = check_github_auth()

    formatted = _format_output({"authenticated": valid, "message": message}, output_format)
    if formatted is not None:
        typer.echo(formatted)
        return

    if valid:
        console.print(f"[green]{message}")
    else:
        console.print(f"[yellow]![/yellow] {message}")


@auth_app.command("whoami")
def auth_whoami(
    output_format: str = typer.Option(
        "rich", "--format", help="Output format: rich, json, markdown, csv, yaml"
    ),
):
    """Show current user identity."""
    _svc, db = _get_svc()
    try:
        from ..services.user_service import UserService

        user_service = UserService(db)
        user = user_service.get_current_user()

        formatted = _format_output(user, output_format)
        if formatted is not None:
            typer.echo(formatted)
            return

        if user.get("github_id", 0) == 0:
            console.print("[yellow]Not authenticated with GitHub[/yellow]")
            console.print("Identity: [bold]local[/bold] (no GitHub auth)")
            console.print("\nRun 'pyrite auth github-login' to authenticate.")
        else:
            console.print(f"[bold cyan]{user['github_login']}[/bold cyan]")
            if user.get("display_name"):
                console.print(f"  Name: {user['display_name']}")
            if user.get("email"):
                console.print(f"  Email: {user['email']}")
            console.print(f"  GitHub ID: {user['github_id']}")
    finally:
        db.close()


@auth_app.command("github-login")
def auth_github_login(
    client_id: str | None = typer.Option(None, "--client-id", help="OAuth App client ID"),
    client_secret: str | None = typer.Option(
        None, "--client-secret", help="OAuth App client secret"
    ),
):
    """Authenticate with GitHub using OAuth."""
    from ..github_auth import start_oauth_flow

    success, message = start_oauth_flow(client_id, client_secret)
    if success:
        console.print(f"[green]{message}")
    else:
        console.print(f"[red]{message}")
        raise typer.Exit(1)


@auth_app.command("github-logout")
def auth_github_logout():
    """Remove GitHub authentication."""
    from ..github_auth import clear_github_auth

    if typer.confirm("Remove GitHub authentication?"):
        clear_github_auth()
        console.print("[green]GitHub authentication removed.[/green]")


@auth_app.command("github-setup")
def auth_github_setup():
    """Set up GitHub OAuth App credentials."""
    console.print("\n[bold]GitHub OAuth Setup[/bold]\n")
    console.print("To use GitHub OAuth, you need to create an OAuth App:")
    console.print("1. Go to https://github.com/settings/developers")
    console.print("2. Click 'New OAuth App'")
    console.print("3. Set the callback URL to: http://127.0.0.1:8765/callback")
    console.print("4. Copy the Client ID and Client Secret\n")

    client_id = typer.prompt("Client ID")
    client_secret = typer.prompt("Client Secret", hide_input=True)

    from ..github_auth import GitHubAuth, save_github_auth

    auth = GitHubAuth(
        client_id=client_id,
        client_secret=client_secret,
    )
    save_github_auth(auth)

    console.print("\n[green]Credentials saved.")
    console.print("Run 'pyrite auth github-login' to authenticate.")


# =============================================================================
# MCP Server Commands
# =============================================================================


@app.command("mcp")
def mcp_server():
    """
    Start the MCP (Model Context Protocol) server.

    This runs the write-tier server over stdio for integration with Claude Code
    and other MCP-compatible AI agents.

    Tools exposed (write tier):
    - kb_list, kb_search, kb_get, kb_timeline, kb_backlinks, kb_tags, kb_stats, kb_schema
    - kb_create, kb_update, kb_delete
    """
    from ..server.mcp_server import PyriteMCPServer

    console.print("[dim]Starting MCP server (write tier) on stdio...[/dim]", err=True)
    server = PyriteMCPServer(tier="write")
    try:
        server.run_stdio()
    finally:
        server.close()


@app.command("mcp-setup")
def mcp_setup(
    config_path: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to Claude Code config (default: ~/.claude/claude_desktop_config.json)",
    ),
):
    """
    Set up MCP server integration with Claude Code.

    Adds pyrite to Claude Code's MCP server configuration.
    """
    import json
    import shutil

    if config_path is None:
        config_path = Path.home() / ".claude" / "claude_desktop_config.json"

    config_path = config_path.expanduser()

    pyrite_exe = shutil.which("pyrite-admin")
    if not pyrite_exe:
        pyrite_exe = "python -m pyrite.admin_cli"
        console.print("[yellow]Warning: pyrite-admin not in PATH, using module path[/yellow]")

    if config_path.exists():
        with open(config_path) as f:
            claude_config = json.load(f)
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        claude_config = {}

    if "mcpServers" not in claude_config:
        claude_config["mcpServers"] = {}

    claude_config["mcpServers"]["pyrite"] = {
        "command": pyrite_exe if "python" not in pyrite_exe else "python",
        "args": ["-m", "pyrite.admin_cli", "mcp"] if "python" in pyrite_exe else ["mcp"],
        "env": {},
    }

    with open(config_path, "w") as f:
        json.dump(claude_config, f, indent=2)

    console.print(f"[green]MCP server configured in {config_path}[/green]")
    console.print("\nRestart Claude Code to load the new MCP server.")
    console.print("\nAvailable tools:")
    console.print("  • kb_list - List knowledge bases")
    console.print("  • kb_search - Full-text search across KBs")
    console.print("  • kb_get - Get entry by ID")
    console.print("  • kb_schema - Get KB schema for agents")
    console.print("  • kb_create - Create new entry")
    console.print("  • kb_update - Update entry")
    console.print("  • kb_delete - Delete entry")
    console.print("  • kb_timeline - Query timeline events")
    console.print("  • kb_backlinks - Find entries linking to an entry")
    console.print("  • kb_tags - Get all tags with counts")
    console.print("  • kb_stats - Get index statistics")
    console.print("  • kb_index_sync - Sync index (admin tier)")
    console.print("  • kb_manage - Manage KBs (admin tier)")


def main():
    app()


if __name__ == "__main__":
    main()
