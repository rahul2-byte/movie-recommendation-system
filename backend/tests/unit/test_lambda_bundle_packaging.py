from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_lambda_image_and_sam_template_configure_the_model_bundle_contract():
    dockerfile = (ROOT / "backend" / "Dockerfile.lambda").read_text()
    template = (ROOT / "template.yaml").read_text()
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
    preflight = (ROOT / "backend" / "scripts" / "lambda_preflight.sh").read_text()

    assert "ARG MODEL_BUNDLE_PATH" in dockerfile
    for package in (
        "main.py",
        "api/",
        "common/",
        "configs/",
        "logger/",
        "retrieval/",
        "serving/",
    ):
        assert f"COPY backend/{package}" in dockerfile
    for retired in ("features/", "pipeline/", "ranking/"):
        assert f"COPY backend/{retired}" not in dockerfile
    assert "COPY ${MODEL_BUNDLE_PATH}/ ${LAMBDA_TASK_ROOT}/model_bundle/" in dockerfile
    assert (
        "RUN test -f ${LAMBDA_TASK_ROOT}/model_bundle/bundle_manifest.json"
        in dockerfile
    )
    assert 'ENV MODEL_BUNDLE_DIR="/var/task/model_bundle"' in dockerfile
    assert "MODEL_BUNDLE_DIR: /var/task/model_bundle" in template
    assert "S3BucketName:" not in template
    assert "S3ReadPolicy" not in template
    assert "S3_ARTIFACT_BUCKET" not in template
    assert (
        "MODEL_BUNDLE_PATH: backend/model_bundle/movielens-32m-4retriever-ranker-v1"
        in workflow
    )
    assert 'test -f "$MODEL_BUNDLE_PATH/bundle_manifest.json"' in workflow
    assert "--build-arg MODEL_BUNDLE_PATH=$MODEL_BUNDLE_PATH" in workflow
    assert "astral-sh/setup-uv@v5" in workflow
    assert "uv sync --frozen" in workflow
    assert "uv run --frozen ruff check backend" in workflow
    assert "PYTHONPATH=backend uv run --frozen pytest -q" in workflow
    assert "S3BucketName=" not in workflow
    assert "S3_ARTIFACT_BUCKET" not in preflight
    assert (
        'MODEL_BUNDLE_PATH="${MODEL_BUNDLE_PATH:-backend/model_bundle/movielens-32m-4retriever-ranker-v1}"'
        in preflight
    )
    assert 'test -f "$MODEL_BUNDLE_PATH/bundle_manifest.json"' in preflight
    assert "--build-arg MODEL_BUNDLE_PATH=$MODEL_BUNDLE_PATH" in preflight
    assert preflight.index(
        'test -f "$MODEL_BUNDLE_PATH/bundle_manifest.json"'
    ) < preflight.index("trap cleanup EXIT")
