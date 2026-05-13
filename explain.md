# ProctorVision Backend: Technical Deep Dive

This document provides an exhaustive technical breakdown of the ProctorVision backend, covering its architecture, algorithmic logic, data processing pipelines, and system orchestration.

---

## 1. System Architecture

ProctorVision follows a **Multithreaded Micro-Pipeline** architecture built on Python. It separates hardware I/O, AI inference, and state management into distinct logical layers to ensure high performance and low latency.

### 1.1 Concurrency Model
- **Primary Thread (Flask/SocketIO):** Handles HTTP requests and WebSocket connections.
- **Processing Thread (`_stream_loop`):** Orchestrates the data flow from camera to AI to UI.
- **I/O Thread (`CameraStream`):** Dedicated to pulling frames from the hardware buffer to prevent blocking the processing loop.

---

## 2. Component Detailed Breakdown

### 2.1 Hardware Interface (`backend/pipeline/camera.py`)
The `CameraStream` class manages the lifecycle of `cv2.VideoCapture`.
- **Threaded Capture:** Constantly reads the latest frame into a shared memory buffer.
- **Locking Mechanism:** Uses `threading.Lock()` to ensure that the processing thread always reads a complete, non-corrupted frame.
- **Auto-Config:** Automatically applies resolution and buffer size settings from `config.json`.

### 2.2 Vision Pipeline (`backend/pipeline/vision_pipeline.py`)
The most complex part of the system, combining two distinct AI frameworks.

#### A. Head Pose Estimation (MediaPipe + solvePnP)
The system uses the **Perspective-n-Point (PnP)** algorithm to estimate the user's head orientation in 3D space.
- **Input:** 6 specific 2D landmarks (Nose, Chin, Eyes, Mouth Corners).
- **World Model:** A generic 3D face model (`MODEL_POINTS`).
- **Algorithm:** `cv2.solvePnP` calculates the rotation vector (`rot_vec`) and translation vector (`trans_vec`) relative to the camera.
- **Output:** Decomposed Euler angles (**Yaw, Pitch, Roll**).
    - *Yaw:* Horizontal rotation (Looking left/right).
    - *Pitch:* Vertical rotation (Looking up/down).
    - *Roll:* Tilting the head.

#### B. Object Detection (YOLOv8 + ONNX Runtime)
- **Model:** YOLOv8 Nano (optimized for speed).
- **Inference:** Executed via `onnxruntime`, allowing for hardware acceleration (CPU/GPU) without the overhead of PyTorch.
- **Preprocessing:** Includes letterbox resizing (640x640) and normalization.
- **Post-processing:** Uses **Non-Maximum Suppression (NMS)** to filter overlapping bounding boxes for persons, phones, and hands.

### 2.3 Behavioral Fusion Engine (`backend/pipeline/fusion_engine.py`)
This engine transforms raw detections into "Semantic Events."

#### Logic for "Mouth Covered":
1. **Hand Proximity:** Calculates the Euclidean distance between the hand center and face center.
2. **Proximity Factor:** If `Distance < (FaceWidth * Factor)`, the hand is considered "near the face."
3. **Occlusion Check:** If the hand is near the face AND the `mouth_ratio` (distance between lips) drops below a threshold, it flags `mouth_covered`.

#### Event Confirmation (Tolerance):
To prevent "flickering" alerts caused by temporary AI noise:
- **Alert Tolerance:** Events must persist for a configurable duration (e.g., 500ms) before a `start` alert is broadcast.
- **Attention States:** 
    - `Attentive`: Default state.
    - `Distracted`: One or more suspicious flags active.
    - `Warning`: Suspicious flags persist beyond the `warning_duration_s` threshold.

### 2.4 Session Management (`backend/session/session_manager.py`)
- **State Persistence:** Manages the `Session` object, which acts as a transient database for the current proctoring session.
- **Aggregation:** Every 1 second, the system takes the mean/latest values of all vision metrics and saves them as a "Record."
- **Event Extraction:** When the session stops, it scans the records to identify continuous time intervals for each violation type.

### 2.5 Reporting Engine (`backend/reports/report_generator.py`)
- **PDF Construction:** Uses `ReportLab` to programmatically build a document tree.
- **Data Visualization:** Uses `Matplotlib` (Agg backend) to render an attention timeline chart showing the "Attention State" over the duration of the exam.
- **CSV Export:** Generates a UTF-8-BOM encoded CSV for compatibility with Excel.

---

## 3. Communication Protocol

### 3.1 WebSocket Events
- `frame`: Binary-to-Base64 JPEG stream. Includes `session_id`.
- `stats`: Real-time JSON update containing the current state percentages and event counts.
- `alert`: Instant notification when a violation is *confirmed* (starts) or *resolved* (ends).

### 3.2 REST Endpoints
- `GET /api/v1/status`: Checks camera health.
- `POST /api/v1/session/start`: Initializes AI models and starts the processing thread.
- `POST /api/v1/session/stop`: Stops the camera, cleans up threads, and generates report files.
- `GET /api/v1/reports`: Lists all generated PDF/CSV files.

---

## 4. Configuration Schema (`config.json`)
The entire backend behavior is driven by a nested JSON configuration:
- **`thresholds`:** Yaw/Pitch limits, mouth ratios, and NMS confidence.
- **`camera`:** Device index and target resolution.
- **`output`:** JPEG quality and report directory paths.

---

## 5. Security Architecture
1. **Local Host Binding:** The Flask server binds to `127.0.0.1` by default to prevent unauthorized network access.
2. **Path Sanitization:** `ReportGenerator` uses `Path.name` to prevent directory traversal attacks when downloading reports.
3. **Resource Cleanup:** Uses `daemon=True` threads and explicit `stop()` methods with join timeouts to ensure the application shuts down cleanly without leaving "zombie" processes using the camera.
