"""
ViralClipper AI Studio - Video Analysis Module
Performs scene boundary detection, face detection for 9:16 vertical reframing,
visual motion energy calculation, and keyframe extraction with OpenCV.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from pydantic import BaseModel, Field

from src.config import TEMP_DIR


class VideoProperties(BaseModel):
    width: int
    height: int
    fps: float
    duration: float
    total_frames: int


class FaceBox(BaseModel):
    x: int
    y: int
    w: int
    h: int
    confidence: float = 1.0


class SceneChange(BaseModel):
    timestamp: float
    frame_index: int
    score: float


def get_video_properties(video_path: str) -> VideoProperties:
    """Reads basic video metadata using OpenCV."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0.0
    cap.release()

    return VideoProperties(
        width=width,
        height=height,
        fps=fps,
        duration=duration,
        total_frames=total_frames
    )


def detect_scene_changes(
    video_path: str,
    threshold: float = 0.35,
    sample_fps: float = 2.0
) -> List[SceneChange]:
    """
    Detects shot and scene cuts by comparing HSV color histograms of sampled frames.
    sample_fps=2.0 evaluates 2 frames per second for high performance on long-form video.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_step = max(1, int(fps / sample_fps))

    prev_hist = None
    changes: List[SceneChange] = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_step == 0:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

            if prev_hist is not None:
                dist = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                if dist > threshold:
                    t = round(frame_idx / fps, 2)
                    changes.append(SceneChange(timestamp=t, frame_index=frame_idx, score=float(dist)))
            prev_hist = hist

        frame_idx += 1

    cap.release()
    return changes


def detect_faces_in_frame(frame: np.ndarray) -> List[FaceBox]:
    """
    Detects faces or active speaker head regions in a frame.
    Supports Haar cascades where available, with a fast HSV facial skin-tone
    saliency tracker compatible with OpenCV 5.0+.
    """
    boxes: List[FaceBox] = []

    # 1. Try OpenCV CascadeClassifier if available
    if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=4, minSize=(40, 40))
            for (x, y, w, h) in faces:
                boxes.append(FaceBox(x=int(x), y=int(y), w=int(w), h=int(h)))
            if boxes:
                return boxes
        except Exception:
            pass

    # 2. HSV Facial Skin-Tone & Saliency Contour Detector (robust cross-platform fallback)
    try:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 25, 50], dtype=np.uint8)
        upper_skin = np.array([25, 180, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h_img, w_img = frame.shape[:2]
        min_area = (w_img * h_img) * 0.005
        for c in contours:
            area = cv2.contourArea(c)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(c)
                aspect = h / float(w)
                if 0.7 <= aspect <= 2.5:
                    boxes.append(FaceBox(x=int(x), y=int(y), w=int(w), h=int(h)))
    except Exception:
        pass

    return boxes


def calculate_optimal_crop_center(
    video_path: str,
    start_time: float,
    end_time: float,
    num_samples: int = 6
) -> float:
    """
    Samples frames across a clip window, detects faces, and returns the optimal
    horizontal center (normalized 0.0 to 1.0) for vertical 9:16 cropping.
    Defaults to 0.5 (center) if no faces are detected.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return 0.5

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920.0
    sample_times = np.linspace(start_time, end_time, num_samples)

    centers: List[float] = []

    for t in sample_times:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ret, frame = cap.read()
        if not ret:
            continue
        faces = detect_faces_in_frame(frame)
        if faces:
            best_face = max(faces, key=lambda f: f.w * f.h)
            face_center_x = (best_face.x + best_face.w / 2.0) / width
            centers.append(face_center_x)

    cap.release()

    if not centers:
        return 0.5

    optimal_center = float(np.median(centers))
    return float(np.clip(optimal_center, 0.25, 0.75))


def extract_keyframe(
    video_path: str,
    timestamp: float,
    output_path: Optional[str] = None
) -> str:
    """Extracts a representative video frame at a given timestamp and saves to disk."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video for keyframe extraction: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(timestamp * fps))
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    out_file = output_path or str(TEMP_DIR / f"keyframe_{int(timestamp * 1000)}.jpg")
    cv2.imwrite(out_file, frame)
    return out_file


def compute_visual_energy(
    video_path: str,
    start_time: float,
    end_time: float,
    num_samples: int = 8
) -> float:
    """Computes visual motion energy across a clip (0.0 to 1.0)."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return 0.5

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    sample_frames = [int(t * fps) for t in np.linspace(start_time, end_time, num_samples)]

    diffs = []
    prev_gray = None

    for f_idx in sample_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        if not ret:
            continue
        small = cv2.resize(frame, (160, 90))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = np.mean(cv2.absdiff(prev_gray, gray))
            diffs.append(diff)
        prev_gray = gray

    cap.release()

    if not diffs:
        return 0.5

    avg_diff = float(np.mean(diffs))
    return float(np.clip(avg_diff / 25.0, 0.0, 1.0))
