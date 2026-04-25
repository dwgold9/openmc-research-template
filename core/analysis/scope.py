from pathlib import Path
import openmc4d as mc
import xarray as xr
import json, yaml
from enum import Enum, auto

from .measurement import Measurement, AggregateMeasurement

class Scope(Enum):
    MEMBER = auto()
    CASE = auto()
    STUDY = auto()

class MemberContext:
    def __init__(self, member_id, path, metadata=None, parent=None):
        self.member_id = member_id
        self.path = Path(path)
        self.measurements_path = self.path / "measurements"
        self.metadata = metadata or {}
        self.parent = parent
        self.params = self._load()

        self._measurement_cache = {}

    @property
    def run_dir(self):
        return self.path / "run"

    def get_measurement(self, name):

        if name not in self._measurement_cache:

            path = self.measurements_path / f"{name}.nc"

            if not path.exists():
                self._measurement_cache[name] = None
            else:
                ds = xr.load_dataset(path)

                tags = {
                    "scope": "member",
                    **self.params,
                    "member_id": self.member_id
                }

                self._measurement_cache[name] = Measurement(ds, tags)

        m = self._measurement_cache[name]

        if m is None:
            return None

        return m.copy()
    
    def _load(self):
        with open(self.path / "resolved_params.json") as f:
            data = json.load(f)
        return data


class CaseContext:
    def __init__(self, case_id, path, members, metadata=None, parent=None):
        self.case_id = case_id
        self.path = Path(path)
        self.members = members
        self.metadata = metadata or {}
        self.parent = parent
        self.params = self._load()

        for m in self.members:
            m.parent = self

    def get_measurement(self, name):

        measurements = [
            m.get_measurement(name)
            for m in self.members
        ]

        measurements = [m for m in measurements if m is not None]

        return AggregateMeasurement(measurements)
    
    def get_member(self, where: dict):
        """
        Return first member matching parameter constraints.
        """

        for member in self.members:

            params = member.params

            match = True
            for key, val in where.items():
                if params.get(key) != val:
                    match = False
                    break

            if match:
                return member

        raise ValueError(f"No member matches {where}")
    
    def __iter__(self):
        return iter(self.members)
    
    def _load(self):
        with open(self.path / "case_params.json") as f:
            data = json.load(f)
        return data
    

class StudyContext:
    def __init__(self, study_id, path, cases, metadata=None):
        self.study_id = study_id
        self.path = Path(path)
        self.cases = cases
        self.metadata = metadata or {}
        self.params = {}

        for c in self.cases:
            c.parent = self

    def get_measurement(self, name):

        measurements = [
            m.get_measurement(name)
            for m in self.cases
        ]

        measurements = [m for m in measurements if m is not None]

        return AggregateMeasurement(measurements)
    
    def __iter__(self):
        return iter(self.cases)
    
    def _load(self):
        with open(self.path / "frozen_config.yaml") as f:
            data = yaml.safe_load(f)
        return data['parameters']
    

def build_context(root):
    cases = []
    for case_dir in Path(root).iterdir():
        if not case_dir.is_dir():
            continue

        members = []
        for member_dir in case_dir.iterdir():
            if not member_dir.is_dir():
                continue

            members.append(
                MemberContext(
                    member_id=member_dir.name,
                    path=member_dir
                )
            )

        cases.append(
            CaseContext(
                case_id=case_dir.name,
                path=case_dir,
                members=members
            )
        )

    return StudyContext("my_study", root, cases)