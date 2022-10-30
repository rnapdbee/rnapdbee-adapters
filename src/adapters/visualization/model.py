from typing import List
from dataclasses import dataclass

from dataclasses_json import DataClassJsonMixin


@dataclass(frozen=True, order=True)
class Strand(DataClassJsonMixin):
    name: str
    sequence: str
    structure: str


@dataclass(frozen=True, order=True)
class ResultMulti2D(DataClassJsonMixin):
    adapter: str
    strands: List[Strand]


@dataclass(frozen=True, order=True)
class ModelMulti2D(DataClassJsonMixin):
    results: List[ResultMulti2D]
