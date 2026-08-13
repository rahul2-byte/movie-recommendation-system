from pathlib import Path


def test_lambda_image_copies_only_tracked_runtime_paths():
    dockerfile = (Path(__file__).parents[2] / "Dockerfile.lambda").read_text()

    assert "COPY backend/pipeline/" not in dockerfile
    assert "COPY backend/ranking/" not in dockerfile
    assert "COPY backend/features/" not in dockerfile
    assert "yum install -y gcc gcc-c++ make" in dockerfile
    for path in (
        "main.py",
        "api/",
        "common/",
        "configs/",
        "logger/",
        "retrieval/",
        "serving/",
    ):
        assert f"COPY backend/{path}" in dockerfile
