import os
import tempfile

# ============================================================================
# Test Environment Configuration
# ============================================================================
# This file MUST be imported before any app modules to ensure that
# the application configures itself for testing (e.g. using a test DB).

os.environ["LLM_MODEL"] = "gpt-4o-mini"
os.environ["LLM_BASE_URL"] = "http://localhost:8000"
os.environ["LLM_API_KEY"] = "sk-dummy"
os.environ["OPENAI_API_KEY"] = "sk-dummy"

# Ensure project root is in path BEFORE app imports
import sys

# Path to the 'tests' directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Parent of 'tests' should be the project root
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"DEBUG: Added {project_root} to sys.path")

# Use file-based sqlite for sharing between app and test fixtures
TEST_DB_DIR = tempfile.mkdtemp()
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

# Export for conftest.py
__all__ = ["TEST_DB_DIR", "TEST_DB_PATH"]
