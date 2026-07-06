import google.generativeai as genai

# Paste your REAL Gemini key here (starts with AIza...)
API_KEY = "paste-your-key-here"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

response = model.generate_content("Say hello in one word")
print("SUCCESS:", response.text)