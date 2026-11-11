#!/usr/bin/env python3
"""Writes a made-up AncestryDNA-style file covering every marker in the library, for layout and length tests.
No real person's data: markers whose single-copy result would be "notable" get the usual genotype, every other
marker gets one copy of its variant, and ClinVar scan positions get the usual letters at their real position.
Usage: python tools/make_sample_file.py OUT.txt"""
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
lib = json.load(open(os.path.join(here, '..', 'library', 'markers.json'), encoding='utf-8'))
rows = []
for i, m in enumerate(lib['markers']):
    a, b = m['alleles']['normal'], m['alleles']['variant']
    het = ''.join(sorted(a + b))
    g = (a, a) if m['genotypes'][het]['status'] == 'notable' else (a, b)
    rows.append((m['rsid'], '1', str(1000 + i), *g))
for v in (lib.get('clinvarScan') or {}).get('variants', []):
    rows.append((v['rs'], '23' if v['chr'] == 'X' else v['chr'], str(v['pos']), v['ref'], v['ref']))
with open(sys.argv[1], 'w', encoding='utf-8', newline='\n') as f:
    f.write('#AncestryDNA raw data download\n#SAMPLE FILE - made-up genotypes for layout tests\n#Data was converted using build 37.1\n')
    f.write('rsid\tchromosome\tposition\tallele1\tallele2\n')
    for r in rows: f.write('\t'.join(r) + '\n')
    for i in range(6000):  # filler rows with made-up rsIDs so the app accepts the file (it requires 5,000+ rows)
        f.write(f'rs9{i:08d}\t2\t{100000 + i}\tA\tG\n')
print(len(rows), 'library rows + 6000 filler rows')
