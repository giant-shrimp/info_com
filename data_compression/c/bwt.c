#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#define BLOCK_SIZE 262144

int global_n;
int global_k;
int global_rank[BLOCK_SIZE];
int temp_rank[BLOCK_SIZE];
int pairs_sa[BLOCK_SIZE];

unsigned char block[BLOCK_SIZE];
unsigned char bwt_data[BLOCK_SIZE];
unsigned char mtf_data[BLOCK_SIZE];

int next_arr[BLOCK_SIZE];
int count[256];
int offset[256];

int compare_suffix(const void *a, const void *b) {
    int i = *(const int *)a;
    int j = *(const int *)b;
    if (global_rank[i] != global_rank[j]) {
        return global_rank[i] - global_rank[j];
    }
    int ri = global_rank[(i + global_k) % global_n];
    int rj = global_rank[(j + global_k) % global_n];
    return ri - rj;
}

void build_suffix_array(unsigned char *text, int n, int *sa) {
    if (n <= 1) {
        if (n == 1) sa[0] = 0;
        return;
    }
    global_n = n;
    for (int i = 0; i < n; i++) {
        global_rank[i] = text[i];
        sa[i] = i;
    }
    global_k = 1;
    while (global_k < n) {
        qsort(sa, n, sizeof(int), compare_suffix);
        
        temp_rank[sa[0]] = 0;
        int r = 0;
        for (int i = 1; i < n; i++) {
            int prev = sa[i - 1];
            int curr = sa[i];
            int rank_prev_1 = global_rank[prev];
            int rank_curr_1 = global_rank[curr];
            int rank_prev_2 = global_rank[(prev + global_k) % n];
            int rank_curr_2 = global_rank[(curr + global_k) % n];
            
            if (rank_prev_1 != rank_curr_1 || rank_prev_2 != rank_curr_2) {
                r++;
            }
            temp_rank[curr] = r;
        }
        for (int i = 0; i < n; i++) {
            global_rank[i] = temp_rank[i];
        }
        if (r == n - 1) break;
        global_k *= 2;
    }
}

void bwt_encode_block(unsigned char *text, int n, unsigned char *out_bwt, uint32_t *primary_idx) {
    if (n == 0) return;
    build_suffix_array(text, n, pairs_sa);
    for (int i = 0; i < n; i++) {
        if (pairs_sa[i] == 0) {
            out_bwt[i] = text[n - 1];
            *primary_idx = i;
        } else {
            out_bwt[i] = text[pairs_sa[i] - 1];
        }
    }
}

void mtf_encode(unsigned char *data, int n, unsigned char *out) {
    unsigned char alphabet[256];
    for (int i = 0; i < 256; i++) alphabet[i] = (unsigned char)i;
    for (int i = 0; i < n; i++) {
        unsigned char c = data[i];
        int idx = 0;
        for (; idx < 256; idx++) {
            if (alphabet[idx] == c) break;
        }
        out[i] = idx;
        for (int j = idx; j > 0; j--) {
            alphabet[j] = alphabet[j - 1];
        }
        alphabet[0] = c;
    }
}

void inverse_bwt(unsigned char *in_bwt, int n, uint32_t primary_idx, unsigned char *out) {
    if (n == 0) return;
    for (int i = 0; i < 256; i++) count[i] = 0;
    for (int i = 0; i < n; i++) {
        count[in_bwt[i]]++;
    }
    int s = 0;
    for (int i = 0; i < 256; i++) {
        offset[i] = s;
        s += count[i];
    }
    for (int i = 0; i < n; i++) {
        unsigned char b = in_bwt[i];
        next_arr[i] = offset[b];
        offset[b]++;
    }
    int curr = primary_idx;
    for (int i = n - 1; i >= 0; i--) {
        out[i] = in_bwt[curr];
        curr = next_arr[curr];
    }
}

void mtf_decode(unsigned char *data, int n, unsigned char *out) {
    unsigned char alphabet[256];
    for (int i = 0; i < 256; i++) alphabet[i] = (unsigned char)i;
    for (int i = 0; i < n; i++) {
        unsigned char idx = data[i];
        unsigned char c = alphabet[idx];
        out[i] = c;
        for (int j = idx; j > 0; j--) {
            alphabet[j] = alphabet[j - 1];
        }
        alphabet[0] = c;
    }
}

void encode_file(FILE *fin, FILE *fout) {
    size_t bytes_read;
    while ((bytes_read = fread(block, 1, BLOCK_SIZE, fin)) > 0) {
        uint32_t primary_idx = 0;
        bwt_encode_block(block, bytes_read, bwt_data, &primary_idx);
        mtf_encode(bwt_data, bytes_read, mtf_data);
        
        unsigned char header[8];
        uint32_t block_size_le = bytes_read;
        uint32_t primary_idx_le = primary_idx;
        
        header[0] = block_size_le & 0xFF;
        header[1] = (block_size_le >> 8) & 0xFF;
        header[2] = (block_size_le >> 16) & 0xFF;
        header[3] = (block_size_le >> 24) & 0xFF;
        header[4] = primary_idx_le & 0xFF;
        header[5] = (primary_idx_le >> 8) & 0xFF;
        header[6] = (primary_idx_le >> 16) & 0xFF;
        header[7] = (primary_idx_le >> 24) & 0xFF;
        
        fwrite(header, 1, 8, fout);
        fwrite(mtf_data, 1, bytes_read, fout);
    }
}

void decode_file(FILE *fin, FILE *fout) {
    unsigned char header[8];
    while (fread(header, 1, 8, fin) == 8) {
        uint32_t block_size = header[0] | (header[1] << 8) | (header[2] << 16) | (header[3] << 24);
        uint32_t primary_idx = header[4] | (header[5] << 8) | (header[6] << 16) | (header[7] << 24);
        
        if (block_size > BLOCK_SIZE) {
            fprintf(stderr, "Block size too large: %u\n", block_size);
            exit(1);
        }
        
        if (block_size > 0) {
            if (fread(mtf_data, 1, block_size, fin) != block_size) {
                fprintf(stderr, "Truncated block data\n");
                exit(1);
            }
            mtf_decode(mtf_data, block_size, bwt_data);
            inverse_bwt(bwt_data, block_size, primary_idx, block);
            fwrite(block, 1, block_size, fout);
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "Usage: %s [e|d] <input> <output>\n", argv[0]);
        return 1;
    }
    char mode = argv[1][0];
    FILE *fin = fopen(argv[2], "rb");
    if (!fin) {
        perror("Failed to open input file");
        return 1;
    }
    FILE *fout = fopen(argv[3], "wb");
    if (!fout) {
        perror("Failed to open output file");
        fclose(fin);
        return 1;
    }
    
    if (mode == 'e' || mode == 'E') {
        encode_file(fin, fout);
    } else if (mode == 'd' || mode == 'D') {
        decode_file(fin, fout);
    } else {
        fprintf(stderr, "Invalid mode '%c'\n", mode);
        return 1;
    }
    
    fclose(fin);
    fclose(fout);
    return 0;
}
