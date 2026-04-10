import cv2
import numpy as np
import threading
import queue as _queue
import math
from ultralytics import YOLO


class HumanDetector:

    MODES = ("ground", "elevated", "topdown")

    def __init__(self, model_path: str = "yolo11m.pt"):
        self.model_path  = model_path
        self.model       = YOLO(model_path)
        self.mode        = "ground"
        self._lock       = threading.Lock()
        self._last_boxes = []
        self._calibrated = False
        self._prev_gray  = None

        self._frame_q  = _queue.Queue(maxsize=2)
        self._result_q = _queue.Queue(maxsize=2)
        self._worker   = threading.Thread(
            target=self._worker_loop, daemon=True, name="yolo-worker"
        )
        self._worker.start()
        print(f"[HumanDetector] Ready — {model_path} | 3-pass | SAHI: OFF | ByteTrack: OFF")

    # ── Worker ────────────────────────────────────────────────────────────────
    def _worker_loop(self):
        while True:
            frame = self._frame_q.get()
            if frame is None:
                break
            try:
                boxes = self._run_yolo(frame)
                while not self._result_q.empty():
                    try: self._result_q.get_nowait()
                    except _queue.Empty: break
                self._result_q.put(boxes)
            except Exception as e:
                print(f"[HumanDetector] Worker error: {e}")

    def shutdown(self):
        self._frame_q.put(None)

    # ── 3-Pass YOLO ───────────────────────────────────────────────────────────
    def _run_yolo(self, frame) -> list:
        h, w  = frame.shape[:2]
        boxes = []
        scale_x = w / 1280

        # Pass 1 — Full frame
        res1 = self.model(
            frame, classes=[0], conf=0.15,
            iou=0.30, imgsz=1280, verbose=False,
        )[0]
        for box in res1.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            boxes.append(("person", x1, y1, x2, y2, float(box.conf[0])))

        # Pass 2 — Mid-band crop (20%–80% height)
        band_top     = int(h * 0.20)
        band_bottom  = int(h * 0.80)
        band_h       = band_bottom - band_top
        band_resized = cv2.resize(frame[band_top:band_bottom, :], (1280, 720))
        scale_y2     = band_h / 720

        res2 = self.model(
            band_resized, classes=[0], conf=0.15,
            iou=0.30, imgsz=1280, verbose=False,
        )[0]
        for box in res2.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            boxes.append(("person",
                      int(x1*scale_x), int(y1*scale_y2)+band_top,
                      int(x2*scale_x), int(y2*scale_y2)+band_top,
                      float(box.conf[0])))

         # Pass 3 — Top 55% crop (far/distant people, elevated/topdown only)
        if self.mode in ("elevated", "topdown"):
            crop_h      = int(h * 0.55)
            top_resized = cv2.resize(frame[:crop_h, :], (1280, 720))
            scale_y3    = crop_h / 720

            res3 = self.model(
                top_resized, classes=[0], conf=0.15,
                iou=0.30, imgsz=1280, verbose=False,
            )[0]
            for box in res3.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append(("person",
                          int(x1*scale_x), int(y1*scale_y3),
                          int(x2*scale_x), int(y2*scale_y3),
                          float(box.conf[0])))

        # Pass 4 — Head-region scan (queue/corridor scenes)
        # Heads are always visible even when bodies are fully occluded
        head_bottom  = int(h * 0.70)
        head_resized = cv2.resize(frame[:head_bottom, :], (1280, 720))
        scale_y4     = head_bottom / 720

        res4 = self.model(
            head_resized, classes=[0], conf=0.12,
            iou=0.25, imgsz=1280, verbose=False,
        )[0]
        for box in res4.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            if (y2 - y1) > 120:   # skip full-body detections already caught
                continue
            boxes.append(("person",
                      int(x1*scale_x), int(y1*scale_y4),
                      int(x2*scale_x), int(y2*scale_y4),
                      float(box.conf[0])))

        return self._nms(boxes, iou_threshold=0.30)

    # ── NMS ───────────────────────────────────────────────────────────────────
    def _nms(self, boxes: list, iou_threshold: float = 0.30) -> list:
        if not boxes:
            return []
        coords = np.array([[b[1], b[2], b[3], b[4]] for b in boxes], dtype=np.float32)
        scores = np.array([b[5] for b in boxes],                      dtype=np.float32)
        x1, y1, x2, y2 = coords[:,0], coords[:,1], coords[:,2], coords[:,3]
        areas  = np.maximum(0, (x2-x1)) * np.maximum(0, (y2-y1))
        order  = scores.argsort()[::-1]
        keep   = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            if order.size == 1:
                break
            xx1   = np.maximum(x1[i], x1[order[1:]])
            yy1   = np.maximum(y1[i], y1[order[1:]])
            xx2   = np.minimum(x2[i], x2[order[1:]])
            yy2   = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0, xx2-xx1) * np.maximum(0, yy2-yy1)
            iou   = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            order = order[np.where(iou <= iou_threshold)[0] + 1]
        return [boxes[i] for i in keep]

    # ── Calibration ───────────────────────────────────────────────────────────
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
        print(f"[HumanDetector] Mode set manually: {mode.upper()}")

    def _analyse_camera_angle(self, frame) -> str:
        h, w  = frame.shape[:2]
        # Use a quick single pass for calibration (speed > accuracy here)
        res   = self.model(
            frame, classes=[0], conf=0.25,
            iou=0.45, imgsz=640, verbose=False,
        )[0]
        if len(res.boxes) == 0:
            return "elevated"   # default to elevated — safer for crowd scenes
        aspects, rel_heights = [], []
        for box in res.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            bw = max(1, x2-x1); bh = max(1, y2-y1)
            aspects.append(bh / bw)
            rel_heights.append(bh / h)
        avg_a = float(np.mean(aspects))
        avg_h = float(np.mean(rel_heights))
        if avg_a > 1.8 and avg_h > 0.25:
            return "ground"
        elif avg_a > 1.1:
            return "elevated"
        else:
            return "topdown"

    # ── Preprocessing ─────────────────────────────────────────────────────────
    def _preprocess(self, frame) -> np.ndarray:
        """CLAHE contrast enhancement — helps in low-light / compressed video."""
        lab     = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe   = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return cv2.cvtColor(cv2.merge([clahe.apply(l), a, b]), cv2.COLOR_LAB2BGR)

    # ── Ground anchors ────────────────────────────────────────────────────────
    def get_ground_anchors(self, boxes: list) -> list:
        anchors = []
        for box in boxes:
            if len(box) < 5:
                continue
            x1, y1, x2, y2 = box[1], box[2], box[3], box[4]
            cx = (x1 + x2) // 2
            # Topdown: use centroid. All others: use foot (bottom-center)
            cy = (y1 + y2) // 2 if self.mode == "topdown" else y2
            anchors.append((cx, cy))
        return anchors

    # ── Detect — main entry point ─────────────────────────────────────────────
    def detect(self, frame, frame_count: int):
        if not self._calibrated:
            self.calibrate(frame)

        processed = self._preprocess(frame)
        if not self._frame_q.full():
            self._frame_q.put_nowait(processed)

        if not self._result_q.empty():
            try:
                boxes = self._result_q.get_nowait()
                with self._lock:
                    self._last_boxes = boxes
            except _queue.Empty:
                pass

        with self._lock:
            boxes = list(self._last_boxes)

        self._draw(frame, boxes)
        centers = [((b[1]+b[3])//2, (b[2]+b[4])//2) for b in boxes]
        return frame, centers

    # ── Draw ──────────────────────────────────────────────────────────────────
    def _draw(self, frame, boxes):
        for box in boxes:
            _, x1, y1, x2, y2, cf = box
            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,220,255), 2)
            cv2.putText(frame, f"{cf:.2f}", (x1, y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0,220,255), 1)
            # Foot dot
            cx = (x1+x2)//2
            cy = y2 if self.mode != "topdown" else (y1+y2)//2
            cv2.circle(frame, (cx, cy), 4, (0,255,80), -1)

    # ── Optical flow ──────────────────────────────────────────────────────────
    def optical_flow(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._prev_gray is None or self._prev_gray.shape != gray.shape:
            self._prev_gray = gray
            return 0.0, 0.0
        flow      = cv2.calcOpticalFlowFarneback(
            self._prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=2, poly_n=5, poly_sigma=1.2, flags=0)
        self._prev_gray = gray.copy()
        mag, _    = cv2.cartToPolar(flow[...,0], flow[...,1])
        avg_speed = float(np.mean(mag))
        fx        = flow[...,0]
        mid       = fx.shape[1] // 2
        lm, rm    = float(np.mean(fx[:,:mid])), float(np.mean(fx[:,mid:]))
        conflict  = min(1.0, (abs(lm)+abs(rm))/10.0) if (lm>0) != (rm>0) else 0.0
        return round(avg_speed, 3), round(conflict, 3)

    # ── Heatmap ───────────────────────────────────────────────────────────────
    def heatmap(self, frame, centers):
        h, w  = frame.shape[:2]
        heat  = np.zeros((h, w), dtype=np.float32)
        for cx, cy in centers:
            if 0 <= cx < w and 0 <= cy < h:
                heat[cy, cx] += 1
        heat    = cv2.GaussianBlur(heat, (151,151), 0)
        if heat.max() > 0:
            heat /= heat.max()
        colored = cv2.applyColorMap((heat*255).astype(np.uint8), cv2.COLORMAP_JET)
        return cv2.addWeighted(frame, 0.5, colored, 0.5, 0)

    def zone_counts(self, frame, centers, rows=3, cols=3):
        h, w   = frame.shape[:2]
        zw, zh = w//cols, h//rows
        zones  = {}
        for r in range(rows):
            for c in range(cols):
                label  = f"Z{r*cols+c+1}"
                x0,y0  = c*zw, r*zh
                x1,y1  = x0+zw, y0+zh
                zones[label] = sum(
                    1 for cx,cy in centers
                    if x0<=cx<x1 and y0<=cy<y1
                )
        return zones

    def reset(self):
        self._prev_gray  = None
        self._last_boxes = []
        self._calibrated = False
        while not self._frame_q.empty():
            try: self._frame_q.get_nowait()
            except _queue.Empty: break
        while not self._result_q.empty():
            try: self._result_q.get_nowait()
            except _queue.Empty: break
        print("[HumanDetector] Reset.")


_detector = HumanDetector("yolo11m.pt")