import sys
import struct

BLOCK_SIZE = 256 * 1024  # 256 kB

def build_suffix_array(text):
    n = len(text)
    if n <= 1:
        return list(range(n))
    rank = list(text)
    k = 1
    
    while k < n:
        pairs = [((rank[i], rank[(i+k)%n]), i) for i in range(n)]
        pairs.sort(key=lambda x: x[0])
        
        sa = [x[1] for x in pairs]
        
        rank = [0] * n
        r = 0
        rank[sa[0]] = 0
        for i in range(1, n):
            if pairs[i][0] != pairs[i-1][0]:
                r += 1
            rank[sa[i]] = r
            
        if r == n - 1:
            break
        k *= 2
        
    return sa

def bwt(text):
    n = len(text)
    if n == 0:
        return bytearray(), 0
    sa = build_suffix_array(text)
    bwt_data = bytearray(n)
    primary_idx = 0
    for i in range(n):
        if sa[i] == 0:
            bwt_data[i] = text[n - 1]
            primary_idx = i
        else:
            bwt_data[i] = text[sa[i] - 1]
    return bwt_data, primary_idx

def inverse_bwt(bwt_data, primary_idx):
    n = len(bwt_data)
    if n == 0:
        return bytearray()
    
    count = [0] * 256
    for b in bwt_data:
        count[b] += 1
        
    offset = [0] * 256
    s = 0
    for i in range(256):
        offset[i] = s
        s += count[i]
        
    next_arr = [0] * n
    for i, b in enumerate(bwt_data):
        next_arr[i] = offset[b]
        offset[b] += 1
        
    out = bytearray(n)
    curr = primary_idx
    for i in range(n - 1, -1, -1):
        out[i] = bwt_data[curr]
        curr = next_arr[curr]
    return out

def mtf_encode(data):
    alphabet = list(range(256))
    out = bytearray(len(data))
    for i, byte in enumerate(data):
        idx = alphabet.index(byte)
        out[i] = idx
        if idx != 0:
            alphabet.insert(0, alphabet.pop(idx))
    return out

def mtf_decode(data):
    alphabet = list(range(256))
    out = bytearray(len(data))
    for i, idx in enumerate(data):
        byte = alphabet[idx]
        out[i] = byte
        if idx != 0:
            alphabet.insert(0, alphabet.pop(idx))
    return out

def encode(infile, outfile):
    # Process in blocks
    while True:
        block = infile.read(BLOCK_SIZE)
        if not block:
            break
        
        bwt_data, primary_idx = bwt(block)
        mtf_data = mtf_encode(bwt_data)
        
        # Write block header: block_size (4 bytes), primary_idx (4 bytes)
        outfile.write(struct.pack('<I', len(block)))
        outfile.write(struct.pack('<I', primary_idx))
        outfile.write(mtf_data)

def decode(infile, outfile):
    while True:
        header = infile.read(8)
        if not header:
            break
        if len(header) < 8:
            sys.stderr.write("Truncated file header.\n")
            sys.exit(1)
            
        block_size, primary_idx = struct.unpack('<II', header)
        mtf_data = infile.read(block_size)
        if len(mtf_data) < block_size:
            sys.stderr.write("Truncated block data.\n")
            sys.exit(1)
            
        bwt_data = mtf_decode(mtf_data)
        orig_data = inverse_bwt(bwt_data, primary_idx)
        outfile.write(orig_data)

def main():
    if len(sys.argv) != 4:
        sys.stderr.write("Usage: python3 bwt.py [e|d] <input> <output>\n")
        sys.exit(1)
        
    mode = sys.argv[1].lower()
    in_path = sys.argv[2]
    out_path = sys.argv[3]
    
    with open(in_path, 'rb') as f_in, open(out_path, 'wb') as f_out:
        if mode == 'e':
            encode(f_in, f_out)
        elif mode == 'd':
            decode(f_in, f_out)
        else:
            sys.stderr.write("Invalid mode. Use 'e' or 'd'.\n")
            sys.exit(1)

if __name__ == '__main__':
    main()
