#!/bin/bash
set -e

DATA_DIR="${PYRITE_DATA_DIR:-/data}"

# Skip if already seeded
if [ -f "$DATA_DIR/.seeded" ]; then
    echo "Already seeded, skipping."
    exit 0
fi

echo "Seeding demo KBs..."

# --- Pyrite project KB ---
cp -r /seed/pyrite-kb "$DATA_DIR/pyrite-kb"
pyrite kb add "$DATA_DIR/pyrite-kb" --name pyrite
pyrite index build pyrite --force
echo "  Indexed: pyrite"

# --- Demo KBs (intellectual biographies, movements, etc.) ---
if [ -d /seed/demo-kbs ]; then
    for kb_dir in /seed/demo-kbs/*/; do
        kb_name=$(basename "$kb_dir")

        # Skip non-KB directories (no kb.yaml = not a KB)
        if [ ! -f "$kb_dir/kb.yaml" ]; then
            echo "  Skipping $kb_name (no kb.yaml)"
            continue
        fi

        cp -r "$kb_dir" "$DATA_DIR/$kb_name"
        pyrite kb add "$DATA_DIR/$kb_name" --name "$kb_name"
        pyrite index build "$kb_name" --force
        echo "  Indexed: $kb_name"
    done
fi

# --- Embed all KBs for semantic search ---
echo "Building semantic embeddings (this may take a few minutes)..."
for kb_dir in "$DATA_DIR"/*/; do
    kb_name=$(basename "$kb_dir")
    if [ -f "$kb_dir/kb.yaml" ]; then
        pyrite index embed "$kb_name" 2>/dev/null || echo "  Embed skipped for $kb_name"
    fi
done

touch "$DATA_DIR/.seeded"
echo "Demo seeded successfully."
