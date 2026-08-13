from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_lambda_image_and_sam_template_configure_the_model_bundle_contract():
    dockerfile = (ROOT / "backend" / "Dockerfile.lambda").read_text()
    template = (ROOT / "template.yaml").read_text()

    assert "ARG MODEL_BUNDLE_PATH" in dockerfile
    assert "COPY main.py ${LAMBDA_TASK_ROOT}/" in dockerfile
    assert "COPY serving/ ${LAMBDA_TASK_ROOT}/serving/" in dockerfile
    assert "COPY ${MODEL_BUNDLE_PATH}/ ${LAMBDA_TASK_ROOT}/model_bundle/" in dockerfile
    assert 'ENV MODEL_BUNDLE_DIR="/var/task/model_bundle"' in dockerfile
    assert "MODEL_BUNDLE_DIR: /var/task/model_bundle" in template
