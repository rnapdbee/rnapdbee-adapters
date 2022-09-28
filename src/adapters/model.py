# pylint: disable=invalid-name
from dataclasses import dataclass
from typing import List

from rnapolis.common import (BasePair, BasePhosphate, BaseRibose,
                             OtherInteraction, Stacking)


@dataclass
class AnalysisOutput:
    basePairs: List[BasePair]
    stackings: List[Stacking]
    baseRiboseInteractions: List[BaseRibose]
    basePhosphateInteractions: List[BasePhosphate]
    otherInteractions: List[OtherInteraction]
