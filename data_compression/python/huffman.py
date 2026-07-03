import sys
import struct
import bitio

N = 256
CHARBITS = 8
heapsize = 0
heap = [0] * (2 * N)
parent = [0] * (2 * N)
left = [0] * (2 * N)
right = [0] * (2 * N)
freq = [0] * (2 * N)

readtree_avail = N

def downheap(i):
    global heap, freq
    k = heap[i]
    while True:
        j = 2 * i
        if j > heapsize:
            break
        if j < heapsize and freq[heap[j]] > freq[heap[j + 1]]:
            j += 1
        if freq[k] <= freq[heap[j]]:
            break
        heap[i] = heap[j]
        i = j
    heap[i] = k

def writetree(i):
    if i < N:
        bitio.putbit(0)
        bitio.putbits(CHARBITS, i)
    else:
        bitio.putbit(1)
        writetree(left[i])
        writetree(right[i])

def encode():
    global heapsize, heap, parent, left, right, freq
    
    codebit = [0] * N
    
    for i in range(N):
        freq[i] = 0
        
    while True:
        i = bitio.getc(bitio.infile)
        if i == -1:
            break
        freq[i] += 1
        
    heap[1] = 0
    heapsize = 0
    for i in range(N):
        if freq[i] != 0:
            heapsize += 1
            heap[heapsize] = i
            
    for i in range(heapsize // 2, 0, -1):
        downheap(i)
        
    for i in range(2 * N - 1):
        parent[i] = 0
        
    k = heap[1]
    avail = N
    while heapsize > 1:
        i = heap[1]
        heap[1] = heap[heapsize]
        heapsize -= 1
        downheap(1)
        
        j = heap[1]
        k = avail
        avail += 1
        freq[k] = freq[i] + freq[j]
        heap[1] = k
        downheap(1)
        
        parent[i] = k
        parent[j] = -k
        left[k] = i
        right[k] = j
        
    writetree(k)
    tablesize = bitio.outcount
    incount = 0
    
    bitio.infile.seek(0)
    while True:
        j = bitio.getc(bitio.infile)
        if j == -1:
            break
        k_idx = 0
        while True:
            j = parent[j]
            if j == 0:
                break
            if j > 0:
                codebit[k_idx] = 0
                k_idx += 1
            else:
                codebit[k_idx] = 1
                k_idx += 1
                j = -j
        
        k_idx -= 1
        while k_idx >= 0:
            bitio.putbit(codebit[k_idx])
            k_idx -= 1
            
        incount += 1
        if (incount & 1023) == 0:
            sys.stdout.write(f"{incount:12d}\r")
            sys.stdout.flush()
            
    bitio.putbits(7, 0)
    sys.stdout.write(f"In : {incount} bytes\n")
    sys.stdout.write(f"Out: {bitio.outcount} bytes (table: {tablesize} bytes)\n")
    if incount != 0:
        cr = (1000 * bitio.outcount + incount // 2) // incount
        sys.stdout.write(f"Out/In: {cr // 1000}.{cr % 1000:03d}\n")

def readtree():
    global readtree_avail, left, right
    
    if bitio.getbit():
        i = readtree_avail
        readtree_avail += 1
        if i >= 2 * N - 1:
            bitio.error("表が間違っています")
        left[i] = readtree()
        right[i] = readtree()
        return i
    else:
        return bitio.getbits(CHARBITS)

def decode(size):
    global readtree_avail
    
    readtree_avail = N
    root = readtree()
    
    for k in range(size):
        j = root
        while j >= N:
            if bitio.getbit():
                j = right[j]
            else:
                j = left[j]
        bitio.outfile.write(bytes([j]))
        if (k & 1023) == 0:
            sys.stdout.write(f"{k:12d}\r")
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
