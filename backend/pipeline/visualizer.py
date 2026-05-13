import cv2

class Visualizer:
    def __init__(self, config):
        self.config = config
        self.color_map = {
            'Attentive':  (0, 255, 0),
            'Distracted': (0, 165, 255),
            'Warning':    (0, 0, 255),
        }

    def draw_overlays(self, frame, vision, attention_state):
        """Draws AI vision detections and attention status on the frame."""
        color = self.color_map.get(attention_state, (200, 200, 200))
        h, w = frame.shape[:2]

        # Face bounding box (magenta)
        for (x1, y1, x2, y2) in vision.get('face_bboxes', []):
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 255), 2)
            cv2.putText(
                frame, 'Face', (int(x1), int(y1) - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1,
            )

        # Person bounding boxes (cyan)
        for (x1, y1, x2, y2) in vision.get('person_bboxes', []):
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)
            cv2.putText(
                frame, 'Person', (int(x1), int(y1) - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1,
            )

        # Hand bounding boxes (yellow)
        for (x1, y1, x2, y2) in vision.get('hand_bboxes', []):
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 0), 2)
            cv2.putText(
                frame, 'Hand', (int(x1), int(y1) - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1,
            )

        # Gaze indicator
        gaze = vision.get('gaze_direction', 'Inside')
        if gaze == 'Outside':
            # Arrow pointing away from center
            cx, cy = w // 2, h // 2
            cv2.arrowedLine(frame, (cx, cy), (cx + 60, cy - 30), (0, 0, 255), 3)
            cv2.putText(
                frame, 'LOOKING AWAY', (cx + 10, cy - 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2,
            )

        # Status banner at top
        banner_h = 40
        cv2.rectangle(frame, (0, 0), (w, banner_h), color, -1)
        cv2.putText(
            frame,
            f"State: {attention_state} | Gaze: {gaze}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
        )

        return frame
