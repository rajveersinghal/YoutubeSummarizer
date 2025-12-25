# test_gemini_models.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure API
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("=" * 60)
print("TESTING AVAILABLE GEMINI MODELS")
print("=" * 60)
print(f"\nAPI Key: {api_key[:20]}...{api_key[-4:]}\n")

# List all available models
print("📋 Available models that support generateContent:\n")
working_models = []

try:
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            model_name = model.name.replace('models/', '')  # Remove prefix
            print(f"✅ {model_name}")
            working_models.append(model_name)
except Exception as e:
    print(f"❌ Error listing models: {e}")

print("\n" + "=" * 60)
print("TESTING MODELS")
print("=" * 60)

# Test each model format
test_models = [
    "gemini-pro",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "models/gemini-1.5-flash",
]

for model_name in test_models:
    try:
        print(f"\n🧪 Testing: {model_name}")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Hello'")
        print(f"   ✅ SUCCESS: {response.text.strip()[:50]}")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            print(f"   ❌ NOT FOUND")
        elif "429" in error_msg:
            print(f"   ⚠️  QUOTA EXCEEDED")
        else:
            print(f"   ❌ ERROR: {error_msg[:100]}")

print("\n" + "=" * 60)
print("✅ RECOMMENDED MODEL TO USE:")
print("=" * 60)
if working_models:
    print(f"\nUse: {working_models[0]}")
else:
    print("\n⚠️  No models found. Check your API key.")
