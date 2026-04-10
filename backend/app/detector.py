from app.human_detector import _detector

def detect_people(frame, frame_count):
    return _detector.detect(frame, frame_count)

def generate_heatmap(frame, centers):
    return _detector.heatmap(frame, centers)

def get_zone_counts(frame, centers):
    return _detector.zone_counts(frame, centers, rows=4, cols=4)

def compute_optical_flow(frame):
    return _detector.optical_flow(frame)

def compute_crowd_alert(zone_counts_dict):
    return _detector.crowd_alert(zone_counts_dict)

def reset_optical_flow():
    _detector.reset()