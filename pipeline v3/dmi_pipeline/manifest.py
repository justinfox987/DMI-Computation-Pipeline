"""Small JSON helpers. plan.json and config.json are inputs written by prepare;
every other JSON file is a report that no command reads back (D-021)."""

from hashlib import sha256
import json
from pathlib import Path


def load(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return value


def save(value: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def file_hash(path: str | Path) -> str:
    """SHA-256 of the job script, quoted in the generated Slurm array."""
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
