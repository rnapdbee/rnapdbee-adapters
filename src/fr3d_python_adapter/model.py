from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class LeontisWesthof(Enum):
    cWW = 'cWW'
    cWH = 'cWH'
    cWS = 'cWS'
    cHW = 'cHW'
    cHH = 'cHH'
    cHS = 'cHS'
    cSW = 'cSW'
    cSH = 'cSH'
    cSS = 'cSS'
    tWW = 'tWW'
    tWH = 'tWH'
    tWS = 'tWS'
    tHW = 'tHW'
    tHH = 'tHH'
    tHS = 'tHS'
    tSW = 'tSW'
    tSH = 'tSH'
    tSS = 'tSS'


class StackingTopology(Enum):
    upward = 'upward'
    downward = 'downward'
    inward = 'inward'
    outward = 'outward'


# TODO
class BR(Enum):
    unknown = 'unknown'


# TODO
class BPh(Enum):
    unknown = 'unknown'


@dataclass
class ResidueLabel:
    chain: str
    number: int


@dataclass
class ResidueAuth:
    chain: str
    number: int
    icode: str


@dataclass
class Residue:
    label: Optional[ResidueLabel]
    auth: Optional[ResidueAuth]


@dataclass
class Interaction:
    nt1: Residue
    nt2: Residue


@dataclass
class BasePair(Interaction):
    lw: LeontisWesthof


@dataclass
class Stacking(Interaction):
    topology: StackingTopology


@dataclass
class BaseRibose(Interaction):
    br: BR


@dataclass
class BasePhosphate(Interaction):
    bph: BPh


@dataclass
class Structure2D:
    basePairs: List[BasePair]
    stackings: List[Stacking]
    baseRiboseInteractions: List[BaseRibose]
    basePhosphateInteractions: List[BasePhosphate]
