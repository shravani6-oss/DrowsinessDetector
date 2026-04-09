import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

def main():
    port = int(os.environ.get('PORT', 7860))
    app.run(debug=False, threaded=True, host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()

