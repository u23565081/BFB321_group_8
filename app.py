"""Alternate entry module for markers and hosts that expect app.py.

The application factory lives in the app package. This module builds the
same Flask object as run.py. run.py, the start scripts, and the Docker
command stay the supported way to launch the application.
"""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=5000, debug=app.config.get("DEBUG", False))
