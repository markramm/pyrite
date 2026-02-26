"""
Markdown Block Extraction

Parses markdown text into discrete blocks (headings, paragraphs, lists, code)
for block-level referencing. Each block gets an auto-generated ID from a SHA-256
hash of its content, unless an explicit ^block-id marker is present.
"""

import hashlib
import re

# Matches explicit block ID markers like ^block-id at end of a block
_BLOCK_ID_RE = re.compile(r"\s*\^([a-zA-Z0-9_-]+)\s*$")


def _make_block_id(content: str) -> str:
    """Generate a block ID from SHA-256 of content (first 8 hex chars)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]


def _extract_explicit_id(text: str) -> tuple[str, str | None]:
    """Check for and extract an explicit ^block-id marker from the last line.

    Returns (cleaned_text, block_id_or_None).
    """
    lines = text.rstrip().split("\n")
    if lines:
        match = _BLOCK_ID_RE.match(lines[-1])
        if match:
            block_id = match.group(1)
            cleaned = "\n".join(lines[:-1]).rstrip()
            if not cleaned:
                # The marker was the only content after the block content
                # Check if there's content before the marker on the same line
                cleaned = text.rstrip()
                # Try inline: "some text ^block-id"
                inline_match = re.match(r"^(.*?)\s+\^([a-zA-Z0-9_-]+)\s*$", cleaned)
                if inline_match:
                    return inline_match.group(1), inline_match.group(2)
                return cleaned, None
            return cleaned, block_id
    return text, None


def extract_blocks(markdown_text: str) -> list[dict[str, str | int | None]]:
    """Extract blocks from markdown text.

    Block types: heading, paragraph, list, code.
    Each block includes:
        - block_id: SHA-256 based (first 8 hex chars) or explicit ^id
        - heading: current heading context (None if before any heading)
        - content: the block text
        - position: 0-based index of block in document
        - block_type: one of heading, paragraph, list, code
    """
    if not markdown_text or not markdown_text.strip():
        return []

    lines = markdown_text.split("\n")
    blocks: list[dict[str, str | int | None]] = []
    current_heading: str | None = None
    position = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip blank lines
        if not line.strip():
            i += 1
            continue

        # Fenced code block
        if line.strip().startswith("```"):
            code_lines = [line]
            i += 1
            while i < len(lines):
                code_lines.append(lines[i])
                if lines[i].strip().startswith("```") and len(code_lines) > 1:
                    i += 1
                    break
                i += 1
            content = "\n".join(code_lines)
            content, explicit_id = _check_next_line_marker(lines, i, content)
            if explicit_id:
                # Skip the marker line
                i += 1
            block_id = explicit_id or _make_block_id(content)
            blocks.append({
                "block_id": block_id,
                "heading": current_heading,
                "content": content,
                "position": position,
                "block_type": "code",
            })
            position += 1
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            content = line
            content, explicit_id = _check_next_line_marker(lines, i + 1, content)
            skip_extra = 1 if explicit_id else 0
            block_id = explicit_id or _make_block_id(content)
            current_heading = heading_match.group(2).strip()
            # Check for inline ^block-id
            inline_match = _BLOCK_ID_RE.search(current_heading)
            if inline_match:
                current_heading = current_heading[:inline_match.start()].strip()
                if not explicit_id:
                    explicit_id = inline_match.group(1)
                    content = line[:line.rfind("^")].rstrip()
                    block_id = explicit_id
            blocks.append({
                "block_id": block_id,
                "heading": current_heading,
                "content": content,
                "position": position,
                "block_type": "heading",
            })
            position += 1
            i += 1 + skip_extra
            continue

        # List (bulleted or numbered)
        if re.match(r"^(\s*[-*+]|\s*\d+\.)\s+", line):
            list_lines = [line]
            i += 1
            while i < len(lines):
                cur = lines[i]
                # Continue list: list item or indented continuation or blank line between items
                if re.match(r"^(\s*[-*+]|\s*\d+\.)\s+", cur):
                    list_lines.append(cur)
                    i += 1
                elif cur.strip() == "" and i + 1 < len(lines) and re.match(
                    r"^(\s*[-*+]|\s*\d+\.)\s+", lines[i + 1]
                ):
                    list_lines.append(cur)
                    i += 1
                elif cur.startswith("  ") or cur.startswith("\t"):
                    # Indented continuation
                    list_lines.append(cur)
                    i += 1
                else:
                    break
            content = "\n".join(list_lines).rstrip()
            content, explicit_id = _check_next_line_marker(lines, i, content)
            if explicit_id:
                i += 1
            # Also check last line of content for inline marker
            if not explicit_id:
                content, explicit_id = _extract_explicit_id(content)
            block_id = explicit_id or _make_block_id(content)
            blocks.append({
                "block_id": block_id,
                "heading": current_heading,
                "content": content,
                "position": position,
                "block_type": "list",
            })
            position += 1
            continue

        # Paragraph (default): collect contiguous non-blank, non-special lines
        para_lines = [line]
        i += 1
        while i < len(lines):
            cur = lines[i]
            if not cur.strip():
                break
            if cur.strip().startswith("```"):
                break
            if re.match(r"^#{1,6}\s+", cur):
                break
            if re.match(r"^(\s*[-*+]|\s*\d+\.)\s+", cur):
                break
            para_lines.append(cur)
            i += 1
        content = "\n".join(para_lines).rstrip()
        content, explicit_id = _extract_explicit_id(content)
        if not explicit_id:
            content_stripped = content
            content_stripped, explicit_id = _check_next_line_marker(lines, i, content_stripped)
            if explicit_id:
                content = content_stripped
                i += 1
        block_id = explicit_id or _make_block_id(content)
        blocks.append({
            "block_id": block_id,
            "heading": current_heading,
            "content": content,
            "position": position,
            "block_type": "paragraph",
        })
        position += 1

    return blocks


def _check_next_line_marker(
    lines: list[str], next_idx: int, content: str
) -> tuple[str, str | None]:
    """Check if the line at next_idx is a standalone ^block-id marker."""
    if next_idx < len(lines):
        match = _BLOCK_ID_RE.match(lines[next_idx])
        if match and not lines[next_idx].strip().startswith("#"):
            return content, match.group(1)
    return content, None
