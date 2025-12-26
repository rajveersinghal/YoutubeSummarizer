# test_import.py
print("Testing imports...")

try:
    print("1. Importing settings...")
    from config.settings import settings
    print(f"   ✅ Settings imported - LOG_LEVEL: {settings.LOG_LEVEL}")
except Exception as e:
    print(f"   ❌ Error importing settings: {e}")
    exit(1)

try:
    print("2. Importing logger...")
    from config.logging_config import logger
    print(f"   ✅ Logger imported - Level: {logger.level}")
except Exception as e:
    print(f"   ❌ Error importing logger: {e}")
    exit(1)

try:
    print("3. Testing logger...")
    logger.info("Test log message")
    print("   ✅ Logger working")
except Exception as e:
    print(f"   ❌ Error testing logger: {e}")
    exit(1)

print("\n✅ All imports successful!")
