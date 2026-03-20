#!/bin/bash

# sync-commands.sh
# Syncs command templates from .project-context/commands/ to host-specific directories.

GOV_CMD_DIR=".project-context/commands"
CLAUDE_CMD_DIR=".claude/commands"
OPENCODE_CMD_DIR=".opencode/commands"
CODEX_PRMPT_DIR=".codex/prompts"
GEMINI_CMD_DIR=".gemini/commands"
AGENT_WF_DIR=".agents/workflows"

sync_cmd() {
    local cmd_name=$1
    if [ -f "$GOV_CMD_DIR/$cmd_name.md" ]; then
        echo "Syncing $cmd_name..."
        [ -d "$CLAUDE_CMD_DIR" ] && cp "$GOV_CMD_DIR/$cmd_name.md" "$CLAUDE_CMD_DIR/$cmd_name.md"
        [ -d "$OPENCODE_CMD_DIR" ] && cp "$GOV_CMD_DIR/$cmd_name.md" "$OPENCODE_CMD_DIR/$cmd_name.md"
        [ -d "$CODEX_PRMPT_DIR" ] && cp "$GOV_CMD_DIR/$cmd_name.md" "$CODEX_PRMPT_DIR/$cmd_name.md"
        [ -d "$GEMINI_CMD_DIR" ] && cp "$GOV_CMD_DIR/$cmd_name.md" "$GEMINI_CMD_DIR/$cmd_name.md"
        [ -d "$AGENT_WF_DIR" ] && cp "$GOV_CMD_DIR/$cmd_name.md" "$AGENT_WF_DIR/$cmd_name.md"
    fi
}

mkdir -p "$CLAUDE_CMD_DIR" "$OPENCODE_CMD_DIR" "$CODEX_PRMPT_DIR" "$GEMINI_CMD_DIR" "$AGENT_WF_DIR"

sync_cmd "ctx-load"
sync_cmd "ctx-save"

echo "Sync complete."
