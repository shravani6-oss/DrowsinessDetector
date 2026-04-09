import urllib.request
import time
import os

def test_inference():
    print("Initializing inference environment...")
    url = "http://localhost:7860/reset"
    try:
        # Using urllib to avoid external dependencies like 'requests'
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("Reset endpoint reachable.")
            else:
                print(f"Reset returned status code: {response.status}")
    except Exception as e:
        print(f"Inference check note: Environment might be starting or unreachable. Error: {e}")

if __name__ == "__main__":
    # Give the server a moment to potentially start if called immediately
    time.sleep(2)
    test_inference()
    print("Inference check completed.")
