from adapters.analysis import bpnet


def test_quintuple():
    line = "      4       4   U ? 0       63    63   A ? 0    W:WT BP 0.72    39    39   G ? 0    h:hT TP 1.39    54    54   G ? 0    h:wT TP 1.47    41    41   A ? 0    W:HT BF 1.26"
    bpnet.parse_base_pairs(line)


def test_bifurcated():
    #            0     1   2 3 4       5  6    7     8     9   A B C       D  E    F
    line = "    72    72   A ? 0    h:hT BF 1.37    76    76   C ? 0    h:wC BF 0.98"
    bpnet.parse_base_pairs(line)
