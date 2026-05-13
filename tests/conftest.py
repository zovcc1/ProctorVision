import pytest
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

@pytest.fixture
def fusion_engine():
    from backend.pipeline.fusion_engine import FusionEngine
    return FusionEngine()

@pytest.fixture
def mock_vision_results():
    return {
        'face_bboxes': [[100, 100, 300, 300]], # Face in center
        'hand_bboxes': [],
        'persons_count': 1,
        'phone_detected': False,
        'gaze_direction': 'Inside',
        'mouth_ratio': 0.5,
        'head_pose': {'yaw': 0, 'pitch': 0, 'roll': 0}
    }
