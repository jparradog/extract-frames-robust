# extract_frames_robust/cli.py

import typer
from extract_frames_robust.core import extraer_y_seleccionar
from rich import print
import os
import re
from pathlib import Path

app = typer.Typer(
    help="Extrae fotogramas óptimos de videos de broncoscopia priorizando nitidez."
)


@app.command()
def extract(
    video: str = typer.Argument(..., help="Ruta del archivo de video"),
    output: str = typer.Option("frames_selected", help="Directorio de salida"),
    stage1_dur: float = typer.Option(
        1.0, help="Duración (s) de segmento de etapa 1 (nitidez)"
    ),
    stage2_dur: float = typer.Option(
        5.0, help="Duración (s) de segmento de etapa 2 (score combinado)"
    ),
    sample_step: int = typer.Option(1, help="Muestreo cada N frames en etapa 1"),
    w_sharp: float = typer.Option(1.0, help="Peso de nitidez en el score de etapa 2"),
    w_red: float = typer.Option(100.0, help="Peso de eritema en el score de etapa 2"),
    w_entropy: float = typer.Option(
        1.0, help="Peso de entropía en el score de la etapa 2"
    ),
    sharp_percentile: float = typer.Option(
        0.1, help="Percentil de nitidez para umbral dinámico en etapa 1 (0-1)"
    ),
    top_n: int = typer.Option(1, help="Número de frames top-N por ventana en etapa 1"),
    stage1_stride: float | None = typer.Option(
        None,
        help="Stride (s) entre ventanas de etapa 1 (por defecto igual a stage1-dur)",
    ),
):
    """
    Extrae fotogramas útiles de un video usando metodología jerárquica (nitidez + eritema).
    """
    extraer_y_seleccionar(
        video_path=video,
        output_dir=output,
        stage1_dur=stage1_dur,
        stage2_dur=stage2_dur,
        sample_step=sample_step,
        w_sharp=w_sharp,
        w_red=w_red,
        w_entropy=w_entropy,
        sharp_percentile=sharp_percentile,
        top_n=top_n,
        stage1_stride=stage1_stride,
    )


@app.command()
def validate(
    videos: list[str] = typer.Argument(..., help="Rutas de videos a validar"),
    gt_dir: str = typer.Option(..., help="Directorio con ground truth .txt por video"),
    output: str = typer.Option(
        "val_frames", help="Directorio para predicciones temporales"
    ),
    stage1_dur: float = typer.Option(1.0, help="Duración etapa1 (s)"),
    stage2_dur: float = typer.Option(4.0, help="Duración etapa2 (s)"),
    sample_step: int = typer.Option(1, help="Muestreo etapa1"),
    w_sharp: float = typer.Option(1.0, help="Peso nitidez"),
    w_red: float = typer.Option(100.0, help="Peso eritema"),
    w_entropy: float = typer.Option(1.0, help="Peso entropía"),
    sharp_percentile: float = typer.Option(0.1, help="Percentil nitidez (0-1)"),
    top_n: int = typer.Option(1, help="Top-N por ventana"),
    stage1_stride: float | None = typer.Option(None, help="Stride etapa1 (s)"),
):
    """
    Valida precision y recall de extracción contra anotaciones (ground truth).
    Cada video debe tener un .txt en gt_dir con índices de frame por línea.
    """
    total_tp = total_pred = total_gt = 0
    for video in videos:
        name = Path(video).stem
        sub_out = os.path.join(output, name)
        # ejecutar extracción
        extraer_y_seleccionar(
            video_path=video,
            output_dir=sub_out,
            stage1_dur=stage1_dur,
            stage2_dur=stage2_dur,
            sample_step=sample_step,
            w_sharp=w_sharp,
            w_red=w_red,
            w_entropy=w_entropy,
            sharp_percentile=sharp_percentile,
            top_n=top_n,
            stage1_stride=stage1_stride,
        )
        # recolectar predicciones
        preds = set()
        for p in Path(sub_out).glob("*.png"):
            m = re.match(r"frame_(\d+)_", p.name)
            if m:
                preds.add(int(m.group(1)))
        # load GT
        gt_file = Path(gt_dir) / (name + ".txt")
        if not gt_file.exists():
            print(f"[WARN] GT faltante para {name}")
            continue
        gts = {
            int(l.strip())
            for l in gt_file.read_text().splitlines()
            if l.strip().isdigit()
        }
        tp = len(preds & gts)
        total_tp += tp
        total_pred += len(preds)
        total_gt += len(gts)
    recall = total_tp / total_gt if total_gt else 0.0
    precision = total_tp / total_pred if total_pred else 0.0
    print(f"Precision: {precision:.3f}, Recall: {recall:.3f}")


if __name__ == "__main__":
    app()
