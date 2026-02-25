import os
import socket
import sys


def audit_hook(event, args):
    # Block networking
    if event.startswith("socket."):
        raise PermissionError(f"Network access blocked: {event}")

    # Block subprocesses
    if event in ("os.system", "subprocess.Popen", "os.spawn", "os.posix_spawn"):
        raise PermissionError(f"Subprocess blocked: {event}")

    # Block file access outside allowed dir
    if event == "open":
        file_path = args[0]
        # Very crude check for demo
        if not str(file_path).startswith("/tmp/sandbox"):
            # Allow reading standard python libs (usually in /usr or /Library)
            if not (str(file_path).startswith("/usr/") or str(file_path).startswith("/Library/")):
                raise PermissionError(f"File access blocked: {file_path}")


sys.addaudithook(audit_hook)

print("Starting tests...")

try:
    print("Testing network...")
    socket.socket().connect(("8.8.8.8", 53))
except PermissionError as e:
    print(f"Caught expected error: {e}")

try:
    print("Testing subprocess...")
    os.system("ls")
except PermissionError as e:
    print(f"Caught expected error: {e}")

try:
    print("Testing file access...")
    with open("/etc/passwd", "r") as f:
        print(f.read(10))
except PermissionError as e:
    print(f"Caught expected error: {e}")

print("Tests finished.")
