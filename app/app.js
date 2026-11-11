(function () {
  'use strict';
  /* ---- Configuration: change these before release ---- */
  var CONFIG = {
    appName: 'DNA Decrypt',
    company: 'DNA Decrypt',
    version: 'v0.1.3',
    showUnverifiedFlag: true,   // set to false once interpretations have had expert review
    minMarkers: 5,
    minRows: 5000
  };
  var lib = JSON.parse(document.getElementById('library').textContent);
  var E = window.DnaEngine, Z = window.ZipText;
  var state = { file: null, scored: null, meta: null, reveal: [], filter: 'all' };
  var $ = function (id) { return document.getElementById(id); };
  var LABEL = { notable: 'Discuss with your doctor', common_variant: 'Common variant', lower_risk: 'Lower-end risk', normal: 'Typical result', info: 'For your information' };
  var SENS_TEXT = {
    cancer_inherited: 'Variants in genes such as BRCA1 and BRCA2 that can raise the risk of certain cancers.',
    /* kept in sync with library categories; shown on the opt-in screen */
    alzheimers: "Your APOE type and one rare variant linked to Alzheimer's disease.",
    parkinsons: "Variants linked to Parkinson's disease, including LRRK2 and GBA.",
    carrier: 'Whether you carry variants for conditions such as cystic fibrosis, Tay-Sachs, PKU, hearing loss, or blood disorders such as sickle cell. Most carriers have no symptoms. This mainly matters for family planning.',
    clinvar_scan: 'An extra check against ClinVar, the US public database of disease variants. To avoid false alarms it uses only exact matches to well-reviewed "Pathogenic" variants that are common enough for DNA chips to read reliably, so it checks a short list and most people have no findings.'
  };
  var SHORT_LABEL = { notable: 'Discuss', common_variant: 'Common variant', lower_risk: 'Lower-end risk', normal: 'Typical', info: 'Info' };
  var SHORT = { notable: 'discuss', common_variant: 'common variant', lower_risk: 'lower-end risk', info: 'for your information' };
  var KEY = [
    ['notable', 'Worth raising with your doctor. The box above explains each one.'],
    ['common_variant', 'You carry a variant that many people have. On its own it usually has a small effect or none.'],
    ['lower_risk', 'You have the version linked to lower-than-average risk.'],
    ['normal', 'The usual result: the variant checked for was not found.'],
    ['info', 'Neither good nor bad, just useful to know, for example for some medicines.']
  ];
  var SCAN_SHORT = 'Exact matches only, against a short list of well-reviewed "Pathogenic" ClinVar variants that DNA chips read reliably. A clean scan does not rule anything out.';
  var TIER_TEXT = {
    high: ['Most meaningful results', 'Well-established findings with large effects, or drug advice backed by prescribing guidelines. These are the results most worth knowing and sharing with your doctor, including the ones that came back typical.'],
    medium: ['Somewhat meaningful results', 'Real but moderate effects, markers that stand in for the true one, or results that only matter in specific situations, such as certain medicines or symptoms.'],
    low: ['Least meaningful results', 'Small effects found in large population studies, or weak evidence. Interesting, but not a reason to change anything on their own.']
  };
  var SCAN_NOTE ='How this scan works: a variant is shown only if your file has the same rsID, chromosome, position and exact DNA letters as ClinVar\'s entry. Only variants ClinVar classifies as "Pathogenic" with 2 or more review stars are used, and only those seen in at least 1 in 1,000 gene copies in every population database, because DNA chips misread rarer variants. Two copies of a rare variant are not shown, because they are almost always a chip error. Even so, any finding should be confirmed with a clinical test. A clean scan does not rule anything out: rare variants can only be found by clinical testing.';
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function each(sel, fn) { Array.prototype.forEach.call(document.querySelectorAll(sel), fn); }

  each('[data-app-name]', function (n) { n.textContent = CONFIG.appName; });
  each('[data-company]', function (n) { n.textContent = CONFIG.company; });
  each('[data-version]', function (n) { n.textContent = CONFIG.version; });
  document.title = CONFIG.appName;

  /* ---- Steps ---- */
  function showStep(n) {
    each('.sheet', function (s) { s.hidden = Number(s.getAttribute('data-step')) !== n; });
    each('#steps li', function (li) {
      var k = Number(li.getAttribute('data-s'));
      li.className = k < n ? 'done' : (k === n ? 'current' : '');
      if (k === n) li.setAttribute('aria-current', 'step'); else li.removeAttribute('aria-current');
    });
    window.scrollTo(0, 0);
    var h = document.querySelector('.sheet[data-step="' + n + '"] h1, .sheet[data-step="' + n + '"] h2');
    if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
  }

  /* ---- Step 1 ---- */
  $('agree').addEventListener('change', function () { $('accept').disabled = !this.checked; });
  $('accept').addEventListener('click', function () { showStep(2); });
  $('decline').addEventListener('click', function () {
    $('accept-actions').hidden = true; $('agree').disabled = true; $('declined').hidden = false;
  });

  /* ---- Step 2 ---- */
  function fmtSize(b) { return b > 1048576 ? (b / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(b / 1024)) + ' KB'; }
  function showError(msg) { var e = $('fileError'); e.textContent = msg; e.hidden = false; }
  function onFile(file) {
    $('fileError').hidden = true; state.file = file;
    $('fname').textContent = file.name; $('fmeta').textContent = fmtSize(file.size);
    $('picked').hidden = false; $('drop').hidden = true; $('confirm').disabled = false;
  }
  function clearFile() { state.file = null; $('fileInput').value = ''; $('picked').hidden = true; $('drop').hidden = false; $('confirm').disabled = true; $('fileError').hidden = true; }
  $('browse').addEventListener('click', function () { $('fileInput').click(); });
  $('fileInput').addEventListener('change', function () { if (this.files[0]) onFile(this.files[0]); });
  $('change').addEventListener('click', clearFile);
  var drop = $('drop');
  ['dragenter', 'dragover'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('over'); }); });
  ['dragleave', 'drop'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('over'); }); });
  drop.addEventListener('drop', function (e) { if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]); });
  window.addEventListener('dragover', function (e) { e.preventDefault(); });
  window.addEventListener('drop', function (e) { e.preventDefault(); });

  $('confirm').addEventListener('click', async function () {
    var btn = this, file = state.file; if (!file) return;
    btn.disabled = true; $('busy').hidden = false; $('fileError').hidden = true;
    try {
      var text;
      try { text = (await Z.isZip(file)) ? await Z.firstText(file) : await file.text(); }
      catch (err) {
        var m = String(err && err.message);
        throw new Error(m === 'zip_unsupported' ? 'This .zip could not be opened here. Unzip it first, then choose the .txt file inside.' :
          (m === 'zip_no_text' ? 'No .txt or .csv file was found inside this .zip.' : 'This file could not be read. Choose the raw data file you downloaded.'));
      }
      var res = E.analyze(lib, text, { revealCategories: [], includeDevInfo: true });
      text = null;
      if (!res.parsed.format || res.parsed.rowsRead < CONFIG.minRows)
        throw new Error('This does not look like an AncestryDNA or 23andMe raw data file. Download the "raw data" file from your account (not the ancestry results or a PDF) and try again.');
      var ok = res.scored.filter(function (r) { return r.coverage === 'ok'; }).length;
      if (ok < CONFIG.minMarkers)
        throw new Error('Only ' + ok + ' of the markers in this program were found in your file, so a report would not be useful. This can happen with older or very limited test versions.');
      state.scored = res.scored; state.meta = { vendor: res.parsed.vendor, rows: res.parsed.rowsRead };
      state.file = null; $('fileInput').value = '';
      prepareChoices();
    } catch (err) {
      showError(err.message); btn.disabled = false;
    } finally { $('busy').hidden = true; }
  });

  /* ---- Step 3 ---- */
  function analyzedBy(cat) { return state.scored.filter(function (r) { return r.category === cat && r.coverage === 'ok'; }).length; }
  function prepareChoices() {
    var std = lib.categories.filter(function (c) { return !c.sensitive && c.group !== 'traits' && analyzedBy(c.id) > 0; }).map(function (c) { return c.name.toLowerCase(); });
    var fun = lib.categories.filter(function (c) { return !c.sensitive && c.group === 'traits' && analyzedBy(c.id) > 0; }).map(function (c) { return c.name.toLowerCase(); });
    $('standardList').textContent = 'Included: ' + std.join(', ') + '.' + (fun.length ? ' Also included, in a separate section: ' + fun.join(', ') + '.' : '');
    var sens = lib.categories.filter(function (c) { return c.sensitive && analyzedBy(c.id) > 0; });
    if (!sens.length) { state.reveal = []; renderReport(); showStep(4); return; }
    $('choices').innerHTML = sens.map(function (c) {
      return '<label class="choice"><input type="checkbox" value="' + esc(c.id) + '"' + (state.reveal.indexOf(c.id) >= 0 ? ' checked' : '') + '>' +
        '<div><strong>' + esc(c.name) + '</strong><span>' + esc(SENS_TEXT[c.id] || '') + ' (' + analyzedBy(c.id) + ' markers found in your file)</span></div></label>';
    }).join('');
    syncSelectAll();
    showStep(3);
  }
  function syncSelectAll() {
    var boxes = document.querySelectorAll('#choices input'), all = boxes.length > 0;
    Array.prototype.forEach.call(boxes, function (b) { if (!b.checked) all = false; });
    $('selectAll').textContent = all ? 'Clear all' : 'Select all';
    $('selectAll').setAttribute('aria-pressed', all ? 'true' : 'false');
  }
  $('selectAll').addEventListener('click', function () {
    var on = this.getAttribute('aria-pressed') !== 'true';
    Array.prototype.forEach.call(document.querySelectorAll('#choices input'), function (b) { b.checked = on; });
    syncSelectAll();
  });
  $('choices').addEventListener('change', syncSelectAll);
  $('showReport').addEventListener('click', function () {
    state.reveal = Array.prototype.map.call(document.querySelectorAll('#choices input:checked'), function (i) { return i.value; });
    renderReport(); showStep(4);
  });

  /* ---- Step 4 ---- */
  function renderReport() {
    var rep = E.buildReport(lib, state.scored, { revealCategories: state.reveal, includeDevInfo: true });
    var flag = CONFIG.showUnverifiedFlag, anyFlag = false, f = state.filter;
    function dag(v) { if (flag && v === 'inferred') { anyFlag = true; return ' <sup title="Interpretation still being reviewed">\u2020</sup>'; } return ''; }
    var s = rep.summary, typical = s.normal + s.lower_risk + s.info;
    var date = new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
    var h = '<div class="rhead"><div><div class="brand"><svg width="22" height="22" viewBox="0 0 28 28" aria-hidden="true"><rect width="28" height="28" rx="6" fill="#0f5c6e"/><path d="M9 5c0 6 10 6 10 9s-10 3-10 9M19 5c0 6-10 6-10 9s10 3 10 9" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>' + esc(CONFIG.appName) + '</div><h1 id="reportTitle">Genetic health marker report</h1></div>' +
      '<dl class="meta"><dt>Prepared for</dt><dd id="prepDd"><input id="prepName" type="text" placeholder="Name (optional)" aria-label="Name to print on the report" value="' + esc(state.name || '') + '"></dd>' +
      '<dt>Date</dt><dd>' + esc(date) + '</dd><dt>Data source</dt><dd>' + esc(state.meta.vendor) + ' raw data file</dd><dt>Library</dt><dd>' + esc(rep.libraryVersion) + '</dd></dl></div>';
    h += '<p class="intro">This report lists genetic markers found in your raw data file. It is for information only. Bring it to your doctor to talk about what, if anything, is worth following up.</p>';
    h += '<div class="doctor"><h2>Discuss with your doctor</h2>';
    if (rep.doctorBrief.length) {
      h += '<ol>' + rep.doctorBrief.map(function (b) { return '<li><span class="box" aria-hidden="true"></span><div><strong>' + esc(b.name) + dag(b.verifyLevel) + '</strong><span class="where">' + esc(b.category) + (TIER_TEXT[b.tier] ? ' · ' + esc(TIER_TEXT[b.tier][0].replace(' results', '')) : '') + '</span>' + esc(b.text) + '</div></li>'; }).join('') + '</ol>';
    } else h += '<p class="none">None of the results included in this report were flagged for discussion. That does not mean you have no risk. See the notes at the end.</p>';
    h += '</div>';
    h += '<div class="summary"><span><b>' + s.checked + '</b> health markers included</span><span><b>' + s.notable + '</b> to discuss</span><span><b>' + s.common_variant + '</b> common variants</span><span><b>' + typical + '</b> typical or informational</span>' + (s.traits ? '<span><b>' + s.traits + '</b> traits and fun facts</span>' : '') + '</div>';
    h += '<div class="toolbar noprint"><div class="seg" role="radiogroup" aria-label="Which results to show"><label><input type="radio" name="flt" value="all"' + (f === 'all' ? ' checked' : '') + '><span>All results</span></label><label><input type="radio" name="flt" value="flag"' + (f === 'flag' ? ' checked' : '') + '><span>Only flagged and common variants</span></label></div>' +
      '<div class="actions"><button class="btn" data-act="print">Print or save as PDF</button></div></div>';
    h += '<p class="fine noprint">Each line shows the marker, your DNA letters and your result, followed by a short explanation of the gene. Full details for anything to discuss are in the box above. In the print window, choose "Save as PDF" to make a file.</p>';
    h += '<dl class="key" aria-label="What the results mean">' + KEY.map(function (k) { return '<div class="st-' + k[0] + '"><dt><span class="dot" aria-hidden="true"></span>' + esc(SHORT_LABEL[k[0]]) + '</dt><dd>' + esc(k[1]) + '</dd></div>'; }).join('') + '</dl>';
    h += '{{JUMP}}';
    /* List layout: one line per marker (name, your DNA letters, result, and the opening sentence of what it means).
       The full explanation of every "discuss" result is in the doctor list at the top. */
    function shown(it) { return f === 'all' || it.status === 'notable' || it.status === 'common_variant'; }
    function lead(text) {
      var re = /[.!?](?=\s+[A-Z(])/g, m, cut = -1;
      while ((m = re.exec(text))) { cut = m.index + 1; if (cut >= 50) break; }
      return esc(cut < 0 ? text : text.slice(0, cut));
    }
    function line(it) {
      var nm = it.name + (it.id.indexOf('CV_') === 0 && it.name === it.gene ? ' ' + it.rsid : '');
      return '<li class="mk st-' + it.status + '"><span class="nm"><span class="dot" aria-hidden="true"></span>' + esc(nm) + dag(it.verifyLevel) + '</span>' +
        '<span class="gx">' + (it.combined ? 'combined' : esc(it.genotype)) + '</span><span class="lb">' + esc(SHORT_LABEL[it.status]) + '</span>' +
        '<span class="tx">' + lead(it.text) + '</span>' + (it.about || it.caveat ? '<span class="ab">' + (it.about ? esc(it.about) : '') +
        (it.caveat ? ' <span class="mnote">Note: ' + esc(it.caveat) + '</span>' : '') + '</span>' : '') + '</li>';
    }
    var jump = [];
    function renderHealth(sec, tier) {
      var sid = 'sec-' + tier + '-' + sec.categoryId;
      var h = '<section class="cat" id="' + esc(sid) + '"><h3>' + esc(sec.name);
      if (sec.hidden) { jump.push([sid, sec.name]); return h + '</h3><p class="hiddenline">Hidden at your request (' + sec.analyzedCount + ' result' + (sec.analyzedCount === 1 ? '' : 's') + '). <button class="linkbtn noprint" data-act="choose">Show it</button></p></section>'; }
      var items = sec.items.filter(shown);
      if (sec.categoryId === 'clinvar_scan') {
        var found = sec.items.filter(function (it) { return it.status === 'notable'; }).length, wh = rep.coverage.unreliable.length;
        h += ' <small>' + found + ' finding' + (found === 1 ? '' : 's') + ' in ' + sec.items.length + ' checked</small></h3>' +
          '<p class="fine">' + esc(SCAN_SHORT) + (rep.scan ? ' ClinVar snapshot ' + esc(rep.scan.snapshot) + '.' : '') +
          (wh ? ' ' + wh + ' result' + (wh === 1 ? ' was' : 's were') + ' withheld as a likely chip error.' : '') + '</p>' +
          '<details class="noprint how"><summary>How this scan works</summary><p class="fine">' + esc(SCAN_NOTE) + '</p></details>';
        if (!items.length) { jump.push([sid, sec.name]); return h + '</section>'; }
      } else {
        if (!items.length) return '';
        h += '</h3>';
      }
      jump.push([sid, sec.name]);
      return h + '<ul class="mklist">' + items.map(line).join('') + '</ul></section>';
    }
    var groups = [];
    function renderTier(t) {
      jump = [];
      var b = t.sections.map(function (sec) { return renderHealth(sec, t.tier); }).join('');
      groups.push(['tier-' + t.tier, TIER_TEXT[t.tier][0], jump]);
      return b;
    }
    /* Health results: by meaningfulness tier first, then by category inside each tier. */
    rep.tiers.forEach(function (t) {
      var body = renderTier(t);
      if (!body) { groups.pop(); return; }
      h += '<div class="tierhead tier-' + t.tier + '" id="tier-' + t.tier + '"><h2>' + esc(TIER_TEXT[t.tier][0]) + '</h2><p>' + esc(TIER_TEXT[t.tier][1]) + '</p></div>' + body;
    });
    var tsecs = rep.sections.filter(function (s) { return s.group === 'traits' && !s.hidden && s.items.length; });
    if (tsecs.length) {
      groups.push(['traits', 'Traits and fun facts', tsecs.map(function (sec) { return ['sec-trait-' + sec.categoryId, sec.name]; })]);
      h += '<div class="traitshead" id="traits"><h2>Traits, ancestry clues and fun facts</h2><p>Just for fun, not health results, and not counted above. Most traits depend on many genes plus your environment, so treat each one as a "likely," not a certainty.</p></div>';
      tsecs.forEach(function (sec) {
        h += '<section class="cat trait" id="sec-trait-' + esc(sec.categoryId) + '"><h3>' + esc(sec.name) + '</h3><ul class="mklist trait">' + sec.items.map(line).join('') + '</ul></section>';
      });
    }
    h += '<div class="reportfoot"><h2>Notes</h2>';
    h += '<p>A result that shows no variant does not rule out risk. This report checks only a small number of markers, and consumer DNA files can contain errors. Anything that matters for your health should be confirmed with a clinical test ordered by a health provider.</p>';
    if (anyFlag) h += '<p>\u2020 The interpretation of this marker is still being reviewed.</p>';
    if (rep.coverage.notOnFile.length) h += '<details class="noprint"><summary>' + rep.coverage.notOnFile.length + ' markers were not in your file</summary><p class="fine">' + esc(rep.coverage.notOnFile.join('; ')) + '</p></details>';
    h += '<details class="noprint"><summary>What this report does not cover</summary><ul>' + rep.notCovered.map(function (n) { return '<li>' + esc(n.item) + ': ' + esc(n.reason) + '</li>'; }).join('') + '</ul></details>';
    h += '<p class="fine"><button class="linkbtn noprint" data-act="restart">Start over and erase this report from this window</button></p></div>';
    h += '<div class="printfoot">For informational purposes only. Not medical advice. Discuss these results with your doctor. ' + esc(CONFIG.appName) + ' ' + esc(CONFIG.version) + '</div>';
    h += '<button type="button" class="totop noprint" data-act="top" aria-label="Back to top" hidden><svg width="16" height="16" viewBox="0 0 18 18" aria-hidden="true"><path d="M9 15V4M4 8.5 9 3.5l5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>Top</button>';
    var jh = '<nav class="jump noprint" aria-label="Jump to a section"><h2>Jump to</h2>' + groups.map(function (g) {
      return '<div class="jrow"><a class="jg" href="#' + esc(g[0]) + '">' + esc(g[1]) + '</a><span class="jl">' +
        g[2].map(function (j) { return '<a href="#' + esc(j[0]) + '">' + esc(j[1]) + '</a>'; }).join('') + '</span></div>';
    }).join('') + '</nav>';
    $('report').innerHTML = h.replace('{{JUMP}}', function () { return jh; });
    syncTop();
  }
  $('report').addEventListener('click', function (e) {
    var link = e.target.closest('a[href^="#"]');
    if (link) { e.preventDefault(); goTo(document.getElementById(link.getAttribute('href').slice(1))); return; }
    var a = e.target.closest('[data-act]'); if (!a) return;
    var act = a.getAttribute('data-act');
    if (act === 'print') { state.name = ($('prepName') || {}).value || ''; window.print(); }
    if (act === 'choose') { state.name = ($('prepName') || {}).value || ''; prepareChoicesFromReport(); }
    if (act === 'top') goTo($('report').firstChild);
    if (act === 'restart') { state.scored = null; location.reload(); }
  });
  $('report').addEventListener('change', function (e) {
    if (e.target.name === 'flt') { state.name = ($('prepName') || {}).value || ''; state.filter = e.target.value; renderReport(); }
  });
  function prepareChoicesFromReport() { prepareChoices(); }
  /* Jump-to links and the floating "Top" button. The target heading gets focus so keyboard users land there too. */
  function goTo(el) {
    if (!el) return;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    var hd = el.matches('h1,h2,h3') ? el : el.querySelector('h1,h2,h3');
    if (hd) { hd.setAttribute('tabindex', '-1'); hd.focus({ preventScroll: true }); }
  }
  function syncTop() { var b = document.querySelector('.totop'); if (b) b.hidden = $('s4').hidden || window.scrollY < 600; }
  window.addEventListener('scroll', syncTop, { passive: true });
  window.addEventListener('beforeprint', function () { var n = $('prepName'); var dd = $('prepDd'); if (n && dd) { dd.setAttribute('data-empty', n.value.trim() ? '0' : '1'); var dt = dd.previousElementSibling; if (dt) dt.setAttribute('data-empty', n.value.trim() ? '0' : '1'); } });
  showStep(1);
})();

