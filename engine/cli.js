#!/usr/bin/env node
// Usage: node cli.js <rawDataFile> [--reveal=all|cat1,cat2] [--dev]
const fs = require('fs'), path = require('path');
const E = require('./engine.js');
const lib = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'library', 'markers.json'), 'utf8'));
const file = process.argv[2];
if (!file) { console.error('Usage: node cli.js <rawDataFile> [--reveal=all|cat1,cat2] [--dev]'); process.exit(1); }
const arg = (process.argv.find(a => a.startsWith('--reveal=')) || '').slice(9);
const reveal = arg === 'all' ? lib.categories.filter(c => c.sensitive).map(c => c.id) : arg.split(',').filter(Boolean);
const { report } = E.analyze(lib, fs.readFileSync(file, 'utf8'), { revealCategories: reveal, includeDevInfo: process.argv.includes('--dev') });
console.log(`${report.file.vendor}: ${report.file.rowsRead.toLocaleString()} rows read; library v${report.libraryVersion}`);
console.log('Summary:', JSON.stringify(report.summary));
report.sections.forEach(s => console.log(s.hidden ? `- ${s.name}: HIDDEN (${s.analyzedCount} markers analyzed)` : `- ${s.name}: ${s.items.length} results`));
console.log('\nItems to discuss with your doctor:');
report.doctorBrief.forEach(b => console.log(` * [${b.category}] ${b.name}: ${b.text}`));
console.log('\nNot on file:', report.coverage.notOnFile.join('; ') || 'none');
console.log('No-calls:', report.coverage.noCall.join('; ') || 'none', '| Unrecognized:', report.coverage.unrecognized.join('; ') || 'none');
