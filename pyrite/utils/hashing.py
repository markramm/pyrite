"""Git-compatible content hashing utilities."""

import hashlib


def git_blob_hash(content: bytes) -> str:
    """Compute git blob object hash (SHA-1) for file content.

    Uses the same algorithm as ``git hash-object``:
    SHA-1 of ``b"blob {size}\\0{content}"``.

    Deterministic, offline-capable, rename-proof.
    """
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324
