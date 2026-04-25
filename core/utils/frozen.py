import shutil
import stat
import hashlib
from pathlib import Path
import copy
import yaml
import re
from itertools import product


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def freeze_study_yaml(source_yaml: Path, runs_root: Path):
    source_yaml = Path(source_yaml)
    runs_root = Path(runs_root)

    frozen_path = runs_root / "frozen_study.yaml"

    if frozen_path.exists():
        raise RuntimeError("Frozen study.yaml already exists.")

    shutil.copy2(source_yaml, frozen_path)

    frozen_path.chmod(stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)

    return frozen_path


def get_latest_frozen(runs_root: Path) -> tuple[int, Path]:

    base = runs_root / "frozen_study.yaml"

    if not base.exists():
        raise RuntimeError("No frozen_study.yaml found.")

    revisions = [base]

    for f in runs_root.glob("frozen_study.rev*.yaml"):
        revisions.append(f)

    def revision_number(path):
        match = re.search(r"\.rev(\d+)\.yaml$", path.name)
        if match:
            return int(match.group(1))
        return 0

    latest = max(revisions, key=revision_number)
    return revision_number(latest), latest


def handle_resume_with_revisioning(source_yaml: Path, runs_root: Path):

    latest_rev, frozen_path = get_latest_frozen(runs_root)

    src = load_yaml(source_yaml)
    frozen = load_yaml(frozen_path)

    if src == frozen:
        print(f"Resuming with frozen revision {latest_rev}.")
        return

    # -----------------------------
    # Extract sections
    # -----------------------------
    src_parametric = src.get("parametric", {})
    frozen_parametric = frozen.get("parametric", {})

    src_ensemble = src.get("ensemble", {})
    frozen_ensemble = frozen.get("ensemble", {})

    frozen_plot = frozen.get("plot", {})
    frozen_metrics = frozen.get("metrics", {})
    frozen_artifacts = frozen.get("artifacts", {})

    # -----------------------------
    # Enforce non-parametric identity
    # -----------------------------
    src_copy = dict(src)
    src_copy["parametric"] = frozen_parametric
    src_copy["ensemble"] = frozen_ensemble
    src_copy["plot"] = frozen_plot
    src_copy["metrics"] = frozen_metrics
    src_copy["artifacts"] = frozen_artifacts

    if src_copy != frozen:
        raise RuntimeError(
            "study.yaml differs outside allowed parametric extension."
        )

    # -----------------------------
    # Validate parametric extension
    # -----------------------------
    if not parametric_extension_allowed(frozen_parametric, src_parametric):
        raise RuntimeError("Invalid parametric modification.")

    # -----------------------------
    # Validate ensemble extension (unchanged logic)
    # -----------------------------
    if not sweep_extension_allowed(frozen_ensemble, src_ensemble):
        raise RuntimeError("Invalid ensemble modification.")

    # -----------------------------
    # Create new revision
    # -----------------------------
    new_rev = latest_rev + 1
    new_path = runs_root / f"frozen_study.rev{new_rev}.yaml"

    with open(new_path, "w") as f:
        yaml.safe_dump(src, f)

    print(f"Parameter domain extended. Created revision {new_rev}.")


def load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ============================================================
# New: Case-based parametric validation
# ============================================================

def parametric_extension_allowed(old_cfg, new_cfg):

    # Require identical non-variable structure (e.g. criticality)
    if strip_variables(old_cfg) != strip_variables(new_cfg):
        return False

    old_cases = expand_parametric(old_cfg)
    new_cases = expand_parametric(new_cfg)

    old_set = {freeze_case(c) for c in old_cases}
    new_set = {freeze_case(c) for c in new_cases}

    return old_set.issubset(new_set)


def strip_variables(cfg):
    cfg = dict(cfg)
    cfg["variables"] = {}
    return cfg


def expand_parametric(cfg):

    variables = cfg.get("variables", {})
    mode = cfg.get("mode", "outer")

    keys = list(variables.keys())
    domains = [normalize_domain(variables[k]) for k in keys]

    if not keys:
        return [{}]

    if mode == "outer":
        return [
            dict(zip(keys, values))
            for values in product(*domains)
        ]

    elif mode == "inner":
        length = len(domains[0])
        if not all(len(d) == length for d in domains):
            raise RuntimeError("Inner mode requires equal-length domains.")

        return [
            dict(zip(keys, values))
            for values in zip(*domains)
        ]

    else:
        raise RuntimeError(f"Unknown parametric mode '{mode}'")


def freeze_case(case: dict):
    return tuple(sorted(case.items()))


# ============================================================
# Existing logic (kept for ensemble)
# ============================================================

def sweep_extension_allowed(old_params, new_params):

    if set(old_params.keys()) != set(new_params.keys()):
        return False

    for key in old_params:

        old_val = old_params[key]
        new_val = new_params[key]

        if isinstance(old_val, list):

            if not isinstance(new_val, list):
                return False

            old_domain = normalize_domain(old_val)
            new_domain = normalize_domain(new_val)

            if not is_prefix_extension(old_domain, new_domain):
                return False

        else:
            if old_val != new_val:
                return False

    return True


def is_prefix_extension(old, new):
    return new[:len(old)] == old


def normalize_domain(domain):
    normalized = []
    for v in domain:
        if isinstance(v, float):
            normalized.append(round(v, 12))
        else:
            normalized.append(v)
    return normalized