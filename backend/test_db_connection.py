import sys
import logging
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database import engine, check_db_connection, init_db
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("db_test")

def main():
    print("=" * 60)
    print(" Neon PostgreSQL / Database Connection Verifier")
    print("=" * 60)
    
    # Redact password for safe terminal output
    url = str(engine.url)
    if engine.url.password:
        safe_url = url.replace(engine.url.password, "******")
    else:
        safe_url = url

    print(f"* Target URL: {safe_url}")
    print(f"* Dialect:    {engine.dialect.name}")
    print(f"* Driver:     {engine.driver}")
    print("=" * 60)

    print("\n[1/3] Testing basic connectivity...")
    if not check_db_connection():
        print("[FAIL] Failed to connect to the database.")
        print("Please verify your DATABASE_URL in backend/.env and ensure your Neon project is active.")
        sys.exit(1)
    print("[SUCCESS] Established connection to database.")

    print("\n[2/3] Checking / initializing tables (jobs, job_hashes)...")
    try:
        init_db()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"[SUCCESS] Tables present in database: {tables}")
    except Exception as e:
        print(f"[FAIL] Table initialization failed: {e}")
        sys.exit(1)

    print("\n[3/3] Database is ready for JobRadar AI ingestion & scoring!")
    print("=" * 60)

if __name__ == "__main__":
    main()
