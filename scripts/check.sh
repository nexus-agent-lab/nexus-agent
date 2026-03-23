#!/bin/bash
# Usage: ./scripts/check.sh [--online]
set -euo pipefail

RUFF="uv run ruff"
PYTEST="uv run pytest"

MODE="offline"
if [[ "${1:-}" == "--online" ]]; then
    MODE="online"
fi

collect_staged_files() {
    git diff --cached --name-only --diff-filter=ACMR
}

is_python_target() {
    local path="$1"
    [[ "$path" == app/*.py || "$path" == tests/*.py || "$path" == tests/**/*.py || "$path" == scripts/*.py || "$path" == scripts/**/*.py ]]
}

needs_full_pytest() {
    local path
    for path in "$@"; do
        case "$path" in
            tests/conftest.py|pyproject.toml|requirements-dev.txt)
                return 0
                ;;
        esac
    done
    return 1
}

collect_python_files() {
    local path
    for path in "$@"; do
        if is_python_target "$path"; then
            printf '%s\n' "$path"
        fi
    done
}

collect_web_files() {
    local path
    for path in "$@"; do
        if [[ "$path" == web/* ]]; then
            printf '%s\n' "$path"
        fi
    done
}

is_web_lint_target() {
    local path="$1"
    [[ "$path" == web/* ]] || return 1
    case "$path" in
        *.js|*.jsx|*.ts|*.tsx|*.mjs|*.cjs)
            return 0
            ;;
    esac
    return 1
}

needs_full_web_lint() {
    local path
    for path in "$@"; do
        case "$path" in
            web/package.json|web/package-lock.json|web/eslint.config.mjs|web/tsconfig.json)
                return 0
                ;;
        esac
    done
    return 1
}

collect_web_lint_files() {
    local path
    for path in "$@"; do
        if is_web_lint_target "$path"; then
            printf '%s\n' "${path#web/}"
        fi
    done
}

append_unique() {
    local candidate="$1"
    [[ -n "$candidate" && -f "$candidate" ]] || return 0

    local existing
    for existing in "${TEST_TARGETS[@]-}"; do
        [[ "$existing" == "$candidate" ]] && return 0
    done
    TEST_TARGETS+=("$candidate")
}

infer_related_tests() {
    local source_file="$1"
    local stem
    stem="$(basename "$source_file" .py)"

    if [[ "$source_file" == tests/*.py || "$source_file" == tests/**/*.py ]]; then
        append_unique "$source_file"
        return 0
    fi

    if [[ "$stem" == "__init__" ]]; then
        return 0
    fi

    while IFS= read -r match; do
        append_unique "$match"
    done < <(find tests -type f \( -name "test_${stem}.py" -o -name "test_${stem}_*.py" -o -name "test_*${stem}*.py" \) | sort)
}

echo "--- 🛡️ Pre-commit Hook: Running staged checks ---"

STAGED_FILES=()
while IFS= read -r path; do
    [[ -n "$path" ]] && STAGED_FILES+=("$path")
done < <(collect_staged_files)

if [[ "${#STAGED_FILES[@]}" -eq 0 ]]; then
    echo "--- ℹ️ No staged files detected, skipping checks. ---"
    exit 0
fi

PYTHON_FILES=()
while IFS= read -r path; do
    [[ -n "$path" ]] && PYTHON_FILES+=("$path")
done < <(collect_python_files "${STAGED_FILES[@]}")

WEB_FILES=()
while IFS= read -r path; do
    [[ -n "$path" ]] && WEB_FILES+=("$path")
done < <(collect_web_files "${STAGED_FILES[@]}")

WEB_LINT_FILES=()
while IFS= read -r path; do
    [[ -n "$path" ]] && WEB_LINT_FILES+=("$path")
done < <(collect_web_lint_files "${STAGED_FILES[@]}")

if [[ "${#PYTHON_FILES[@]}" -gt 0 ]]; then
    echo "--- 🐍 Verifying Python syntax for staged files ---"
    for pyfile in "${PYTHON_FILES[@]}"; do
        python3 -m py_compile "$pyfile"
    done

    echo "--- 🛠️ Running Ruff Check on staged Python files ---"
    $RUFF check --fix --unsafe-fixes "${PYTHON_FILES[@]}"

    echo "--- 🛠️ Running Ruff Format on staged Python files ---"
    $RUFF format "${PYTHON_FILES[@]}"

    echo "--- 📌 Re-staging Ruff fixes ---"
    git add -- "${PYTHON_FILES[@]}"
else
    echo "--- ℹ️ No staged Python files, skipping Python lint. ---"
fi

if [[ "${#WEB_FILES[@]}" -gt 0 ]]; then
    if needs_full_web_lint "${STAGED_FILES[@]}"; then
        echo "--- 🧹 Running full web ESLint due to config changes ---"
        (
            cd web
            npm run lint -- .
        )
    elif [[ "${#WEB_LINT_FILES[@]}" -gt 0 ]]; then
        echo "--- 🧹 Running ESLint on staged web files ---"
        (
            cd web
            npm run lint -- "${WEB_LINT_FILES[@]}"
        )
    else
        echo "--- ℹ️ No staged web JS/TS files, skipping web lint. ---"
    fi

    echo "--- 🌐 Detected staged web changes, running frontend build ---"
    docker-compose build web
else
    echo "--- ℹ️ No staged web changes, skipping web lint and frontend build. ---"
fi

if [[ "${#PYTHON_FILES[@]}" -eq 0 ]]; then
    echo "--- ℹ️ No staged Python files, skipping pytest. ---"
    echo "--- ✅ Staged checks passed! ---"
    exit 0
fi

if needs_full_pytest "${STAGED_FILES[@]}"; then
    echo "--- 🧪 Running full pytest suite due to shared test/config changes ---"
    if [[ "$MODE" == "offline" ]]; then
        $PYTEST -m "not integration" tests/
    else
        $PYTEST tests/
    fi
    echo "--- ✅ Staged checks passed! ---"
    exit 0
fi

TEST_TARGETS=()
for pyfile in "${PYTHON_FILES[@]}"; do
    infer_related_tests "$pyfile"
done

if [[ "${#TEST_TARGETS[@]}" -eq 0 ]]; then
    echo "--- ℹ️ No directly related tests inferred from staged files, skipping pytest. ---"
    echo "--- ✅ Staged checks passed! ---"
    exit 0
fi

echo "--- 🧪 Running related pytest targets ---"
printf '   %s\n' "${TEST_TARGETS[@]}"

if [[ "$MODE" == "offline" ]]; then
    $PYTEST -m "not integration" "${TEST_TARGETS[@]}"
else
    $PYTEST "${TEST_TARGETS[@]}"
fi

echo "--- ✅ Staged checks passed! ---"
