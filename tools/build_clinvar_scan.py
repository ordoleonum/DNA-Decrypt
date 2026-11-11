#!/usr/bin/env python3
"""Builds library/clinvar_scan.json, the strict "Wider ClinVar scan" list, from ClinVar's GRCh37 VCF.

Usage: python -I tools/build_clinvar_scan.py path/to/clinvar.vcf.gz
Download: https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh37/clinvar.vcf.gz (check it against the .md5 file).
ClinVar is NCBI public data with no restrictions on use. Only rsIDs, positions and ClinVar text go into the app.

A variant is kept only if it passes ALL of these rules (chosen to keep chip false positives as close to zero as possible):
 1. Single-letter change (SNV) with one rsID, on chromosomes 1-22 or X, GRCh37 positions.
    (The engine then requires the same rsID, chromosome, position and exact letters in the user's file; no strand flipping.)
 2. Not an A/T or C/G change (strand cannot be told apart).
 3. No insertions or deletions (excluded by rule 1).
 4. ClinVar classification exactly "Pathogenic" (not "Likely pathogenic", not mixed, not conflicting),
    with 2+ stars: multiple submitters with no conflicts, an expert panel, or a practice guideline.
 5. Allele frequency of at least 1 in 1,000 (0.1%) in EVERY source that reports it (ExAC, 1000 Genomes, ESP),
    with at least 2 sources reporting. Chips read rarer variants unreliably (Weedon et al., BMJ 2021), and a high
    frequency seen in only one source is often a sequencing artifact at a hard-to-read site.
 6. Not on EXCLUDE below (variants whose reported frequency is impossible for their condition, a sign of a bad site).
 7. (Applied by the engine) two copies of a variant rarer than 1% (lowest source) are not reported; they are almost
    always chip errors.
"""
import gzip, json, os, sys, collections

STARS = {'criteria_provided,_multiple_submitters,_no_conflicts': 2, 'reviewed_by_expert_panel': 3, 'practice_guideline': 4}
CHROMS = {str(i) for i in range(1, 23)} | {'X'}
PAL = ({'A', 'T'}, {'C', 'G'})
MIN_AF = 0.001
EXCLUDE = {
    'rs200962248': 'NF1 splice variant reported at 0.8-1.4%, but neurofibromatosis type 1 affects about 1 in 3,000 people; '
                   'the frequency points to a misread site (NF1 has many look-alike pseudogene copies).',
    'rs6445': 'CYP21A2 sits next to a 98%-identical pseudogene (CYP21A1P); chips and short-read sequencing often confuse '
              'the two, so calls here are unreliable.',
}
# Plain-language notes for kept variants (checked 2026-11-08: ClinGen hearing-loss panel 2019 for GJB2; Pompe LOPD
# literature for GAA; Matthijs 2000 and gnomAD for PMM2; Haematologica / Casonato 2022 for VWF R854Q).
# A variant added by a later ClinVar refresh with no note gets the generic text in the engine.
ABCA4 = ('ABCA4', 'One copy of a harmful variant in ABCA4, a gene for the light-sensing cells of the eye. ABCA4 conditions, such as '
         'Stargardt disease (a cause of central vision loss), are recessive: they happen only when both copies of the gene carry a '
         'harmful variant. With one copy you are a carrier and usually have no symptoms. It matters for children if a partner also '
         'carries an ABCA4 variant.')
NOTES = {
    'rs1800553': ABCA4, 'rs61754045': ABCA4, 'rs62642564': ABCA4,
    'rs386834236': ('GAA c.-32-13T>G', 'One copy of the most common variant behind late-onset Pompe disease, a slowly progressing '
                    'muscle condition. Pompe disease is recessive, so one copy makes you a carrier, usually with no symptoms. It matters '
                    'for children if a partner is also a carrier.'),
    'rs35887622': ('GJB2 M34T', 'One copy of a mild GJB2 hearing-loss variant. GJB2 hearing loss is recessive: people with two '
                   'variants typically have mild to moderate hearing loss, and some have none. With one copy you are a carrier.'),
    'rs72474224': ('GJB2 V37I', 'One copy of a mild GJB2 hearing-loss variant that is common in people of East Asian ancestry. GJB2 '
                   'hearing loss is recessive: people with two variants typically have mild to moderate hearing loss, and some have '
                   'none. With one copy you are a carrier.'),
    'rs28936415': ('PMM2 R141H', 'One copy of the most common variant behind PMM2-CDG, a rare inherited metabolic condition that '
                   'appears in early childhood. It is recessive, so one copy makes you a carrier with no symptoms. Roughly 1 in 60 to '
                   '1 in 220 people of European ancestry carry it.'),
    'rs41276738': ('VWF R854Q', 'One copy of R854Q, the most common cause of type 2N von Willebrand disease, a mild bleeding disorder. '
                   'Bleeding problems usually happen only with two copies, or together with another VWF variant; one copy usually '
                   'causes none. Mention it to your doctor if you or relatives have unusual bleeding, or before surgery.'),
}
SKIP_DN = {'not provided', 'not specified', 'See cases', 'none provided', 'Inborn genetic diseases',
           'Fetal anomalies with a likely genetic cause'}

def conditions(dn):
    out = []
    for d in dn.split('|'):
        d = d.replace('_', ' ').strip()
        if d and d not in SKIP_DN and d not in out: out.append(d)
    return out[:3]

def main(path):
    steps = collections.Counter(); out = []; date = ''
    for line in gzip.open(path, 'rt', encoding='utf-8'):
        if line.startswith('##fileDate='): date = line.strip().split('=', 1)[1]
        if line.startswith('#'): continue
        steps['all ClinVar records'] += 1
        c, pos, _id, ref, alt, _q, _f, inf = line.rstrip('\n').split('\t')[:8]
        info = dict(x.split('=', 1) if '=' in x else (x, '') for x in inf.split(';'))
        if info.get('CLNSIG') != 'Pathogenic': continue
        steps['1. classified exactly Pathogenic'] += 1
        stars = STARS.get(info.get('CLNREVSTAT', ''))
        if not stars: continue
        steps['2. reviewed: 2+ stars'] += 1
        rs = info.get('RS', '')
        if info.get('CLNVC') != 'single_nucleotide_variant' or len(ref) != 1 or len(alt) != 1 or ref not in 'ACGT' or alt not in 'ACGT' \
           or c not in CHROMS or not rs.isdigit():
            continue
        steps['3. single-letter change with one rsID, chr 1-22 or X'] += 1
        if {ref, alt} in PAL: continue
        steps['4. not A/T or C/G'] += 1
        afs = [float(info[k]) for k in ('AF_EXAC', 'AF_TGP', 'AF_ESP') if info.get(k)]
        if len(afs) < 2 or min(afs) < MIN_AF: continue
        steps['5. at least 1 in 1,000 in every source, 2+ sources agree'] += 1
        if 'rs' + rs in EXCLUDE: continue
        steps['6. not on the known-artifact list'] += 1
        gene = info.get('GENEINFO', '').split('|')[0].split(':')[0]
        mc = info.get('MC', '').split('|')[1].split(',')[0].replace('_', ' ') if '|' in info.get('MC', '') else ''
        label, note = NOTES.get('rs' + rs, (gene, ''))
        out.append(dict(rs='rs' + rs, chr=c, pos=int(pos), ref=ref, alt=alt, gene=gene, name=label, note=note,
                        conditions=conditions(info.get('CLNDN', '')),
                        stars=stars, af=round(min(afs), 5), afMax=round(max(afs), 5), consequence=mc, variationId=_id))
    out.sort(key=lambda v: (v['gene'], v['rs']))
    meta = dict(source='ClinVar GRCh37 VCF (NCBI, public data)', snapshot=date, minAlleleFrequency=MIN_AF,
                homozygousRareCutoff=0.01, steps=dict(steps), kept=len(out), excluded=EXCLUDE)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, '..', 'library', 'clinvar_scan.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(meta=meta, variants=out), f, indent=0, ensure_ascii=False)
    for k, v in steps.items(): print(f'{v:>9,}  {k}')
    print('snapshot', date, '| kept', len(out))

if __name__ == '__main__':
    main(sys.argv[1])
