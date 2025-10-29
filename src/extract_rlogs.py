# Copyright ©️TealTwo, Subject to MIT License
#!/usr/bin/env python3
import os
import zipfile
from pathlib import Path
import paramiko
import stat
import requests
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# config
COMMA_IP = "192.168.173.10"  # Comma 3x Local Static IP
COMMA_USER = "comma"  # this should just be "comma", leave this alone
REALDATA_PATH = "/data/media/0/realdata"  # leave this alone
DONGLE_ID_PATH = "/data/params/d/DongleId"  # leave this alone
LOCAL_TEMP_DIR = Path("./comma_rlogs_temp")  # leave this alone
OUTPUT_DIR = Path(".")  # leave this alone

# filebrowser config
BASE_URL = "https://dl.relay.net:4443" # base url
UPLOAD_PATH = "/VW Passat NMS with torque steer/" # upload path
USERNAME = "nnlc" # username
PASSWORD = "nnlc" # password
def connect_sftp():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(COMMA_IP, username=COMMA_USER, look_for_keys=True)
    sftp = ssh.open_sftp()
    return ssh, sftp
def get_dongle_id(sftp):
    try:
        with sftp.file(DONGLE_ID_PATH, 'r') as f:
            return f.read().decode().strip()
    except Exception as e:
        print(f"Error reading dongle ID: {e}")
        return "unknown"

def download_rlogs(sftp, temp_dir):
    temp_dir.mkdir(exist_ok=True)
    rlogs = []
    print("Scanning for rlogs...")
    route_dirs = sorted(sftp.listdir(REALDATA_PATH))
    print(f"Found {len(route_dirs)} items in realdata")
    for i, route_name in enumerate(route_dirs, 1):
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
                print(f"[{i}/{len(route_dirs)}] Downloading {route_name}/{rlog_name}...")
                sftp.get(remote_rlog, str(local_rlog))
                rlogs.append(local_rlog)
                break
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"Error downloading {route_name}/{rlog_name}: {e}")
                continue
    return rlogs

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
            verify=False
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
                verify=False
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
    print("Connecting to Comma 3X...")
    ssh, sftp = connect_sftp()
    print("Connected!")
    dongle_id = get_dongle_id(sftp)
    print(f"Dongle ID: {dongle_id}")
    rlogs = download_rlogs(sftp, LOCAL_TEMP_DIR)
    if not rlogs:
        print("\nNo rlogs found!")
        sftp.close()
        ssh.close()
        exit(1)
    print(f"\nDownloaded {len(rlogs)} rlog files")
    sftp.close()
    ssh.close()
    print("SFTP connection closed")
    zip_path = create_zip(rlogs, dongle_id, OUTPUT_DIR, LOCAL_TEMP_DIR)
    token = login_filebrowser()
    if not token:
        print("\nFailed to login to FileBrowser")
        print(f"Local file saved at: {zip_path}")
        exit(1)
    upload_url = upload_to_filebrowser(token, zip_path)
    if upload_url:
        print(f"\nAll done! File available at: {upload_url}")
    else:
        print(f"\nUpload failed. Local file saved at: {zip_path}")