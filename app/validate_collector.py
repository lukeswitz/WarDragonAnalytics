#!/usr/bin/env python3
"""
Validation script for collector.py

Checks:
1. Python syntax
2. Import dependencies
3. Configuration loading
4. Database connection (optional)
5. HTTP client initialization
"""

import sys
import os
from pathlib import Path

def check_syntax():
    """Check Python syntax"""
    print("Checking Python syntax...")
    try:
        import py_compile
        py_compile.compile('collector.py', doraise=True)
        print("✓ Syntax check passed")
        return True
    except py_compile.PyCompileError as e:
        print(f"✗ Syntax error: {e}")
        return False

def check_imports():
    """Check if all required imports are available"""
    print("\nChecking required dependencies...")
    required = {
        'asyncio': 'Python standard library',
        'logging': 'Python standard library',
        'signal': 'Python standard library',
        'sys': 'Python standard library',
        'datetime': 'Python standard library',
        'pathlib': 'Python standard library',
        'typing': 'Python standard library',
        'os': 'Python standard library',
        'httpx': 'pip install httpx',
        'yaml': 'pip install pyyaml',
        'sqlalchemy': 'pip install sqlalchemy',
    }

    missing = []
    for module, install_cmd in required.items():
        try:
            if module == 'yaml':
                import yaml
            else:
                __import__(module)
            print(f"  ✓ {module}")
        except ImportError:
            print(f"  ✗ {module} - {install_cmd}")
            missing.append(module)

    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False

    print("✓ All dependencies available")
    return True

def check_config_loading():
    """Test configuration loading"""
    print("\nChecking configuration loading...")
    try:
        import yaml
        config_file = Path('../config/kits.yaml')

        if not config_file.exists():
            config_file = Path('../config/kits.yaml.example')

        if not config_file.exists():
            print("  ⚠ No config file found (expected at ../config/kits.yaml)")
            return True  # Not a fatal error

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        if 'kits' not in config:
            print("  ✗ Configuration missing 'kits' key")
            return False

        kits = config['kits']
        print(f"  ✓ Configuration loaded: {len(kits)} kits defined")

        # Validate kit configs
        for i, kit in enumerate(kits):
            if 'id' not in kit:
                print(f"  ✗ Kit {i} missing 'id' field")
                return False
            if 'api_url' not in kit:
                print(f"  ✗ Kit {kit.get('id', i)} missing 'api_url' field")
                return False
            print(f"    - {kit['id']}: {kit['api_url']}")

        print("✓ Configuration validation passed")
        return True
    except Exception as e:
        print(f"  ✗ Configuration loading error: {e}")
        return False

def check_database_connection():
    """Test database connection (optional)"""
    print("\nChecking database connection (optional)...")

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("  ⚠ DATABASE_URL not set, skipping database test")
        return True

    try:
        from sqlalchemy import create_engine, text

        print(f"  Connecting to: {database_url.split('@')[1] if '@' in database_url else database_url}")
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            if row[0] == 1:
                print("  ✓ Database connection successful")

                # Check if tables exist
                result = conn.execute(text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('kits', 'drones', 'signals', 'system_health')
                """))
                tables = [row[0] for row in result]

                if tables:
                    print(f"  ✓ Found tables: {', '.join(tables)}")
                else:
                    print("  ⚠ Database tables not found (run timescaledb/init.sql)")

                return True

    except ImportError:
        print("  ⚠ sqlalchemy not installed, skipping database test")
        return True
    except Exception as e:
        print(f"  ✗ Database connection failed: {e}")
        print("  ⚠ This is not fatal - collector will retry on startup")
        return True  # Not fatal for validation

def check_http_client():
    """Test HTTP client initialization"""
    print("\nChecking HTTP client...")
    try:
        import httpx

        client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            ),
            timeout=httpx.Timeout(10.0)
        )
        print("  ✓ HTTP client initialized")
        return True
    except ImportError:
        print("  ✗ httpx not installed")
        return False
    except Exception as e:
        print(f"  ✗ HTTP client error: {e}")
        return False

def check_collector_module():
    """Try importing collector module"""
    print("\nChecking collector module...")
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        # Try importing (without running main)
        import collector

        # Check if main classes exist
        required_classes = [
            'KitHealth',
            'DatabaseWriter',
            'KitCollector',
            'CollectorService'
        ]

        for cls in required_classes:
            if not hasattr(collector, cls):
                print(f"  ✗ Missing class: {cls}")
                return False
            print(f"  ✓ Found class: {cls}")

        print("✓ Collector module loaded successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed to import collector: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all validation checks"""
    print("=" * 60)
    print("WarDragon Analytics Collector - Validation Script")
    print("=" * 60)

    checks = [
        ("Syntax", check_syntax),
        ("Imports", check_imports),
        ("Configuration", check_config_loading),
        ("Database", check_database_connection),
        ("HTTP Client", check_http_client),
        ("Module Loading", check_collector_module),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check failed with exception: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")

    print(f"\nResult: {passed}/{total} checks passed")

    if passed == total:
        print("\n✓ All validation checks passed!")
        print("\nNext steps:")
        print("  1. Set up TimescaleDB: docker-compose up -d timescaledb")
        print("  2. Initialize schema: docker exec -i timescaledb psql -U wardragon < timescaledb/init.sql")
        print("  3. Configure kits: cp config/kits.yaml.example config/kits.yaml")
        print("  4. Start collector: python collector.py")
        return 0
    else:
        print("\n✗ Some validation checks failed")
        print("\nFix the issues above before running the collector")
        return 1

if __name__ == '__main__':
    sys.exit(main())
