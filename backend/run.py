import os

from app import app

if __name__ == "__main__":
    # PUBLIC_INTERFACE
    # The entrypoint for running the Flask development server.
    # Reads host/port/debug from environment variables.
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3001"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
