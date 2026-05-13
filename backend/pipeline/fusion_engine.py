import time
from typing import Dict, Any, List, Optional
from backend.config.config_manager import config


class FusionEngine:
    def __init__(self):
        self._events: Dict[str, Dict[str, Any]] = {}
        self._records: List[Dict[str, Any]] = []
        self._frame_count = 0
        self._last_record_time = 0.0
        self._alert_listeners = []
        self._suspicious_start: Optional[float] = None

    def reset(self):
        self._events.clear()
        self._records.clear()
        self._frame_count = 0
        self._last_record_time = 0.0
        self._suspicious_start = None

    def process(self, vision_results: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        self._frame_count += 1

        face_bboxes = vision_results.get('face_bboxes', [])
        hand_bboxes = vision_results.get('hand_bboxes', [])
        face_detected = len(face_bboxes) > 0

        # Hand proximity to face
        hand_near_face = False
        if face_bboxes and hand_bboxes:
            fx1, fy1, fx2, fy2 = face_bboxes[0]
            face_cx = (fx1 + fx2) / 2
            face_cy = (fy1 + fy2) / 2
            face_w = fx2 - fx1
            proximity_threshold = (
                config.get('thresholds.hand_face_proximity_factor', 1.5) * face_w
            )
            for hx1, hy1, hx2, hy2 in hand_bboxes:
                hcx = (hx1 + hx2) / 2
                hcy = (hy1 + hy2) / 2
                dist = ((hcx - face_cx) ** 2 + (hcy - face_cy) ** 2) ** 0.5
                if dist < proximity_threshold:
                    hand_near_face = True
                    break

        # Mouth covered
        mouth_ratio = vision_results.get('mouth_ratio', 0.0)
        mouth_thresh = config.get('thresholds.mouth_open_ratio', 0.2)
        mouth_covered = mouth_ratio < mouth_thresh and hand_near_face

        # Behavioral flags — no face in frame counts as gaze outside
        effective_gaze_outside = (not face_detected) or vision_results.get('gaze_direction') == 'Outside'
        flags = {
            'gaze_outside':   effective_gaze_outside,
            'phone_detected': vision_results.get('phone_detected', False),
            'extra_person':   vision_results.get('persons_count', 0) > 1,
            'mouth_covered':  mouth_covered,
        }

        # Event tracker with confirmation tolerance
        tolerance = config.get('thresholds.alert_tolerance_ms', 500) / 1000.0
        alerts = []
        for event_name, active in flags.items():
            state = self._events.get(
                event_name,
                {'active': False, 'start': 0.0, 'confirmed': False},
            )

            if active and not state['active']:
                state['active'] = True
                state['start'] = now
                state['confirmed'] = False

            elif not active and state['active']:
                elapsed = now - state['start']
                if state['confirmed']:
                    alerts.append({
                        'type': 'end',
                        'event': event_name,
                        'duration': round(elapsed, 2),
                    })
                state['active'] = False
                state['confirmed'] = False

            elif active and state['active']:
                elapsed = now - state['start']
                if not state['confirmed'] and elapsed >= tolerance:
                    state['confirmed'] = True
                    alerts.append({'type': 'start', 'event': event_name})

            self._events[event_name] = state

        # Notify listeners
        for alert in alerts:
            for listener in self._alert_listeners:
                try:
                    listener(alert)
                except Exception as e:
                    print(f"Alert listener error: {e}")

        # Attention state
        any_suspicious = any(flags.values())
        warning_duration = config.get('thresholds.warning_duration_s', 3.0)

        if any_suspicious:
            if self._suspicious_start is None:
                self._suspicious_start = now
            suspicious_duration = now - self._suspicious_start
        else:
            self._suspicious_start = None
            suspicious_duration = 0.0

        if not any_suspicious:
            attention_state = 'Attentive'
        elif suspicious_duration >= warning_duration:
            attention_state = 'Warning'
        else:
            attention_state = 'Distracted'

        # Aggregate record once per second
        record = None
        if now - self._last_record_time >= 1.0:
            record = {
                'timestamp':       now,
                'frame_count':     self._frame_count,
                'attention_state': attention_state,
                'face_detected':   face_detected,
                'gaze_direction':  'Outside' if not face_detected else vision_results.get('gaze_direction', 'Inside'),
                'yaw':             vision_results.get('head_pose', {}).get('yaw', 0.0),
                'pitch':           vision_results.get('head_pose', {}).get('pitch', 0.0),
                'roll':            vision_results.get('head_pose', {}).get('roll', 0.0),
                'mouth_ratio':     mouth_ratio,
                'persons_count':   vision_results.get('persons_count', 0),
                'phone_detected':  vision_results.get('phone_detected', False),
                'hand_near_face':  hand_near_face,
                'mouth_covered':   mouth_covered,
            }
            self._records.append(record)
            self._last_record_time = now

        return {
            'record':          record,
            'alerts':          alerts,
            'flags':           flags,
            'hand_near_face':  hand_near_face,
            'attention_state': attention_state,
        }

    def get_records(self) -> List[Dict[str, Any]]:
        return list(self._records)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._records)
        if total == 0:
            return {
                'total_records':        0,
                'attentive_pct':        0.0,
                'distracted_pct':       0.0,
                'warning_pct':          0.0,
                'phone_events':         0,
                'gaze_outside_events':  0,
                'extra_person_events':  0,
                'mouth_covered_events': 0,
                'duration_seconds':     0,
            }

        counts = {'Attentive': 0, 'Distracted': 0, 'Warning': 0}
        phone_events = 0
        gaze_events = 0
        extra_events = 0
        mouth_events = 0

        for r in self._records:
            st = r.get('attention_state', 'Attentive')
            counts[st] = counts.get(st, 0) + 1
            if r.get('phone_detected'):
                phone_events += 1
            if r.get('gaze_direction') == 'Outside':
                gaze_events += 1
            if r.get('persons_count', 0) > 1:
                extra_events += 1
            if r.get('mouth_covered'):
                mouth_events += 1

        return {
            'total_records':        total,
            'attentive_pct':        round(counts['Attentive']  / total * 100, 1),
            'distracted_pct':       round(counts['Distracted'] / total * 100, 1),
            'warning_pct':          round(counts['Warning']    / total * 100, 1),
            'phone_events':         phone_events,
            'gaze_outside_events':  gaze_events,
            'extra_person_events':  extra_events,
            'mouth_covered_events': mouth_events,
            'duration_seconds':     total,
        }

    def add_alert_listener(self, callback):
        self._alert_listeners.append(callback)

    def remove_alert_listener(self, callback):
        if callback in self._alert_listeners:
            self._alert_listeners.remove(callback)