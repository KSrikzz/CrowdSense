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
from app.detector           import detect_people, generate_heatmap, get_zone_counts, compute_optical_flow, compute_crowd_alert, reset_optical_flow
from app.predictor          import record_zone, forecast_zone, reset_forecast_history
from app.stampede_predictor import get_all_risks, get_officer_alerts, reset_density_history
from app.alerting           import process_alerts, get_alert_history, get_alert_stats, reset_alerts

app = FastAPI(title="CrowdSense AI — Stampede Prediction System", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

video_source = None
is_running   = False


@app.get("/health")
async def health():
    det = _det_module._detector
    return {
        "status":           "running",
        "version":          "4.0",
        "source":           str(video_source),
        "streaming":        is_running,
        "cam_mode":         det.mode,
        "sahi_enabled":     det._sahi_model is not None,
        "model":            det.model_path,
        "unique_ids_seen":  len(det._active_ids),
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
        "mode":         det.mode,
        "calibrated":   det._calibrated,
        "sahi_enabled": det._sahi_model is not None,
        "model":        det.model_path,
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
    return JSONResponse({"status": "ok", "message": f"Uploaded: {file.filename}"})


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
    reset_alerts()
    _det_module._detector.reset()
    return {"status": "stopped", "message": "Stream stopped and all state reset"}


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

            # FPS tracker
            if fps_count >= 30:
                elapsed    = time.time() - fps_start
                actual_fps = round(fps_count / max(elapsed, 0.001), 1)
                fps_count  = 0
                fps_start  = time.time()

            # Stage 1: Detection (async worker — non-blocking)
            annotated, centers = detect_people(frame.copy(), frame_count)
            heatmap_frame      = generate_heatmap(annotated.copy(), centers)
            zone_counts        = get_zone_counts(frame, centers)
            crowd_alert_data   = compute_crowd_alert(zone_counts)

            # Stage 2: Optical flow (every 2nd frame)
            avg_speed, conflict = 0.0, 0.0
            if frame_count % 2 == 0:
                avg_speed, conflict = compute_optical_flow(frame)

            # Stage 3: Stampede risk scoring
            all_risks      = get_all_risks(zone_counts, conflict)
            officer_alerts = get_officer_alerts(all_risks)

            # Stage 4: Alerting
            new_alerts = process_alerts(officer_alerts)

            # Stage 5: Linear trend forecast (every 5th frame, ~2ms)
            zone_forecasts = {}
            if frame_count % 5 == 0:
                for zone, count in zone_counts.items():
                    record_zone(zone, count)
                    result = forecast_zone(zone)
                    if result:
                        zone_forecasts[zone] = result

            # Stage 6: Encode frame
            _, buffer = cv2.imencode(".jpg", heatmap_frame,
                                     [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_b64 = base64.b64encode(buffer).decode("utf-8")

            # Stage 7: Send payload
            await ws.send_text(json.dumps({
                "frame":            frame_b64,
                "total_people":     len(centers),
                "unique_ids_total": len(_det_module._detector._active_ids),
                "avg_speed":        avg_speed,
                "flow_conflict":    conflict,
                "zone_counts":      zone_counts,
                "zone_forecasts":   zone_forecasts,
                "stampede_risks":   all_risks,
                "officer_alerts":   officer_alerts,
                "new_alerts":       new_alerts,
                "highest_risk":     all_risks[0] if all_risks else None,
                "alert_stats":      get_alert_stats(),
                "crowd_alert":      crowd_alert_data["alert"],
                "smoothed_total":   crowd_alert_data["smoothed_total"],
                "zones_smoothed":   crowd_alert_data["zones_smoothed"],
                "cam_mode":         _det_module._detector.mode,
                "sahi_enabled":     _det_module._detector._sahi_model is not None,
                "frame_number":     frame_count,
                "actual_fps":       actual_fps,
            }))

            await asyncio.sleep(0.016)

    except WebSocketDisconnect:
        pass
    finally:
        cap.release()
        is_running = False
