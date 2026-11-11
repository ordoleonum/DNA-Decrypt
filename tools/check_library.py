#!/usr/bin/env python3
"""Validates library/markers.json and, optionally, replays a raw data file against it (prints counts only).
Usage: python3 check_library.py [path/to/raw_data.txt]"""
import json, sys, os, collections
here=os.path.dirname(os.path.abspath(__file__))
lib=json.load(open(os.path.join(here,'..','library','markers.json'),encoding='utf-8'))
if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8',errors='replace')
raw=sys.argv[1] if len(sys.argv)>1 else None
STAT={'normal','lower_risk','common_variant','notable','info'}
COMP={'A':'T','T':'A','C':'G','G':'C','D':'D','I':'I'}
errs=[]
cats={c['id'] for c in lib['categories']}
seen=set()
for m in lib['markers']:
    if m['id'] in seen: errs.append('duplicate id '+m['id'])
    seen.add(m['id'])
    if m['category'] not in cats: errs.append('bad category '+m['id'])
    n,v=m['alleles']['normal'],m['alleles']['variant']
    exp={''.join(sorted(n+n)),''.join(sorted(n+v)),''.join(sorted(v+v))}
    if set(m['genotypes'])!=exp: errs.append('genotype keys '+m['id'])
    for k,g in m['genotypes'].items():
        if g['status'] not in STAT or not g['text'].strip(): errs.append(f"bad entry {m['id']} {k}")
mrs={m['rsid']:m for m in lib['markers']}
for c in lib['composites']:
    if c['category'] not in cats: errs.append('bad category '+c['id'])
    for kk,v in c['rules'].items():
        e=c['texts'][v] if isinstance(v,int) else v
        if len(kk.split('|'))!=len(c['rsids']) and not kk.endswith('|*'): errs.append(f"rule key length {c['id']} {kk}")
        if e[0] not in STAT or not e[1].strip(): errs.append(f"bad rule {c['id']} {kk}")
    for r in c['rsids']:  # a combined reading must use the same letters as the single marker it reuses
        if r in mrs and set(c['alleleSets'][r])!={mrs[r]['alleles']['normal'],mrs[r]['alleles']['variant']}: errs.append(f"letters differ {c['id']} {r}")
    if c.get('combined'):
        n=len(c['rsids']); full=sum(1 for kk in c['rules'] if '?' not in kk.split('|'))
        if full!=3**n: errs.append(f"{c['id']}: {full} of {3**n} full genotype combinations have a reading")
sc=lib.get('clinvarScan')
if sc:
    covered=set(mrs)|{r for c in lib['composites'] for r in c['rsids']}
    for v in sc['variants']:
        if v['rs'] in covered: errs.append('scan repeats a library marker '+v['rs'])
        if len(v['ref'])!=1 or len(v['alt'])!=1 or {v['ref'],v['alt']} in ({'A','T'},{'C','G'}): errs.append('scan variant not a clear SNV '+v['rs'])
        if v['af']<sc['meta']['minAlleleFrequency'] or v['stars']<2: errs.append('scan variant breaks a rule '+v['rs'])
    print(f"ClinVar scan: {len(sc['variants'])} variants, snapshot {sc['meta']['snapshot']}")
# 23andMe insertion/deletion probes: one entry for every D/I position, no probe ID used twice, never by position
ind={m['rsid'] for m in lib['markers'] if m['alleles']['normal'] in 'DI'}|{r for c in lib['composites'] for r,a in c['alleleSets'].items() if a[0] in 'DI'}
i23=lib.get('indel23andMe') or {}
if set(i23)!=ind: errs.append('indel23andMe must list exactly the D/I positions: '+str(sorted(set(i23)^ind)))
ids=[i for e in i23.values() for i in e['ids']]
if len(ids)!=len(set(ids)): errs.append('a 23andMe probe ID is listed twice')
for r,e in i23.items():
    if not e['ids'] or not isinstance(e['swap'],bool) or not isinstance(e['rareTwoCopy'],bool): errs.append('bad indel23andMe entry '+r)
if ind & set(lib.get('positions') or {}): errs.append('a D/I position has a position-matching entry')
rs=collections.Counter(m['rsid'] for m in lib['markers'])
errs+=['duplicate rsid '+r for r,c in rs.items() if c>1]
print(f"Library: {len(lib['markers'])} markers + {len(lib['composites'])} composites; structural errors: {len(errs)}")
for e in errs: print('  ',e)
if not raw: sys.exit(1 if errs else 0)

def load(path):
    d={}
    for line in open(path,encoding='utf-8',errors='replace'):
        if line.startswith('#') or line.startswith('rsid'): continue
        p=line.rstrip('\n').split('\t')
        if len(p)>=5: d[p[0]]=(p[3],p[4])
        elif len(p)==4: d[p[0]]=(p[3][0],p[3][1:2]) if len(p[3])>=2 else None
    return d
G=load(raw)
def norm_gt(m,a):
    if a is None or '0' in a or '-' in a: return None
    n,v=m['alleles']['normal'],m['alleles']['variant']
    s=set(a)
    if s<={n,v}: return ''.join(sorted(a))
    if not m['palindromic']:
        f=[COMP.get(x) for x in a]
        if None not in f and set(f)<={n,v}: return ''.join(sorted(f))
    return 'UNRECOGNIZED'
res={}
for m in lib['markers']:
    if m['rsid'] not in G: res[m['id']]=('not_on_file',None); continue
    k=norm_gt(m,G[m['rsid']])
    if k is None: res[m['id']]=('no_call',None)
    elif k=='UNRECOGNIZED': res[m['id']]=('unrecognized',G[m['rsid']])
    else: res[m['id']]=('ok',m['genotypes'][k]['status'])
print('Replay on',os.path.basename(raw),':',dict(collections.Counter(v[0] for v in res.values())))
print('  unrecognized genotypes:',[(i,v[1]) for i,v in res.items() if v[0]=='unrecognized'])
# composites
def gk(rsid,allowed):
    if rsid not in G or G[rsid] is None: return None
    a=''.join(G[rsid])
    if '0' in a or '-' in a or not a: return None
    if len(a)==1: a=a+a
    if not set(a)<=set(allowed):
        f=''.join(COMP.get(x,'?') for x in a)
        if set(allowed) not in ({'A','T'},{'C','G'}) and set(f)<=set(allowed): a=f
        else: return 'UNRECOGNIZED'
    return ''.join(sorted(a))
for c in lib['composites']:
    if len(c['rsids'])<2 or any(len(set(c['alleleSets'][r]))!=2 for r in c['rsids']): errs.append('bad composite '+c['id'])
    keys=[gk(r,c['alleleSets'][r]) for r in c['rsids']]
    def val(v): return c['texts'][v] if isinstance(v,int) else v
    out=None
    if 'UNRECOGNIZED' in keys: out='UNRECOGNIZED '+str(keys)
    elif all(keys): out=val(c['rules'].get('|'.join(keys))) or val(c['rules'].get(keys[0]+'|*'))
    else: out=val(c['rules'].get('|'.join(x or '?' for x in keys)))
    if out is None and keys[0] and keys[0]!='UNRECOGNIZED':
        out=(c.get('partial') or {}).get(c['rsids'][0],{}).get(keys[0]) or (None if all(keys) else c['rules'].get(keys[0]+'|*'))
    print(f"  composite {c['id']}: {'result found' if out and not str(out).startswith('UNREC') else out}")
