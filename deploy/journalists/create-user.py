#!/usr/bin/env python3
"""Create a local user directly (bypasses registration config).

Usage: python create-user.py <username> <password> [--admin]
First user always gets admin role regardless of --admin flag.
"""
import argparse
import sqlite3
import sys
import os
from datetime import datetime, timezone

DATA_DIR = os.environ.get("PYRITE_DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "pyrite.db")


def main():
    parser = argparse.ArgumentParser(description="Create a Pyrite user")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--admin", action="store_true", help="Grant admin role")
    args = parser.parse_args()

    if len(args.password) < 8:
        print("Error: password must be at least 8 characters", file=sys.stderr)
        sys.exit(1)

    import bcrypt

    conn = sqlite3.connect(DB_PATH)

    # Check if user exists
    row = conn.execute(
        "SELECT id FROM local_user WHERE username = ?", (args.username,)
    ).fetchone()
    if row:
        print(f"Error: username '{args.username}' already exists", file=sys.stderr)
        sys.exit(1)

    # First user gets admin; otherwise respect --admin flag
    count = conn.execute("SELECT COUNT(*) FROM local_user").fetchone()[0]
    if count == 0:
        role = "admin"
    else:
        role = "admin" if args.admin else "write"

    # Hash password with bcrypt (matches auth_service)
    password_hash = bcrypt.hashpw(args.password.encode(), bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT INTO local_user
        (username, display_name, password_hash, role, auth_provider, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'local', ?, ?)""",
        (args.username, None, password_hash, role, now, now),
    )
    conn.commit()
    conn.close()

    print(f"Created user '{args.username}' with role '{role}'")


if __name__ == "__main__":
    main()
