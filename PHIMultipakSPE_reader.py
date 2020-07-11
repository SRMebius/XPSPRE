# -*- coding: utf-8 -*-
"""
# =============================================================================
# Created on Sun Jun 28 15:47:18 2020

# @ author: SRMebius
# =============================================================================
"""
# =============================================================================
# The file structure is 

# (1) ASCII Header
#  ......
#  structre SpectralRegDef
#      variable num1
# 	   variable num2
# 	   string name
# 	   variable PHI_AtomicNumber
# 	   variable points
# 	   variable step
# 	   variable start1
# 	   variable ende1
# 	   variable start2
# 	   variable ende2
# 	   variable dwelltime //collection time
# 	   variable Epass
# 	   string str
#  ......

# (2) Binary Header with the following binary datatypes:
#   uint32 group //??
# 	uint32 numspectra
# 	uint32 datalen2 //length of spectraheader (4*24*numspectra)
# 	uint32 datalen1 //length of binheader

# (3) several Spectral Headers
#     Number is defined by ‘NoSpectralReg’ in the ASCII header
#     each with the following binary datatypes:
# 	uint32 spectranum
# 	uint32 bool1
# 	uint32 bool2
# 	uint32 spectranum2
# 	uint32 bool4
# 	uint32 points // // compare to SpectralRegDef..points
# 	uint32 bool5
# 	uint32 bool6
# 	char char1[4] // chn
# 	uint32 num8
# 	char char2[4] // sar
# 	uint32 num10
# 	uint32 num11
# 	uint32 num12
# 	uchar yunit[4] // c/s; 
# 	uint32 num14
# 	uint32 num15
# 	uint32 num16
# 	char datatype[4] //f4 --> float; f8 --> double
# 	uint32 datalen // points * datatype (bytes)
# 	uint32 datastart // start of datablock
# 	uint32 num20
# 	uint32 num21
# 	uint32 offset2 // start off additional information

# (4) The actual spectra
#   The position of each spectra is given by '(3) datastart'
#   which is an offset which needs to be added from the file
#   position where the binary data starts. Spectra can have a
#   different binary datatype which is defined by '(3) datatype'.
#   At the end of each spectra there might be also additional
#   bytes until the next spectra starts.
# =============================================================================

from struct import unpack, calcsize

import numpy as np
import pandas as pd


file_path = './ex.SPE'

with open(file_path, 'rb') as f:
    s = f.read()

# ahpos: ASCII Header Position
# bhpos: Binary Header Position
# shpos: Spectral Header Position
ahpos = 0    
bhpos = s.find(b'\r\nEOFH\r\n') + 8
shpos = bhpos + 16

# ASCII Header: basic information
ascii_header = s[6:bhpos-8].decode('utf8').split('\r\n')
keys = [infos.split(':')[0].strip(' ') for infos in ascii_header]
vals = [infos.split(':')[1].strip(' ') for infos in ascii_header]
ascii_header = dict(zip(keys, vals))

energy_ev = float(ascii_header['XraySource'].split(' ')[1])
Ta, Tb = tuple(ascii_header['IntensityCalCoeff'].split(' '))
Ta, Tb = float(Ta), float(Tb)

SpectralRegDef = pd.DataFrame(
    {vals[i].split(' ')[2]:vals[i].split(' ') for i in range(len(keys)) if keys[i] == 'SpectralRegDef'},
    index = ['num1', 'num2', 'name', 'PHI_AtomicNumber', 'points', 
             'step', 'start1', 'ende1', 'start2', 'ende2',
             'dwelltime', 'Epass', 'str']
    )

# get the number of spectra
binary_header = unpack('4I', s[bhpos:shpos])
_, spectranum, _ ,_ = binary_header

# get the overall spectral information
fmt = '8I3sI3s3I3s3I2s5I' * spectranum
bytesnum = calcsize(fmt)
spectral_header = unpack(fmt, s[shpos:shpos+bytesnum])
datastart = [spectral_header[n*24+20] for n in range(spectranum)]

# get the actual spectra data and load into 'data' DataFrame
data = pd.DataFrame()

for n in range(spectranum):
    spectrumname = SpectralRegDef.columns[n]
    points = int(SpectralRegDef[spectrumname].points)
    step = float(SpectralRegDef[spectrumname].step)
    start1 = float(SpectralRegDef[spectrumname].start1)
    ende1 = float(SpectralRegDef[spectrumname].ende1)
    
    spectrumdata = s[bhpos:][datastart[n]:datastart[n]+8*points]

    df_BE = pd.DataFrame(
        np.arange(start1, ende1+step, step),
        columns = [f'{spectrumname}_BE']
        )
    data = pd.concat([data, df_BE], axis=1)

    df_Intensity = pd.DataFrame(
        np.array(unpack('d'*points, spectrumdata)),
        columns = [f'{spectrumname}_Intensity']
        )
    data = pd.concat([data, df_Intensity], axis=1)




