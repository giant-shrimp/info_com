#!/usr/bin/env python3
import urllib.request
import re
import os

files = {
    'alice.txt': 'https://www.gutenberg.org/cache/epub/11/pg11.txt',
    'moby_dick.txt': 'https://www.gutenberg.org/cache/epub/2701/pg2701.txt',
    'frankenstein.txt': 'https://www.gutenberg.org/cache/epub/84/pg84.txt',
    'pride.txt': 'https://www.gutenberg.org/cache/epub/1342/pg1342.txt'
}

# The script is located in the textdata directory, so we save files in the same directory.
out_dir = os.path.dirname(os.path.abspath(__file__))

for filename, url in files.items():
    print(f"Downloading {filename}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            text = response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        continue
    
    # Remove CRLF -> LF
    text = text.replace('\r\n', '\n')
    
    # Remove Gutenberg headers
    start_match = re.search(r'\*\*\* START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*', text)
    if start_match:
        text = text[start_match.end():]
        
    # Remove Gutenberg footers
    end_match = re.search(r'\*\*\* END OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*', text)
    if end_match:
        text = text[:end_match.start()]
        
    text = text.strip() + '\n'
    
    out_path = os.path.join(out_dir, filename)
    with open(out_path, 'wb') as f:
        f.write(text.encode('utf-8'))
    print(f"Saved {filename}: {os.path.getsize(out_path)} bytes")

print("Download complete.")
