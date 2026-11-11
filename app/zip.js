/* Minimal ZIP reader: returns the text of the first .txt/.csv file. Offline, no dependencies.
   Needs DecompressionStream('deflate-raw') (all current browsers and Node 18+). */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.ZipText = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  async function isZip(blob) {
    var b = new Uint8Array(await blob.slice(0, 4).arrayBuffer());
    return b[0] === 0x50 && b[1] === 0x4b;
  }
  async function firstText(blob) {
    var buf = await blob.arrayBuffer(), dv = new DataView(buf), u8 = new Uint8Array(buf), i, eocd = -1;
    for (i = buf.byteLength - 22; i >= Math.max(0, buf.byteLength - 65557); i--) {
      if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) throw new Error('zip_unreadable');
    var count = dv.getUint16(eocd + 10, true), p = dv.getUint32(eocd + 16, true), entries = [];
    for (var k = 0; k < count; k++) {
      if (dv.getUint32(p, true) !== 0x02014b50) break;
      var nlen = dv.getUint16(p + 28, true), elen = dv.getUint16(p + 30, true), clen = dv.getUint16(p + 32, true);
      entries.push({ method: dv.getUint16(p + 10, true), csize: dv.getUint32(p + 20, true), lho: dv.getUint32(p + 42, true),
        name: new TextDecoder().decode(u8.subarray(p + 46, p + 46 + nlen)) });
      p += 46 + nlen + elen + clen;
    }
    var e = entries.find(function (x) { return /\.(txt|csv)$/i.test(x.name) && x.name.indexOf('__MACOSX') < 0; });
    if (!e) throw new Error('zip_no_text');
    var start = e.lho + 30 + dv.getUint16(e.lho + 26, true) + dv.getUint16(e.lho + 28, true);
    var data = u8.subarray(start, start + e.csize);
    if (e.method === 0) return new TextDecoder().decode(data);
    if (e.method === 8) {
      if (typeof DecompressionStream === 'undefined') throw new Error('zip_unsupported');
      var stream = new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
      return await new Response(stream).text();
    }
    throw new Error('zip_unsupported');
  }
  return { isZip: isZip, firstText: firstText };
});

