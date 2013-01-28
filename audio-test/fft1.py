#!/usr/bin/python
#
# Depends on python-scipy and python-matplotlib
#
# This test analyzes the .wav file and uses FFT (Fast Fourier Transform)
# to analyze the frequency range. Only one channel is analyzed (use -right
# option to select the second one). Samples  are normalized before FFT.
# Frequencies bellow 200Hz and above 6000Hz are ommited. The utility
# compares the frequencies using 200Hz steps with given or predefined
# FFT samples and the diff to the most-close FFT sample is printed.
#

import sys
import scipy
import struct
from numpy import average as npavg, max as npmax, abs as npabs, sum as npsum, fromfile as npfromfile
from scipy.fftpack import fft, fftfreq
from scipy.io import wavfile

FFT_SAMPLES = {
  'zero': (
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  ),
  'noise1': (
    [9, 6, 7, 6, 6, 5, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [13, 3, 11, 23, 23, 8, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]
  ),
  'noise2': (
    [11, 6, 7, 9, 7, 11, 4, 3, 3, 2, 2, 2, 3, 2, 2, 2, 2, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [12, 3, 11, 22, 16, 8, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1]
  ),
  'speech1': (
    [10, 6, 6, 9, 12, 7, 3, 3, 3, 2, 2, 2, 2, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [8, 4, 10, 21, 19, 9, 2, 2, 2, 1, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
  ),
  'speech2': (
    [8, 6, 7, 6, 6, 5, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2, 2],
    [15, 4, 11, 25, 18, 8, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0]
  ),
  'opera1': (
    [5, 6, 11, 11, 9, 5, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1],
    [7, 9, 10, 11, 10, 4, 5, 3, 2, 2, 2, 2, 3, 2, 2, 3, 2, 2, 1, 2, 1, 1, 1, 3, 1, 1, 6, 1, 1]
  ),
  'sweep1': (
    [9, 7, 6, 5, 5, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [9, 7, 6, 5, 4, 4, 4, 4, 3, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 3, 3, 2, 2, 2, 2]
  ),
  'sine-500': (
    [4, 47, 2, 1, 1, 1, 4, 1, 1, 1, 1, 9, 1, 1, 1, 1, 7, 1, 1, 1, 1, 3, 1, 1, 1, 1, 4, 2, 1],
    [1, 45, 0, 0, 0, 0, 17, 1, 0, 1, 1, 10, 0, 0, 0, 0, 5, 1, 0, 0, 1, 7, 0, 0, 0, 0, 4, 1, 0]
  ),
  'sine-1000': (
    [2, 2, 2, 24, 27, 2, 1, 1, 1, 1, 1, 1, 1, 4, 2, 2, 2, 1, 1, 1, 1, 1, 2, 8, 6, 1, 1, 1, 1],
    [0, 1, 1, 19, 41, 0, 0, 0, 0, 0, 0, 0, 0, 15, 2, 1, 1, 0, 0, 0, 0, 1, 1, 8, 6, 0, 0, 0, 0]
  ),
  'sine-5000': (
    [2, 2, 1, 5, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 2, 2, 1, 2, 1, 2, 2, 2, 2, 31, 29, 2, 1, 2, 1],
    [1, 1, 0, 6, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 4, 1, 2, 1, 1, 1, 2, 1, 41, 30, 0, 0, 1, 0]
  )
}

class WavFileWarning(UserWarning):
    pass

_big_endian = False

def asbytes(s):
  return str(s)

# assumes file pointer is immediately
#  after the 'fmt ' id
def _read_fmt_chunk(fid):
    if _big_endian:
        fmt = '>'
    else:
        fmt = '<'
    res = struct.unpack(fmt+'ihHIIHH',fid.read(20))
    size, comp, noc, rate, sbytes, ba, bits = res
    if (comp != 1 or size > 16):
        warnings.warn("Unfamiliar format bytes", WavFileWarning)
        if (size>16):
            fid.read(size-16)
    return size, comp, noc, rate, sbytes, ba, bits

# assumes file pointer is immediately
#   after the 'data' id
def _read_data_chunk(fid, noc, bits):
    if _big_endian:
        fmt = '>i'
    else:
        fmt = '<i'
    size = struct.unpack(fmt,fid.read(4))[0]
    if bits == 8:
        data = npfromfile(fid, dtype=numpy.ubyte, count=size)
        if noc > 1:
            data = data.reshape(-1,noc)
    else:
        bytes = bits//8
        if _big_endian:
            dtype = '>i%d' % bytes
        else:
            dtype = '<i%d' % bytes
        data = npfromfile(fid, dtype=dtype, count=size//bytes)
        if noc > 1:
            data = data.reshape(-1,noc)
    return data

def _read_riff_chunk(fid):
    global _big_endian
    str1 = fid.read(4)
    if str1 == asbytes('RIFX'):
        _big_endian = True
    elif str1 != asbytes('RIFF'):
        raise ValueError("Not a WAV file.")
    if _big_endian:
        fmt = '>I'
    else:
        fmt = '<I'
    fsize = struct.unpack(fmt, fid.read(4))[0] + 8
    str2 = fid.read(4)
    if (str2 != asbytes('WAVE')):
        raise ValueError("Not a WAV file.")
    if str1 == asbytes('RIFX'):
        _big_endian = True
    return fsize

# open a wave-file
def read_wav0(file):
    """
    Return the sample rate (in samples/sec) and data from a WAV file

    Parameters
    ----------
    file : file
        Input wav file.

    Returns
    -------
    rate : int
        Sample rate of wav file
    data : numpy array
        Data read from wav file

    Notes
    -----

    * The file can be an open file or a filename.

    * The returned sample rate is a Python integer
    * The data is returned as a numpy array with a
      data-type determined from the file.

    """
    if hasattr(file,'read'):
        fid = file
    else:
        fid = open(file, 'rb')

    fsize = _read_riff_chunk(fid)
    noc = 1
    bits = 8
    while (fid.tell() < fsize):
        # read the next chunk
        chunk_id = fid.read(4)
        if chunk_id == asbytes('fmt '):
            size, comp, noc, rate, sbytes, ba, bits = _read_fmt_chunk(fid)
        elif chunk_id == asbytes('data'):
            data = _read_data_chunk(fid, noc, bits)
        else:
            warnings.warn("chunk not understood", WavFileWarning)
            data = fid.read(4)
            if _big_endian:
                fmt = '>i'
            else:
                fmt = '<i'
            size = struct.unpack(fmt, data)[0]
            fid.seek(size, 1)
    fid.close()
    return rate, data

def read_wav(filename, channel=0):
  a = read_wav0(filename)
  samplerate, data = a
  try:
    data = map(lambda x: x[channel], data)
  except:
    pass
  m = npmax(npabs(data), axis=0)
  print '# absolute sample maximum in percent'
  print 'SAMPLE_MAXIMUM=%s' % int((m * 100 + 32768 / 2) / 32768.0)
  if m > 0:
    data /= m 
  return samplerate, data

def fft_test(args):
  global FFT_SAMPLES
  graph = False
  values = False
  channel = 0
  while 1:
    if args[0] == '-graph':
      del args[0]
      graph = True
      continue
    if args[0] == '-values':
      del args[0]
      values = True
      continue
    if args[0] == '-left':
      del args[0]
      channel = 0
      continue
    if args[0] == '-right':
      del args[0]
      channel = 1
      continue
    if args[0] == '-clean':
      del args[0]
      a = FFT_SAMPLES['zero']
      FFT_SAMPLES = {}
      FFT_SAMPLES['zero'] = a
      continue
    if args[0].startswith('-avg='):
      avg = eval(args[0][5:])
      del args[0]
      continue
    if args[0].startswith('-max='):
      mex = eval(args[0][5:])
      del args[0]
      continue
    if args[0].startswith('-name='):
      name = args[0][6:]
      del args[0]
      FFT_SAMPLES[name] = (avg, mex)
      print repr(FFT_SAMPLES[name])
    break

  filename = args[0]

  samplerate, data = read_wav(filename, channel)

  windowsize = len(data)
  lowfreq = 200
  highfreq = 6000
  
  ffty = fft(data[:windowsize])
  fftx = fftfreq(windowsize, 1.0 / samplerate)
  l, h = 0, 0
  for x in fftx:
    if x >= lowfreq:
      break
    l += 1
  for x in fftx:
    if x >= highfreq:
      break
    h += 1
  ffty = ffty[l:h]
  fftx = fftx[l:h]
  ffty = map(lambda x: (float(abs(x)) * 1000) / windowsize, ffty)
  a = 200
  r = {}
  m = {}
  totalr = totalm = 0.0
  for b in range(400, 6000 + 1, 200):
    l, h = 0, 0
    for x in fftx:
      if x >= a:
        break
      l += 1
    for x in fftx:
      if x >= b:
        break
      h += 1
    ar = ffty[l:h]
    r[b] = npsum(ar)
    m[b] = npmax(ar)
    totalr += r[b]
    totalm += m[b]
    a = b
  l = r.keys()
  l.sort()
  if totalr > 0.0:
    r = map(lambda x: int(((r[x] * 100) + totalr / 2) / totalr), l)
  else:
    r = map(lambda x: 0, l)
  if totalm > 0.0:
    m = map(lambda x: int(((m[x] * 100) + totalm / 2) / totalm), l)
  else:
    m = map(lambda x: 0, l)
  check = {}
  for s in FFT_SAMPLES:
    x, y = FFT_SAMPLES[s]
    diffa = diffm = idx = 0
    for idx in range(len(r)):
      diffa += abs(r[idx] - x[idx])
      diffm += abs(m[idx] - y[idx])
    check[diffa + diffm] = s
  l = check.keys()
  l.sort()
  print '# closest spectral diff and name'
  print 'SPECTRAL_DIFF=%s' % l[0]
  print 'SPECTRAL_NAME="%s"' % check[l[0]]
  if values:
    print '-avg="%s"' % repr(r)
    print '-max="%s"' % repr(m)
  if graph:
    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(abs(fftx), ffty, 'ro')
    ax.set_xlabel('Frequency in Hz')
    ax.set_ylabel('Occurence')
    plt.title(filename)
    plt.show()

if __name__ == '__main__':
  fft_test(sys.argv[1:])  
