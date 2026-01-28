import requests
import json
import sys

def test_stream(message):
    url = "http://localhost:8000/chat/stream"
    headers = {
        "X-API-Key": "sk-test-123456",
        "Content-Type": "application/json"
    }
    payload = {"message": message}

    print(f"--- Sending Stream Request: {message} ---")
    
    with requests.post(url, json=payload, headers=headers, stream=True) as response:
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data = json.loads(decoded_line[6:])
                    event = data.get("event")
                    payload = data.get("data")
                    
                    if event == "heartbeat":
                        print(f"💓 {payload}")
                    elif event == "thought":
                        print(f"💭 {payload}", end="", flush=True)
                    elif event == "tool_start":
                        print(f"\n🔧 Calling {payload.get('name')} with {payload.get('args')}")
                    elif event == "tool_end":
                        print(f"✅ {payload.get('name')} result: {payload.get('result')[:50]}...")
                    elif event == "final_answer":
                        print(f"\n🏁 Final Answer: {payload}")
                    elif event == "error":
                        print(f"\n❌ Error: {payload}")

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "你好，你是谁？"
    test_stream(msg)
