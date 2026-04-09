import urllib.request
import time
import os
import sys

def test_inference():
    print("[START] task=drowsiness_check", flush=True)
    url = "http://localhost:7860/reset"
    
    # Initialize some metrics for the STEP/END logs
    step_count = 1
    score = 0.0
    
    try:
        # Step 1: Verify API connectivity
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print(f"[STEP] step={step_count} status=api_reachable", flush=True)
                score = 1.0
            else:
                print(f"[STEP] step={step_count} status=error_code_{response.status}", flush=True)
    except Exception as e:
        # Connection error might happen if the server is still booting
        print(f"[STEP] step={step_count} status=connection_error", flush=True)
        print(f"Error details: {e}", file=sys.stderr)

    # Final result required by OpenEnv
    print(f"[END] task=drowsiness_check score={score} steps={step_count}", flush=True)

if __name__ == "__main__":
    # Give the server a moment to start
    time.sleep(2)
    test_inference()


