import re
from pathlib import Path

content = Path("skills/homeassistant.md").read_text(encoding="utf-8")
section_name = "Critical Rules"

print(f"Searching for section: '{section_name}' in content of length {len(content)}")

# Original Regex
pattern_str = rf"^##\s+.*?{re.escape(section_name)}.*?\n(.*?)(?=\n##\s+|$)"
print(f"Pattern: {pattern_str}")

pattern = re.compile(pattern_str, re.DOTALL | re.MULTILINE | re.IGNORECASE)
match = pattern.search(content)

if match:
    print("MATCH FOUND!")
    print(f"Captured length: {len(match.group(1))}")
    print("Preview: " + match.group(1)[:100].replace("\n", "\\n"))
else:
    print("NO MATCH.")
    # Debug: Print headers found
    headers = re.findall(r"^##\s+.*$", content, re.MULTILINE)
    print("Headers found:")
    for h in headers:
        print(f"  '{h}'")
