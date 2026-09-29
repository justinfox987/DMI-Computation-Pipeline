"""Small JSON evidence store for the N0 milestone; atomic writes and byte hashes."""

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile


def load(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return value


def save(value: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, allow_nan=False) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def file_hash(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprints(paths) -> dict[str, str]:
    return {str(Path(path).resolve()): file_hash(path) for path in paths}


def check_files(files: dict[str, str]) -> None:
    if not files:
        raise ValueError("Completion evidence has no input hashes")
    for name, expected in files.items():
        if file_hash(name) != expected:
            raise ValueError(f"Input changed since validation: {name}")


def require_done(directory: str | Path, kind: str) -> dict:
    directory = Path(directory)
    if (directory / "FAILED").exists():
        raise ValueError(f"{directory} has a FAILED marker; rerun finish after fixing the cause")
    record = load(directory / "DONE")
    if record.get("kind") != kind or record.get("passed") is not True:
        raise ValueError(f"{directory}/DONE has no passing {kind} evidence")
    check_files(record.get("files", {}))
    if kind == "dump_P":
        actual = {str(p.resolve()) for p in directory.glob("CPROJ.*.bin")}
        recorded = {p for p in record["files"] if Path(p).name.startswith("CPROJ.")}
        if actual != recorded:
            raise ValueError("CPROJ rank-file set changed since W0")
    return record
