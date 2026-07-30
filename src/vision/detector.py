"""Detector — receives a frame, feeds it into YOLOv8 to find whether/where a target object is

TARGET_CLASS / CONF_THRESHOLD are still TODO per SPEC.md §4 — default values are set just to test
the pipeline. Change the real values at config/settings.yaml -> detection (no need to edit this code).
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
        """Returns the Detection with highest confidence matching target_class, or None if not found"""
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
