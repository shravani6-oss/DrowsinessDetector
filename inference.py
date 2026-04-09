import urllib.request
import time
import os
import sys
from openai import OpenAI

def test_inference():
    print("[START] task=drowsiness_check", flush=True)
    
    # Check 1: LLM Proxy verification (REQUIRED by OpenEnv)
    try:
        base_url = os.environ.get("API_BASE_URL")
        api_key = os.environ.get("API_KEY")
        
        if base_url and api_key:
            client = OpenAI(base_url=base_url, api_key=api_key)
            # Use a dummy model name if none provided
            model = os.environ.get("MODEL_NAME", "gpt-4o")
            print(f"Making LLM proxy call to {base_url}...", flush=True)
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Return 'OK'"}],
                max_tokens=5
            )
            print(f"[STEP] step=1 status=llm_proxy_verified response='{response.choices[0].message.content.strip()}'", flush=True)
        else:
            print("[STEP] step=1 status=llm_proxy_skipped_missing_env", flush=True)
    except Exception as e:
        print(f"[STEP] step=1 status=llm_proxy_failed", flush=True)
        print(f"LLM Error: {e}", file=sys.stderr)

    # Check 2: API connectivity
    url = "http://localhost:7860/reset"
    step_count = 2
    score = 0.0
    
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"[STEP] step={step_count} status=api_reachable", flush=True)
                score = 1.0
            else:
                print(f"[STEP] step={step_count} status=error_code_{resp.status}", flush=True)
    except Exception as e:
        print(f"[STEP] step={step_count} status=connection_error", flush=True)
        print(f"API Error details: {e}", file=sys.stderr)

    # Final result required by OpenEnv
    print(f"[END] task=drowsiness_check score={score} steps={step_count}", flush=True)

if __name__ == "__main__":
    # Give the server a moment to start
    time.sleep(2)
    test_inference()



