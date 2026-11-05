"""Alternate entry module for markers and hosts that expect app.py.

The application factory lives in the app package. This module builds the
same Flask object as run.py. run.py, the start scripts, and the Docker
command stay the supported way to launch the application.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))
