/* DNA Health Marker engine. Pure JavaScript, no dependencies, no network access.
   Works in a browser (window.DnaEngine) and in Node (require). */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DnaEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var COMP = { A: 'T', T: 'A', C: 'G', G: 'C', D: 'D', I: 'I' };
  var VALID = 'ACGTDI';
  var ORDER = { notable: 0, common_variant: 1, lower_risk: 2, normal: 3, info: 4 };
  var TIERS = ['high', 'medium', 'low'];

  function libraryRsids(lib) {
    var s = new Set();
    lib.markers.forEach(function (m) { s.add(m.rsid); });
    lib.composites.forEach(function (c) { c.rsids.forEach(function (r) { s.add(r); }); });
    if (lib.clinvarScan) lib.clinvarScan.variants.forEach(function (v) { s.add(v.rs); });
    return s;
  }

  /* ---------- parsing ---------- */
  function parseGenotype(format, parts) {
    var a;
    if (format === 'ancestry') {
      a = [String(parts[3] || '').toUpperCase(), String(parts[4] || '').toUpperCase()];
    } else {
      var g = String(parts[3] || '').toUpperCase().replace(/\s/g, '');
      a = g.split('');
    }
    if (!a.length || a.length > 2) return { noCall: true };
    for (var i = 0; i < a.length; i++) if (a[i].length !== 1 || VALID.indexOf(a[i]) < 0) return { noCall: true };
    if (a.length === 1) return { alleles: [a[0], a[0]], hemizygous: true };
    return { alleles: a };
  }

  /* Reads the whole file text but KEEPS only the rsids in `wanted` (privacy and memory). */
  /* Positions of single-letter markers, keyed "chr:pos" (GRCh37). Used only for 23andMe files, which list some markers
     under internal "i" IDs instead of rsIDs. Insertion/deletion markers are never matched this way. */
  function positionIndex(lib) {
    var idx = Object.create(null), P = lib.positions || {};
    function add(rs, letters) {
      var p = P[rs];
      if (!p || letters.indexOf('D') >= 0 || letters.indexOf('I') >= 0) return;
      var k = p[0] + ':' + p[1];
      if (!idx[k]) idx[k] = { rsid: rs, letters: letters };
    }
    lib.markers.forEach(function (m) { add(m.rsid, [m.alleles.normal, m.alleles.variant]); });
    lib.composites.forEach(function (c) { c.rsids.forEach(function (r) { add(r, c.alleleSets[r]); }); });
    return idx;
  }

  function parse(text, wanted, posIndex) {
    var genotypes = Object.create(null), header = [], format = null, delim = null, rows = 0, cands = Object.create(null);
    var pos = 0, n = text.length;
    while (pos < n) {
      var end = text.indexOf('\n', pos); if (end === -1) end = n;
      var line = text.slice(pos, end); pos = end + 1;
      if (line.charCodeAt(line.length - 1) === 13) line = line.slice(0, -1);
      if (!line) continue;
      if (line.charCodeAt(0) === 35) { if (header.length < 80) header.push(line); continue; }
      if (delim === null) {
        delim = line.indexOf('\t') >= 0 ? '\t' : (line.indexOf(',') >= 0 ? ',' : null);
        if (delim === null) continue;
      }
      var parts = line.split(delim);
      if (delim === ',') for (var k = 0; k < parts.length; k++) parts[k] = parts[k].replace(/^"|"$/g, '');
      if (parts[0].toLowerCase() === 'rsid') {
        if (!format) format = parts.length >= 5 ? 'ancestry' : (parts.length === 4 ? 'four_column' : null);
        continue;
      }
      if (!format) format = parts.length >= 5 ? 'ancestry' : (parts.length === 4 ? 'four_column' : null);
      if (!format) continue;
      rows++;
      var rs = parts[0];
      if (wanted && !wanted.has(rs)) {
        if (posIndex && parts.length >= 4) {
          var hit = posIndex[normChr(parts[1]) + ':' + parts[2]];
          if (hit) { var c = parseGenotype(format, parts); c.sourceId = rs; (cands[hit.rsid] = cands[hit.rsid] || []).push({ g: c, letters: hit.letters }); }
        }
        continue;
      }
      var gt = parseGenotype(format, parts);
      gt.chr = parts[1]; gt.pos = parts[2]; /* kept so the ClinVar scan can require an exact position match */
      genotypes[rs] = gt;
    }
    var head = header.join('\n').toLowerCase();
    var vendor = format === 'ancestry' ? 'AncestryDNA'
      : (head.indexOf('23andme') >= 0 ? '23andMe' : (format === 'four_column' ? 'Compatible 4-column file' : 'Unknown'));
    /* 23andMe only: a marker missing by rsID is taken from a row at the exact same position, but only if every letter
       is one of the marker's two expected letters (no strand flipping) and all such rows agree. */
    if (vendor === '23andMe') Object.keys(cands).forEach(function (rsid) {
      if (genotypes[rsid]) return;
      var list = cands[rsid], byKey = Object.create(null);
      list.forEach(function (x) {
        if (!x.g.noCall && x.g.alleles.every(function (a) { return x.letters.indexOf(a) >= 0; })) byKey[sortedKey(x.g.alleles)] = x.g;
      });
      var ks = Object.keys(byKey);
      if (ks.length === 1) { byKey[ks[0]].byPosition = true; genotypes[rsid] = byKey[ks[0]]; }
      else if (!ks.length && list.every(function (x) { return x.g.noCall; })) genotypes[rsid] = { noCall: true };
    });
    return { format: format, vendor: vendor, rowsRead: rows, genotypes: genotypes, header: header.slice(0, 12) };
  }

  /* ---------- scoring ---------- */
  function sortedKey(a) { return a.slice().sort().join(''); }
  function resolve(alleles, allowed, palindromic) {
    var set = new Set(alleles), ok = alleles.every(function (x) { return allowed.indexOf(x) >= 0; });
    if (ok) return { key: sortedKey(alleles), flipped: false };
    if (!palindromic) {
      var f = alleles.map(function (x) { return COMP[x]; });
      if (f.every(function (x) { return x && allowed.indexOf(x) >= 0; })) return { key: sortedKey(f), flipped: true };
    }
    return null;
  }
  function isPal(allowed) { var s = allowed.slice().sort().join(''); return s === 'AT' || s === 'CG'; }

  var INDEL_23 = '23andMe does not document its insertion/deletion letters, so confirm this result with a clinical test.';
  function isIndel(letters) { return letters.indexOf('D') >= 0 || letters.indexOf('I') >= 0; }
  function join(a, b) { return a ? (b ? a + ' ' + b : a) : (b || ''); }
  function scoreMarker(m, parsed) {
    var base = { id: m.id, kind: 'marker', category: m.category, name: m.name, gene: m.gene, rsid: m.rsid,
      caveat: m.caveat, about: m.about, verifyLevel: m.verify.level, tier: m.tier };
    var g = parsed.genotypes[m.rsid];
    if (!g) return Object.assign(base, { coverage: 'not_on_file' });
    if (g.noCall) return Object.assign(base, { coverage: 'no_call' });
    var r = resolve(g.alleles, [m.alleles.normal, m.alleles.variant], m.palindromic);
    if (!r) return Object.assign(base, { coverage: 'unrecognized', genotype: g.alleles.join('') });
    var e = m.genotypes[r.key];
    if (g.byPosition) base.caveat = join(base.caveat, 'Read from 23andMe marker ' + g.sourceId + ' at the same DNA position.');
    if (parsed.vendor === '23andMe' && isIndel([m.alleles.normal, m.alleles.variant])) base.caveat = join(base.caveat, INDEL_23);
    return Object.assign(base, { coverage: 'ok', genotype: g.alleles.join(''), flipped: r.flipped, byPosition: !!g.byPosition,
      hemizygous: !!g.hemizygous, status: e.status, text: e.text });
  }

  function scoreComposite(c, parsed) {
    var base = { id: c.id, kind: 'composite', category: c.category, name: c.name, gene: c.gene,
      rsid: c.rsids.join('+'), caveat: c.caveat, about: c.about, verifyLevel: c.verify.level, tier: c.tier };
    var keys = [], any = false, noCall = false, bad = false;
    c.rsids.forEach(function (rs) {
      var g = parsed.genotypes[rs];
      if (!g) { keys.push(null); return; }
      if (g.noCall) { keys.push(null); noCall = true; return; }
      var al = c.alleleSets[rs], r = resolve(g.alleles, al, isPal(al));
      if (!r) { bad = true; keys.push(null); return; }
      keys.push(r.key); any = true;
    });
    if (bad) return Object.assign(base, { coverage: 'unrecognized' });
    if (!any) return Object.assign(base, { coverage: noCall ? 'no_call' : 'not_on_file' });
    /* Rules are keyed by every position's sorted genotype joined with "|" (2 or more positions).
       "<first>|*" matches whatever the other positions are; `partial` covers files that only have the first position. */
    /* Combined readings may also list rules with "?" for a position that is missing from the file,
       and may store a rule as a number pointing into `texts` (to keep the library small). */
    function val(v) { return typeof v === 'number' ? (c.texts || [])[v] || null : v || null; }
    var full = keys.every(Boolean), e = null;
    if (full) e = val(c.rules[keys.join('|')]) || val(c.rules[keys[0] + '|*']);
    if (!e && !full) e = val(c.rules[keys.map(function (k) { return k || '?'; }).join('|')]);
    if (!e && keys[0] && c.partial && c.partial[c.rsids[0]]) e = c.partial[c.rsids[0]][keys[0]] || null;
    if (!e && keys[0] && !full && c.rules[keys[0] + '|*']) e = c.rules[keys[0] + '|*'];
    if (!e) return Object.assign(base, { coverage: 'partial_unresolved' });
    if (parsed.vendor === '23andMe' && c.rsids.some(function (rs, i) { return keys[i] && isIndel(c.alleleSets[rs]); })) base.caveat = join(base.caveat, INDEL_23);
    return Object.assign(base, { coverage: 'ok', genotype: keys.map(function (k) { return k || '?'; }).join(' / '), status: e[0], text: e[1],
      partial: !full && c.rules[(keys[0] || '') + '|*'] === undefined });
  }

  /* ---------- Wider ClinVar scan (strict) ----------
     A variant counts only on an EXACT match: same rsID, same chromosome and GRCh37 position, and every letter in the
     file is exactly ClinVar's reference or variant letter (no strand flipping). Two copies of a variant rarer than the
     cutoff are withheld as a likely chip error. Variants not in the file are not listed at all. */
  function normChr(c) { c = String(c || '').toUpperCase().replace(/^CHR/, ''); return { '23': 'X', '24': 'Y', '25': 'XY', '26': 'MT', 'M': 'MT' }[c] || c; }
  function carriers(af) { var n = 1 / (2 * af); n = n >= 100 ? Math.round(n / 10) * 10 : Math.round(n); return 'About 1 in ' + n.toLocaleString('en-US') + ' people carry one copy (lowest estimate across population databases).'; }
  var SCAN_ONE = 'One copy of a variant that ClinVar lists as pathogenic. Many such conditions are recessive, so one copy often means you are a carrier, but some cause disease with one copy. A genetic counselor can explain what it means for you.';
  var SCAN_TWO = 'Two copies of a variant that ClinVar lists as pathogenic. Confirm with a clinical test and see a genetic counselor.';
  function scanClinvar(lib, parsed) {
    var sc = lib.clinvarScan, out = [];
    if (!sc) return out;
    sc.variants.forEach(function (v) {
      var g = parsed.genotypes[v.rs];
      if (!g) return;
      var base = { id: 'CV_' + v.rs, kind: 'scan', category: 'clinvar_scan', name: v.name, gene: v.gene, rsid: v.rs, about: v.about, verifyLevel: 'clinvar', tier: 'high',
        caveat: 'ClinVar: Pathogenic, ' + v.stars + ' stars, snapshot ' + sc.meta.snapshot + '. Listed for: ' + (v.conditions.join('; ') || 'see ClinVar') + '. ' + carriers(v.af) +
          ' A finding should be confirmed with a clinical test before you act on it.' };
      if (g.noCall) { out.push(Object.assign(base, { coverage: 'no_call' })); return; }
      var al = g.alleles, exact = normChr(g.chr) === v.chr && Number(g.pos) === v.pos &&
        al.every(function (a) { return a === v.ref || a === v.alt; });
      if (!exact) { out.push(Object.assign(base, { coverage: 'unrecognized', genotype: al.join('') })); return; }
      var n = al.filter(function (a) { return a === v.alt; }).length;
      if (n === 2 && v.af < sc.meta.homozygousRareCutoff) { out.push(Object.assign(base, { coverage: 'unreliable', genotype: al.join('') })); return; }
      out.push(Object.assign(base, { coverage: 'ok', genotype: al.join(''), status: n ? 'notable' : 'normal',
        text: n === 0 ? 'Not found: you do not carry this variant.' : (n === 1 ? (v.note || SCAN_ONE) : SCAN_TWO) }));
    });
    return out;
  }

  function score(lib, parsed) {
    var out = lib.markers.map(function (m) { return scoreMarker(m, parsed); });
    lib.composites.forEach(function (c) { out.push(scoreComposite(c, parsed)); });
    return out.concat(scanClinvar(lib, parsed));
  }

  /* ---------- report ---------- */
  function buildReport(lib, scored, opts) {
    opts = opts || {};
    var reveal = new Set(opts.revealCategories || []);
    var cats = lib.categories, byCat = {};
    cats.forEach(function (c) { byCat[c.id] = []; });
    scored.forEach(function (r) { byCat[r.category].push(r); });
    /* Categories with group "traits" (looks, food, ancestry clues, fun facts) are reported separately:
       they never count toward the health summary or the doctor list. */
    var summary = { checked: 0, notable: 0, common_variant: 0, lower_risk: 0, normal: 0, info: 0, traits: 0 };
    var sections = [], brief = [];
    cats.forEach(function (c) {
      var items = byCat[c.id], analyzed = items.filter(function (r) { return r.coverage === 'ok'; });
      var group = c.group || 'health';
      if (!items.length) return;
      if (c.sensitive && !reveal.has(c.id)) {
        var tc = {}; analyzed.forEach(function (r) { tc[r.tier] = (tc[r.tier] || 0) + 1; });
        sections.push({ categoryId: c.id, name: c.name, group: group, sensitive: true, hidden: true, analyzedCount: analyzed.length, tierCounts: tc, items: [] });
        return;
      }
      var shown = analyzed.map(function (r) {
        if (group === 'traits') summary.traits++;
        else { summary.checked++; summary[r.status]++; }
        var it = { id: r.id, name: r.name, gene: r.gene, rsid: r.rsid, genotype: r.genotype, status: r.status, text: r.text, caveat: r.caveat, about: r.about, combined: r.kind === 'composite', tier: r.tier };
        if (opts.includeDevInfo) { it.verifyLevel = r.verifyLevel; it.flipped = r.flipped; }
        if (r.status === 'notable' && group !== 'traits') brief.push({ id: r.id, category: c.name, name: r.name, text: r.text, verifyLevel: r.verifyLevel, tier: r.tier });
        return it;
      });
      if (group !== 'traits') shown.sort(function (a, b) { return ORDER[a.status] - ORDER[b.status]; });
      sections.push({ categoryId: c.id, name: c.name, group: group, sensitive: c.sensitive, hidden: false, items: shown });
    });
    /* Health results grouped by meaningfulness tier first (high, medium, low), then by category inside each tier.
       A hidden sensitive category shows a placeholder in every tier where it has results. */
    var tiers = TIERS.map(function (t) {
      var secs = [];
      sections.forEach(function (s) {
        if (s.group === 'traits') return;
        if (s.hidden) { if (s.tierCounts[t]) secs.push(Object.assign({}, s, { analyzedCount: s.tierCounts[t] })); return; }
        var its = s.items.filter(function (it) { return it.tier === t; });
        if (its.length) secs.push(Object.assign({}, s, { items: its }));
      });
      return { tier: t, sections: secs };
    });
    brief.sort(function (a, b) { return TIERS.indexOf(a.tier) - TIERS.indexOf(b.tier); });
    function ids(cov) { return scored.filter(function (r) { return r.coverage === cov && (!lib.categories.find(function (c) { return c.id === r.category; }).sensitive || reveal.has(r.category)); }).map(function (r) { return r.name; }); }
    return { libraryVersion: lib.meta.libraryVersion, summary: summary, sections: sections, tiers: tiers, doctorBrief: brief,
      coverage: { notOnFile: ids('not_on_file'), noCall: ids('no_call'), unrecognized: ids('unrecognized'), unreliable: ids('unreliable') },
      notCovered: lib.notCovered, scan: lib.clinvarScan ? { snapshot: lib.clinvarScan.meta.snapshot, variants: lib.clinvarScan.variants.length } : null };
  }

  function analyze(lib, text, opts) {
    var parsed = parse(text, libraryRsids(lib), positionIndex(lib));
    var scored = score(lib, parsed);
    var report = buildReport(lib, scored, opts);
    report.file = { vendor: parsed.vendor, format: parsed.format, rowsRead: parsed.rowsRead };
    return { parsed: parsed, scored: scored, report: report };
  }

  return { parse: parse, positionIndex: positionIndex, score: score, buildReport: buildReport, analyze: analyze, libraryRsids: libraryRsids };
});
