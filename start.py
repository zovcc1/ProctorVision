#!/usr/bin/env python3
"""
ProctorVision Desktop Edition - Startup Script
Run: python start.py
"""
import os
import sys
import webbrowser
import time
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import app, socketio

def open_browser():
    time.sleep(1.5)
    url = "http://127.0.0.1:5000"
    print(f"Opening browser at {url}")
    webbrowser.open(url)

if __name__ == '__main__':
    print("=" * 50)
    print("ProctorVision Desktop Edition")
    print("Student Attention Monitoring System")
    print("=" * 50)
    print("Starting server at http://127.0.0.1:5000")
    print("Press CTRL+C to stop")
    print("=" * 50)

    threading.Thread(target=open_browser, daemon=True).start()
    socketio.run(app, host='127.0.0.1', port=5000, debug=False, allow_unsafe_werkzeug=True)
