# check.py
import requests
import time

print("Checking if server is running...")

for i in range(5):
    try:
        # Increase timeout to 30 seconds
        response = requests.get("http://localhost:5000/api/health", timeout=30)
        print(f"✅ Server is running! Status: {response.status_code}")
        print(response.json())
        break
    except requests.exceptions.ConnectionError:
        print(f"❌ Attempt {i+1}/5: Server not responding...")
        time.sleep(1)
    except requests.exceptions.ReadTimeout:
        print(f"⚠️  Attempt {i+1}/5: Server is slow (still loading models)...")
        time.sleep(2)
else:
    print("\n⚠️  Server is NOT running or taking too long!")
    print("\nPlease start the server first:")
    print("  python app.py")
