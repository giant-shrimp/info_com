import os
import sys
import time
import subprocess
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
C_DIR = BASE_DIR / "c"
PY_DIR = BASE_DIR / "python"
TEXT_DIR = BASE_DIR / "textdata"
OUT_DIR = BASE_DIR / "benchmark_output"

METHODS = ["arith", "huffman", "slide", "squeeze"]
TEXT_FILES = sorted([f for f in TEXT_DIR.iterdir() if f.is_file()])

def compile_c_tools():
    print("Compiling C tools...")
    c_out = C_DIR / "output"
    c_out.mkdir(exist_ok=True)
    for method in METHODS:
        src = C_DIR / f"{method}.c"
        exe = c_out / f"{method}_c"
        subprocess.run(["gcc", "-O2", str(src), "-o", str(exe)], check=True)

def run_cmd(cmd):
    start = time.perf_counter()
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    end = time.perf_counter()
    return end - start

def check_roundtrip(orig, decoded):
    # Use cmp to verify files are identical
    result = subprocess.run(["cmp", "-s", str(orig), str(decoded)])
    if result.returncode != 0:
        print(f"  [ERROR] Roundtrip failed: {orig.name} != {decoded.name}", file=sys.stderr)
        sys.exit(1)

def run_benchmark():
    OUT_DIR.mkdir(exist_ok=True)
    compile_c_tools()
    
    results = []
    
    print(f"{'File':<15} | {'Method':<10} | {'BWT':<5} | {'Size (B)':<10} | {'Comp (B)':<10} | {'Ratio':<7} | {'Enc Time (s)':<12} | {'Dec Time (s)':<12}")
    print("-" * 95)
    
    for txt_file in TEXT_FILES:
        orig_size = txt_file.stat().st_size
        
        # 1. Base Methods (Without BWT)
        for method in METHODS:
            exe = C_DIR / "output" / f"{method}_c"
            enc_file = OUT_DIR / f"{txt_file.name}.{method}.enc"
            dec_file = OUT_DIR / f"{txt_file.name}.{method}.dec"
            
            enc_time = run_cmd([str(exe), "e", str(txt_file), str(enc_file)])
            dec_time = run_cmd([str(exe), "d", str(enc_file), str(dec_file)])
            
            check_roundtrip(txt_file, dec_file)
            comp_size = enc_file.stat().st_size
            ratio = comp_size / orig_size
            
            results.append({
                "File": txt_file.name, "Method": method, "BWT": "No",
                "OrigSize": orig_size, "CompSize": comp_size, "Ratio": ratio,
                "BWT_EncTime": 0.0, "Comp_EncTime": enc_time,
                "BWT_DecTime": 0.0, "Comp_DecTime": dec_time
            })
            
            print(f"{txt_file.name:<15} | {method:<10} | {'No':<5} | {orig_size:<10} | {comp_size:<10} | {ratio:.4f}  | {enc_time:<12.4f} | {dec_time:<12.4f}")
            
        # 2. Methods With BWT
        bwt_file = OUT_DIR / f"{txt_file.name}.bwt"
        bwt_enc_time = run_cmd(["python3", str(PY_DIR / "bwt.py"), "e", str(txt_file), str(bwt_file)])
        
        for method in METHODS:
            exe = C_DIR / "output" / f"{method}_c"
            enc_file = OUT_DIR / f"{txt_file.name}.bwt.{method}.enc"
            dec_file = OUT_DIR / f"{txt_file.name}.bwt.{method}.dec"
            final_dec = OUT_DIR / f"{txt_file.name}.bwt.{method}.final"
            
            comp_enc_time = run_cmd([str(exe), "e", str(bwt_file), str(enc_file)])
            comp_dec_time = run_cmd([str(exe), "d", str(enc_file), str(dec_file)])
            
            bwt_dec_time = run_cmd(["python3", str(PY_DIR / "bwt.py"), "d", str(dec_file), str(final_dec)])
            
            check_roundtrip(txt_file, final_dec)
            comp_size = enc_file.stat().st_size
            ratio = comp_size / orig_size
            
            tot_enc_time = bwt_enc_time + comp_enc_time
            tot_dec_time = bwt_dec_time + comp_dec_time
            
            results.append({
                "File": txt_file.name, "Method": method, "BWT": "Yes",
                "OrigSize": orig_size, "CompSize": comp_size, "Ratio": ratio,
                "BWT_EncTime": bwt_enc_time, "Comp_EncTime": comp_enc_time,
                "BWT_DecTime": bwt_dec_time, "Comp_DecTime": comp_dec_time
            })
            
            print(f"{txt_file.name:<15} | {method:<10} | {'Yes':<5} | {orig_size:<10} | {comp_size:<10} | {ratio:.4f}  | {tot_enc_time:<12.4f} | {tot_dec_time:<12.4f}")
            
    # Write CSV
    csv_path = BASE_DIR / "benchmark_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved to {csv_path}")

if __name__ == "__main__":
    run_benchmark()
