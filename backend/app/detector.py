from app.human_detector import _detector

def detect_people(frame, frame_count: int):
    return _detector.detect(frame, frame_count)

def generate_heatmap(frame, centers):
    return _detector.heatmap(frame, centers)

def get_zone_counts(frame, centers):
    return _detector.zone_counts(frame, centers)

def compute_optical_flow(frame):
    return _detector.optical_flow(frame)

def reset_optical_flow():
    _detector._prev_gray = None

def get_ground_anchors():
    with _detector._lock:
        boxes = list(_detector._last_boxes)
    return _detector.get_ground_anchors(boxes)