# pylint: skip-file
# flake8: noqa
# type: ignore
import os
import os.path
import sys
import tempfile
import uuid

from System import Activator, Array
from System.IO import StringWriter
from System.Reflection import Assembly, BindingFlags, TargetInvocationException

import clr

clr.AddReference('PseudoViewer3.exe')
import PseudoViewer
import PseudoViewer.PVIO
import PseudoViewer.PVIO.Strand

ASSEMBLY = Assembly.LoadFile('/pseudoviewer/PseudoViewer3.exe')
STATIC = BindingFlags.InvokeMethod | BindingFlags.Static | BindingFlags.Public
STATIC_NP = BindingFlags.InvokeMethod | BindingFlags.Static | BindingFlags.NonPublic


def saveImageSvg(pvInput, outpath):
    drawSvgType = ASSEMBLY.GetType('PseudoViewer.DrawSVG')
    drawSvg = Activator.CreateInstance(drawSvgType, outpath)

    drawType = ASSEMBLY.GetType('PseudoViewer.Draw')
    drawType.InvokeMember('DrawStructure', STATIC, None, None, Array[object]([drawSvg, pvInput]))


def saveImage(pvInput, outpath):
    drawEpsType = ASSEMBLY.GetType('PseudoViewer.DrawEPS')
    drawEps = Activator.CreateInstance(drawEpsType, outpath)

    drawType = ASSEMBLY.GetType('PseudoViewer.Draw')
    drawType.InvokeMember('DrawStructure', STATIC, None, None, Array[object]([drawEps, pvInput]))


def saveImageFromSeqStr(sequence, structure, outpath):
    pvInputType = ASSEMBLY.GetType('PseudoViewer.PVIO.PVInput')
    pvInput = Activator.CreateInstance(pvInputType, sequence, structure, 1)
    saveImageSvg(pvInput, outpath)


def saveImageFromPVFile(pvFile, outpath):
    wspvInFileDataType = ASSEMBLY.GetType('PseudoViewer.WSPVInFileData')
    wspvInFileData = Activator.CreateInstance(wspvInFileDataType)
    wspvInFileData.PV_file = pvFile
    pvInput = wspvInFileData.toPVInput()
    saveImage(pvInput, outpath)


def saveImageFromPVFile2(pvFileSequence, pvFileStructure, outpath, eps=True):
    sequence = StringWriter()
    structure = StringWriter()

    ioReadFilesType = ASSEMBLY.GetType('PseudoViewer.PVIO.IOReadFiles')
    makeStrandType = ASSEMBLY.GetType('PseudoViewer.PVIO.MakeStrand')
    makeStrand = Activator.CreateInstance(makeStrandType)

    flag = True
    for line in pvFileSequence.split('\n'):
        line = line.strip()
        if not line:
            continue
        if flag:
            startBase = line
        else:
            args = Array[object]([sequence, startBase, makeStrand, line])
            ioReadFilesType.InvokeMember('dealSeauence', STATIC_NP, None, None, args)
        flag ^= True

    flag = True
    for line in pvFileStructure.split('\n'):
        line = line.strip()
        if not line:
            continue
        if flag:
            startBase = line
        else:
            args = Array[object]([structure, line])
            ioReadFilesType.InvokeMember('dealStructure', STATIC_NP, None, None, args)
        flag ^= True

    strandsType = ASSEMBLY.GetType('PseudoViewer.PVIO.Strands')
    strandType = ASSEMBLY.GetType('PseudoViewer.PVIO.Strand')

    sequence = sequence.ToString()
    structure = structure.ToString()
    strands = PseudoViewer.PVIO.Strands(makeStrand.getStrands)

    pvInputType = ASSEMBLY.GetType('PseudoViewer.PVIO.PVInput')
    pvInput = Activator.CreateInstance(pvInputType, sequence, structure, strands)
    if eps:
        saveImage(pvInput, outpath)
    else:
        saveImageSvg(pvInput, outpath)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: wine ipy.exe pvwrap.py <INPUT-SEQ> <INPUT-STR> <OUTPUT-FILE>')
        exit(1)

    f = open(sys.argv[1])
    sequence = f.read()
    f.close()

    f = open(sys.argv[2])
    structure = f.read()
    f.close()

    saveImageFromPVFile2(sequence, structure, sys.argv[3], False)