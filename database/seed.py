"""Compatibility entry point for the required database seed script."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.services.seed import seed_database


if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        seed_database()
    print("Demo users, five shops, 20 SKUs and demand history loaded.")
