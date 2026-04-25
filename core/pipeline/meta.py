# meta.py

from __future__ import annotations

import json
import time
import yaml
import os
import json
import stat

import hashlib
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List


# ============================================================
# Status Enum
# ============================================================

class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


# ============================================================
# Hashing
# ============================================================

def stable_hash(obj: Any) -> str:
    serialized = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


# ============================================================
# Atomic YAML I/O
# ============================================================

def _write_yaml_atomic(path: Path, data: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        yaml.safe_dump(data, f)
    tmp_path.replace(path)


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}
    




# ============================================================
# BaseMeta (Shared Behavior)
# ============================================================

class BaseMeta:
    FILENAME = None

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.path = self.directory / self.FILENAME

        if not self.path.exists():
            self._initialize()

        self.data = _read_yaml(self.path)

    def _initialize(self):
        raise NotImplementedError

    def _commit(self):
        _write_yaml_atomic(self.path, self.data)

    @property
    def status(self) -> Status:
        return Status(self.data["status"])

    def set_status(self, status: Status):
        self.data["status"] = status.value
        self._commit()


# ============================================================
# MemberMeta
# ============================================================

class MemberMeta(BaseMeta):

    FILENAME = "member_meta.yaml"

    def _initialize(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        data = {
            "status": Status.PENDING.value,
            "started_at": None,
            "completed_at": None,
            "runtime_seconds": None,
            "input_hash": None,
            "seed": None,
        }
        _write_yaml_atomic(self.path, data)

    def validate_input(self, config: Dict[str, Any]):
        new_hash = stable_hash(config)

        if self.data["input_hash"] is None:
            self.data["input_hash"] = new_hash
            self._commit()
        elif self.data["input_hash"] != new_hash:
            raise RuntimeError(
                f"Input mismatch in {self.directory}"
            )

    def should_run(self) -> bool:
        return self.status != Status.COMPLETE

    def mark_running(self):
        self.data["status"] = Status.RUNNING.value
        self.data["started_at"] = time.time()
        self._commit()

    def mark_complete(self):
        self.data["status"] = Status.COMPLETE.value
        self.data["completed_at"] = time.time()

        if self.data["started_at"] is not None:
            self.data["runtime_seconds"] = (
                self.data["completed_at"] - self.data["started_at"]
            )

        self._commit()

    def mark_failed(self):
        self.data["status"] = Status.FAILED.value
        self._commit()


# ============================================================
# CaseMeta
# ============================================================

class CaseMeta(BaseMeta):

    FILENAME = "case_meta.yaml"

    def _initialize(self):
        data = {
            "status": Status.PENDING.value,
            "members_total": 0,
            "members_completed": 0,
            "members_failed": 0,
        }
        _write_yaml_atomic(self.path, data)

    def update_from_members(self, member_dirs: List[Path]):
        total = 0
        completed = 0
        failed = 0
        running = 0

        for mdir in member_dirs:
            meta = MemberMeta(mdir)
            total += 1
            if meta.status == Status.COMPLETE:
                completed += 1
            elif meta.status == Status.FAILED:
                failed += 1
            elif meta.status == Status.RUNNING:
                running += 1

        self.data["members_total"] = total
        self.data["members_completed"] = completed
        self.data["members_failed"] = failed

        if completed == total and total > 0:
            self.data["status"] = Status.COMPLETE.value
        elif running > 0:
            self.data["status"] = Status.RUNNING.value
        elif failed > 0:
            self.data["status"] = Status.FAILED.value
        else:
            self.data["status"] = Status.PENDING.value

        self._commit()


# ============================================================
# StudyMeta
# ============================================================

class StudyMeta(BaseMeta):

    FILENAME = "study_meta.yaml"

    def _initialize(self):
        data = {
            "status": Status.PENDING.value,
            "cases_total": 0,
            "cases_completed": 0,
            "cases_failed": 0,
            "created_at": time.time(),
            "last_updated": None,
        }
        _write_yaml_atomic(self.path, data)

    def update_from_cases(self, case_dirs: List[Path]):
        total = 0
        completed = 0
        failed = 0
        running = 0

        for cdir in case_dirs:
            meta = CaseMeta(cdir)
            total += 1
            if meta.status == Status.COMPLETE:
                completed += 1
            elif meta.status == Status.FAILED:
                failed += 1
            elif meta.status == Status.RUNNING:
                running += 1

        self.data["cases_total"] = total
        self.data["cases_completed"] = completed
        self.data["cases_failed"] = failed
        self.data["last_updated"] = time.time()

        if completed == total and total > 0:
            self.data["status"] = Status.COMPLETE.value
        elif running > 0:
            self.data["status"] = Status.RUNNING.value
        elif failed > 0:
            self.data["status"] = Status.FAILED.value
        else:
            self.data["status"] = Status.PENDING.value

        self._commit()


# ============================================================
# Execution Wrapper (unchanged)
# ============================================================

def execute_member(member_dir: Path,
                   config: Dict[str, Any],
                   run_callable) -> None:

    meta = MemberMeta(member_dir)

    if not meta.should_run():
        return

    meta.validate_input(config)
    meta.mark_running()

    try:
        run_callable()
        meta.mark_complete()
    except Exception:
        meta.mark_failed()
        raise