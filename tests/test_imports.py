import importlib
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.append(os.getcwd())


def find_modules(start_path):
    """Recursively find all python modules in app/"""
    modules = []
    path = Path(start_path)

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                # Convert path to module name
                # e.g. app/core/agent.py -> app.core.agent
                rel_path = os.path.relpath(os.path.join(root, file), os.getcwd())
                module_name = rel_path.replace(os.sep, ".")[:-3]
                modules.append(module_name)
    return modules


def test_import_all_modules():
    """
    Dynamically attempts to import every python file in the app directory.
    This catches SyntaxErrors, IndentationErrors, and missing imports.
    """
    modules_to_test = find_modules("app")

    print(f"\nDiscovered {len(modules_to_test)} modules.")

    failed = []
    for module_name in modules_to_test:
        try:
            importlib.import_module(module_name)
        except Exception as e:
            failed.append(f"{module_name}: {e}")

    if failed:
        pytest.fail(f"Failed to import {len(failed)} modules:\n" + "\n".join(failed))
