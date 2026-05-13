import os
import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from backend.config.config_manager import config

try:
    import mediapipe as mp
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python import BaseOptions
    MEDIAPIPE_TASKS = True
except ImportError:
    MEDIAPIPE_TASKS = False
    import mediapipe as mp

class VisionPipeline:
    def __init__(self):
        self._face_landmarker = None
        self._face_detector_legacy = None
        self._hand_detector = None
        self._yolo_session = None
        self._yolo_input_name = None
        self._frame_count = 0
        self._initialized = False
        self._smooth_yaw = 0.0
        self._smooth_pitch = 0.0
        self._smooth_roll = 0.0

    def initialize(self):
        if self._initialized:
            return
        base_dir = Path(__file__).resolve().parent.parent.parent

        if MEDIAPIPE_TASKS:
            model_path = config.get(
                'mediapipe.model_path',
                'models/face_landmarker_v2_with_blendshapes.task'
            )
            if not Path(model_path).is_absolute():
                model_path = str(base_dir / model_path)
            if os.path.exists(model_path):
                base_options = BaseOptions(model_asset_path=model_path)
                # Attempt creation with extra parameters first, then without
                try:
                    options = vision.FaceLandmarkerOptions(
                        base_options=base_options,
                        running_mode=vision.RunningMode.IMAGE,
                        num_faces=2,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5,
                        output_facial_transformation_matrixes=True
                    )
                    self._face_landmarker = vision.FaceLandmarker.create_from_options(options)
                    print("[INIT] FaceLandmarker (tasks) ready – accurate head pose")
                except TypeError:
                    # Fallback: create without min_confidence arguments
                    options = vision.FaceLandmarkerOptions(
                        base_options=base_options,
                        running_mode=vision.RunningMode.IMAGE,
                        num_faces=2,
                        output_facial_transformation_matrixes=True
                    )
                    self._face_landmarker = vision.FaceLandmarker.create_from_options(options)
                    print("[INIT] FaceLandmarker (tasks) loaded (default confidence)")
                except Exception as e:
                    print(f"[INIT] FaceLandmarker failed: {e} – falling back to legacy")
                    self._face_landmarker = None
            else:
                print(f"[INIT] FaceLandmarker model missing at {model_path}")
                self._face_landmarker = None

        if self._face_landmarker is None:
            try:
                self._face_detector_legacy = mp.solutions.face_mesh.FaceMesh(
                    static_image_mode=False,
                    max_num_faces=2,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
                print("[INIT] Legacy FaceMesh fallback (inaccurate angles)")
            except Exception as e:
                print(f"Legacy FaceMesh init failed: {e}")
                self._face_detector_legacy = None

        try:
            self._hand_detector = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            print("[INIT] MediaPipe Hands loaded")
        except Exception as e:
            print(f"Hands init error: {e}")
            self._hand_detector = None

        yolo_path = config.get('yolo.model_path', 'models/yolov8n.onnx')
        if not Path(yolo_path).is_absolute():
            yolo_path = str(base_dir / yolo_path)

        if os.path.exists(yolo_path):
            try:
                providers = ort.get_available_providers()
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                self._yolo_session = ort.InferenceSession(
                    yolo_path, sess_options, providers=providers
                )
                inp = self._yolo_session.get_inputs()[0]
                self._yolo_input_name = inp.name
                print("[INIT] YOLO ONNX loaded")
            except Exception as e:
                print(f"YOLO init error: {e}")
                self._yolo_session = None
        else:
            print(f"YOLO model not found at {yolo_path}")

        self._initialized = True

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        if not self._initialized:
            self.initialize()

        diag = (self._frame_count % 60 == 0)
        self._frame_count += 1

        results = {
            'face_landmarks': None,
            'head_pose': {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0},
            'gaze_direction': 'Inside',
            'mouth_ratio': 0.0,
            'mouth_covered': False,
            'persons_count': 0,
            'phone_detected': False,
            'face_bboxes': [],
            'hand_bboxes': [],
            'person_bboxes': [],
        }

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        face_detected = False

        if self._face_landmarker is not None:
            try:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                lm_result = self._face_landmarker.detect(mp_image)
                if lm_result.face_landmarks and len(lm_result.face_landmarks) > 0:
                    face_detected = True
                    landmarks_raw = lm_result.face_landmarks[0]
                    xs = [int(lm.x * w) for lm in landmarks_raw]
                    ys = [int(lm.y * h) for lm in landmarks_raw]
                    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                    results['face_bboxes'] = [(x1, y1, x2, y2)]

                    if (lm_result.facial_transformation_matrixes and
                            len(lm_result.facial_transformation_matrixes) > 0):
                        matrix = np.array(
                            lm_result.facial_transformation_matrixes[0],
                            dtype=np.float32
                        ).reshape(4, 4)
                        rot_mat = matrix[:3, :3]
                        euler = self._matrix_to_euler(rot_mat)
                        raw_yaw, raw_pitch, raw_roll = float(euler[1]), float(euler[0]), float(euler[2])
                        alpha = config.get('thresholds.smoothing_alpha', 0.3)
                        self._smooth_yaw = alpha * raw_yaw + (1 - alpha) * self._smooth_yaw
                        self._smooth_pitch = alpha * raw_pitch + (1 - alpha) * self._smooth_pitch
                        self._smooth_roll = alpha * raw_roll + (1 - alpha) * self._smooth_roll
                        results['head_pose']['yaw'] = self._smooth_yaw
                        results['head_pose']['pitch'] = self._smooth_pitch
                        results['head_pose']['roll'] = self._smooth_roll

                        yaw_thresh = config.get('thresholds.yaw_threshold', 35)
                        pitch_thresh = config.get('thresholds.pitch_threshold', 25)
                        if (abs(results['head_pose']['yaw']) > yaw_thresh or
                                abs(results['head_pose']['pitch']) > pitch_thresh):
                            results['gaze_direction'] = 'Outside'
                        else:
                            results['gaze_direction'] = 'Inside'

                    def get_lm(idx):
                        lm = landmarks_raw[idx]
                        return int(lm.x * w), int(lm.y * h)

                    top_lip = np.array(get_lm(13))
                    bottom_lip = np.array(get_lm(14))
                    left_m = np.array(get_lm(61))
                    right_m = np.array(get_lm(291))
                    mouth_h = np.linalg.norm(top_lip - bottom_lip)
                    mouth_w = np.linalg.norm(left_m - right_m)
                    if mouth_w > 0:
                        results['mouth_ratio'] = float(mouth_h / mouth_w)

                    if diag:
                        print(f"[DIAG] FaceLandmarker: yaw={results['head_pose']['yaw']:.1f} "
                              f"pitch={results['head_pose']['pitch']:.1f} gaze={results['gaze_direction']}")
            except Exception as e:
                if diag:
                    print(f"[DIAG] FaceLandmarker error: {e}")

        elif self._face_detector_legacy is not None:
            mp_results = self._face_detector_legacy.process(rgb)
            if mp_results.multi_face_landmarks:
                face_detected = True
                face = mp_results.multi_face_landmarks[0]
                self._extract_face_data_legacy(face, w, h, results)
                if diag:
                    print(f"[DIAG] Legacy: yaw={results['head_pose']['yaw']:.1f} "
                          f"pitch={results['head_pose']['pitch']:.1f} (ignore)")

        if not face_detected and diag:
            print(f"[DIAG] Face NOT detected (frame {w}x{h})")

        if self._hand_detector is not None:
            try:
                hand_results = self._hand_detector.process(rgb)
                if hand_results.multi_hand_landmarks:
                    for hand_lm in hand_results.multi_hand_landmarks:
                        xs = [lm.x * w for lm in hand_lm.landmark]
                        ys = [lm.y * h for lm in hand_lm.landmark]
                        x1, y1 = max(0, int(min(xs))), max(0, int(min(ys)))
                        x2, y2 = min(w, int(max(xs))), min(h, int(max(ys)))
                        results['hand_bboxes'].append((x1, y1, x2, y2))
                if diag:
                    print(f"[DIAG] Hands: {len(results['hand_bboxes'])} detected")
            except Exception as e:
                if diag:
                    print(f"[DIAG] Hands error: {e}")

        if self._yolo_session is not None:
            try:
                detections = self._run_yolo(frame)
                yolo_persons = [d['bbox'] for d in detections if d['class'] == 'person']
                phone_bboxes = [d['bbox'] for d in detections if d['class'] == 'cell phone']

                face_bboxes = results['face_bboxes']
                final_person_bboxes = list(face_bboxes)

                for yolo_box in yolo_persons:
                    yx1, yy1, yx2, yy2 = map(int, yolo_box)
                    is_duplicate = False
                    for fbox in face_bboxes:
                        fx1, fy1, fx2, fy2 = fbox
                        inter_x1 = max(yx1, fx1)
                        inter_y1 = max(yy1, fy1)
                        inter_x2 = min(yx2, fx2)
                        inter_y2 = min(yy2, fy2)
                        if inter_x1 < inter_x2 and inter_y1 < inter_y2:
                            inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                            yolo_area = (yx2 - yx1) * (yy2 - yy1)
                            face_area = (fx2 - fx1) * (fy2 - fy1)
                            if inter_area / min(yolo_area, face_area) > 0.5:
                                is_duplicate = True
                                break
                    if not is_duplicate:
                        final_person_bboxes.append((yx1, yy1, yx2, yy2))

                results['persons_count'] = len(final_person_bboxes)
                results['person_bboxes'] = final_person_bboxes
                results['phone_detected'] = len(phone_bboxes) > 0

                if diag:
                    print(f"[DIAG] YOLO: raw={len(yolo_persons)} merged={len(final_person_bboxes)} phones={len(phone_bboxes)}")
            except Exception as e:
                if diag:
                    print(f"[DIAG] YOLO error: {e}")

        return results

    def _extract_face_data_legacy(self, face_lm, img_w, img_h, results):
        landmarks = face_lm.landmark
        def gp(idx): return int(landmarks[idx].x * img_w), int(landmarks[idx].y * img_h)
        xs = [int(lm.x * img_w) for lm in landmarks]
        ys = [int(lm.y * img_h) for lm in landmarks]
        results['face_bboxes'] = [(min(xs), min(ys), max(xs), max(ys))]
        img_pts = np.array([gp(1), gp(152), gp(33), gp(263), gp(61), gp(291)], dtype=np.float32)
        K = self._build_camera_matrix(img_w, img_h)
        dist = np.array([0,0,0,0,0], dtype=np.float32)
        model_pts = np.array([
            [0.0, 0.0, 0.0],
            [0.0, -70.0, -20.0],
            [-50.0, 40.0, -30.0],
            [50.0, 40.0, -30.0],
            [-35.0, -35.0, -25.0],
            [35.0, -35.0, -25.0],
        ], dtype=np.float32)
        success, rvec, tvec = cv2.solvePnP(model_pts, img_pts, K, dist, flags=cv2.SOLVEPNP_ITERATIVE)
        if success:
            R, _ = cv2.Rodrigues(rvec)
            euler = self._decompose_projection(np.hstack((R, tvec)))
            raw_yaw, raw_pitch = float(euler[1]), float(euler[0])
            self._smooth_yaw = raw_yaw
            self._smooth_pitch = raw_pitch
            results['head_pose']['yaw'] = raw_yaw
            results['head_pose']['pitch'] = raw_pitch
            results['head_pose']['roll'] = float(euler[2])
            yaw_th = config.get('thresholds.yaw_threshold', 35)
            pitch_th = config.get('thresholds.pitch_threshold', 25)
            if abs(results['head_pose']['yaw']) > yaw_th or abs(results['head_pose']['pitch']) > pitch_th:
                results['gaze_direction'] = 'Outside'
            else:
                results['gaze_direction'] = 'Inside'
        top_lip = np.array(gp(13))
        bottom_lip = np.array(gp(14))
        left_m = np.array(gp(61))
        right_m = np.array(gp(291))
        mh = np.linalg.norm(top_lip - bottom_lip)
        mw = np.linalg.norm(left_m - right_m)
        if mw > 0:
            results['mouth_ratio'] = float(mh / mw)

    def _matrix_to_euler(self, R):
        sy = np.sqrt(R[0,0]**2 + R[1,0]**2)
        singular = sy < 1e-6
        if not singular:
            x = np.arctan2(R[2,1], R[2,2])
            y = np.arctan2(-R[2,0], sy)
            z = np.arctan2(R[1,0], R[0,0])
        else:
            x = np.arctan2(-R[1,2], R[1,1])
            y = np.arctan2(-R[2,0], sy)
            z = 0
        return np.degrees([x, y, z])

    def _build_camera_matrix(self, img_w, img_h):
        fx = config.get('camera_intrinsics.fx', None)
        if fx is None:
            hfov = config.get('camera_intrinsics.hfov_degrees', 63.0)
            fx = (img_w / 2.0) / np.tan(np.radians(hfov) / 2.0)
        fy = config.get('camera_intrinsics.fy', fx)
        cx = config.get('camera_intrinsics.cx', img_w / 2.0)
        cy = config.get('camera_intrinsics.cy', img_h / 2.0)
        return np.array([[fx,0,cx],[0,fy,cy],[0,0,1]], dtype=np.float32)

    def _decompose_projection(self, P):
        R = P[:,:3]
        sy = np.sqrt(R[0,0]**2 + R[1,0]**2)
        singular = sy < 1e-6
        if not singular:
            x = np.arctan2(R[2,1], R[2,2])
            y = np.arctan2(-R[2,0], sy)
            z = np.arctan2(R[1,0], R[0,0])
        else:
            x = np.arctan2(-R[1,2], R[1,1])
            y = np.arctan2(-R[2,0], sy)
            z = 0
        return np.degrees([x, y, z])

    def _run_yolo(self, frame):
        model_h = model_w = 640
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]
        scale = min(model_w/w, model_h/h)
        new_w, new_h = int(w*scale), int(h*scale)
        pad_x = (model_w - new_w)//2
        pad_y = (model_h - new_h)//2
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        padded = np.full((model_h, model_w, 3), 114, dtype=np.uint8)
        padded[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized
        input_tensor = padded.astype(np.float32)/255.0
        input_tensor = np.transpose(input_tensor, (2,0,1))
        input_tensor = np.expand_dims(input_tensor, 0)
        outputs = self._yolo_session.run(None, {self._yolo_input_name: input_tensor})
        return self._parse_yolo_outputs(outputs[0], w, h, scale, pad_x, pad_y)

    def _parse_yolo_outputs(self, output, img_w, img_h, scale, pad_x, pad_y):
        if output.ndim == 3:
            output = output[0]
        output = np.transpose(output)
        conf_thresh = config.get('yolo.confidence', 0.25)
        iou_thresh = config.get('yolo.iou_threshold', 0.45)
        allowed = {'person', 'cell phone'}
        coco_names = [
            'person','bicycle','car','motorcycle','airplane','bus','train',
            'truck','boat','traffic light','fire hydrant','stop sign',
            'parking meter','bench','bird','cat','dog','horse','sheep',
            'cow','elephant','bear','zebra','giraffe','backpack','umbrella',
            'handbag','tie','suitcase','frisbee','skis','snowboard',
            'sports ball','kite','baseball bat','baseball glove','skateboard',
            'surfboard','tennis racket','bottle','wine glass','cup','fork',
            'knife','spoon','bowl','banana','apple','sandwich','orange',
            'broccoli','carrot','hot dog','pizza','donut','cake','chair',
            'couch','potted plant','bed','dining table','toilet','tv',
            'laptop','mouse','remote','keyboard','cell phone','microwave',
            'oven','toaster','sink','refrigerator','book','clock','vase',
            'scissors','teddy bear','hair drier','toothbrush',
        ]
        boxes = []
        for row in output:
            x_center, y_center, bw, bh = row[:4]
            class_scores = row[4:]
            class_id = int(np.argmax(class_scores))
            score = float(class_scores[class_id])
            if score < conf_thresh:
                continue
            name = coco_names[class_id] if class_id < len(coco_names) else 'unknown'
            if name not in allowed:
                continue
            x1 = (x_center - bw/2 - pad_x)/scale
            y1 = (y_center - bh/2 - pad_y)/scale
            x2 = (x_center + bw/2 - pad_x)/scale
            y2 = (y_center + bh/2 - pad_y)/scale
            x1, y1 = max(0,x1), max(0,y1)
            x2, y2 = min(img_w,x2), min(img_h,y2)
            boxes.append({'bbox':[x1,y1,x2,y2],'score':score,'class':name,'class_id':class_id})
        if not boxes:
            return []
        bboxes_xywh = np.array([[b['bbox'][0],b['bbox'][1],b['bbox'][2]-b['bbox'][0],b['bbox'][3]-b['bbox'][1]] for b in boxes])
        scores = np.array([b['score'] for b in boxes])
        indices = cv2.dnn.NMSBoxes(bboxes_xywh.tolist(), scores.tolist(), conf_thresh, iou_thresh)
        if isinstance(indices, tuple):
            indices = list(indices)
        else:
            indices = indices.flatten().tolist()
        return [boxes[i] for i in indices]

    def close(self):
        if self._face_landmarker:
            self._face_landmarker.close()
        if self._face_detector_legacy:
            self._face_detector_legacy.close()
        if self._hand_detector:
            self._hand_detector.close()
        self._yolo_session = None