"""
Test setup script: registers user, uploads and parses resume, prints resume_id.
Usage: python test_setup.py
"""

import requests

BASE_URL = "http://localhost:8000"
RESUME_PATH = "/home/reddy/Downloads/resume.docx"

# 1. Save user contact
print("1. Saving user...")
resp = requests.post(f"{BASE_URL}/save-user", json={
    "name": "Alex Johnson",
    "email": "alex.johnson@email.com",
    "location": "San Francisco, CA",
    "phone": "5551234567",
    "country_code": "+1",
    "linkedin": "https://linkedin.com/in/alexjohnson",
    "github": "https://github.com/alexjohnson",
})
resp.raise_for_status()
print(f"   {resp.json()}")

# 2. Upload resume file
print("2. Uploading resume file...")
with open(RESUME_PATH, "rb") as f:
    resp = requests.post(
        f"{BASE_URL}/upload",
        params={"user_email": "alex.johnson@email.com"},
        files={"file": ("alex_johnson.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
resp.raise_for_status()
upload_data = resp.json()
saved_path = upload_data["path"]
print(f"   saved to: {saved_path}")

# 3. Parse resume (LLM extracts structured data)
print("3. Parsing resume with LLM (this may take a moment)...")
resp = requests.post(f"{BASE_URL}/upload-resume", json={"path": saved_path})
resp.raise_for_status()
resume_id = resp.json()
print(f"\nresume_id: {resume_id}")
