from __future__ import annotations

from pathlib import Path
from urllib.parse import quote


COMPUTER_CONTROL_ARTIFACT_ROOT = (
    Path(__file__).resolve().parents[4] / ".run_logs" / "computer_control"
)
COMPUTER_CONTROL_ARTIFACT_ROUTE = "/computer-control-artifacts"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def artifact_url_for_path(path: str | Path | None) -> str | None:
    if not path:
        return None

    try:
        candidate = Path(path).expanduser().resolve()
        root = COMPUTER_CONTROL_ARTIFACT_ROOT.resolve()
        relative = candidate.relative_to(root)
    except (OSError, ValueError):
        return None

    if candidate.suffix.lower() not in IMAGE_SUFFIXES or not candidate.is_file():
        return None

    return f"{COMPUTER_CONTROL_ARTIFACT_ROUTE}/{quote(relative.as_posix())}"
