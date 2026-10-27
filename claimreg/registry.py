"""Load claims and vocabularies from a registry checkout."""
import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Claim:
    path: Path
    data: dict

    @property
    def id(self):
        return self.data.get("id")


@dataclass
class Registry:
    root: Path
    claims: dict          # id (or file stem if id is missing) -> Claim
    families: dict        # family name -> {"versions": [...], "parent": ...}
    task_families: set
    load_errors: list     # (path, message) for files that could not be parsed


def is_stale(claim, today=None):
    """True when `today` (default: the current date) is past the claim's review_by date."""
    review_by = claim.data.get("review_by")
    if not isinstance(review_by, dt.date):      # missing or malformed; `validate` reports it
        return False
    return (today or dt.date.today()) > review_by


def load(root="."):
    root = Path(root)
    families = yaml.safe_load((root / "vocab/model-families.yaml").read_text()) or {}
    tasks = set(yaml.safe_load((root / "vocab/task-families.yaml").read_text()) or [])
    claims, errors = {}, []
    for path in sorted((root / "claims").rglob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as e:
            errors.append((path, f"invalid YAML: {e}"))
            continue
        if not isinstance(data, dict):
            errors.append((path, "file is not a YAML mapping"))
            continue
        key = data.get("id") or path.stem
        if key in claims:
            errors.append((path, f"duplicate id {key!r} (also in {claims[key].path})"))
            continue
        claims[key] = Claim(path, data)
    return Registry(root, claims, families, tasks, errors)
