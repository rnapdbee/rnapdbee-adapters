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


class Saenger(Enum):
    I = 'I'
    II = 'II'
    III = 'III'
    IV = 'IV'
    V = 'V'
    VI = 'VI'
    VII = 'VII'
    VIII = 'VIII'
    IX = 'IX'
    X = 'X'
    XI = 'XI'
    XII = 'XII'
    XIII = 'XIII'
    XIV = 'XIV'
    XV = 'XV'
    XVI = 'XVI'
    XVII = 'XVII'
    XVIII = 'XVIII'
    XIX = 'XIX'
    XX = 'XX'
    XXI = 'XXI'
    XXII = 'XXII'
    XXIII = 'XXIII'
    XXIV = 'XXIV'
    XXV = 'XXV'
    XXVI = 'XXVI'
    XXVII = 'XXVII'
    XXVIII = 'XXVIII'


class StackingTopology(Enum):
    upward = 'upward'
    downward = 'downward'
    inward = 'inward'
    outward = 'outward'


class BR(Enum):
    _0 = 0
    _1 = 1
    _2 = 2
    _3 = 3
    _4 = 4
    _5 = 5
    _6 = 6
    _7 = 7
    _8 = 8
    _9 = 9


class BPh(Enum):
    _0 = 0
    _1 = 1
    _2 = 2
    _3 = 3
    _4 = 4
    _5 = 5
    _6 = 6
    _7 = 7
    _8 = 8
    _9 = 9


@dataclass
class ResidueLabel:
    chain: str
    number: int
    name: str


@dataclass
class ResidueAuth:
    chain: str
    number: int
    icode: Optional[str]
    name: str


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
    saenger: Optional[Saenger]


@dataclass
class Stacking(Interaction):
    topology: Optional[StackingTopology]


@dataclass
class BaseRibose(Interaction):
    br: Optional[BR]


@dataclass
class BasePhosphate(Interaction):
    bph: Optional[BPh]


@dataclass
class OtherInteraction(Interaction):
    pass


@dataclass
class AnalysisOutput:
    basePairs: List[BasePair]
    stackings: List[Stacking]
    baseRiboseInteractions: List[BaseRibose]
    basePhosphateInteractions: List[BasePhosphate]
    otherInteractions: List[OtherInteraction]
