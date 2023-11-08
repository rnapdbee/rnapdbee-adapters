from adapters.analysis import bpnet


def test_quintuple():
    line = '      4       4   U ? 0       63    63   A ? 0    W:WT BP 0.72    39    39   G ? 0    h:hT TP 1.39    54    54   G ? 0    h:wT TP 1.47    41    41   A ? 0    W:HT BF 1.26'
    bpnet.parse_base_pairs(line)