import sys
import struct
import bitio

N = 256
USHRT_BIT = 16
Q1 = (1 << (USHRT_BIT - 2))
Q2 = (2 * Q1)
Q3 = (3 * Q1)

cum = [0] * (N + 1)
ns = 0

def output(bit):
    global ns
    bitio.putbit(bit)
    while ns > 0:
        bitio.putbit(1 ^ bit)
        ns -= 1

def encode():
    global ns, cum
    
    count = [0] * N
    
    # Read entire file to count frequencies
    while True:
        c = bitio.getc(bitio.infile)
        if c == -1:
            break
        count[c] += 1
        
    incount = sum(count)
    maxcount = max(count) if incount > 0 else 0
    
    if incount == 0:
        return
        
    d = max((maxcount + N - 2) // (N - 1), (incount + Q1 - 257) // (Q1 - 256))
    if d != 1:
        for c in range(N):
            count[c] = (count[c] + d - 1) // d
            
    cum[0] = 0
    for c in range(N):
        bitio.outfile.write(bytes([count[c]]))
        cum[c + 1] = cum[c] + count[c]
        
    bitio.outcount = N
    bitio.infile.seek(0)
    incount = 0
    
    low = 0
    high = 0xFFFF
    ns = 0
    
    while True:
        c = bitio.getc(bitio.infile)
        if c == -1:
            break
            
        range_val = (high - low + 1)
        high = (low + (range_val * cum[c + 1]) // cum[N] - 1) & 0xFFFF
        low = (low + (range_val * cum[c]) // cum[N]) & 0xFFFF
        
        while True:
            if high < Q2:
                output(0)
            elif low >= Q2:
                output(1)
            elif low >= Q1 and high < Q3:
                ns += 1
                low = (low - Q1) & 0xFFFF
                high = (high - Q1) & 0xFFFF
            else:
                break
            low = (low << 1) & 0xFFFF
            high = ((high << 1) + 1) & 0xFFFF
            
        incount += 1
        if (incount & 1023) == 0:
            sys.stdout.write(f"{incount:12d}\r")
            sys.stdout.flush()
            
    ns += 8
    if low < Q1:
        output(0)
    else:
        output(1)
        
    sys.stdout.write(f"In : {incount} bytes\n")
    sys.stdout.write(f"Out: {bitio.outcount} bytes (table: {N})\n")
    cr = (1000 * bitio.outcount + incount // 2) // incount
    sys.stdout.write(f"Out/In: {cr // 1000}.{cr % 1000:03d}\n")

def binarysearch(x):
    i = 1
    j = N
    while i < j:
        k = (i + j) // 2
        if cum[k] <= x:
            i = k + 1
        else:
            j = k
    return i - 1

def decode(size):
    global cum
    
    if size == 0:
        return
        
    count = [0] * N
    cum[0] = 0
    for c in range(N):
        val = bitio.getc(bitio.infile)
        if val == -1:
            val = 0
        count[c] = val
        cum[c + 1] = cum[c] + count[c]
        
    value = 0
    for c in range(USHRT_BIT):
        value = ((value * 2) + bitio.getbit()) & 0xFFFF
        
    low = 0
    high = 0xFFFF
    
    for i in range(size):
        range_val = (high - low + 1)
        c = binarysearch( (((value - low + 1) & 0xFFFF) * cum[N] - 1) // range_val )
        
        high = (low + (range_val * cum[c + 1]) // cum[N] - 1) & 0xFFFF
        low = (low + (range_val * cum[c]) // cum[N]) & 0xFFFF
        
        while True:
            if high < Q2:
                pass
            elif low >= Q2:
                pass
            elif low >= Q1 and high < Q3:
                value = (value - Q1) & 0xFFFF
                low = (low - Q1) & 0xFFFF
                high = (high - Q1) & 0xFFFF
            else:
                break
            low = (low << 1) & 0xFFFF
            high = ((high << 1) + 1) & 0xFFFF
            value = ((value << 1) + bitio.getbit()) & 0xFFFF
            
        bitio.outfile.write(bytes([c]))
        
        if (i & 1023) == 0:
            sys.stdout.write(f"{i:12d}\r")
            sys.stdout.flush()
            
    sys.stdout.write(f"{size:12d}\n")

def main():
    if len(sys.argv) != 4:
        bitio.error("使用法は本文を参照してください")
    
    mode = sys.argv[1]
    if mode not in ('E', 'e', 'D', 'd'):
        bitio.error("使用法は本文を参照してください")
        
    try:
        bitio.infile = open(sys.argv[2], "rb")
    except IOError:
        bitio.error("入力ファイルが開きません")
        
    try:
        bitio.outfile = open(sys.argv[3], "wb")
    except IOError:
        bitio.error("出力ファイルが開きません")
        
    bitio.init_bitio()
    
    if mode in ('E', 'e'):
        bitio.infile.seek(0, 2)
        size = bitio.infile.tell()
        bitio.outfile.write(struct.pack('<Q', size))
        bitio.infile.seek(0)
        encode()
    else:
        size_data = bitio.infile.read(8)
        if len(size_data) == 8:
            size = struct.unpack('<Q', size_data)[0]
            decode(size)
            
    bitio.infile.close()
    bitio.outfile.close()

if __name__ == '__main__':
    main()
