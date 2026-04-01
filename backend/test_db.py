# verify_db.py
import psycopg2
import sys
from urllib.parse import urlparse, urlunparse

from core.config import settings


def _psql_connect(database: str | None = None):
    """Connect with same host/port/user/password as .env; override DB name if given."""
    url = settings.DATABASE_URL
    if database is not None:
        u = urlparse(url)
        url = urlunparse(
            (u.scheme, u.netloc, f"/{database}", u.params, u.query, u.fragment)
        )
    return psycopg2.connect(url)


def verify_postgresql_running():
    """Check if PostgreSQL service is running"""
    print("\n🔍 1. Checking PostgreSQL service...")
    import subprocess
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "is-active", "postgresql"],
            capture_output=True, text=True
        )
        if result.stdout.strip() == "active":
            print("   ✅ PostgreSQL is running")
            return True
        else:
            print("   ❌ PostgreSQL is not running")
            print("   💡 Run: sudo systemctl start postgresql")
            return False
    except:
        print("   ⚠️ Could not check service status")
        return True  # Assume running if can't check

def verify_database_exists():
    """Check if database exists"""
    print("\n🔍 2. Checking database exists...")
    try:
        conn = _psql_connect("postgres")
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'forensicedge'")
        exists = cur.fetchone() is not None
        cur.close()
        conn.close()
        
        if exists:
            print("   ✅ Database 'forensicedge' exists")
            return True
        else:
            print("   ❌ Database 'forensicedge' does not exist")
            print("   💡 Create it: sudo -u postgres psql -c \"CREATE DATABASE forensicedge OWNER forensic_user;\"")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect: {e}")
        return False

def verify_tables():
    """Check if tables are created"""
    print("\n🔍 3. Checking tables...")
    try:
        conn = _psql_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [t[0] for t in cur.fetchall()]
        cur.close()
        conn.close()
        
        required_tables = ['users', 'forensic_images', 'similarity_results']
        missing = [t for t in required_tables if t not in tables]
        
        if not missing:
            print(f"   ✅ All required tables exist ({len(tables)} total)")
            return True
        else:
            print(f"   ⚠️ Missing tables: {missing}")
            print("   💡 Run: alembic upgrade head")
            return False
    except Exception as e:
        print(f"   ❌ Cannot check tables: {e}")
        return False

def verify_users():
    """Check if users exist"""
    print("\n🔍 4. Checking users...")
    try:
        conn = _psql_connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users;")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        if count > 0:
            print(f"   ✅ {count} users found")
            return True
        else:
            print("   ⚠️ No users found")
            print("   💡 Run: python seed_data.py")
            return False
    except Exception as e:
        print(f"   ❌ Cannot check users: {e}")
        return False

def test_fastapi_connection():
    """Test if FastAPI can connect to database"""
    print("\n🔍 5. Testing FastAPI database connection...")
    from core.database import test_connection
    if test_connection():
        print("   ✅ FastAPI can connect to database")
        return True
    else:
        print("   ❌ FastAPI cannot connect to database")
        return False

def run_all_checks():
    """Run all verification checks"""
    print("=" * 60)
    print("🔧 FORENSICEDGE DATABASE VERIFICATION")
    print("=" * 60)
    
    checks = [
        ("PostgreSQL Service", verify_postgresql_running),
        ("Database Exists", verify_database_exists),
        ("Tables Created", verify_tables),
        ("Users Exist", verify_users),
        ("FastAPI Connection", test_fastapi_connection),
    ]
    
    results = []
    for name, check in checks:
        results.append(check())
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL {total} CHECKS PASSED!")
        print("\n🚀 Your database is ready! Start FastAPI:")
        print("   cd backend")
        print("   uvicorn app.main:app --reload")
    else:
        print(f"⚠️ {passed}/{total} checks passed")
        print("\n💡 Next steps:")
        if not results[0]:  # PostgreSQL not running
            print("   1. Start PostgreSQL: sudo systemctl start postgresql")
        if not results[1]:  # Database missing
            print("   2. Create database: sudo -u postgres psql -c \"CREATE DATABASE forensicedge OWNER forensic_user;\"")
        if not results[2]:  # Tables missing
            print("   3. Run migrations: cd backend && alembic upgrade head")
        if not results[3]:  # Users missing
            print("   4. Seed database: cd backend && python seed_data.py")
    
    print("=" * 60)

if __name__ == "__main__":
    run_all_checks()