import os
import sys
import time
import json
import base64
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_socketio import SocketIO, emit, join_room, leave_room

# Ensure backend is on path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))

from backend.config.config_manager import config
from backend.session.session_manager import SessionManager
from backend.reports.report_generator import ReportGenerator
from backend.pipeline.visualizer import Visualizer

# Frontend distribution folder (relative to backend/app.py)
UI_DIST = BASE_DIR.parent / 'ui' / 'dist'

app = Flask(__name__, static_folder=str(UI_DIST), static_url_path='')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

session_manager = SessionManager()
report_generator = ReportGenerator()
visualizer = Visualizer(config)
_stream_thread = None
_stream_running = False


def _broadcast_frame(frame_b64, session_id):
    socketio.emit('frame', {'image': frame_b64, 'session_id': session_id}, room=session_id)


def _broadcast_stats(stats, session_id):
    socketio.emit('stats', stats, room=session_id)


def _broadcast_alert(alert, session_id):
    socketio.emit('alert', {**alert, 'session_id': session_id}, room=session_id)


def _stream_loop():
    global _stream_running
    import cv2
    while _stream_running and session_manager.is_running():
        frame = session_manager.read_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        result = session_manager.process_frame(frame)
        vision = result['vision']
        fusion = result['fusion']

        jpeg_quality = config.get('output.jpeg_quality', 60)
        annotated = visualizer.draw_overlays(frame, vision, fusion.get('attention_state', 'Attentive'))
        _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
        b64 = base64.b64encode(buf).decode('utf-8')

        session = session_manager.get_session()
        if session:
            _broadcast_frame(b64, session.id)
            if fusion.get('record'):
                stats = session_manager.get_stats()
                stats['session_id'] = session.id
                stats['current_state'] = fusion.get('attention_state', 'Attentive')
                _broadcast_stats(stats, session.id)

        target_fps = config.get('target_fps', 20)
        time.sleep(1.0 / target_fps)


# REST API
@app.route('/api/v1/status', methods=['GET'])
def api_status():
    cam_ok = False
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        cam_ok = cap.isOpened()
        cap.release()
    except Exception:
        pass
    return jsonify({'status': 'ready', 'camera_available': cam_ok})


@app.route('/api/v1/session/start', methods=['POST'])
def session_start():
    if session_manager.is_running():
        return jsonify({'error': 'Session already active'}), 409
    session = session_manager.start_session()
    if session is None:
        return jsonify({'error': 'Camera unavailable'}), 503

    def on_alert(alert):
        socketio.emit('alert', {**alert, 'session_id': session.id}, room=session.id)

    session_manager.add_alert_listener(on_alert)

    global _stream_thread, _stream_running
    _stream_running = True
    _stream_thread = threading.Thread(target=_stream_loop, daemon=True)
    _stream_thread.start()

    return jsonify({
        'session_id': session.id,
        'start_time': session.start_time,
        'websocket_room': session.id,
    })


@app.route('/api/v1/session/stop', methods=['POST'])
def session_stop():
    if not session_manager.is_running():
        return jsonify({'error': 'No active session'}), 404

    global _stream_running
    _stream_running = False
    if _stream_thread:
        _stream_thread.join(timeout=3.0)

    session = session_manager.stop_session()
    csv_path = report_generator.generate_csv(session)
    pdf_path = report_generator.generate_pdf(session)

    return jsonify({
        'session_id': session.id,
        'duration_seconds': session.duration(),
        'records_count': len(session.records),
        'csv_file': os.path.basename(csv_path),
        'pdf_file': os.path.basename(pdf_path),
    })


@app.route('/api/v1/session', methods=['GET'])
def session_get():
    session = session_manager.get_session()
    if not session:
        return jsonify({'active': False}), 200
    return jsonify(session.to_dict())


@app.route('/api/v1/settings', methods=['GET'])
def settings_get():
    return jsonify(config.get())


@app.route('/api/v1/settings', methods=['PUT'])
def settings_put():
    data = request.get_json(force=True, silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON body'}), 400
    config.update(data)
    return jsonify(config.get())


@app.route('/api/v1/reports', methods=['GET'])
def list_reports():
    reports_dir = report_generator._reports_dir
    files = sorted(
        [f.name for f in reports_dir.iterdir() if f.is_file()],
        reverse=True,
    )
    return jsonify({'reports': files})


@app.route('/api/v1/reports/<filename>', methods=['GET'])
def download_report(filename):
    reports_dir = report_generator._reports_dir
    safe_name = Path(filename).name
    file_path = reports_dir / safe_name
    if not file_path.exists():
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory(str(reports_dir), safe_name, as_attachment=True)


# WebSocket Events
@socketio.on('connect')
def ws_connect():
    emit('connected', {'message': 'ProctorVision WebSocket ready'})


@socketio.on('join')
def ws_join(data):
    room = data.get('session_id', '')
    if room:
        join_room(room)
        emit('joined', {'session_id': room})


@socketio.on('disconnect')
def ws_disconnect():
    pass


# Serve frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    static_file = Path(app.static_folder) / path
    if static_file.exists() and static_file.is_file():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
