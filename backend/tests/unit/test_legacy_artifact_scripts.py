from pathlib import Path


def test_legacy_s3_artifact_scripts_are_not_supported_entrypoints():
    scripts = Path(__file__).parents[2] / "scripts"
    assert not (scripts / "upload_artifacts.py").exists()
    assert not (scripts / "verify_models.py").exists()
    assert (scripts / "lambda_preflight.sh").is_file()
