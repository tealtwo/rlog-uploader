#!/usr/bin/env python3

from flask import Flask, render_template_string, request, jsonify, Response
import subprocess
import json
import sys
import time
import re
import os
from pathlib import Path

app = Flask(__name__)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
if DATA_DIR.exists():
    CONFIG_FILE = DATA_DIR / "config.json"
    UPLOADED_LOGS_FILE = DATA_DIR / "uploaded_logs.json"
    LOG_FILE = DATA_DIR / "rlog_monitor.log"
else:
    CONFIG_FILE = SCRIPT_DIR / "config.json"
    UPLOADED_LOGS_FILE = SCRIPT_DIR / "uploaded_logs.json"
    LOG_FILE = SCRIPT_DIR / "rlog_monitor.log"

SCRIPT_FILE = SCRIPT_DIR / "rlog_downloader.py"

running_process = None
log_position = 0

DEFAULT_CONFIG = {
    "comma_ip": "192.168.173.10",
    "comma_user": "comma",
    "base_url": "https://dl.relay.net:4443",
    "upload_path": "/VW Passat NMS with torque steer/",
    "fb_username": "nnlc",
    "fb_password": "nnlc",
    "auto_start": False
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Comma 3X Rlog Auto-Uploader</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background: #1a1a1a; color: #e0e0e0; padding: 20px; line-height: 1.6; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #4CAF50; margin-bottom: 10px; font-size: 28px; }
        .subtitle { color: #888; margin-bottom: 30px; font-size: 14px; }
        .section { background: #2a2a2a; border-radius: 8px; padding: 25px; margin-bottom: 20px; border: 1px solid #3a3a3a; }
        .section h2 { color: #4CAF50; font-size: 18px; margin-bottom: 15px; border-bottom: 1px solid #3a3a3a; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #b0b0b0; font-size: 14px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; background: #1a1a1a; border: 1px solid #444; border-radius: 4px; color: #e0e0e0; font-size: 14px; }
        input[type="checkbox"] { width: 18px; height: 18px; cursor: pointer; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; }
        .readonly { background: #222 !important; color: #666 !important; }
        button { background: #4CAF50; color: white; border: none; padding: 12px 30px; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: 500; transition: background 0.3s; }
        button:hover { background: #45a049; }
        button:disabled { background: #555; cursor: not-allowed; }
        button.stop { background: #f44336; }
        button.stop:hover { background: #da190b; }
        #output { background: #0a0a0a; border: 1px solid #333; border-radius: 4px; padding: 15px; font-family: 'Courier New', monospace; font-size: 13px; min-height: 400px; max-height: 600px; overflow-y: auto; white-space: pre-wrap; word-wrap: break-word; color: #00ff00; display: none; margin-top: 20px; }
        #output.active { display: block; }
        .status { padding: 10px 15px; border-radius: 4px; margin-top: 15px; display: none; }
        .status.running { background: #1a4d2e; color: #4CAF50; display: block; }
        .status.error { background: #4d1a1a; color: #f44336; display: block; }
        .status.success { background: #1a4d2e; color: #4CAF50; display: block; }
        .buttons { display: flex; gap: 10px; flex-wrap: wrap; }
        .note { background: #2a2a1a; border-left: 3px solid #FFC107; padding: 10px 15px; margin-top: 15px; font-size: 13px; color: #d0d0d0; }
        .stats { background: #1a2a2a; border-left: 3px solid #2196F3; padding: 10px 15px; margin-top: 15px; font-size: 13px; color: #d0d0d0; }
        #clearBtn { background: #ff9800; }
        #clearBtn:hover { background: #e68900; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 Comma 3X Rlog Auto-Uploader</h1>
        <p class="subtitle">Automatically monitors for Comma 3X and uploads new logs</p>

        <div class="section">
            <h2>Comma 3X Configuration</h2>
            <div class="form-group">
                <label>Comma 3X IP Address</label>
                <input type="text" id="comma_ip" value="{{ config.comma_ip }}">
            </div>
            <div class="form-group">
                <label>SSH Username (leave as "comma")</label>
                <input type="text" id="comma_user" value="{{ config.comma_user }}" class="readonly" readonly>
            </div>
            <div class="note">💡 Make sure your SSH key is already added to the Comma 3X</div>
        </div>

        <div class="section">
            <h2>FileBrowser Server Configuration</h2>
            <div class="form-group">
                <label>Server URL</label>
                <input type="text" id="base_url" value="{{ config.base_url }}">
            </div>
            <div class="form-group">
                <label>Upload Path</label>
                <input type="text" id="upload_path" value="{{ config.upload_path }}">
            </div>
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="fb_username" value="{{ config.fb_username }}">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="fb_password" value="{{ config.fb_password }}">
            </div>
            <div class="form-group">
                <div class="checkbox-group">
                    <input type="checkbox" id="auto_start" {% if config.auto_start %}checked{% endif %}>
                    <label for="auto_start" style="margin: 0;">Auto-start monitoring when page loads</label>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="stats">
                📊 <strong>Uploaded Routes:</strong> <span id="uploaded_count">{{ uploaded_count }}</span>
            </div>

            <div class="buttons" style="margin-top: 15px;">
                <button onclick="window.updateScript()">💾 Update Script & Save</button>
                <button onclick="window.startMonitoring()" id="startBtn">🚀 Start Monitoring</button>
                <button onclick="window.startMonitoring()" id="viewLogsBtn" style="display: none;">👁️ View Live Logs</button>
                <button onclick="window.stopMonitoring()" id="stopBtn" class="stop" style="display: none;">🛑 Stop Monitoring</button>
                <button onclick="window.clearHistory()" id="clearBtn">🗑️ Clear Upload History</button>
            </div>

            <div id="status" class="status"></div>
            <div id="output"></div>
        </div>
    </div>

    <script type="text/javascript">
        var eventSource = null;
        var AUTO_START = {{ auto_start_js|safe }};

        window.updateScript = function() {
            var config = {
                comma_ip: document.getElementById('comma_ip').value,
                comma_user: document.getElementById('comma_user').value,
                base_url: document.getElementById('base_url').value,
                upload_path: document.getElementById('upload_path').value,
                fb_username: document.getElementById('fb_username').value,
                fb_password: document.getElementById('fb_password').value,
                auto_start: document.getElementById('auto_start').checked
            };

            fetch('/update_script', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    showStatus('Script updated and configuration saved!', 'success');
                    setTimeout(function() { hideStatus(); }, 2000);
                } else {
                    showStatus('Error: ' + (data.error || 'Unknown error'), 'error');
                }
            })
            .catch(function(err) {
                showStatus('Error: ' + err, 'error');
            });
        };

        window.startMonitoring = function() {
            var startBtn = document.getElementById('startBtn');
            var viewLogsBtn = document.getElementById('viewLogsBtn');
            var stopBtn = document.getElementById('stopBtn');
            var output = document.getElementById('output');

            startBtn.style.display = 'none';
            viewLogsBtn.style.display = 'none';
            stopBtn.style.display = 'block';
            output.innerHTML = 'Connecting to monitor...\\n';
            output.classList.add('active');
            showStatus('Monitoring...', 'running');

            eventSource = new EventSource('/run');

            eventSource.onmessage = function(event) {
                if (event.data === '[DONE]' || event.data === '[ERROR]') {
                    eventSource.close();
                    eventSource = null;
                    // Check status to determine which button to show
                    checkStatus();
                    showStatus(event.data === '[DONE]' ? 'Stopped' : 'Error occurred', event.data === '[DONE]' ? 'success' : 'error');
                    updateUploadCount();
                } else {
                    output.innerHTML += event.data + '\\n';
                    output.scrollTop = output.scrollHeight;
                }
            };

            eventSource.onerror = function() {
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
                // Check status to determine which button to show
                checkStatus();
                showStatus('Connection closed', 'success');
            };
        };

        window.stopMonitoring = function() {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }

            fetch('/stop', { method: 'POST' })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    // Reset UI to start state
                    document.getElementById('startBtn').style.display = 'block';
                    document.getElementById('viewLogsBtn').style.display = 'none';
                    document.getElementById('stopBtn').style.display = 'none';
                    showStatus('Monitoring stopped', 'success');
                    updateUploadCount();
                    setTimeout(function() { hideStatus(); }, 3000);
                });
        };

        window.clearHistory = function() {
            if (confirm('Clear upload history? This will cause all logs to be re-uploaded next time.')) {
                fetch('/clear_history', { method: 'POST' })
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        showStatus('Upload history cleared', 'success');
                        updateUploadCount();
                    });
            }
        };

        function updateUploadCount() {
            fetch('/upload_count')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    document.getElementById('uploaded_count').textContent = data.count;
                });
        }

        function showStatus(message, type) {
            var status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
        }

        function hideStatus() {
            var status = document.getElementById('status');
            status.className = 'status';
        }

        function checkStatus() {
            fetch('/status')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.running) {
                        // Process is already running - show view logs button
                        document.getElementById('startBtn').style.display = 'none';
                        document.getElementById('viewLogsBtn').style.display = 'block';
                        document.getElementById('stopBtn').style.display = 'block';
                        showStatus('Monitoring is active (click "View Live Logs" to reconnect)', 'running');
                    } else {
                        // Process not running - show start button
                        document.getElementById('startBtn').style.display = 'block';
                        document.getElementById('viewLogsBtn').style.display = 'none';
                        document.getElementById('stopBtn').style.display = 'none';
                    }
                });
        }

        window.addEventListener('load', function() {
            // Check if process is already running
            checkStatus();

            // Auto-start if enabled and not already running
            if (AUTO_START) {
                setTimeout(function() {
                    fetch('/status')
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            if (!data.running) {
                                window.startMonitoring();
                            }
                        });
                }, 1000);
            }
        });

        updateUploadCount();
    </script>
</body>
</html>"""


def load_config():
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
                for key in DEFAULT_CONFIG.keys():
                    if key in saved_config:
                        config[key] = saved_config[key]
        except Exception as e:
            print(f"Warning: Failed to load config: {e}")
    return config

@app.route('/')
def index():
    config = load_config()
    uploaded_count = get_uploaded_count()
    auto_start_js = 'true' if config.get('auto_start', False) else 'false'
    return render_template_string(
        HTML_TEMPLATE,
        config=config,
        uploaded_count=uploaded_count,
        auto_start_js=auto_start_js
    )

def save_config_to_file(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def update_script_file(config):
    if not SCRIPT_FILE.exists():
        return False, "Script file not found"

    try:
        with open(SCRIPT_FILE, 'r') as f:
            script_content = f.read()

        script_content = re.sub(
            r'COMMA_IP = "[^"]*"',
            f'COMMA_IP = "{config["comma_ip"]}"',
            script_content
        )
        script_content = re.sub(
            r'BASE_URL = "[^"]*"',
            f'BASE_URL = "{config["base_url"]}"',
            script_content
        )
        script_content = re.sub(
            r'UPLOAD_PATH = "[^"]*"',
            f'UPLOAD_PATH = "{config["upload_path"]}"',
            script_content
        )
        script_content = re.sub(
            r'USERNAME = "[^"]*"',
            f'USERNAME = "{config["fb_username"]}"',
            script_content
        )
        script_content = re.sub(
            r'PASSWORD = "[^"]*"',
            f'PASSWORD = "{config["fb_password"]}"',
            script_content
        )

        with open(SCRIPT_FILE, 'w') as f:
            f.write(script_content)

        return True, "Script updated successfully"
    except Exception as e:
        return False, str(e)


def get_uploaded_count():
    if UPLOADED_LOGS_FILE.exists():
        try:
            with open(UPLOADED_LOGS_FILE, 'r') as f:
                data = json.load(f)
                return len(data) if isinstance(data, list) else 0
        except Exception as e:
            print(f"Warning: Failed to read upload count: {e}")
            return 0
    return 0

@app.route('/update_script', methods=['POST'])
def update_script_route():
    config = request.json

    success, message = update_script_file(config)

    if success:
        save_config_to_file(config)
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "error": message})


@app.route('/upload_count')
def upload_count():
    return jsonify({"count": get_uploaded_count()})


@app.route('/status')
def status():
    global running_process
    is_running = running_process is not None and running_process.poll() is None
    return jsonify({
        "running": is_running,
        "log_exists": LOG_FILE.exists()
    })


@app.route('/clear_history', methods=['POST'])
def clear_history():
    if UPLOADED_LOGS_FILE.exists():
        UPLOADED_LOGS_FILE.unlink()
    return jsonify({"success": True})


@app.route('/stop', methods=['POST'])
def stop_route():
    global running_process
    if running_process and running_process.poll() is None:
        try:
            running_process.terminate()
            running_process.wait(timeout=5)
        except:
            pass
        running_process = None
    return jsonify({"success": True})


@app.route('/run')
def run_script():
    global running_process

    def generate():
        global running_process

        try:
            if not SCRIPT_FILE.exists():
                yield f"data: ERROR: {SCRIPT_FILE} not found\n\n"
                yield "data: [ERROR]\n\n"
                return

            already_running = running_process is not None and running_process.poll() is None

            if already_running:
                yield "data: ✓ Monitoring is already running (reconnecting to logs...)\n\n"
                if LOG_FILE.exists():
                    with open(LOG_FILE, 'r') as f:
                        lines = f.readlines()
                        for line in lines[-50:]:
                            yield f"data: {line.rstrip()}\n\n"
                        f.seek(0, 2)
                        while running_process and running_process.poll() is None:
                            line = f.readline()
                            if line:
                                yield f"data: {line.rstrip()}\n\n"
                            else:
                                time.sleep(0.1)
                yield "data: [DONE]\n\n"
                return

            yield "data: Starting rlog auto-uploader...\n\n"

            log_file = open(LOG_FILE, 'w')

            running_process = subprocess.Popen(
                [sys.executable, str(SCRIPT_FILE)],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            with open(LOG_FILE, 'r') as f:
                while running_process and running_process.poll() is None:
                    line = f.readline()
                    if line:
                        yield f"data: {line.rstrip()}\n\n"
                    else:
                        time.sleep(0.1)

                for line in f.readlines():
                    yield f"data: {line.rstrip()}\n\n"

            log_file.close()
            running_process.wait()
            running_process = None

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: ERROR: {str(e)}\n\n"
            yield "data: [ERROR]\n\n"
            running_process = None

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    port = int(os.getenv('PORT', '3111'))

    print("=" * 60)
    print("Comma 3X Rlog Auto-Uploader - Web Interface")
    print("=" * 60)
    print(f"\n✓ Working directory: {Path.cwd()}")
    print(f"✓ Script file: {SCRIPT_FILE.absolute()}")
    print(f"\n🌐 Open: http://localhost:{port}\n")
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)