import sys
import struct

N = 4096
F = 18
NIL = N

text = bytearray(N + F - 1)
dad = [0] * (N + 1)
lson = [0] * (N + 1)
rson = [0] * (N + 257)

matchpos = 0
matchlen = 0

def init_tree():
    global rson, dad
    for i in range(N + 1, N + 257):
        rson[i] = NIL
    for i in range(N):
        dad[i] = NIL

def insert_node(r):
    global matchpos, matchlen, rson, lson, dad
    
    cmp = 1
    key_idx = r
    p = N + 1 + text[key_idx]
    
    rson[r] = NIL
    lson[r] = NIL
    matchlen = 0
    
    while True:
        if cmp >= 0:
            if rson[p] != NIL:
                p = rson[p]
            else:
                rson[p] = r
                dad[r] = p
                return
        else:
            if lson[p] != NIL:
                p = lson[p]
            else:
                lson[p] = r
                dad[r] = p
                return
                
        for i in range(1, F):
            cmp = text[key_idx + i] - text[p + i]
            if cmp != 0:
                break
        else:
            i = F
            
        if i > matchlen:
            matchpos = p
            matchlen = i
            if matchlen >= F:
                break
                
    dad[r] = dad[p]
    lson[r] = lson[p]
    rson[r] = rson[p]
    dad[lson[p]] = r
    dad[rson[p]] = r
    
    if rson[dad[p]] == p:
        rson[dad[p]] = r
    else:
        lson[dad[p]] = r
        
    dad[p] = NIL

def delete_node(p):
    global rson, lson, dad
    
    if dad[p] == NIL:
        return
        
    if rson[p] == NIL:
        q = lson[p]
    elif lson[p] == NIL:
        q = rson[p]
    else:
        q = lson[p]
        if rson[q] != NIL:
            while rson[q] != NIL:
                q = rson[q]
            rson[dad[q]] = lson[q]
            dad[lson[q]] = dad[q]
            lson[q] = lson[p]
            dad[lson[p]] = q
        rson[q] = rson[p]
        dad[rson[p]] = q
        
    dad[q] = dad[p]
    if rson[dad[p]] == p:
        rson[dad[p]] = q
    else:
        lson[dad[p]] = q
        
    dad[p] = NIL

def encode(infile, outfile):
    global matchlen, text
    
    init_tree()
    code = bytearray(17)
    code[0] = 0
    codeptr = 1
    mask = 1
    
    s = 0
    r = N - F
    for i in range(s, r):
        text[i] = 0
        
    length = 0
    for i in range(F):
        b = infile.read(1)
        if not b:
            break
        text[r + i] = b[0]
        length += 1
        
    incount = length
    outcount = 0
    printcount = 0
    
    if incount == 0:
        return
        
    for i in range(1, F + 1):
        insert_node(r - i)
        
    insert_node(r)
    
    while length > 0:
        if matchlen > length:
            matchlen = length
            
        if matchlen < 3:
            matchlen = 1
            code[0] |= mask
            code[codeptr] = text[r]
            codeptr += 1
        else:
            code[codeptr] = matchpos & 0xFF
            codeptr += 1
            code[codeptr] = (((matchpos >> 4) & 0xF0) | (matchlen - 3)) & 0xFF
            codeptr += 1
            
        mask <<= 1
        if mask == 0x100:
            outfile.write(code[:codeptr])
            outcount += codeptr
            code[0] = 0
            codeptr = 1
            mask = 1
            
        lastmatchlen = matchlen
        
        i = 0
        while i < lastmatchlen:
            b = infile.read(1)
            if not b:
                break
            c = b[0]
            
            delete_node(s)
            text[s] = c
            if s < F - 1:
                text[s + N] = c
                
            s = (s + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            insert_node(r)
            i += 1
            
        incount += i
        if incount > printcount:
            sys.stdout.write(f"{incount:12d}\r")
            sys.stdout.flush()
            printcount += 1024
            
        while i < lastmatchlen:
            delete_node(s)
            s = (s + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            length -= 1
            if length > 0:
                insert_node(r)
            i += 1
            
    if codeptr > 1:
        outfile.write(code[:codeptr])
        outcount += codeptr
        
    sys.stdout.write(f"In : {incount} bytes\n")
    sys.stdout.write(f"Out: {outcount} bytes\n")
    if incount != 0:
        cr = (1000 * outcount + incount // 2) // incount
        sys.stdout.write(f"Out/In: {cr // 1000}.{cr % 1000:03d}\n")

def decode(size, infile, outfile):
    global text
    
    for i in range(N - F):
        text[i] = 0
        
    r = N - F
    flags = 0
    count = 0
    
    while count < size:
        flags >>= 1
        if (flags & 256) == 0:
            b = infile.read(1)
            if not b:
                break
            flags = b[0] | 0xFF00
            
        if flags & 1:
            b = infile.read(1)
            if not b:
                break
            c = b[0]
            outfile.write(bytes([c]))
            count += 1
            text[r] = c
            r = (r + 1) & (N - 1)
        else:
            b_i = infile.read(1)
            if not b_i:
                break
            b_j = infile.read(1)
            if not b_j:
                break
                
            i_val = b_i[0]
            j_val = b_j[0]
            
            i_val |= ((j_val & 0xF0) << 4)
            j_val = (j_val & 0x0F) + 2
            
            for k in range(j_val + 1):
                if count >= size:
                    break
                c = text[(i_val + k) & (N - 1)]
                outfile.write(bytes([c]))
                count += 1
                text[r] = c
                r = (r + 1) & (N - 1)
                
    sys.stdout.write(f"{size:12d}\n")

def main():
    if len(sys.argv) != 4:
        sys.stderr.write("\n使用法は本文を参照してください\n")
        sys.exit(1)
        
    mode = sys.argv[1]
    if mode not in ('E', 'e', 'D', 'd'):
        sys.stderr.write("\n使用法は本文を参照してください\n")
        sys.exit(1)
        
    try:
        infile = open(sys.argv[2], "rb")
    except IOError:
        sys.stderr.write("\n入力ファイルが開きません\n")
        sys.exit(1)
        
    try:
        outfile = open(sys.argv[3], "wb")
    except IOError:
        sys.stderr.write("\n出力ファイルが開きません\n")
        sys.exit(1)
        
    if mode in ('E', 'e'):
        infile.seek(0, 2)
        size = infile.tell()
        outfile.write(struct.pack('<Q', size))
        infile.seek(0)
        encode(infile, outfile)
    else:
        size_data = infile.read(8)
        if len(size_data) == 8:
            size = struct.unpack('<Q', size_data)[0]
            decode(size, infile, outfile)
            
    infile.close()
    outfile.close()

if __name__ == '__main__':
    main()
