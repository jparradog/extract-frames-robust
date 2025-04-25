import os
import tempfile
import cv2
import numpy as np
import pytest
from pathlib import Path
from typer.testing import CliRunner
from extract_frames_robust.cli import app

# Helper to create a synthetic test video
def create_test_video(path: str, frame_count: int = 20, size=(100, 100)) -> None:
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(path, fourcc, 10.0, size)
    
    # Create frames with varying sharpness and red content
    for i in range(frame_count):
        # Base image
        img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        
        # Add index text - make some frames sharper than others
        thickness = 2 if i % 3 == 0 else 1  # Vary text thickness for sharpness
        font_scale = 1.0 if i % 5 == 0 else 0.8
        cv2.putText(img, f"Frame {i}", (10, size[1]//2), cv2.FONT_HERSHEY_SIMPLEX, 
                    font_scale, (255, 255, 255), thickness)
        
        # Add red content to some frames (for eritema detection)
        if i % 4 == 0:  # Every 4th frame has significant red content
            # Create a red circular region (HSV: reddish hue)
            center = (size[0] // 2, size[1] // 2)
            radius = min(size) // 4
            cv2.circle(img, center, radius, (0, 0, 255), -1)  # Filled red circle
        
        # Add some high-frequency details to certain frames (helps with sharpness)
        if i % 3 == 1:
            for x in range(0, size[0], 8):
                for y in range(0, size[1], 8):
                    if (x + y) % 16 == 0:
                        cv2.rectangle(img, (x, y), (x+3, y+3), (255, 255, 255), 1)
        
        # Apply blur to some frames to further vary sharpness
        if i % 5 != 0:  # Keep every 5th frame very sharp
            blur_amount = (i % 4) + 1
            img = cv2.GaussianBlur(img, (blur_amount*2+1, blur_amount*2+1), 0)
            
        writer.write(img)
    writer.release()

@pytest.fixture
def temp_workspace():
    # Create temp directory in the current project directory to avoid cross-drive issues
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_dir = tempfile.mkdtemp(dir=current_dir)
    temp_path = Path(temp_dir)
    
    # setup temporary workspace with video and directories
    video_path = temp_path / "test.avi"
    create_test_video(str(video_path))
    out_dir = temp_path / "out"
    gt_dir = temp_path / "gt"
    out_dir.mkdir()
    gt_dir.mkdir()
    
    try:
        yield temp_path, str(video_path), str(out_dir), str(gt_dir)
    finally:
        # Clean up the temp directory after the test
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_extract_and_validate(temp_workspace):
    tmp_path, video, out_dir, gt_dir = temp_workspace
    runner = CliRunner()
    
    print("\n=== Starting extract process ===")
    # Run extract
    result = runner.invoke(app, ["extract", video, "--output", out_dir, "--top-n", "2", "--stage1-stride", "0.5"])
    assert result.exit_code == 0, result.stdout
    print(f"Extract result: {result.stdout}")

    # Check output folder structure
    # Should contain one subfolder
    subs = list(Path(out_dir).iterdir())
    assert len(subs) == 1, f"Expected 1 subfolder, found {len(subs)}: {subs}"
    imgs = list(subs[0].glob("*.png"))
    assert imgs, "No se generaron imágenes de salida"
    
    print(f"\n=== Generated frames: {len(imgs)} ===")
    for img in imgs:
        print(f"Frame file: {img.name}")
    
    # Parse frame indices correctly from the filename format: frame_XXXXXX_...
    frame_indices = []
    for img in imgs:
        parts = img.name.split('_')
        # Extract the index from the 'frameXXXXXX' part
        if len(parts) >= 2 and parts[0] == 'frame':
            frame_idx = int(parts[1])
            frame_indices.append(frame_idx)
            print(f"Extracted frame index: {frame_idx}")
    
    print(f"\n=== Creating ground truth file with indices: {frame_indices} ===")
    # Create GT matching all generated frames
    gt_file = Path(gt_dir) / (Path(video).stem + ".txt")
    with open(gt_file, 'w') as f:
        for idx in frame_indices:
            f.write(f"{idx}\n")
    
    # Also verify the ground truth file content
    with open(gt_file, 'r') as f:
        gt_content = f.read().strip()
        print(f"Ground truth file content: {gt_content}")

    print("\n=== Running validation ===")
    # Run validate
    result_val = runner.invoke(app, ["validate", video, "--gt-dir", gt_dir, "--output", os.path.join(out_dir, 'val')])
    assert result_val.exit_code == 0, result_val.stdout
    print(f"Validation result: {result_val.stdout}")
    
    # Adjust expectations if needed
    assert "Precision:" in result_val.stdout
    assert "Recall:" in result_val.stdout
