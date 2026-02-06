import os
import re


def test_dashboard_static_imports():
    """
    Perform static analysis on dashboard files to ensure they don't use the 'from dashboard.utils'
    prefix which causes ModuleNotFoundError when run via Streamlit.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dashboard_dir = os.path.join(project_root, "dashboard")

    files_to_check = [os.path.join(dashboard_dir, "Main.py")]
    pages_dir = os.path.join(dashboard_dir, "pages")
    for filename in os.listdir(pages_dir):
        if filename.endswith(".py"):
            files_to_check.append(os.path.join(pages_dir, filename))

    errors = []
    for filepath in files_to_check:
        with open(filepath, "r") as f:
            content = f.read()
            # Look for 'from dashboard.utils' (case sensitive)
            if re.search(r"from\s+dashboard\.utils", content):
                errors.append(f"❌ {os.path.basename(filepath)}: Contains invalid 'from dashboard.utils' import.")
            else:
                print(f"✅ {os.path.basename(filepath)}: Import check passed.")

    if errors:
        print("\n".join(errors))
        exit(1)
    else:
        print("\nSummary: All dashboard files verified. No invalid 'dashboard.utils' imports found.")


if __name__ == "__main__":
    test_dashboard_static_imports()
