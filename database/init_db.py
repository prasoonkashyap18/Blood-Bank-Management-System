"""Create the SQLite database and tables if they do not already exist.

Safe to run any number of times: it only ever issues CREATE TABLE/INDEX IF
NOT EXISTS statements, so existing data is never touched.

Usage (from the project root):
    python database/init_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import Config  # noqa: E402
from backend.database import init_db  # noqa: E402

if __name__ == "__main__":
    init_db(Config.DATABASE_PATH)
    print(f"Database ready at {Config.DATABASE_PATH}")
