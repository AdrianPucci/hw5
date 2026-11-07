"""Reset the working database to the original tickets.

Copies data/campus_customs.db (the untouched original) over data/campus_customs_new.db
(the working copy the MCP server and backend use). Stop the servers before running it.

Run from the HMW 5 folder:  python scripts/reset_db.py
"""

import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
ORIGINAL = DATA / "campus_customs.db"
WORKING = DATA / "campus_customs_new.db"

if __name__ == "__main__":
    shutil.copyfile(ORIGINAL, WORKING)
    print(f"Reset {WORKING.name} from {ORIGINAL.name}")
