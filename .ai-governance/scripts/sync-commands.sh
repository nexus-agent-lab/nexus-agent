#!/bin/bash

# sync-commands.sh
# Syncs neutral command templates from .ai-governance/commands/ to host-specific directories.

GOV_CMD_DIR=".ai-governance/commands"
CLAUDE_CMD_DIR=".claude/commands"
OPENCODE_CMD_DIR=".opencode/commands"
CODEX_PRMPT_DIR=".codex/prompts"
GEMINI_CMD_DIR=".gemini/commands"
AGENT_WF_DIR=".agents/workflows"

# Function to sync
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

# Legacy GCC commands to prune (from v2.1 and below)
LEGACY_CMDS=(
    "task-archive"
    "task-bootstrap"
    "task-branch"
    "task-commit"
    "task-context"
    "task-merge"
    "verify-change"
)

# Function to safely prune only legacy GCC files
prune_legacy() {
    local target_dir=$1
    local ext=$2
    if [ -d "$target_dir" ]; then
        for cmd in "${LEGACY_CMDS[@]}"; do
            if [ -f "$target_dir/$cmd.$ext" ]; then
                echo "Pruning legacy command: $target_dir/$cmd.$ext"
                rm "$target_dir/$cmd.$ext"
            fi
        done
    fi
}

# Cleanup only specific legacy GCC files before sync
echo "Cleaning up legacy GCC commands (v2.1 logic)..."
prune_legacy "$CLAUDE_CMD_DIR" "md"
prune_legacy "$OPENCODE_CMD_DIR" "md"
prune_legacy "$CODEX_PRMPT_DIR" "md"
prune_legacy "$GEMINI_CMD_DIR" "toml"
prune_legacy "$AGENT_WF_DIR" "md"

mkdir -p "$CLAUDE_CMD_DIR" "$OPENCODE_CMD_DIR" "$CODEX_PRMPT_DIR" "$GEMINI_CMD_DIR" "$AGENT_WF_DIR"

sync_cmd "gov-context"
sync_cmd "gov-writeback"

echo "Sync complete."
