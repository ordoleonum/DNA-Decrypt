#!/usr/bin/env python3
"""Database check: verifies every marker in library/markers.json against dbSNP data (via the Ensembl GRCh37 REST API)
and, optionally, against a real raw data file. Writes library/verification_report.csv.

Usage: python tools/verify_library.py [path/to/raw_data.txt]

Only public rsIDs are sent to Ensembl. A raw data file, if given, is read locally and never sent anywhere, but its
genotypes are written into the report's file_genotype column: do not commit or share the report after such a run.

Checks per marker:
  forward_ok      normal and variant letters are both forward-strand GRCh37 alleles in dbSNP
  variant_minor   the variant letter is the global minor allele (expected for rare variants; for common
                  risk alleles a "no" can be correct, so those rows need a literature check of the risk direction)
  clinvar         ClinVar significance terms Ensembl reports for the rsID
  on_file / file_genotype   whether the raw data file has the marker (chip coverage) and its D/I letters for indels
This script does not replace expert review; it narrows down what a reviewer must look at.
"""
import csv, json, os, sys, urllib.request

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(here, '..')
lib = json.load(open(os.path.join(root, 'library', 'markers.json'), encoding='utf-8'))
raw = sys.argv[1] if len(sys.argv) > 1 else None
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')

rows = [(m['id'], m['rsid'], m['alleles']['normal'], m['alleles']['variant'], m['verify']['level'], m['verify']['note']) for m in lib['markers']]
for c in lib['composites']:
    for rs in c['rsids']:
        a = c['alleleSets'][rs]
        rows.append((c['id'], rs, a[0], a[1], c['verify']['level'], c['verify']['note']))
ids = sorted({r[1] for r in rows})

req = urllib.request.Request('https://grch37.rest.ensembl.org/variation/homo_sapiens',
    data=json.dumps({'ids': ids}).encode(), headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
ens = json.load(urllib.request.urlopen(req, timeout=120))

genos = {}
if raw:
    want = set(ids)
    for line in open(raw, encoding='utf-8', errors='replace'):
        if line.startswith('#') or line.lower().startswith('rsid'): continue
        p = line.rstrip('\r\n').split('\t')
        if p[0] in want:
            genos[p[0]] = (p[3] + p[4]) if len(p) >= 5 else (p[3] if len(p) >= 4 else '')

out, flags = [], 0
for mid, rs, n, v, level, note in rows:
    e = ens.get(rs) or {}
    mp = next((x for x in e.get('mappings', []) if x.get('assembly_name') == 'GRCh37' and x.get('seq_region_name', '').isalnum() and len(x.get('seq_region_name', '')) <= 2), {})
    alleles = (mp.get('allele_string') or '').split('/')
    indel = n in 'DI'
    fwd = 'n/a (indel)' if indel else ('yes' if n in alleles and v in alleles else 'NO')
    minor = e.get('minor_allele') or ''
    vm = '' if indel or not minor else ('yes' if minor == v else 'no')
    if fwd == 'NO': flags += 1
    out.append(dict(id=mid, rsid=rs, normal=n, variant=v, verify_level=level, verify_note=note,
        dbsnp_grch37=mp.get('allele_string', 'NOT FOUND'), chrom=mp.get('seq_region_name', ''), pos=mp.get('start', ''),
        forward_ok=fwd, minor_allele=minor, maf=e.get('MAF', ''), variant_minor=vm,
        clinvar=';'.join(e.get('clinical_significance', [])),
        on_file=('' if not raw else ('yes' if rs in genos else 'no')),
        file_genotype=(genos.get(rs, '') if indel else '')))

path = os.path.join(root, 'library', 'verification_report.csv')
with open(path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f'{len(out)} rows checked; forward-strand problems: {flags}')
for r in out:
    if r['forward_ok'] == 'NO': print('  STRAND', r['id'], r['rsid'], f"library {r['normal']}>{r['variant']}", 'dbSNP', r['dbsnp_grch37'])
for r in out:
    if r['variant_minor'] == 'no': print('  CHECK DIRECTION', r['id'], r['rsid'], f"variant {r['variant']}, minor {r['minor_allele']} ({r['maf']})")
if raw: print('  not on file:', ', '.join(f"{r['id']} ({r['rsid']})" for r in out if r['on_file'] == 'no') or 'none')
print('Wrote', os.path.relpath(path, root))
