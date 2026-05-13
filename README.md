# ProctorVision Desktop Edition

ProctorVision is a comprehensive, local-first student attention monitoring system. It uses advanced computer vision to track gaze, detect objects (phones, additional persons), and monitor behavior during exams, all while ensuring 100% data privacy by processing everything on the local machine.

## Key Features

- **100% Local Processing**: No video or personal data ever leaves the device.
- **Advanced Computer Vision**:
  - **Gaze & Head Pose**: High-accuracy tracking using MediaPipe Face Mesh and Perspective-n-Point (PnP) algorithms.
  - **Object Detection**: Real-time detection of mobile phones and additional persons via YOLOv8 (ONNX).
  - **Behavioral Analysis**: Detects whispering (mouth covered) and attention states (Attentive, Distracted, Warning).
- **Real-time Monitoring**: Low-latency video stream with AI-powered overlays.
- **Detailed Reporting**: Generates comprehensive PDF and CSV reports at the end of each session, including an attention timeline chart.
- **Configurable Thresholds**: Fine-tune detection sensitivity (e.g., yaw/pitch limits, alert tolerance) directly through the UI.

## System Architecture

The project follows a modular architecture:

- **Frontend**: A modern React-based dashboard (Vite + Tailwind CSS).
- **Backend**: A multithreaded Flask + SocketIO server for real-time processing.
- **Pipeline**: Dedicated modules for camera I/O, vision inference, and behavioral fusion.

## Project Structure

```
.
├── backend/
│   ├── app.py                 # Flask + SocketIO Entry Point
│   ├── assets/
│   │   └── models/            # AI Models (MediaPipe, YOLO)
│   ├── config/
│   │   ├── config.json        # System Configuration & Thresholds
│   │   └── config_manager.py  # Runtime Settings Loader
│   ├── pipeline/
│   │   ├── camera.py          # Multithreaded Camera I/O
│   │   ├── vision_pipeline.py # AI Inference (MediaPipe + YOLO)
│   │   ├── fusion_engine.py   # Behavioral Logic & Alert Management
│   │   └── visualizer.py      # Real-time Frame Annotation
│   ├── session/
│   │   └── session_manager.py # Session Lifecycle & State Persistence
│   └── reports/
│       └── report_generator.py # PDF/CSV Report Construction
├── ui/                        # React Frontend Source
├── storage/                   # Default location for generated reports
├── start.py                   # Main Application Launcher
└── README.md
```

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 20+** (only for building the UI from source)
- A working webcam.

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd proctorvision
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

### Running the Application

Launch the system using the provided launcher:

```bash
python start.py
```

The application will automatically open your default browser at `http://127.0.0.1:5000`.

## Configuration

You can customize the system behavior in `backend/config/config.json`. Key settings include:

- **Camera**: Resolution and device index.
- **Thresholds**:
  - `yaw_threshold` & `pitch_threshold`: Limits for looking away.
  - `alert_tolerance_ms`: Time an event must persist before triggering an alert.
  - `warning_duration_s`: Time in "Distracted" state before escalating to "Warning".
- **Models**: Paths to the MediaPipe and YOLO ONNX models.

## AI Models

The system requires the following models (pre-configured in `backend/config/config.json`):
- **MediaPipe Face Landmarker**: `face_landmarker_v2_with_blendshapes.task`
- **YOLOv8 Nano (ONNX)**: `yolov8n.onnx`

## License

GPL-3.0
