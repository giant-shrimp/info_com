import sys
import struct
import bitio

N = 256
MAXDICT = 4096
MAXMATCH = 100
NIL = MAXDICT

character = [0] * MAXDICT
parent = [0] * MAXDICT
lchild = [0] * MAXDICT
rsib = [0] * MAXDICT
lsib = [0] * MAXDICT
newer = [0] * MAXDICT
older = [0] * MAXDICT
match_buf = [0] * MAXMATCH

dictsize = N
qin = NIL
qout = NIL
bitlen = 1
bitmax = 2

def reset_static_state():
    global dictsize, qin, qout, bitlen, bitmax
    dictsize = N
    qin = NIL
    qout = NIL
    bitlen = 1
    bitmax = 2

def init_tree():
    global character, parent, lchild, lsib, rsib
    for i in range(N):
        character[i] = i
        parent[i] = NIL
        lchild[i] = NIL
        lsib[i] = NIL
        rsib[i] = NIL

def dequeue(p):
    global qout, newer, older
    if p == qout:
        qout = newer[p]
        older[qout] = NIL
    else:
        o = older[p]
        n = newer[p]
        newer[o] = n
        older[n] = o

def enqueue(p, q):
    global qin, qout, newer, older
    if qin == NIL:
        older[p] = NIL
        newer[p] = NIL
        qin = p
        qout = p
    elif q == NIL:
        older[p] = NIL
        newer[p] = qout
        older[qout] = p
        qout = p
    elif q == qin:
        older[p] = qin
        newer[p] = NIL
        newer[qin] = p
        qin = p
    else:
        older[p] = q
        newer[p] = newer[q]
        newer[q] = p
        older[newer[p]] = p

def child(p, c):
    global lchild, rsib, character
    p = lchild[p]
    while p != NIL and c != character[p]:
        p = rsib[p]
    return p

def addleaf(parp, p, c):
    global character, parent, lchild, lsib, rsib
    character[p] = c
    parent[p] = parp
    lchild[p] = NIL
    lsib[p] = NIL
    q = lchild[parp]
    rsib[p] = q
    if q != NIL:
        lsib[q] = p
    lchild[parp] = p

def deleteleaf(p):
    global lsib, rsib, lchild, parent
    left = lsib[p]
    right = rsib[p]
    if left != NIL:
        rsib[left] = right
    else:
        lchild[parent[p]] = right
    if right != NIL:
        lsib[right] = left

def update(match_arr, curlen, prevp, prevlen):
    global dictsize, qin, qout
    
    if prevp == NIL:
        return
        
    for i in range(curlen):
        prevlen += 1
        if prevlen > MAXMATCH:
            return
        c = match_arr[i]
        p = child(prevp, c)
        if p == NIL:
            if dictsize < MAXDICT:
                p = dictsize
                dictsize += 1
            else:
                if prevp == qout:
                    return
                p = qout
                dequeue(p)
                deleteleaf(p)
            addleaf(prevp, p, c)
            if prevp < N:
                enqueue(p, qin)
            else:
                enqueue(p, older[prevp])
        prevp = p

def output(p):
    global bitlen, bitmax
    if p < N:
        bitio.putbit(0)
        bitio.putbits(8, p)
    else:
        while (dictsize - N) >= bitmax:
            bitlen += 1
            bitmax <<= 1
        bitio.putbit(1)
        bitio.putbits(bitlen, p - N)

def input_code():
    global bitlen, bitmax
    if (dictsize - N) >= bitmax:
        bitmax <<= 1
        bitlen += 1
        
    i = bitio.getbit()
    if i == 0:
        return bitio.getbits(8)
        
    i = bitio.getbits(bitlen)
    return i + N

def encode():
    global match_buf, qin, older
    
    reset_static_state()
    init_tree()
    
    curptr = NIL
    curlen = 0
    incount = 0
    printcount = 0
    
    c = bitio.getc(bitio.infile)
    while c != -1:
        prevptr = curptr
        prevlen = curlen
        curlen = 0
        q = qin
        p = c
        
        while True:
            if p >= N:
                if p == q:
                    q = older[p]
                else:
                    dequeue(p)
                    enqueue(p, q)
            match_buf[curlen] = c
            curlen += 1
            curptr = p
            c = bitio.getc(bitio.infile)
            if c == -1:
                break
            p = child(curptr, c)
            if p == NIL:
                break
                
        output(curptr)
        update(match_buf, curlen, prevptr, prevlen)
        
        incount += curlen
        if incount > printcount:
            sys.stdout.write(f"{incount:12d}\r")
            sys.stdout.flush()
            printcount += 1024
            
    bitio.putbits(7, 0)
    sys.stdout.write(f"In : {incount} bytes\n")
    sys.stdout.write(f"Out: {bitio.outcount} bytes\n")
    if incount != 0:
        cr = (1000 * bitio.outcount + incount // 2) // incount
        sys.stdout.write(f"Out/In: {cr // 1000}.{cr % 1000:03d}\n")

def decode(size):
    global dictsize, qin, match_buf, character, parent
    
    reset_static_state()
    init_tree()
    
    curptr = NIL
    curlen = 0
    count = 0
    printcount = 0
    
    while count < size:
        p = input_code()
        
        if p >= dictsize:
            bitio.error("入力エラー")
            
        prevptr = curptr
        prevlen = curlen
        curptr = p
        curlen = 0
        
        while p != NIL:
            if p >= N and p != qin:
                dequeue(p)
                enqueue(p, qin)
            curlen += 1
            match_buf[MAXMATCH - curlen] = character[p]
            p = parent[p]
            
        base_idx = MAXMATCH - curlen
        for i in range(curlen):
            bitio.outfile.write(bytes([match_buf[base_idx + i]]))
            
        base_slice = match_buf[base_idx:base_idx+curlen]
        update(base_slice, curlen, prevptr, prevlen)
        
        count += curlen
        if count > printcount:
            sys.stdout.write(f"{count:12d}\r")
            sys.stdout.flush()
            printcount += 1024
            
    sys.stdout.write(f"{count:12d}\n")

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
