#!/usr/bin/env python3
"""
Test FileBrowser upload to NNLC server
"""

from pathlib import Path
import requests
from datetime import datetime
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# FileBrowser Configuration
BASE_URL = "https://dl.relay.net:4443"
UPLOAD_PATH = "/VW Passat NMS with torque steer/"
USERNAME = "nnlc"
PASSWORD = "nnlc"


def create_test_file():
    """Create a small test file"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    test_file = Path(f"test-upload-{timestamp}.txt")

    with open(test_file, 'w') as f:
        f.write(f"FileBrowser test file created at {datetime.now()}\n")
        f.write("This is a test upload from the rlog downloader script.\n")
        f.write("If you see this, the upload worked!\n")

    print(f"Created test file: {test_file}")
    return test_file


def login():
    """Login to FileBrowser and get auth token"""
    print("\n1. Logging in to FileBrowser...")

    login_url = f"{BASE_URL}/api/login"

    try:
        response = requests.post(
            login_url,
            json={
                "username": USERNAME,
                "password": PASSWORD
            },
            verify=False
        )

        print(f"   Login status: {response.status_code}")

        if response.status_code == 200:
            token = response.text.strip('"')  # Remove quotes from token
            print(f"   ✓ Login successful!")
            return token
        else:
            print(f"   ✗ Login failed: {response.text}")
            return None

    except Exception as e:
        print(f"   ✗ Login error: {e}")
        return None


def test_upload(token, test_file):
    """Test uploading file to FileBrowser"""
    print("\n2. Testing file upload...")

    # FileBrowser upload endpoint
    upload_url = f"{BASE_URL}/api/resources{UPLOAD_PATH}{test_file.name}"

    print(f"   Upload URL: {upload_url}")

    try:
        with open(test_file, 'rb') as f:
            response = requests.post(
                upload_url,
                headers={
                    "X-Auth": token
                },
                data=f,
                verify=False
            )

        print(f"   Response status: {response.status_code}")

        if response.status_code in [200, 201]:
            print(f"   ✓ Upload successful!")
            view_url = f"{BASE_URL}{UPLOAD_PATH}{test_file.name}"
            print(f"   URL: {view_url}")
            return True
        else:
            print(f"   ✗ Upload failed: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"   ✗ Upload error: {e}")
        return False


if __name__ == "__main__":
    print("FileBrowser Upload Test Script")
    print("=" * 50)

    test_file = create_test_file()

    token = login()
    if not token:
        print("\n❌ Failed to login")
        exit(1)

    success = test_upload(token, test_file)

    print("\n" + "=" * 50)
    if success:
        print(f"✓ Upload works! Check the file at the server.")
        print(f"Local file kept at: {test_file}")
    else:
        print("❌ Upload failed. Check the errors above.")