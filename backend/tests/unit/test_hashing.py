import hashlib
from pathlib import Path

from hashing import sha256


def test_sha256_hashes_file_bytes_in_chunks(tmp_path: Path):
    payload = b"movie-recs" * 200_000
    path = tmp_path / "artifact.bin"
    path.write_bytes(payload)

    assert sha256(path) == hashlib.sha256(payload).hexdigest()
