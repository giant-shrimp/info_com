import os
import sys
import time
import subprocess
import csv
import argparse
import statistics
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
C_DIR = BASE_DIR / "c"
PY_DIR = BASE_DIR / "python"
TEXT_DIR = BASE_DIR / "textdata"
TEST_DIR = BASE_DIR / "textdata_test"
OUT_DIR = BASE_DIR / "output" / "files"

METHODS = ["arith", "huffman", "slide", "squeeze"]
TEXT_FILES = sorted([f for f in TEXT_DIR.glob("*.txt") if f.is_file()])
TEST_FILES = sorted([f for f in TEST_DIR.glob("*.txt") if f.is_file()])

def compile_c_tools():
    print("Compiling C tools...")
    c_out = BASE_DIR / "output" / "bin"
    c_out.mkdir(parents=True, exist_ok=True)
    
    # Compile BWT
    subprocess.run(["gcc", "-O2", str(C_DIR / "bwt.c"), "-o", str(c_out / "bwt_c")], check=True)
    
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

def get_cmd(impl_type, method, mode, in_file, out_file):
    if impl_type == "c":
        bin_dir = BASE_DIR / "output" / "bin"
        if method == "bwt":
            exe = bin_dir / "bwt_c"
        else:
            exe = bin_dir / f"{method}_c"
        return [str(exe), mode, str(in_file), str(out_file)]
    else:
        if method == "bwt":
            script = PY_DIR / "bwt.py"
        else:
            script = PY_DIR / f"{method}.py"
        return ["python3", str(script), mode, str(in_file), str(out_file)]

def measure_median_time(cmd, runs=3):
    times = []
    for _ in range(runs):
        times.append(run_cmd(cmd))
    return statistics.median(times)

def run_benchmark(bwt_impl, comp_impl):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if bwt_impl == "c" or comp_impl == "c":
        compile_c_tools()
    
    results = []
    
    print(f"{'File':<16} | {'Method':<10} | {'BWT':<5} | {'Size (B)':<10} | {'Comp (B)':<10} | {'Ratio':<7} | {'Enc Time (s)':<12} | {'Dec Time (s)':<12}")
    print("-" * 100)
    
    for txt_file in TEXT_FILES:
        orig_size = txt_file.stat().st_size
        
        # 1. Base Methods (Without BWT)
        for method in METHODS:
            enc_file = OUT_DIR / f"{txt_file.name}.{method}.enc"
            dec_file = OUT_DIR / f"{txt_file.name}.{method}.dec"
            
            enc_cmd = get_cmd(comp_impl, method, "e", txt_file, enc_file)
            dec_cmd = get_cmd(comp_impl, method, "d", enc_file, dec_file)
            
            enc_time = measure_median_time(enc_cmd)
            dec_time = measure_median_time(dec_cmd)
            
            check_roundtrip(txt_file, dec_file)
            comp_size = enc_file.stat().st_size if orig_size > 0 else 0
            ratio = (comp_size / orig_size) if orig_size > 0 else 0.0
            
            results.append({
                "File": txt_file.name, "Method": method, "BWT": "No",
                "OrigSize": orig_size, "CompSize": comp_size, "Ratio": ratio,
                "BWT_EncTime": 0.0, "Comp_EncTime": enc_time,
                "BWT_DecTime": 0.0, "Comp_DecTime": dec_time
            })
            
            print(f"{txt_file.name:<16} | {method:<10} | {'No':<5} | {orig_size:<10} | {comp_size:<10} | {ratio:.4f}  | {enc_time:<12.4f} | {dec_time:<12.4f}")
            
        # 2. Methods With BWT
        bwt_file = OUT_DIR / f"{txt_file.name}.bwt"
        bwt_enc_cmd = get_cmd(bwt_impl, "bwt", "e", txt_file, bwt_file)
        bwt_enc_time = measure_median_time(bwt_enc_cmd)
        
        for method in METHODS:
            enc_file = OUT_DIR / f"{txt_file.name}.bwt.{method}.enc"
            dec_file = OUT_DIR / f"{txt_file.name}.bwt.{method}.dec"
            final_dec = OUT_DIR / f"{txt_file.name}.bwt.{method}.final"
            
            comp_enc_cmd = get_cmd(comp_impl, method, "e", bwt_file, enc_file)
            comp_dec_cmd = get_cmd(comp_impl, method, "d", enc_file, dec_file)
            bwt_dec_cmd = get_cmd(bwt_impl, "bwt", "d", dec_file, final_dec)
            
            comp_enc_time = measure_median_time(comp_enc_cmd)
            comp_dec_time = measure_median_time(comp_dec_cmd)
            bwt_dec_time = measure_median_time(bwt_dec_cmd)
            
            check_roundtrip(txt_file, final_dec)
            comp_size = enc_file.stat().st_size if orig_size > 0 else 0
            ratio = (comp_size / orig_size) if orig_size > 0 else 0.0
            
            tot_enc_time = bwt_enc_time + comp_enc_time
            tot_dec_time = bwt_dec_time + comp_dec_time
            
            results.append({
                "File": txt_file.name, "Method": method, "BWT": "Yes",
                "OrigSize": orig_size, "CompSize": comp_size, "Ratio": ratio,
                "BWT_EncTime": bwt_enc_time, "Comp_EncTime": comp_enc_time,
                "BWT_DecTime": bwt_dec_time, "Comp_DecTime": comp_dec_time
            })
            
            print(f"{txt_file.name:<16} | {method:<10} | {'Yes':<5} | {orig_size:<10} | {comp_size:<10} | {ratio:.4f}  | {tot_enc_time:<12.4f} | {tot_dec_time:<12.4f}")
            
    # Boundary Tests (Silence output, just assert roundtrip)
    print("\nRunning boundary tests...")
    for txt_file in TEST_FILES:
        for method in METHODS:
            # No BWT
            enc_file = OUT_DIR / f"{txt_file.name}.{method}.enc"
            dec_file = OUT_DIR / f"{txt_file.name}.{method}.dec"
            run_cmd(get_cmd(comp_impl, method, "e", txt_file, enc_file))
            run_cmd(get_cmd(comp_impl, method, "d", enc_file, dec_file))
            check_roundtrip(txt_file, dec_file)
            
            # With BWT
            bwt_file = OUT_DIR / f"{txt_file.name}.bwt"
            run_cmd(get_cmd(bwt_impl, "bwt", "e", txt_file, bwt_file))
            enc_file = OUT_DIR / f"{txt_file.name}.bwt.{method}.enc"
            dec_file = OUT_DIR / f"{txt_file.name}.bwt.{method}.dec"
            final_dec = OUT_DIR / f"{txt_file.name}.bwt.{method}.final"
            run_cmd(get_cmd(comp_impl, method, "e", bwt_file, enc_file))
            run_cmd(get_cmd(comp_impl, method, "d", enc_file, dec_file))
            run_cmd(get_cmd(bwt_impl, "bwt", "d", dec_file, final_dec))
            check_roundtrip(txt_file, final_dec)
    print("Boundary tests passed successfully!")

    # Write CSV
    csv_path = BASE_DIR / "output" / "benchmark_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved to {csv_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Compression Benchmark")
    parser.add_argument("--bwt-impl", choices=["c", "py"], default="c", help="BWT implementation (default: c)")
    parser.add_argument("--comp-impl", choices=["c", "py"], default="c", help="Compressor implementation (default: c)")
    args = parser.parse_args()
    
    run_benchmark(args.bwt_impl, args.comp_impl)
