#!/usr/bin/env python3

import os
import zipfile
from pathlib import Path
import paramiko
import stat
import requests
from datetime import datetime
import urllib3
import subprocess
import time
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

COMMA_IP = "172.20.10.3"
COMMA_USER = "comma"
REALDATA_PATH = "/data/media/0/realdata"
DONGLE_ID_PATH = "/data/params/d/DongleId"

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
if DATA_DIR.exists():
    LOCAL_TEMP_DIR = DATA_DIR / "comma_rlogs_temp"
    OUTPUT_DIR = DATA_DIR
    UPLOADED_LOGS_FILE = DATA_DIR / "uploaded_logs.json"
else:
    LOCAL_TEMP_DIR = Path("./comma_rlogs_temp")
    OUTPUT_DIR = Path(".")
    UPLOADED_LOGS_FILE = Path("uploaded_logs.json")

BASE_URL = "https://dl.relay.net:4443"
UPLOAD_PATH = "/VW Passat NMS with torque steer/"
USERNAME = "nnlc"
PASSWORD = "nnlc"


def load_uploaded_logs():
    if UPLOADED_LOGS_FILE.exists():
        with open(UPLOADED_LOGS_FILE, 'r') as f:
            return set(json.load(f))
    return set()


def save_uploaded_logs(uploaded_logs):
    with open(UPLOADED_LOGS_FILE, 'w') as f:
        json.dump(list(uploaded_logs), f, indent=2)


def ping_comma():
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '2', COMMA_IP],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except:
        return False


def wait_for_comma():
    print(f"Waiting for Comma 3X at {COMMA_IP}...")

    while not ping_comma():
        print(".", end="", flush=True)
        time.sleep(5)
    print("\n✓ Comma 3X is online!")
    return True


def connect_sftp():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(COMMA_IP, username=COMMA_USER, look_for_keys=True, timeout=10)
    sftp = ssh.open_sftp()
    return ssh, sftp


def get_dongle_id(sftp):
    try:
        with sftp.file(DONGLE_ID_PATH, 'r') as f:
            return f.read().decode().strip()
    except Exception as e:
        print(f"Error reading dongle ID: {e}")
        return "unknown"


def download_new_rlogs(sftp, temp_dir, uploaded_logs):
    temp_dir.mkdir(exist_ok=True)
    rlogs = []
    new_routes = []

    print("Scanning for new rlogs...")

    try:
        route_dirs = sorted(sftp.listdir(REALDATA_PATH))
        total_routes = len(route_dirs)
        already_uploaded = sum(1 for r in route_dirs if r in uploaded_logs)

        print(f"Found {total_routes} routes total, {already_uploaded} already uploaded")
        print(f"Checking for {total_routes - already_uploaded} new routes...")
    except Exception as e:
        print(f"Error listing routes: {e}")
        return rlogs, new_routes

    for i, route_name in enumerate(route_dirs, 1):
        # Skip already uploaded routes
        if route_name in uploaded_logs:
            continue

        route_path = f"{REALDATA_PATH}/{route_name}"

        try:
            file_stat = sftp.stat(route_path)
            if not stat.S_ISDIR(file_stat.st_mode):
                continue
        except Exception as e:
            continue

        for rlog_name in ['rlog.zst']:
            remote_rlog = f"{route_path}/{rlog_name}"
            try:
                sftp.stat(remote_rlog)
                local_route_dir = temp_dir / route_name
                local_route_dir.mkdir(exist_ok=True)
                local_rlog = local_route_dir / rlog_name

                print(f"[NEW] Downloading {route_name}/{rlog_name}...")
                sftp.get(remote_rlog, str(local_rlog))
                rlogs.append(local_rlog)
                new_routes.append(route_name)
                break

            except FileNotFoundError:
                continue
            except Exception as e:
                if "not open" in str(e).lower() or "closed" in str(e).lower() or "connection" in str(e).lower():
                    print(f"\n✗ Connection lost during download!")
                    print(f"Downloaded {len(rlogs)} new rlogs before disconnect")
                    return rlogs, new_routes
                print(f"Error downloading {route_name}/{rlog_name}: {e}")
                continue

    return rlogs, new_routes


def create_zip(rlogs, dongle_id, output_dir, temp_dir):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_filename = output_dir / f"{dongle_id}-rlogs-{timestamp}.zip"
    print(f"\nCreating {zip_filename}...")
    print(f"Compressing {len(rlogs)} rlog files...")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i, rlog_path in enumerate(rlogs, 1):
            arcname = f"{rlog_path.parent.name}/{rlog_path.name}"
            print(f"[{i}/{len(rlogs)}] Adding {arcname}")
            zipf.write(rlog_path, arcname=arcname)
    import shutil
    shutil.rmtree(temp_dir)
    file_size = zip_filename.stat().st_size / (1024 * 1024)
    print(f"\nDone! Created {zip_filename}")
    print(f"Size: {file_size:.2f} MB")
    return zip_filename


def login_filebrowser():
    print("\nLogging in to FileBrowser...")

    login_url = f"{BASE_URL}/api/login"

    try:
        response = requests.post(
            login_url,
            json={
                "username": USERNAME,
                "password": PASSWORD
            },
            verify=False,
            timeout=30
        )

        if response.status_code == 200:
            token = response.text.strip('"')
            print("✓ Login successful!")
            return token
        else:
            print(f"✗ Login failed: {response.text}")
            return None

    except Exception as e:
        print(f"✗ Login error: {e}")
        return None


def upload_to_filebrowser(token, local_file):
    print(f"\nUploading {local_file.name} ({local_file.stat().st_size / (1024 * 1024):.2f} MB)...")
    print("This may take several minutes...")

    upload_url = f"{BASE_URL}/api/resources{UPLOAD_PATH}{local_file.name}"

    try:
        with open(local_file, 'rb') as f:
            response = requests.post(
                upload_url,
                headers={
                    "X-Auth": token
                },
                data=f,
                verify=False,
                timeout=600
            )

        if response.status_code in [200, 201]:
            view_url = f"{BASE_URL}{UPLOAD_PATH}{local_file.name}"
            print(f"✓ Upload complete!")
            print(f"URL: {view_url}")
            return view_url
        else:
            print(f"✗ Upload failed: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"✗ Upload error: {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("Comma 3X Rlog Auto-Uploader")
    print("=" * 60)
    print("Monitoring for new logs and auto-uploading...")
    print("Press Ctrl+C to stop\n")

    uploaded_logs = load_uploaded_logs()
    print(f"Loaded tracking file: {len(uploaded_logs)} routes already uploaded\n")

    try:
        while True:
            wait_for_comma()

            print("\nConnecting to Comma 3X...")

            try:
                ssh, sftp = connect_sftp()
                print("Connected!")

                dongle_id = get_dongle_id(sftp)
                print(f"Dongle ID: {dongle_id}")

                rlogs, new_routes = download_new_rlogs(sftp, LOCAL_TEMP_DIR, uploaded_logs)

                try:
                    sftp.close()
                    ssh.close()
                    print("SFTP connection closed")
                except:
                    pass

                if not rlogs:
                    print("\n✓ No new rlogs to upload!")
                    print("Waiting for device to leave and return with new logs...")

                    # Wait for device to disappear
                    while ping_comma():
                        time.sleep(5)
                    print("\n✗ Comma 3X disconnected")

                    continue

                print(f"\n✓ Downloaded {len(rlogs)} new rlog files")

                # Create zip
                zip_path = create_zip(rlogs, dongle_id, OUTPUT_DIR, LOCAL_TEMP_DIR)

                # Upload to FileBrowser
                token = login_filebrowser()
                if not token:
                    print("\nFailed to login to FileBrowser")
                    print(f"Local file saved at: {zip_path}")
                    time.sleep(60)
                    continue

                upload_url = upload_to_filebrowser(token, zip_path)

                if upload_url:
                    print(f"\n✓ Upload successful!")
                    # Mark these routes as uploaded
                    uploaded_logs.update(new_routes)
                    save_uploaded_logs(uploaded_logs)
                    print(f"✓ Marked {len(new_routes)} routes as uploaded")
                    print(f"Total uploaded routes: {len(uploaded_logs)}")
                else:
                    print(f"\nUpload failed. Local file saved at: {zip_path}")

                # Wait for device to leave before checking again
                print("\nWaiting for device to leave...")
                while ping_comma():
                    time.sleep(5)
                print("\n✗ Comma 3X disconnected")

            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(30)

    except KeyboardInterrupt:
        print("\n\nStopped by user")
        print(f"Total routes uploaded: {len(uploaded_logs)}")