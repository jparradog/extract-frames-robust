# extract_frames_robust/core.py

import heapq
import math
import os
from datetime import datetime

import cv2
import numpy as np
from tqdm import tqdm


def calcular_nitidez(frame: np.ndarray) -> float:
    """
    Calcula la varianza del Laplaciano (nitidez) de un frame.
    """
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gris, cv2.CV_64F)
    return float(lap.var())


def calcular_ratio_rojo(frame: np.ndarray) -> float:
    """
    Calcula proporción de píxeles en tonos rojos (eritema aproximado).
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, (0, 30, 50), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (160, 30, 50), (180, 255, 255))
    mask = cv2.bitwise_or(mask1, mask2)
    return float(np.count_nonzero(mask)) / mask.size


def calcular_entropia(frame: np.ndarray) -> float:
    """
    Calcula la entropía de Shannon de la luminancia del frame.
    """
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hist = np.bincount(gris.flatten(), minlength=256)
    prob = hist / hist.sum() if hist.sum() > 0 else hist
    prob = prob[prob > 0]
    entropy = -(prob * np.log2(prob)).sum() if prob.size > 0 else 0.0
    return float(entropy)


def extraer_y_seleccionar(
    video_path: str,
    output_dir: str,
    stage1_dur: float = 1.0,
    stage2_dur: float = 4.0,
    sample_step: int = 1,
    w_sharp: float = 1.0,
    w_red: float = 100.0,
    w_entropy: float = 1.0,
    sharp_percentile: float = 0.1,
    top_n: int = 1,
    stage1_stride: float | None = None,
):
    """
    Extracción jerárquica de fotogramas relevantes en dos etapas:
    1. Divide el video en segmentos cortos (stage1_dur), selecciona los top-N frames
       más nítidos de cada uno.
    2. Agrupa los seleccionados en segmentos más largos (stage2_dur) y selecciona
       por score combinado.
    Los fotogramas se almacenan en una subcarpeta con el nombre base del video y la
    fecha de generación.
    """
    # Crear subcarpeta historial: <output_dir>/<nombre_video>_<YYYYmmdd_HHMMSS>
    base_video = os.path.splitext(os.path.basename(video_path))[0]
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    historial_dir = os.path.join(output_dir, f"{base_video}_{fecha}")
    os.makedirs(historial_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    # Validación de video
    if not os.path.isfile(video_path):
        print("[WARN] El archivo de video no existe: {}".format(video_path))
        return
    if total_frames == 0 or duration == 0:
        print(
            "[ERROR] El video no contiene frames o está corrupto: {}".format(video_path)
        )
        return

    # Etapa 1: extracción con ventanas solapadas, top-N candidatos y muestreo adaptativo
    if stage1_stride is None or stage1_stride <= 0:
        stage1_stride = stage1_dur
    if stage1_stride > stage1_dur:
        stage1_stride = stage1_dur
    if duration <= stage1_dur:
        starts = [0.0]
    else:
        count = int(math.ceil((duration - stage1_dur) / stage1_stride)) + 1
        starts = [i * stage1_stride for i in range(count)]
    frames_info = []
    sample_step_current = sample_step
    for start_t in tqdm(starts, desc="[1/3] Selección por nitidez", unit="ventana"):
        start_f = int(start_t * fps)
        end_f = int(min(total_frames, (start_t + stage1_dur) * fps))
        heap = []
        frames_window: list[tuple[float, int]] = []
        sharp_list = []
        # recolectar nitidez en la ventana
        for f_idx in range(start_f, end_f, sample_step_current):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            sharp = calcular_nitidez(frame)
            frames_window.append((sharp, f_idx))
            sharp_list.append(sharp)
            if len(heap) < top_n:
                heapq.heappush(heap, (sharp, f_idx))
            elif sharp > heap[0][0]:
                heapq.heapreplace(heap, (sharp, f_idx))
        # Selección por percentil de nitidez (umbral dinámico)
        if 0 < sharp_percentile < 1:
            arr = np.array(sharp_list)
            thr_val = float(np.percentile(arr, 100 * (1 - sharp_percentile)))
            thr_cand = [(s, idx) for s, idx in frames_window if s >= thr_val]
            candidatos_ventana = thr_cand if thr_cand else heap
        else:
            candidatos_ventana = heap
        # agregar candidatos de la ventana
        for sharp_val, f_idx in candidatos_ventana:
            time_sec = f_idx / fps
            frames_info.append({"frame": f_idx, "sharp": sharp_val, "time": time_sec})
        # ajustar muestreo para siguiente ventana
        if sharp_list:
            best_sharp = max(sharp_list)
            var_sharp = float(np.var(sharp_list))
            low_th = best_sharp * 0.1
            high_th = best_sharp * 0.5
            if var_sharp > high_th:
                sample_step_current = max(1, sample_step_current // 2)
            elif var_sharp < low_th:
                sample_step_current *= 2

    if not frames_info:
        print("[ERROR] No se pudieron extraer frames candidatos del video.")
        return

    # Pre-cargar eritema y entropía para cada candidato
    for f in tqdm(
        frames_info, desc="[2/3] Cálculo de eritema y entropía", unit="frame"
    ):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f["frame"]))
        ret, frame = cap.read()
        f["red"] = calcular_ratio_rojo(frame) if ret else 0.0
        f["entropy"] = calcular_entropia(frame) if ret else 0.0

    # Etapa 2: agrupar en segmentos largos y seleccionar por score
    resultados = []
    total_groups = math.ceil((frames_info[-1]["time"]) / stage2_dur)
    for g in range(total_groups):
        start_t = g * stage2_dur
        end_t = start_t + stage2_dur
        candidatos = [f for f in frames_info if start_t <= f["time"] < end_t]
        if not candidatos:
            # Fallback: keyframe medio del segmento
            mid_t = start_t + stage2_dur / 2
            mid_idx = int(mid_t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_idx)
            ret, frame_mid = cap.read()
            if ret:
                sharp_mid = calcular_nitidez(frame_mid)
                red_mid = calcular_ratio_rojo(frame_mid)
                ent_mid = calcular_entropia(frame_mid)
                candidatos = [
                    {
                        "frame": mid_idx,
                        "sharp": sharp_mid,
                        "red": red_mid,
                        "entropy": ent_mid,
                        "fallback": True,
                        "time": mid_t,
                    }
                ]
            else:
                continue
        best = None
        best_score = -float("inf")
        for f in candidatos:
            score = (
                w_sharp * f["sharp"]
                + w_red * f["red"]
                + w_entropy * f.get("entropy", 0.0)
            )
            if score > best_score:
                best_score = score
                best = f
        if best:
            resultados.append(best)

    if not resultados:
        print("[ERROR] No se seleccionaron frames finales para guardar.")
        return

    # Guardar frames seleccionados
    for i, f in enumerate(
        tqdm(resultados, desc="[3/3] Guardando frames", unit="frame"), start=1
    ):
        idx = int(f["frame"])
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        ts = int(f["time"])
        sharp_val = int(f["sharp"])
        red_val = int(f["red"] * 100)
        entropy_val = int(f["entropy"])
        name = (
            f"frame_{idx: 06d}_t{ts: 04d}_sharp{sharp_val}_red{red_val}_"
            f"entropy{entropy_val}.png"
        )  # E231 fixed: whitespace after ':'
        path = os.path.join(historial_dir, name)
        cv2.imwrite(path, frame)

        print(f"Guardado: {os.path.relpath(path)}")

    cap.release()
