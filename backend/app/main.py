import cv2
import base64
import asyncio
import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tempfile

import app.detector as _det_module
from app.detector           import detect_people, generate_heatmap, \
                                   compute_optical_flow, reset_optical_flow, get_ground_anchors
from app.proximity          import compute_proximity, reset_proximity, GRID_ROWS, GRID_COLS
from app.predictor          import record_zone, forecast_zone, reset_forecast_history
from app.stampede_predictor import get_all_risks, get_officer_alerts, reset_density_history
from app.alerting           import process_alerts, get_alert_history, get_alert_stats, reset_alerts

app = FastAPI(title="CrowdSense AI", version="6.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

video_source = None
is_running   = False


@app.get("/health")
async def health():
    det = _det_module._detector
    return {
        "status":    "running",
        "version":   "6.1",
        "source":    str(video_source),
        "streaming": is_running,
        "cam_mode":  det.mode,
        "model":     det.model_path,
        "sahi":      "OFF",
        "bytetrack": "OFF",
        "passes":    3,
    }


@app.post("/set-mode/{mode}")
async def set_mode(mode: str):
    try:
        _det_module._detector.set_mode(mode)
        return {"status": "ok", "mode": mode}
    except AssertionError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/get-mode")
async def get_mode():
    det = _det_module._detector
    return {
        "mode":       det.mode,
        "calibrated": det._calibrated,
        "model":      det.model_path,
    }


@app.get("/alerts/history")
async def alert_history():
    return {"alerts": get_alert_history(50)}


@app.get("/alerts/stats")
async def alert_stats():
    return get_alert_stats()


@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    global video_source
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.write(await file.read())
    tmp.close()
    video_source = tmp.name

    # Read first frame and auto-calibrate camera mode
    cap = cv2.VideoCapture(tmp.name)
    ret, frame = cap.read()
    cap.release()
    detected_mode = "elevated"   # safe default for crowd scenes
    if ret:
        frame = cv2.resize(frame, (1280, 720))
        detected_mode = _det_module._detector.calibrate(frame)

    return JSONResponse({
        "status":   "ok",
        "message":  f"Uploaded: {file.filename}",
        "cam_mode": detected_mode,
    })


@app.post("/use-webcam")
async def use_webcam():
    global video_source
    video_source = 0
    return JSONResponse({"status": "ok", "message": "Using webcam"})


@app.post("/stop")
async def stop_stream():
    global is_running, video_source
    is_running   = False
    video_source = None
    reset_optical_flow()
    reset_forecast_history()
    reset_density_history()
    reset_proximity()
    reset_alerts()
    _det_module._detector.reset()
    return {"status": "stopped"}


@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    global is_running
    await ws.accept()

    if video_source is None:
        await ws.send_text(json.dumps({"error": "No video source set."}))
        await ws.close()
        return

    cap = cv2.VideoCapture(video_source)
    if video_source == 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS,          30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    if not cap.isOpened():
        await ws.send_text(json.dumps({"error": "Cannot open video source."}))
        await ws.close()
        return

    is_running  = True
    frame_count = 0
    fps_start   = time.time()
    fps_count   = 0
    actual_fps  = 0.0

    try:
        while is_running:
            ret, frame = cap.read()
            if not ret:
                if video_source != 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = cv2.resize(frame, (1280, 720))
            frame_count += 1
            fps_count   += 1

            if fps_count >= 30:
                elapsed    = time.time() - fps_start
                actual_fps = round(fps_count / max(elapsed, 0.001), 1)
                fps_count  = 0
                fps_start  = time.time()

            # Stage 1: Detect (async worker — non-blocking)
            annotated, centers = detect_people(frame.copy(), frame_count)

            # Stage 2: Ground anchors + boxes
            ground_anchors = get_ground_anchors()
            with _det_module._detector._lock:
                boxes = list(_det_module._detector._last_boxes)

            # Stage 3: Proximity + jam analysis
            proximity_result = compute_proximity(
                ground_anchors, boxes, frame_w=1280, frame_h=720
            )

            # Stage 4: Draw jam overlay
            annotated = _draw_proximity_overlay(
                annotated,
                ground_anchors,
                set(proximity_result.get("violating_ids", [])),
                proximity_result.get("jammed_ids", []),
            )

            # Stage 5: Heatmap
            heatmap_frame = generate_heatmap(annotated.copy(), centers)

            # Stage 6: Risk scoring
            all_risks      = get_all_risks(proximity_result, 0.0)
            officer_alerts = get_officer_alerts(all_risks)
            new_alerts     = process_alerts(officer_alerts)

            # Stage 7: Forecast (every 5th frame)
            zone_forecasts = {}
            if frame_count % 5 == 0:
                record_zone("PROXIMITY", proximity_result.get("violating_people", 0))
                result = forecast_zone("PROXIMITY")
                if result:
                    zone_forecasts["PROXIMITY"] = result

            # Stage 8: Encode
            _, buffer = cv2.imencode(".jpg", heatmap_frame,
                                     [cv2.IMWRITE_JPEG_QUALITY, 82])
            frame_b64 = base64.b64encode(buffer).decode("utf-8")

            # Stage 9: Send
            await ws.send_text(json.dumps({
                "frame":            frame_b64,
                "total_people":     proximity_result.get("total_people", 0),
                "violating_people": proximity_result.get("violating_people", 0),
                "jammed_sections":  proximity_result.get("jammed_sections", 0),
                "dwell_frames":     proximity_result.get("dwell_frames", 0),
                "close_pair_count": proximity_result.get("close_pair_count", 0),
                "zone_forecasts":   zone_forecasts,
                "stampede_risks":   all_risks,
                "officer_alerts":   officer_alerts,
                "new_alerts":       new_alerts,
                "highest_risk":     all_risks[0] if all_risks else None,
                "alert_stats":      get_alert_stats(),
                "cam_mode":         _det_module._detector.mode,
                "frame_number":     frame_count,
                "actual_fps":       actual_fps,
            }))

            await asyncio.sleep(0.016)

    except WebSocketDisconnect:
        pass
    finally:
        cap.release()
        is_running = False


def _draw_proximity_overlay(frame, anchors, violating_ids, jammed_ids,
                             frame_w=1280, frame_h=720):
    sw = frame_w // GRID_COLS
    sh = frame_h // GRID_ROWS

    # Red tint on jammed sections
    if jammed_ids:
        overlay = frame.copy()
        for sec_id in jammed_ids:
            row, col = divmod(sec_id, GRID_COLS)
            cv2.rectangle(overlay,
                          (col*sw, row*sh),
                          (col*sw+sw, row*sh+sh),
                          (0, 0, 200), -1)
        cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)

    # Grid lines
    for r in range(1, GRID_ROWS):
        cv2.line(frame, (0, r*sh), (frame_w, r*sh), (40,50,70), 1)
    for c in range(1, GRID_COLS):
        cv2.line(frame, (c*sw, 0), (c*sw, frame_h), (40,50,70), 1)

    # Person anchor dots — red if violating, green if safe
    for idx, pt in enumerate(anchors):
        color = (0,0,255) if idx in violating_ids else (0,220,80)
        cv2.circle(frame, pt, 6, color, -1)
        cv2.circle(frame, pt, 9, color, 1)

    return frame