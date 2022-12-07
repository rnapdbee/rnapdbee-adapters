# pylint: disable=invalid-name
from typing import List, Optional
from enum import Enum
from dataclasses import dataclass

from dataclasses_json import DataClassJsonMixin


class SymbolType(Enum):
    BEGIN = 0
    END = 1
    NONE = 2


@dataclass(frozen=True)
class Symbol:
    allowed: bool
    type: SymbolType
    sibling: Optional[str]


SYMBOLS = {
    '.': Symbol(True, SymbolType.NONE, None),
    '-': Symbol(False, SymbolType.NONE, None),
    '(': Symbol(True, SymbolType.BEGIN, ')'),
    ')': Symbol(True, SymbolType.END, '('),
    '[': Symbol(False, SymbolType.BEGIN, ']'),
    ']': Symbol(False, SymbolType.END, '['),
    '{': Symbol(False, SymbolType.BEGIN, '}'),
    '}': Symbol(False, SymbolType.END, '{'),
    '<': Symbol(False, SymbolType.BEGIN, '>'),
    '>': Symbol(False, SymbolType.END, '<'),
    'A': Symbol(False, SymbolType.BEGIN, 'a'),
    'a': Symbol(False, SymbolType.END, 'A'),
    'B': Symbol(False, SymbolType.BEGIN, 'b'),
    'b': Symbol(False, SymbolType.END, 'B'),
    'C': Symbol(False, SymbolType.BEGIN, 'c'),
    'c': Symbol(False, SymbolType.END, 'C'),
    'D': Symbol(False, SymbolType.BEGIN, 'd'),
    'd': Symbol(False, SymbolType.END, 'D'),
    'E': Symbol(False, SymbolType.BEGIN, 'e'),
    'e': Symbol(False, SymbolType.END, 'E'),
}


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


@dataclass(frozen=True, order=True)
class Residue(DataClassJsonMixin):
    chain: str
    number: int
    name: str


class LeontisWesthof(Enum):
    cWW = "cWW"
    cWH = "cWH"
    cWS = "cWS"
    cHW = "cHW"
    cHH = "cHH"
    cHS = "cHS"
    cSW = "cSW"
    cSH = "cSH"
    cSS = "cSS"
    tWW = "tWW"
    tWH = "tWH"
    tWS = "tWS"
    tHW = "tHW"
    tHH = "tHH"
    tHS = "tHS"
    tSW = "tSW"
    tSH = "tSH"
    tSS = "tSS"


@dataclass(frozen=True, order=True)
class Interaction(DataClassJsonMixin):
    residueLeft: Residue
    residueRight: Residue
    leontisWesthof: LeontisWesthof


@dataclass(frozen=True, order=True)
class ChainWithResidues(DataClassJsonMixin):
    name: str
    residues: List[Residue]


@dataclass(frozen=True, order=True)
class NonCanonicalInteractions(DataClassJsonMixin):
    notRepresented: List[Interaction]
    represented: List[Interaction]


@dataclass(frozen=True, order=True)
class Model2D(DataClassJsonMixin):
    strands: List[Strand]
    residues: List[Residue]
    chainsWithResidues: List[ChainWithResidues]
    nonCanonicalInteractions: NonCanonicalInteractions
