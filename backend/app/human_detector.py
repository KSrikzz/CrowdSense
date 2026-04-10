import cv2
import numpy as np
import threading
import queue as _queue
import math
from collections import deque
from ultralytics import YOLO

try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    SAHI_AVAILABLE = True
except ImportError:
    SAHI_AVAILABLE = False
    print("[HumanDetector] SAHI not found — run: pip install sahi lapx")
    print("[HumanDetector] Falling back to standard YOLO inference.")


# ═════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═════════════════════════════════════════════════════════════════════════════
CONF        = 0.2
IOU         = 0.5
IMGSZ       = 1024
MIN_BOX_W   = 10
MIN_BOX_H   = 20
FRAME_W     = 1280
FRAME_H     = 720
GRID_ROWS   = 4
GRID_COLS   = 4
GRID_SIZE   = GRID_ROWS * GRID_COLS  # 16
SMOOTH_WINDOW = 5


# ═════════════════════════════════════════════════════════════════════════════
# SMOOTHING BUFFER — moving average over last 5 frames
# ═════════════════════════════════════════════════════════════════════════════
_total_buffer: deque = deque(maxlen=SMOOTH_WINDOW)
_zones_buffer: deque = deque(maxlen=SMOOTH_WINDOW)


def _smooth_total(raw_total: int) -> float:
    _total_buffer.append(raw_total)
    return sum(_total_buffer) / len(_total_buffer)


def _smooth_zones(raw_zones: list) -> list:
    _zones_buffer.append(raw_zones)
    n = len(_zones_buffer)
    length = len(raw_zones)
    smoothed = [0.0] * length
    for buf in _zones_buffer:
        for i in range(min(length, len(buf))):
            smoothed[i] += buf[i]
    return [round(s / n, 1) for s in smoothed]


def reset_smoothing():
    _total_buffer.clear()
    _zones_buffer.clear()


# ═════════════════════════════════════════════════════════════════════════════
# MODEL LOADING
# ═════════════════════════════════════════════════════════════════════════════
def load_model(model_path: str = "yolo11m.pt") -> YOLO:
    model = YOLO(model_path)
    model.fuse()
    print(f"[CrowdSense] Model loaded: {model_path} (CPU, fused)")
    return model


# ═════════════════════════════════════════════════════════════════════════════
# PREPROCESSING — resize to 1280×720, CLAHE contrast boost
# ═════════════════════════════════════════════════════════════════════════════
def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    frame = cv2.resize(frame, (FRAME_W, FRAME_H))
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


# ═════════════════════════════════════════════════════════════════════════════
# DETECTION — conf=0.2, iou=0.5, imgsz=1024, class 0 only
#              keeps small boxes (w>10, h>20)
# ═════════════════════════════════════════════════════════════════════════════
def detect_people(model: YOLO, frame: np.ndarray) -> list:
    boxes_out = []
    results = model(
        frame,
        classes=[0],
        conf=CONF,
        iou=IOU,
        imgsz=IMGSZ,
        stream=True,
        verbose=False,
    )
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            w = x2 - x1
            h = y2 - y1
            if w > MIN_BOX_W and h > MIN_BOX_H:
                boxes_out.append({"x": x1, "y": y1, "w": w, "h": h})
    return boxes_out


# ═════════════════════════════════════════════════════════════════════════════
# CROWD METRICS — count, avg area, density
# ═════════════════════════════════════════════════════════════════════════════
def compute_crowd_metrics(boxes: list, frame_shape: tuple) -> dict:
    total = len(boxes)
    areas = [b["w"] * b["h"] for b in boxes]
    avg_area = round(sum(areas) / max(total, 1), 1)
    frame_area = frame_shape[0] * frame_shape[1]
    density = round(total / max(frame_area, 1), 8)
    return {"count": total, "avg_box_area": avg_area, "density": density}


# ═════════════════════════════════════════════════════════════════════════════
# ZONE COMPUTATION — 4×4 grid using bbox center
# ═════════════════════════════════════════════════════════════════════════════
def compute_zones(boxes: list, frame_shape: tuple) -> list:
    h, w = frame_shape[:2]
    zones = [0] * GRID_SIZE
    cell_w = w / GRID_COLS
    cell_h = h / GRID_ROWS
    for b in boxes:
        cx = b["x"] + b["w"] / 2.0
        cy = b["y"] + b["h"] / 2.0
        col = min(int(cx / cell_w), GRID_COLS - 1)
        row = min(int(cy / cell_h), GRID_ROWS - 1)
        zones[row * GRID_COLS + col] += 1
    return zones


# ═════════════════════════════════════════════════════════════════════════════
# ALERT LOGIC — HIGH > 12 or max_zone > 6, MEDIUM > 6, uses smoothed total
# ═════════════════════════════════════════════════════════════════════════════
def compute_alert(raw_total: int, smoothed_total: float, max_zone: int) -> str:
    if raw_total > 8:
        return "HIGH"
    
    if smoothed_total > 12 or max_zone > 6:
        return "HIGH"
    elif smoothed_total > 6:
        return "MEDIUM"
    else:
        return "LOW"


# ═════════════════════════════════════════════════════════════════════════════
# DEBUG LOG
# ═════════════════════════════════════════════════════════════════════════════
def debug_log(total: int, avg_total: float, max_zone: int, alert: str):
    print(f"[CrowdSense] detected={total} | avg_total={avg_total:.1f} | max_zone={max_zone} | alert={alert}")


# ═════════════════════════════════════════════════════════════════════════════
# DRAW BOUNDING BOXES (optional debug overlay)
# ═════════════════════════════════════════════════════════════════════════════
def draw_boxes(frame: np.ndarray, boxes: list, alert: str) -> np.ndarray:
    color_map = {"LOW": (0, 255, 0), "MEDIUM": (0, 180, 255), "HIGH": (0, 0, 255)}
    color = color_map.get(alert, (0, 255, 0))
    for b in boxes:
        cv2.rectangle(frame, (b["x"], b["y"]),
                      (b["x"] + b["w"], b["y"] + b["h"]), color, 2)
    cv2.putText(frame, f"People: {len(boxes)} | Alert: {alert}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return frame


# ═════════════════════════════════════════════════════════════════════════════
# FULL-FRAME PIPELINE — single call convenience
# ═════════════════════════════════════════════════════════════════════════════
def process_frame(model: YOLO, frame: np.ndarray) -> dict:
    frame = preprocess_frame(frame)
    boxes = detect_people(model, frame)
    metrics = compute_crowd_metrics(boxes, frame.shape)
    zones = compute_zones(boxes, frame.shape)
    raw_total = metrics["count"]
    smoothed_total = _smooth_total(raw_total)
    smoothed_zones = _smooth_zones(zones)
    max_zone = max(zones) if zones else 0
    alert = compute_alert(raw_total, smoothed_total, max_zone)

    debug_log(raw_total, smoothed_total, max_zone, alert)

    return {
        "boxes": boxes,
        "zones": zones,
        "zones_smoothed": smoothed_zones,
        "count": raw_total,
        "alert": alert,
        "smoothed_total": round(smoothed_total, 1),
        "avg_box_area": metrics["avg_box_area"],
        "density": metrics["density"],
    }


# ═════════════════════════════════════════════════════════════════════════════
# LEGACY CLASS — preserved for backward compat with main.py / detector.py
# ═════════════════════════════════════════════════════════════════════════════
class HumanDetector:

    MODES = ("ground", "elevated", "topdown")

    def __init__(self, model_path: str = "yolo11m.pt"):
        self.model_path     = model_path
        self.model          = YOLO(model_path)
        self.mode           = "ground"
        self._lock          = threading.Lock()

        self._last_centers  = []
        self._last_boxes    = []
        self._active_ids    = set()

        self._frame_q  = _queue.Queue(maxsize=2)
        self._result_q = _queue.Queue(maxsize=2)
        self._worker   = threading.Thread(
            target=self._worker_loop, daemon=True, name="yolo-worker"
        )
        self._worker.start()

        self._sahi_model = None
        if SAHI_AVAILABLE:
            try:
                self._sahi_model = AutoDetectionModel.from_pretrained(
                    model_type="ultralytics",
                    model_path=model_path,
                    confidence_threshold=CONF,
                    device="cpu",
                )
                print(f"[HumanDetector] SAHI sliced inference ready ({model_path})")
            except Exception as e:
                print(f"[HumanDetector] SAHI init failed: {e}. Using standard YOLO.")

        self._prev_gray  = None
        self._calibrated = False

    # ─────────────────────────────────────────────────────────────────────
    # ASYNC WORKER
    # ─────────────────────────────────────────────────────────────────────
    def _worker_loop(self):
        while True:
            frame = self._frame_q.get()
            if frame is None:
                break
            try:
                if self.mode == "ground":
                    c, b = self._detect_ground(frame)
                elif self.mode == "elevated":
                    c, b = self._detect_elevated(frame)
                else:
                    c, b = self._detect_topdown(frame)
                while not self._result_q.empty():
                    try: self._result_q.get_nowait()
                    except _queue.Empty: break
                self._result_q.put((c, b))
            except Exception as e:
                print(f"[HumanDetector] Worker error: {e}")

    def shutdown(self):
        self._frame_q.put(None)

    # ─────────────────────────────────────────────────────────────────────
    # CALIBRATION
    # ─────────────────────────────────────────────────────────────────────
    def calibrate(self, frame):
        mode             = self._analyse_camera_angle(frame)
        self.mode        = mode
        self._calibrated = True
        print(f"[HumanDetector] Camera mode auto-detected: {mode.upper()}")
        return mode

    def set_mode(self, mode: str):
        assert mode in self.MODES, f"Mode must be one of {self.MODES}"
        self.mode        = mode
        self._calibrated = True
        print(f"[HumanDetector] Camera mode manually set: {mode.upper()}")

    def _analyse_camera_angle(self, frame) -> str:
        h, w  = frame.shape[:2]
        res   = self.model(frame, classes=[0], conf=CONF, imgsz=640, verbose=False)[0]
        boxes = res.boxes
        if len(boxes) == 0:
            return "topdown"
        aspects, rel_heights = [], []
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            bw = max(1, x2 - x1); bh = max(1, y2 - y1)
            aspects.append(bh / bw)
            rel_heights.append(bh / h)
        avg_aspect     = np.mean(aspects)
        avg_rel_height = np.mean(rel_heights)
        if avg_aspect > 1.8 and avg_rel_height > 0.25:
            return "ground"
        elif avg_aspect > 1.2:
            return "elevated"
        else:
            return "topdown"

    # ─────────────────────────────────────────────────────────────────────
    # PREPROCESSING
    # ─────────────────────────────────────────────────────────────────────
    def _preprocess(self, frame, mode):
        frame = cv2.resize(frame, (FRAME_W, FRAME_H))
        lab     = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clip    = 2.0 if mode != "topdown" else 3.0
        clahe   = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
        l       = clahe.apply(l)
        frame   = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        if mode == "topdown":
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            frame  = cv2.filter2D(frame, -1, kernel)
        return frame

    # ─────────────────────────────────────────────────────────────────────
    # SAHI HELPER
    # ─────────────────────────────────────────────────────────────────────
    def _sahi_detect(self, frame, slice_size: int = 320):
        centers, boxes = [], []
        result = get_sliced_prediction(
            frame, self._sahi_model,
            slice_height=slice_size, slice_width=slice_size,
            overlap_height_ratio=0.2, overlap_width_ratio=0.2,
            verbose=0,
        )
        for obj in result.object_prediction_list:
            if obj.category.name != "person":
                continue
            x1 = int(obj.bbox.minx); y1 = int(obj.bbox.miny)
            x2 = int(obj.bbox.maxx); y2 = int(obj.bbox.maxy)
            w, h = x2 - x1, y2 - y1
            if w > MIN_BOX_W and h > MIN_BOX_H:
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                centers.append((cx, cy))
                boxes.append(("fg", x1, y1, x2, y2, float(obj.score.value)))
        return centers, boxes

    # ─────────────────────────────────────────────────────────────────────
    # BYTETRACK HELPER — conf=0.2, iou=0.5, imgsz=1024
    # ─────────────────────────────────────────────────────────────────────
    def _bytetrack_detect(self, frame, conf: float = CONF, imgsz: int = IMGSZ):
        centers, boxes, track_ids = [], [], []
        res = self.model.track(
            frame, classes=[0], conf=conf, iou=IOU, imgsz=imgsz,
            tracker="bytetrack.yaml", persist=True, verbose=False,
        )[0]
        for box in res.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            w, h = x2 - x1, y2 - y1
            if w <= MIN_BOX_W or h <= MIN_BOX_H:
                continue
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            tid    = int(box.id[0]) if box.id is not None else -1
            cf     = float(box.conf[0])
            centers.append((cx, cy))
            boxes.append(("fg", x1, y1, x2, y2, cf))
            track_ids.append(tid)
        with self._lock:
            self._active_ids.update(t for t in track_ids if t >= 0)
        return centers, boxes

    # ─────────────────────────────────────────────────────────────────────
    # MODE A: GROUND
    # ─────────────────────────────────────────────────────────────────────
    def _detect_ground(self, frame):
        frame   = self._preprocess(frame, "ground")
        h, w    = frame.shape[:2]
        centers, boxes = [], []

        if self._sahi_model is not None:
            centers, boxes = self._sahi_detect(frame, slice_size=320)
        else:
            c1, b1 = self._bytetrack_detect(frame, conf=CONF, imgsz=IMGSZ)
            centers.extend(c1); boxes.extend(b1)
            top = cv2.resize(frame[:h // 2, :], (w, h))
            c2, b2 = self._bytetrack_detect(top, conf=0.15, imgsz=640)
            for (cx, cy), box in zip(c2, b2):
                oy = int(cy * 0.5)
                if all(abs(cx - ex) > 20 or abs(oy - ey) > 20 for ex, ey in centers):
                    centers.append((cx, oy))
                    boxes.append(("bg", box[1], int(box[2]*0.5),
                                  box[3], int(box[4]*0.5), box[5]))
        return centers, boxes

    # ─────────────────────────────────────────────────────────────────────
    # MODE B: ELEVATED
    # ─────────────────────────────────────────────────────────────────────
    def _detect_elevated(self, frame):
        frame   = self._preprocess(frame, "elevated")
        h, w    = frame.shape[:2]
        centers, boxes = [], []

        if self._sahi_model is not None:
            centers, boxes = self._sahi_detect(frame, slice_size=320)
        else:
            c1, b1 = self._bytetrack_detect(frame, conf=CONF, imgsz=IMGSZ)
            for (cx, cy), box in zip(c1, b1):
                x1, y1, x2, y2 = box[1], box[2], box[3], box[4]
                bh = y2 - y1; bw = max(1, x2 - x1)
                depth_factor = 1.0 - (cy / h) * 0.4
                if (bh / bw) > 0.6 * depth_factor:
                    centers.append((cx, cy)); boxes.append(box)
            bottom = frame[h * 2 // 3:, :]
            c2, b2 = self._bytetrack_detect(bottom, conf=CONF, imgsz=640)
            for (cx, cy), box in zip(c2, b2):
                oy1 = box[2] + h * 2 // 3; oy2 = box[4] + h * 2 // 3
                acy = (oy1 + oy2) // 2
                if all(abs(cx - ex) > 20 or abs(acy - ey) > 20 for ex, ey in centers):
                    centers.append((cx, acy))
                    boxes.append(("fg", box[1], oy1, box[3], oy2, box[5]))
        return centers, boxes

    # ─────────────────────────────────────────────────────────────────────
    # MODE C: TOPDOWN
    # ─────────────────────────────────────────────────────────────────────
    def _detect_topdown(self, frame):
        frame   = self._preprocess(frame, "topdown")
        centers, boxes = [], []

        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        thresh  = cv2.adaptiveThreshold(blurred, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 6)
        kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        thresh  = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh  = cv2.morphologyEx(thresh, cv2.MORPH_OPEN,  kernel)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (600 < area < 6000): continue
            perimeter   = cv2.arcLength(cnt, True)
            circularity = 4 * math.pi * area / (perimeter ** 2 + 1e-6)
            if circularity < 0.40: continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if not (0.5 < bw / (bh + 1e-6) < 2.0): continue
            M = cv2.moments(cnt)
            if M["m00"] == 0: continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            centers.append((cx, cy))
            boxes.append(("head", x, y, x + bw, y + bh))

        res = self.model(frame, classes=[0], conf=0.15, iou=0.30,
                         imgsz=IMGSZ, verbose=False)[0]
        for box in res.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            w, h = x2 - x1, y2 - y1
            if w <= MIN_BOX_W or h <= MIN_BOX_H:
                continue
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            if all(abs(cx - ex) > 25 or abs(cy - ey) > 25 for ex, ey in centers):
                centers.append((cx, cy))
                boxes.append(("yolo", x1, y1, x2, y2))
        return centers, boxes

    # ─────────────────────────────────────────────────────────────────────
    # DRAW
    # ─────────────────────────────────────────────────────────────────────
    def _draw(self, frame, boxes, centers):
        for item in boxes:
            kind            = item[0]
            x1, y1, x2, y2 = item[1], item[2], item[3], item[4]
            cx, cy          = (x1 + x2) // 2, (y1 + y2) // 2
            if kind == "fg":
                conf = item[5]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 255), 2)
                cv2.putText(frame, f"{conf:.2f}", (x1, y1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 220, 255), 1)
            elif kind == "bg":
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 165, 0), 1)
            elif kind == "head":
                cv2.circle(frame, (cx, cy), 10, (0, 220, 255), 2)
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 165, 0), 1)
            cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

        sahi_tag = " | SAHI✓" if self._sahi_model else ""
        label    = f"MODE: {self.mode.upper()}{sahi_tag} | Unique: {len(self._active_ids)}"
        cv2.putText(frame, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 180), 2)

    # ─────────────────────────────────────────────────────────────────────
    # UNIFIED DETECT — main entry point
    # ─────────────────────────────────────────────────────────────────────
    def detect(self, frame, frame_count: int):
        if not self._calibrated:
            self.calibrate(frame)

        if not self._frame_q.full():
            self._frame_q.put_nowait(frame.copy())

        if not self._result_q.empty():
            try:
                c, b = self._result_q.get_nowait()
                with self._lock:
                    self._last_centers = c
                    self._last_boxes   = b
            except _queue.Empty:
                pass

        with self._lock:
            centers = list(self._last_centers)
            boxes   = list(self._last_boxes)

        self._draw(frame, boxes, centers)
        return frame, centers

    # ─────────────────────────────────────────────────────────────────────
    # OPTICAL FLOW
    # ─────────────────────────────────────────────────────────────────────
    def optical_flow(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._prev_gray is None or self._prev_gray.shape != gray.shape:
            self._prev_gray = gray
            return 0.0, 0.0
        flow = cv2.calcOpticalFlowFarneback(
            self._prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0)
        self._prev_gray = gray.copy()
        mag, _    = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        avg_speed = float(np.mean(mag))
        fx        = flow[..., 0]
        mid       = fx.shape[1] // 2
        lm, rm    = float(np.mean(fx[:, :mid])), float(np.mean(fx[:, mid:]))
        conflict  = 0.0
        if (lm > 0 and rm < 0) or (lm < 0 and rm > 0):
            conflict = min(1.0, (abs(lm) + abs(rm)) / 10.0)
        return round(avg_speed, 3), round(conflict, 3)

    # ─────────────────────────────────────────────────────────────────────
    # HEATMAP + ZONES (4×4 grid)
    # ─────────────────────────────────────────────────────────────────────
    def heatmap(self, frame, centers):
        h, w  = frame.shape[:2]
        heat  = np.zeros((h, w), dtype=np.float32)
        for cx, cy in centers:
            if 0 <= cx < w and 0 <= cy < h:
                heat[cy, cx] += 1
        blur   = 201 if self.mode == "topdown" else 301
        heat   = cv2.GaussianBlur(heat, (blur, blur), 0)
        if heat.max() > 0:
            heat /= heat.max()
        colored = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_JET)
        return cv2.addWeighted(frame, 0.45, colored, 0.55, 0)

    def zone_counts(self, frame, centers, rows=GRID_ROWS, cols=GRID_COLS):
        h, w   = frame.shape[:2]
        zw, zh = w // cols, h // rows
        zones  = {}
        for r in range(rows):
            for c in range(cols):
                label  = f"Z{r * cols + c + 1}"
                x0, y0 = c * zw, r * zh
                x1, y1 = x0 + zw, y0 + zh
                count  = sum(1 for cx, cy in centers if x0 <= cx < x1 and y0 <= cy < y1)
                zones[label] = count
        return zones

    # ─────────────────────────────────────────────────────────────────────
    # CROWD ALERT (uses smoothing buffer, fixed thresholds)
    # ─────────────────────────────────────────────────────────────────────
    def crowd_alert(self, zone_counts_dict: dict) -> dict:
        raw_zones = list(zone_counts_dict.values())
        raw_total = sum(raw_zones)
        smoothed_total = _smooth_total(raw_total)
        smoothed_zones = _smooth_zones(raw_zones)
        max_zone = max(raw_zones) if raw_zones else 0
        alert = compute_alert(raw_total, smoothed_total, max_zone)

        debug_log(raw_total, smoothed_total, max_zone, alert)

        return {
            "alert": alert,
            "count": raw_total,
            "smoothed_total": round(smoothed_total, 1),
            "zones_smoothed": smoothed_zones,
        }

    def reset(self):
        self._prev_gray    = None
        self._last_centers = []
        self._last_boxes   = []
        self._active_ids   = set()
        self._calibrated   = False
        reset_smoothing()
        while not self._frame_q.empty():
            try: self._frame_q.get_nowait()
            except _queue.Empty: break
        while not self._result_q.empty():
            try: self._result_q.get_nowait()
            except _queue.Empty: break
        print("[HumanDetector] State reset.")


_detector = HumanDetector("yolo11m.pt")
