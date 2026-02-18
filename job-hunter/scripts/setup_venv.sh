#!/bin/bash
# Setup virtual environment for Job Hunter skill
set -e

VENV_DIR="$HOME/.venv/job-hunter"
SKILL_DIR="$HOME/.claude/skills/job-hunter"

echo "Setting up Job Hunter virtual environment..."

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Created venv at $VENV_DIR"
else
    echo "Venv already exists at $VENV_DIR"
fi

# Install dependencies
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$SKILL_DIR/requirements.txt"

echo ""
echo "Setup complete!"
echo "Python: $VENV_DIR/bin/python3"
echo ""
echo "To activate manually: source $VENV_DIR/bin/activate"
