"""
CLARA backend entry point. Runs the same FastAPI app as server.py.

Usage:
    python app.py              # start server on port 8000
    python app.py 8080         # start server on given port

For development with reload:
    uvicorn server:app --reload --port 8000
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    import uvicorn
    uvicorn.run(
        "server:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=port,
        reload=os.environ.get("RELOAD", "").lower() in ("1", "true", "yes"),
    )
