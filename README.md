# ProctorVision Desktop Edition

نظام مراقبة انتباه الطالب (Student Attention Monitoring System) — نسخة سطح المكتب المحلية بالكامل.

## الميزات

- **معالجة محلية 100%**: لا تغادر أي بيانات الجهاز.
- **رؤية حاسوبية متقدمة**: MediaPipe Face Mesh + YOLOv8 ONNX.
- **بث مباشر**: عرض الفيديو مع تراكيب توضيحية (overlays) في الوقت الفعلي.
- **مقاييس انتباه ذكية**: Attentive / Distracted / Warning.
- **تنبيهات مباشرة**: كشف النظر بعيداً، الهاتف، شخص إضافي، تغطية الفم.
- **تقارير تلقائية**: تصدير CSV + PDF عند إيقاف الجلسة.
- **إعدادات قابلة للتعديل**: تغيير العتبات عبر واجهة المستخدم دون إعادة التشغيل.

## متطلبات التشغيل

- Python 3.10+
- Node.js 20+ (للبناء فقط)
- كاميرا ويب (Webcam)

## تثبيت التبعيات

```bash
# Python dependencies
pip install -r backend/requirements.txt
```

## تشغيل التطبيق

```bash
python start.py
```

يفتح المتصفح تلقائياً على `http://127.0.0.1:5000`.

## هيكل المشروع

```
app/
├── backend/
│   ├── app.py                 # Flask + SocketIO server
│   ├── config/
│   │   ├── config.json        # Default settings
│   │   └── config_manager.py  # Runtime config loader
│   ├── pipeline/
│   │   ├── camera.py          # Camera capture thread
│   │   ├── vision_pipeline.py # MediaPipe + YOLOv8 inference
│   │   └── fusion_engine.py   # Attention logic & alerts
│   ├── session/
│   │   └── session_manager.py # Session lifecycle
│   └── reports/
│       └── report_generator.py # CSV + PDF export
├── frontend/ (built into dist/)
│   ├── src/components/        # React components
│   └── src/contexts/          # Session state management
├── models/                    # YOLOv8 ONNX + MediaPipe task files
├── reports_output/            # Generated reports
├── dist/                      # Built React app
└── start.py                   # Launcher script
```

## ملاحظات النماذج

يجب وضع النماذج في مجلد `models/`:

- `face_landmarker_v2_with_blendshapes.task` — من MediaPipe Tasks
- `yolov8n.onnx` — نموذج YOLOv8n محوّل إلى ONNX

يمكن تحميل `yolov8n.onnx` مسبقاً أو تحويله باستخدام:

```bash
pip install ultralytics
yolo export model=yolov8n.pt format=onnx
```

## نقاط النهاية API

- `GET /api/v1/status` — حالة الخادم والكاميرا
- `POST /api/v1/session/start` — بدء جلسة
- `POST /api/v1/session/stop` — إيقاف الجلسة + توليد التقارير
- `GET /api/v1/session` — معلومات الجلسة الحالية
- `GET /api/v1/settings` — قراءة الإعدادات
- `PUT /api/v1/settings` — تحديث الإعدادات
- `GET /api/v1/reports` — قائمة التقارير
- `GET /api/v1/reports/<filename>` — تحميل تقرير

## الترخيص

GPL-3.0
