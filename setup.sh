#!/bin/sh
# Symlink all skills to ~/.claude/skills/ for local use
#
# Usage: sh setup.sh [--remove]

SKILLS_DIR="$(cd "$(dirname "$0")" && pwd)/skills"
TARGET_DIR="$HOME/.claude/skills"

if [ "$1" = "--remove" ]; then
    for skill_dir in "$SKILLS_DIR"/*/; do
        skill_name=$(basename "$skill_dir")
        target="$TARGET_DIR/$skill_name"
        if [ -L "$target" ]; then
            rm "$target"
            echo "Removed: $skill_name"
        fi
    done
    exit 0
fi

mkdir -p "$TARGET_DIR"
for skill_dir in "$SKILLS_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    ln -sfn "$skill_dir" "$TARGET_DIR/$skill_name"
    echo "Linked: $skill_name -> $skill_dir"
done
echo ""
echo "Skills installed. Restart Claude Code to pick them up."
