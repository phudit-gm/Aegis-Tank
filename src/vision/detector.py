"""ตัวตรวจจับ — รับเฟรม ส่งเข้า YOLOv8 หาว่ามีวัตถุเป้าหมายไหม อยู่ตรงไหน

TARGET_CLASS / CONF_THRESHOLD ยังเป็นค่า TODO ตาม SPEC.md §4 — ตั้งค่า default ไว้ทดสอบ pipeline เท่านั้น
เปลี่ยนค่าจริงได้ที่ config/settings.yaml -> detection (ไม่ต้องแก้โค้ดนี้)
"""

from ultralytics import YOLO


class Detection:
    def __init__(self, x: float, y: float, confidence: float, class_name: str):
        self.x = x
        self.y = y
        self.confidence = confidence
        self.class_name = class_name


class Detector:
    def __init__(self, model_path: str, target_class: str, conf_threshold: float = 0.5):
        self.model = YOLO(model_path)
        self.target_class = target_class
        self.conf_threshold = conf_threshold
        self.class_names = self.model.names  # dict {id: name}

    def detect(self, frame) -> Detection | None:
        """คืน Detection ของเป้าที่ confidence สูงสุดที่ตรง target_class หรือ None ถ้าไม่เจอ"""
        results = self.model.predict(frame, verbose=False, conf=self.conf_threshold)
        best = None

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                name = self.class_names.get(cls_id, str(cls_id))
                if name != self.target_class:
                    continue
                conf = float(box.conf[0])
                if best is not None and conf <= best.confidence:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                best = Detection((x1 + x2) / 2, (y1 + y2) / 2, conf, name)

        return best
