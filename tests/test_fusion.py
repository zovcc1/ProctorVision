import pytest
import time
from hypothesis import given, strategies as st
from backend.pipeline.fusion_engine import FusionEngine

def test_attentive_by_default(fusion_engine, mock_vision_results):
    result = fusion_engine.process(mock_vision_results)
    assert result['attention_state'] == 'Attentive'
    assert result['flags']['mouth_covered'] is False

def test_mouth_covered_logic(fusion_engine, mock_vision_results):
    # Setup: hand near face and mouth ratio low
    # Face center is (200, 200), width is 200. Proximity factor is 1.5. 
    # Threshold = 1.5 * 200 = 300.
    
    mock_vision_results['hand_bboxes'] = [[210, 210, 250, 250]] # Near center
    mock_vision_results['mouth_ratio'] = 0.1 # Below default 0.2
    
    result = fusion_engine.process(mock_vision_results)
    assert result['hand_near_face'] is True
    assert result['flags']['mouth_covered'] is True

def test_alert_tolerance(fusion_engine, mock_vision_results):
    # Alert tolerance is 500ms by default
    mock_vision_results['phone_detected'] = True
    
    # First frame: should be distracted but no alert yet
    res1 = fusion_engine.process(mock_vision_results)
    assert res1['attention_state'] == 'Distracted'
    assert len(res1['alerts']) == 0
    
    # Wait 0.6s and process again
    time.sleep(0.6)
    res2 = fusion_engine.process(mock_vision_results)
    
    # Check if 'start' alert is generated
    alert_types = [a['type'] for a in res2['alerts']]
    assert 'start' in alert_types

@given(
    mouth_ratio=st.floats(min_value=0.0, max_value=1.0),
    hand_dist=st.floats(min_value=0.0, max_value=1000.0)
)
def test_mouth_covered_property(mouth_ratio, hand_dist):
    engine = FusionEngine()
    # Face at (100, 100) to (300, 300) -> center (200, 200), width 200
    # Proximity threshold = 1.5 * 200 = 300
    
    # Calculate hand bbox based on distance from (200, 200)
    # Simple case: move along X axis
    hx = 200 + hand_dist
    hy = 200
    
    vision = {
        'face_bboxes': [[100, 100, 300, 300]],
        'hand_bboxes': [[hx-10, hy-10, hx+10, hy+10]],
        'mouth_ratio': mouth_ratio,
        'gaze_direction': 'Inside'
    }
    
    result = engine.process(vision)
    
    # Logic: mouth_covered if mouth_ratio < 0.2 AND hand_dist < 300
    expected = (mouth_ratio < 0.2) and (hand_dist < 300)
    assert result['flags']['mouth_covered'] == expected
