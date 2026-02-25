from app.tools.sandbox import get_sandbox_tool

tool = get_sandbox_tool()

# Test 1: benign code
print("Test 1: Normal math")
print(tool._run("print(1 + 1)"))

# Test 2: process execution
print("\nTest 2: os.system")
print(tool._run("import os\nos.system('echo hello')"))

# Test 3: network
print("\nTest 3: network")
print(tool._run("import urllib.request\nurllib.request.urlopen('http://example.com')"))

# Test 4: read file outside
print("\nTest 4: read /etc/passwd")
print(tool._run("open('/etc/passwd').read()"))

# Test 5: read import
print("\nTest 5: import json")
print(tool._run("import json\nprint(json.dumps({'a': 1}))"))
