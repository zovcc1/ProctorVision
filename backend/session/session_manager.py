import uuid
import time
from typing import Optional, Dict, Any, List
from backend.pipeline.camera import CameraStream
from backend.pipeline.vision_pipeline import VisionPipeline
from backend.pipeline.fusion_engine import FusionEngine


class Session:
    def __init__(self, session_id: str):
        self.id = session_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.records: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.external_events: List[Dict[str, Any]] = []
        self.captured_frames: List[Dict[str, Any]] = []  # {event, timestamp, path}
        self.active = True
        self.termination_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_seconds': self.duration(),
            'records_count': len(self.records),
            'events_count': len(self.events) + len(self.external_events),
            'active': self.active,
            'termination_reason': self.termination_reason,
        }

    def duration(self) -> float:
        end = self.end_time or time.time()
        return round(end - self.start_time, 1)


class SessionManager:
    def __init__(self):
        self._session: Optional[Session] = None
        self._camera = CameraStream()
        self._vision = VisionPipeline()
        self._fusion = FusionEngine()
        self._running = False
        self._focus_lost_at: Optional[float] = None

    def start_session(self) -> Optional[Session]:
        if self._session and self._session.active:
            return None
        if not self._camera.start():
            return None
        self._session = Session(str(uuid.uuid4()))
        self._fusion.reset()
        self._vision.initialize()
        self._running = True
        return self._session

    def stop_session(self, reason: str = None) -> Optional[Session]:
        if not self._session or not self._session.active:
            return None
        self._running = False
        self._camera.stop()
        self._session.active = False
        self._session.end_time = time.time()
        self._session.termination_reason = reason
        self._session.records = self._fusion.get_records()
        self._session.events = self._extract_events_from_records()
        self._focus_lost_at = None
        return self._session

    def get_session(self) -> Optional[Session]:
        return self._session

    def is_running(self) -> bool:
        return self._running and self._session is not None and self._session.active

    def read_frame(self):
        return self._camera.read_frame()

    def process_frame(self, frame) -> Dict[str, Any]:
        vision_results = self._vision.process_frame(frame)
        fusion_result = self._fusion.process(vision_results)
        if fusion_result.get('record'):
            self._session.records.append(fusion_result['record'])
        return {
            'vision': vision_results,
            'fusion': fusion_result,
        }

    def get_stats(self) -> Dict[str, Any]:
        return self._fusion.get_stats()

    def record_external_event(self, event_type: str, metadata: Dict[str, Any] = None):
        if not self._session or not self._session.active:
            return

        now = time.time()
        if event_type == 'attempted_focus_loss':
            self._focus_lost_at = now
        elif event_type == 'focus':
            self._focus_lost_at = None

        event = {
            'type': event_type,
            'timestamp': now,
            'metadata': metadata or {}
        }
        self._session.external_events.append(event)

    def add_alert_listener(self, callback):
        self._fusion.add_alert_listener(callback)

    def remove_alert_listener(self, callback):
        self._fusion.remove_alert_listener(callback)

    def _extract_events_from_records(self) -> List[Dict[str, Any]]:
        events = []
        event_types = ['phone_detected', 'gaze_outside', 'extra_person', 'mouth_covered']
        for et in event_types:
            active = False
            start = 0
            for idx, rec in enumerate(self._session.records):
                ts = rec.get('timestamp', self._session.start_time + idx)
                is_active = False
                if et == 'phone_detected':
                    is_active = rec.get('phone_detected', False)
                elif et == 'gaze_outside':
                    is_active = rec.get('gaze_direction') == 'Outside'
                elif et == 'extra_person':
                    is_active = rec.get('persons_count', 0) > 1
                elif et == 'mouth_covered':
                    is_active = rec.get('mouth_covered', False)

                if is_active and not active:
                    active = True
                    start = ts
                elif not is_active and active:
                    active = False
                    events.append({
                        'type': et,
                        'start': start,
                        'end': ts,
                        'duration': round(ts - start, 1),
                    })
            if active:
                events.append({
                    'type': et,
                    'start': start,
                    'end': self._session.end_time,
                    'duration': round(self._session.end_time - start, 1),
                })
        return events