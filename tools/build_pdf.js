'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const MarkdownIt = require('markdown-it');

const [, , inMd, outPdf] = process.argv;
if (!inMd || !outPdf) {
  console.error('usage: node build.js <input.md> <output.pdf>');
  process.exit(1);
}

const mdDir = path.dirname(path.resolve(inMd));
const mermaidJs = fs.readFileSync(path.join(__dirname, 'node_modules/mermaid/dist/mermaid.min.js'), 'utf8');

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

const md = new MarkdownIt({ html: true, linkify: false, typographer: false });

// mermaid fenced blocks -> <pre class="mermaid">
const defaultFence = md.renderer.rules.fence.bind(md.renderer.rules);
md.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const token = tokens[idx];
  if ((token.info || '').trim() === 'mermaid') {
    return `<pre class="mermaid">${esc(token.content)}</pre>\n`;
  }
  return defaultFence(tokens, idx, options, env, self);
};

// embed local images as base64 data URIs
md.renderer.rules.image = (tokens, idx, options, env, self) => {
  const token = tokens[idx];
  const srcIdx = token.attrIndex('src');
  let src = token.attrs[srcIdx][1];
  if (!/^https?:|^data:/.test(src)) {
    let rel = src;
    try { rel = decodeURIComponent(src); } catch (e) { /* keep raw */ }
    const abs = path.resolve(mdDir, rel);
    if (fs.existsSync(abs)) {
      const ext = path.extname(abs).slice(1).toLowerCase();
      const mime = ext === 'png' ? 'image/png' : ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : `image/${ext}`;
      const b64 = fs.readFileSync(abs).toString('base64');
      token.attrs[srcIdx][1] = `data:${mime};base64,${b64}`;
    } else {
      console.error('WARN missing image:', abs);
    }
  }
  return self.renderToken(tokens, idx, options);
};

const bodyHtml = md.render(fs.readFileSync(inMd, 'utf8'));

const html = `<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<style>
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Microsoft JhengHei","PingFang TC","Segoe UI",system-ui,sans-serif;
  font-size: 10.8pt; line-height: 1.55; color: #1a1a1a; margin: 0; }
h1 { font-size: 19pt; line-height: 1.25; margin: 0 0 .5em; border-bottom: 2px solid #2b6; padding-bottom: .25em; }
h2 { font-size: 14pt; margin: 1.4em 0 .5em; border-bottom: 1px solid #ccc; padding-bottom: .15em; }
h3 { font-size: 12pt; margin: 1.1em 0 .4em; }
p, li { orphans: 2; widows: 2; }
blockquote { margin: .6em 0; padding: .4em .9em; border-left: 3px solid #2b6; background: #f5f9f5; color: #333; }
blockquote p { margin: .2em 0; }
table { border-collapse: collapse; width: 100%; margin: .8em 0; font-size: 10pt; }
th, td { border: 1px solid #bbb; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #eef4ee; }
code { font-family: "Cascadia Code",Consolas,monospace; background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; }
img { max-width: 100%; height: auto; display: block; margin: .4em auto; }
em { color: #555; }
.mermaid { text-align: center; margin: 1em 0; page-break-inside: avoid; }
.mermaid svg { width: 100% !important; max-width: 100% !important; height: auto !important; }
h2, h3 { page-break-after: avoid; }
table, figure, .mermaid { page-break-inside: avoid; }
</style></head><body>
${bodyHtml}
<script>${mermaidJs}</script>
<script>
  mermaid.initialize({ startOnLoad: false, theme: 'neutral', flowchart: { useMaxWidth: true } });
  window.__ready = false;
  mermaid.run().then(() => { window.__ready = true; document.title = 'READY'; })
    .catch(e => { console.error(e); window.__ready = true; document.title = 'READY'; });
  // if no mermaid present, mark ready immediately
  if (!document.querySelector('.mermaid')) { window.__ready = true; document.title = 'READY'; }
</script>
</body></html>`;

const htmlPath = path.join(__dirname, 'tmp_' + path.basename(outPdf) + '.html');
fs.writeFileSync(htmlPath, html, 'utf8');

const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const fileUrl = 'file:///' + htmlPath.replace(/\\/g, '/');
// 獨立 user-data-dir：避免被既有 Edge 實例接管而沒真正列印（會導致 PDF 沒更新）
const profileDir = path.join(require('os').tmpdir(), 'lc-edge-' + process.pid);

execFileSync(edge, [
  '--headless=new',
  '--disable-gpu',
  `--user-data-dir=${profileDir}`,
  '--no-pdf-header-footer',
  '--virtual-time-budget=25000',
  `--print-to-pdf=${path.resolve(outPdf)}`,   // 必須絕對路徑：Edge 不照 CWD 解析相對輸出
  fileUrl,
], { stdio: 'inherit' });

console.log('PDF written:', path.resolve(outPdf));
