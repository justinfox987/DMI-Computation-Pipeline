"""Small JSON evidence store: atomic writes, byte hashes and dump provenance."""

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


def check_files(files: dict[str, str], root: str | Path | None = None) -> None:
    """Raise unless every file still has its recorded hash; relative paths resolve against root."""
    if not files:
        raise ValueError("Completion evidence has no input hashes")
    for name, expected in files.items():
        path = Path(root) / name if root is not None else Path(name)
        if file_hash(path) != expected:
            raise ValueError(f"Input changed since validation: {name}")


def require_done(directory: str | Path, kind: str, root: str | Path) -> dict:
    """The passing provenance.json of one dump directory, with its hashes rechecked."""
    directory, root = Path(directory), Path(root)
    record = load(directory / "provenance.json")
    if record.get("kind") != kind or record.get("passed") is not True:
        raise ValueError(f"{directory}/provenance.json has no passing {kind} evidence: {record.get('error')}")
    check_files(record.get("files", {}), root)
    actual = {str(p.relative_to(root)) for p in directory.glob("CPROJ.*.bin")}
    recorded = {p for p in record["files"] if Path(p).name.startswith("CPROJ.")}
    if actual != recorded:
        raise ValueError("CPROJ rank-file set changed since finish")
    return record
