# Extract Frames Robust

[![CI](https://github.com/jparradog/extract-frames-robust/actions/workflows/ci.yml/badge.svg)](https://github.com/jparradog/extract-frames-robust/actions/workflows/ci.yml)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](LICENSE)

Extract Frames Robust es una herramienta moderna para extraer automáticamente los fotogramas más clínicamente útiles de videos de broncoscopia, priorizando la nitidez y relevancia del contenido.

## Tabla de Contenidos
- [Extract Frames Robust](#extract-frames-robust)
  - [Tabla de Contenidos](#tabla-de-contenidos)
  - [Requisitos previos](#requisitos-previos)
  - [Instalación](#instalación)
  - [Uso rápido](#uso-rápido)
  - [Parámetros principales](#parámetros-principales)
  - [Ejemplo paso a paso](#ejemplo-paso-a-paso)
    - [Ejemplo con parámetros avanzados](#ejemplo-con-parámetros-avanzados)
  - [Validación cuantitativa](#validación-cuantitativa)
  - [Contributing](#contributing)
  - [Changelog](#changelog)
  - [Seguridad](#seguridad)
  - [License](#license)
  - [Créditos](#créditos)
  - [Ejecución](#ejecución)

## Requisitos previos

- Python 3.12 o superior
- [Poetry](https://python-poetry.org/docs/#installation) para gestión de dependencias

## Instalación

Clona este repositorio y ejecuta:

```bash
git clone https://github.com/jparradog/extract-frames-robust.git
cd extract-frames-robust
poetry install
```

## Uso rápido

La herramienta provee un comando CLI llamado `extract-frames` para extraer automáticamente los mejores fotogramas de un video:

```bash
poetry run extract-frames extract <video.mp4> [opciones]
```

Ejemplo básico:

```bash
poetry run extract-frames extract broncoscopia.mp4 --output resultados_frames
```

## Parámetros principales

- `video` (argumento): Ruta del archivo de video a procesar.
- `--output`: Carpeta donde se guardarán los fotogramas seleccionados (por defecto: `frames_selected`).
- `--stage1-dur`: Duración (en segundos) de los segmentos cortos para la primera etapa de selección por nitidez (por defecto: 1.0).
- `--stage2-dur`: Duración (en segundos) de los segmentos largos para la segunda etapa de selección jerárquica por score combinado (por defecto: 5.0).
- `--sample-step`: Muestreo cada N frames en la etapa 1 (por defecto: 1).
- `--w-sharp`: Peso de la nitidez en el score de la etapa 2 (por defecto: 1.0).
- `--w-red`: Peso del eritema en el score de la etapa 2 (por defecto: 100.0).
- `--w-entropy`: Peso de la entropía en el score de la etapa 2 (por defecto: 1.0).
- `--top-n`: Número de frames top-N por ventana en la etapa 1 (por defecto: 1).
- `--stage1-stride`: Stride (s) entre ventanas de la etapa 1 (por defecto: igual a `stage1-dur`).
- `--sharp-percentile`: Percentil de nitidez para umbral dinámico en la etapa 1 (0-1, por defecto: 0.1).

## Ejemplo paso a paso

1. Instala dependencias:

```bash
poetry install
```

1. Ejecuta la extracción sobre tu video:

```bash
poetry run extract-frames extract tu_video.mp4 --output frames_resultado
```

1. Los fotogramas seleccionados aparecerán en la carpeta indicada.

### Ejemplo con parámetros avanzados

Puedes ajustar la granularidad y criterios de selección jerárquica usando los nuevos parámetros:

```bash
poetry run extract-frames extract tu_video.mp4 \
  --output frames_resultado \
  --stage1-dur 2 \
  --stage1-stride 1 \
  --top-n 3 \
  --stage2-dur 8 \
  --sample-step 2 \
  --w-sharp 1.0 \
  --w-red 200.0 \
  --sharp-percentile 0.2
```

Esto dividirá el video en segmentos de 2 segundos para la primera etapa (selección del frame más nítido por segmento), luego agrupará esos candidatos en bloques de 8 segundos y seleccionará el mejor por score combinado (nitidez + eritema).

## Validación cuantitativa

La herramienta incluye el comando `validate` para medir Precision y Recall comparando los fotogramas seleccionados
con anotaciones manuales (ground truth). Cada video requiere un archivo `.txt` en el directorio de GT,
con índices de frame válidos, uno por línea.

Uso:

```bash
poetry run extract-frames validate video1.mp4 video2.mp4 \
  --gt-dir ground_truth_dir \
  --output val_frames \
  --stage1-dur 2 \
  --sharp-percentile 0.1 \
  --top-n 2 \
  --stage1-stride 1 \
  --stage2-dur 8 \
  --w-sharp 1.0 \
  --w-red 200.0 \
  --w-entropy 1.5
```

El comando imprime Precision y Recall agregados tras procesar todos los videos.

## Contributing
Lee [CONTRIBUTING.md](CONTRIBUTING.md) para detalles sobre cómo contribuir.

## Changelog
Consulta el historial de versiones en [CHANGELOG.md](CHANGELOG.md).

## Seguridad
Para reportar vulnerabilidades, revisa [SECURITY.md](SECURITY.md).

## License
Este proyecto está bajo la licencia [MPL 2.0](LICENSE).

## Créditos

Autor: John Parrado (<japarradog@gmail.com>)

## Ejecución

Para extraer fotogramas desde la CLI:

```bash
poetry run extract-frames extract <video.mp4> --output <directorio_destino> [--opciones]
```

Para ejecutar el test de integración:

```bash
poetry run pytest -q
```

**Ejemplo completo:**

```bash
poetry run extract-frames extract broncoscopia.mp4 --output resultados_frames --stage1-dur 2 \
  --sharp-percentile 0.1 --top-n 3 --stage1-stride 1 --stage2-dur 8 \
  --sample-step 2 --w-sharp 1.0 --w-red 200.0 --w-entropy 1.5
poetry run pytest -q
