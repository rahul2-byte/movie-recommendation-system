from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_lambda_image_and_sam_template_configure_the_model_bundle_contract():
    dockerfile = (ROOT / "backend" / "Dockerfile.lambda").read_text()
    template = (ROOT / "template.yaml").read_text()

    assert "ARG MODEL_BUNDLE_PATH" in dockerfile
    for package in (
        "main.py",
        "api/",
        "common/",
        "configs/",
        "features/",
        "logger/",
        "pipeline/",
        "ranking/",
        "retrieval/",
        "serving/",
    ):
        assert f"COPY backend/{package}" in dockerfile
    assert "COPY ${MODEL_BUNDLE_PATH}/ ${LAMBDA_TASK_ROOT}/model_bundle/" in dockerfile
    assert 'ENV MODEL_BUNDLE_DIR="/var/task/model_bundle"' in dockerfile
    assert "MODEL_BUNDLE_DIR: /var/task/model_bundle" in template
