import sys

# Global state mirroring bitio.c
infile = None
outfile = None
outcount = 0
getcount = 0
putcount = 8
bitbuf = 0

def init_bitio():
    """Reset the global state before each encode/decode operation."""
    global outcount, getcount, putcount, bitbuf
    outcount = 0
    getcount = 0
    putcount = 8
    bitbuf = 0

def error(message):
    sys.stderr.write(f"\n{message}\n")
    sys.exit(1)

def getc(f):
    """
    Returns the next byte from file as an int.
    If EOF, returns -1 (simulating C's EOF).
    """
    b = f.read(1)
    if not b:
        return -1
    return b[0]

def rightbits(n, x):
    return x & ((1 << n) - 1)

def getbit():
    global getcount, bitbuf
    getcount -= 1
    if getcount >= 0:
        return (bitbuf >> getcount) & 1
    
    getcount = 7
    c = getc(infile)
    if c == -1:
        bitbuf = 0xFFFFFFFF  # Simulate getting -1 and placing into unsigned int
    else:
        bitbuf = c
    return (bitbuf >> 7) & 1

def getbits(n):
    global getcount, bitbuf
    x = 0
    while n > getcount:
        n -= getcount
        x |= rightbits(getcount, bitbuf) << n
        c = getc(infile)
        if c == -1:
            bitbuf = 0xFFFFFFFF
        else:
            bitbuf = c
        getcount = 8
    getcount -= n
    return x | rightbits(n, bitbuf >> getcount)

def putbit(bit):
    global putcount, bitbuf, outcount
    putcount -= 1
    if bit != 0:
        bitbuf |= (1 << putcount)
    if putcount == 0:
        outfile.write(bytes([bitbuf & 0xFF]))
        bitbuf = 0
        putcount = 8
        outcount += 1

def putbits(n, x):
    global putcount, bitbuf, outcount
    while n >= putcount:
        n -= putcount
        bitbuf |= rightbits(putcount, x >> n)
        outfile.write(bytes([bitbuf & 0xFF]))
        bitbuf = 0
        putcount = 8
        outcount += 1
    
    putcount -= n
    bitbuf |= rightbits(n, x) << putcount
