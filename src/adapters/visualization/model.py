# pylint: disable=invalid-name
from typing import List
from dataclasses import dataclass

from dataclasses_json import DataClassJsonMixin

# 3D -> multi 2D


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


# 3D -> (...) and 2D -> (...)


@dataclass(frozen=True, order=True)
class Residue(DataClassJsonMixin):
    chain: str
    number: int
    name: str


@dataclass(frozen=True, order=True)
class ResiduePair(DataClassJsonMixin):
    residueLeft: Residue
    residueRight: Residue


@dataclass(frozen=True, order=True)
class Model2D(DataClassJsonMixin):
    strands: List[Strand]
    nonCanonicalInteractions: List[ResiduePair]
