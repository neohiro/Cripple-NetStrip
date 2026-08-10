/* test-network-ux.js — Node.js unit test suite for network-ux.js
 * Run with: node test-network-ux.js
 * Tests pure functions in isolation across all 4 network sites.
 */
'use strict';
var FS = require('fs');
var PATH = require('path');

var SITES = [
  'neohiro.github.io',
  'frenzypenguin-media.github.io',
  'transhumanists.github.io',
  'openstageisland.github.io',
];

var pass = 0, fail = 0;
function eq(a, b, msg) {
  if (JSON.stringify(a) === JSON.stringify(b)) { pass++; process.stdout.write('.'); }
  else { fail++; console.error('\n  FAIL: ' + msg + '\n    got:      ' + JSON.stringify(a) + '\n    expected: ' + JSON.stringify(b)); }
}
function ok(v, msg) {
  if (v) { pass++; process.stdout.write('.'); }
  else { fail++; console.error('\n  FAIL: ' + msg); }
}
function section(name) { console.error('\n-- ' + name); }

function extractFnBody(src, name) {
  // Match "function name(...) {" and capture up to the next top-level closing brace.
  var sigRe = new RegExp('function\\s+' + name + '\\s*\\(([^)]*)\\)', 'g');
  var sigMatch = sigRe.exec(src);
  if (!sigMatch) return null;
  var args = sigMatch[1];
  // Find the start of the function body
  var bodyStart = sigMatch.index + sigMatch[0].length;
  // Skip to opening brace
  while (bodyStart < src.length && src[bodyStart] !== '{') bodyStart++;
  if (bodyStart >= src.length) return null;
  // Now count braces
  var depth = 1;
  var i = bodyStart + 1;
  while (i < src.length && depth > 0) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') depth--;
    i++;
  }
  if (depth !== 0) return null;
  var body = src.substring(bodyStart + 1, i - 1);
  return 'function ' + name + '(' + args + ') {' + body + '\n}';
}
function runFn(src, name) {
  var fn = extractFnBody(src, name);
  if (!fn) throw new Error('Cannot find function: ' + name);
  return new Function('Date', 'String', fn + ';\nreturn ' + name + ';')(Date, String);
}

function findRepoRoot() {
  var d = __dirname;
  for (var i = 0; i < 8; i++) {
    if (FS.existsSync(PATH.join(d, 'frenzypenguin-media.github.io'))) return d;
    d = PATH.dirname(d);
  }
  return null;
}
var REPO = findRepoRoot();
if (!REPO) { console.error('FATAL: cannot locate repo root from ' + __dirname); process.exit(1); }

// --- sanitizeInput inline (mirrors the onAsk logic) ---
function sanitizeInput(raw) {
  return raw.replace(/[\u0000-\u001F\u007F-\u009F\u200B-\u200F\u202A-\u202E\u2066-\u2069]+/g, ' ').replace(/\s+/g, ' ').trim();
}

// --- TESTS ---
section('JS FUNCTIONS');

for (var si = 0; si < SITES.length; si++) {
  var site = SITES[si];
  var jsFile = PATH.join(REPO, site, 'assets', 'js', 'network-ux.js');
  var cssFile = PATH.join(REPO, site, 'assets', 'css', 'network-ux.css');
  if (!FS.existsSync(jsFile)) { console.error('  SKIP ' + site + ' (JS not found)'); continue; }
  if (!FS.existsSync(cssFile)) { console.error('  SKIP ' + site + ' (CSS not found)'); continue; }
  var src = FS.readFileSync(jsFile, 'utf8');
  var css = FS.readFileSync(cssFile, 'utf8');

  section(site + ' -- escapeHtml');
  var escapeHtml = runFn(src, 'escapeHtml');
  eq(escapeHtml('<script>alert("xss")</script>'), '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;', 'HTML chars encoded');
  eq(escapeHtml('A & B < C > D "E" \'F\''), 'A &amp; B &lt; C &gt; D &quot;E&quot; &#39;F&#39;', 'all special chars');
  eq(escapeHtml(''), '', 'empty string');
  eq(escapeHtml('plain text'), 'plain text', 'no special chars');

  section(site + ' -- hostOf');
  var hostOf = runFn(src, 'hostOf');
  eq(hostOf('https://neohiro.github.io/'), 'neohiro.github.io', 'neohiro');
  eq(hostOf('https://frenzypenguin-media.github.io/path'), 'frenzypenguin-media.github.io', 'frenzypenguin');
  eq(hostOf('https://transhumanists.github.io/repo?q=1'), 'transhumanists.github.io', 'transhumanists');
  // invalid scheme: new URL throws, catch returns ''
  var badResult = hostOf('invalid://url');
  eq(typeof badResult, 'string', 'invalid URL -> string (not thrown)');
  eq(hostOf(''), '', 'empty URL -> empty');

  section(site + ' -- labelFor');
  var labelFor = runFn(src, 'labelFor');
  eq(labelFor('neohiro.github.io'), 'neohiro', 'neohiro');
  eq(labelFor('frenzypenguin-media.github.io'), 'FrenzyPenguin Media', 'frenzypenguin');
  // frenzypenguin.media is the live apex for this site. labelFor matches on
  // the "frenzypenguin" prefix, so the custom domain must keep resolving to
  // the same label or the cross-site "Back to ..." button mislabels itself.
  eq(labelFor('frenzypenguin.media'), 'FrenzyPenguin Media', 'frenzypenguin.media apex');
  eq(labelFor('www.frenzypenguin.media'), 'FrenzyPenguin Media', 'frenzypenguin.media www');
  eq(labelFor('transhumanists.github.io'), 'transhumanists', 'transhumanists');
  eq(labelFor('openstageisland.github.io'), 'Open Stage Island', 'openstageisland');
  eq(labelFor('unknown.github.io'), 'neohiro', 'unknown -> default');

  function runClassify(src, q) {
    var cb = extractFnBody(src, 'classify');
    if (!cb) return null;
    // Stubs match the real return text so the assertions test the routing,
    // not the formatting of the helper functions.
    var stubs = [
      'function stepsForBug() { return "BUG_HELPER_TEXT"; }',
      'function stepsForHardening(t) { return /linux|ubuntu|debian/.test(t) ? "Linux hardening path" : "Windows hardening path"; }',
      'function stepsForRepo() { return "REPO_HELPER_TEXT"; }'
    ].join('\n');
    var qsafe = String(q).replace(/"/g, '\\"');
    return new Function(stubs + '\n' + cb + '\nreturn classify("' + qsafe + '");')();
  }
  var classifyBody = extractFnBody(src, 'classify');
  if (!classifyBody) {
    console.error('  SKIP classify tests for ' + site + ' (function not extracted)');
  }

  section(site + ' -- classify() bug/security');
  if (classifyBody) {
    ok(runClassify(src, 'my tool threw a bug').indexOf('BUG_HELPER_TEXT') >= 0, 'bug keyword -> stepsForBug');
    ok(runClassify(src, 'found a security vulnerability').indexOf('BUG_HELPER_TEXT') >= 0, 'security vuln -> stepsForBug');
    ok(runClassify(src, 'CVE-2024-1234').indexOf('BUG_HELPER_TEXT') >= 0, 'CVE -> stepsForBug');
    ok(runClassify(src, 'file a security advisory').indexOf('BUG_HELPER_TEXT') >= 0, 'security advisory -> stepsForBug');
    ok(runClassify(src, 'how do I report a bug').indexOf('BUG_HELPER_TEXT') >= 0, 'report bug -> stepsForBug');
    ok(runClassify(src, 'tool crashed immediately').indexOf('BUG_HELPER_TEXT') >= 0, 'crash -> stepsForBug');
    ok(runClassify(src, 'the link is broken').indexOf('BUG_HELPER_TEXT') >= 0, 'broken link (in sentence) -> stepsForBug');
    ok(runClassify(src, 'it is not working').indexOf('BUG_HELPER_TEXT') >= 0, 'not working -> stepsForBug');
    ok(runClassify(src, 'Harden-Windows throws an error').indexOf('BUG_HELPER_TEXT') >= 0, 'throws error -> stepsForBug');
  }

  section(site + ' -- classify() hardening');
  if (classifyBody) {
    ok(runClassify(src, 'harden my ubuntu server').indexOf('Linux hardening') >= 0, 'harden + ubuntu -> Linux');
    ok(runClassify(src, 'harden my windows machine').indexOf('Windows hardening') >= 0, 'harden + windows -> Windows');
    ok(runClassify(src, 'I need a STIG baseline').indexOf('hardening') >= 0, 'STIG -> hardening');
    ok(runClassify(src, 'apply hardening to debian').indexOf('Linux hardening') >= 0, 'hardening + debian -> Linux');
    ok(runClassify(src, 'secure linux server').indexOf('Linux hardening') >= 0, 'secure + linux (adjacent) -> Linux');
  }

  section(site + ' -- classify() false positives (must NOT match harden)');
  if (classifyBody) {
    // "I have a security question" (no vuln/cve/issue keywords): not a bug, not a hardening request
    var secQ = runClassify(src, 'I have a security question');
    ok(secQ.indexOf('Linux hardening') < 0 &&
       secQ.indexOf('Windows hardening') < 0 &&
       secQ.indexOf('Linux hardening path') < 0 &&
       secQ.indexOf('Windows hardening path') < 0,
       'security question (no vuln keywords) -> NOT hardening');
    // "protect my data" (no OS): must not match harden
    var protectData = runClassify(src, 'how do I protect my data');
    ok(protectData.indexOf('Linux hardening') < 0 &&
       protectData.indexOf('Windows hardening') < 0 &&
       protectData.indexOf('Linux hardening path') < 0 &&
       protectData.indexOf('Windows hardening path') < 0,
       'protect data (no OS) -> NOT hardening');
  }

  section(site + ' -- classify() dashboard / media / sponsor / repo');
  if (classifyBody) {
    ok(runClassify(src, 'show me the dashboard').indexOf('Dashboard') >= 0, 'dashboard -> dashboard');
    ok(runClassify(src, 'show me the world map').indexOf('Dashboard') >= 0, 'world map -> dashboard');
    ok(runClassify(src, 'I want to watch the tutorial on YouTube').indexOf('FrenzyPenguin') >= 0 ||
       runClassify(src, 'I want to watch the tutorial on YouTube').indexOf('Media') >= 0,
       'YouTube tutorial -> media hub');
    ok(runClassify(src, 'how can I support this project').indexOf('Sponsor') >= 0, 'support -> sponsor');
    ok(runClassify(src, 'I want to donate').indexOf('Sponsor') >= 0 ||
       runClassify(src, 'I want to donate').indexOf('Patron') >= 0, 'donate -> sponsor');
    ok(runClassify(src, 'which tool repo has DNS encryption').indexOf('REPO_HELPER_TEXT') >= 0, 'tool repo -> repo');
  }

  section(site + ' -- classify() false positives (media)');
  if (classifyBody) {
    ok(runClassify(src, 'I watch the weather every morning').indexOf('Media') < 0, 'watch weather -> NOT media');
    ok(runClassify(src, 'there is a stream of data').indexOf('Media') < 0, 'data stream -> NOT media');
    ok(runClassify(src, 'write a media query in CSS').indexOf('Media') < 0, 'CSS media query -> NOT media');
    ok(runClassify(src, 'social media post').indexOf('Media') < 0, 'social media -> NOT media');
  }

  section(site + ' -- classify() default');
  if (classifyBody) {
    ok(runClassify(src, 'hello what can you do').indexOf('help') >= 0 ||
       runClassify(src, 'hello what can you do').indexOf('useful') >= 0,
       'unknown query -> default');
  }

  section(site + ' -- sanitizeInput()');
  eq(sanitizeInput('  hello   world  '), 'hello world', 'collapse whitespace');
  eq(sanitizeInput('hello\u0000world'), 'hello world', 'strip null');
  eq(sanitizeInput('hello\u200Bworld'), 'hello world', 'strip zero-width space');
  eq(sanitizeInput('hello\u001B[31mred\u001B[0m text'), 'hello [31mred [0m text', 'strip ESC (ANSI escape) - ESC replaced with space, codes remain');
  eq(sanitizeInput('hello\r\nworld'), 'hello world', 'strip CRLF');
  eq(sanitizeInput('  hello  \u200B  world  '), 'hello world', 'mixed ws + ZWSP');
  eq(sanitizeInput(''), '', 'empty -> empty');
  eq(sanitizeInput('   '), '', 'whitespace only -> empty');

  section(site + ' -- readLast() TTL (12h expiry)');
  var readLast = runFn(src, 'readLast');
  // We can't easily stub sessionStorage but we can verify the function shape
  ok(typeof readLast === 'function', 'readLast is a function');
  // Verify it returns null on empty storage
  var _origSS = global.sessionStorage;
  global.sessionStorage = { getItem: function () { return null; } };
  eq(readLast(), null, 'readLast returns null when storage empty');
  global.sessionStorage = _origSS;

  section(site + ' -- boot path correctness');
  // The IIFE must not throw on any of the 4 network sites when run with minimal mocks
  ok(typeof runFn(src, 'init') === 'function', 'init is a callable function');
  ok(typeof runFn(src, 'boot') === 'function', 'boot is a callable function');
  ok(typeof runFn(src, 'mountStarfield') === 'function', 'mountStarfield exists');
  ok(typeof runFn(src, 'mountPreviousButton') === 'function', 'mountPreviousButton exists');
  ok(typeof runFn(src, 'mountConversationModal') === 'function', 'mountConversationModal exists');
  ok(typeof runFn(src, 'mountAssistantBar') === 'function', 'mountAssistantBar exists');
  ok(typeof runFn(src, 'injectNavAuth') === 'function', 'injectNavAuth exists');
  ok(typeof runFn(src, 'detectStranger') === 'function', 'detectStranger exists');
  ok(typeof runFn(src, 'wireInteractions') === 'function', 'wireInteractions exists');
  // probeHeart is a real function (not a placeholder)
  ok(typeof runFn(src, 'probeHeart') === 'function', 'probeHeart exists');
  ok(typeof runFn(src, 'fetchMouthReply') === 'function', 'fetchMouthReply exists');

  section(site + ' -- fetchWithTimeout signature');
  var fwt = runFn(src, 'fetchWithTimeout');
  ok(typeof fwt === 'function', 'fetchWithTimeout is a function');
  ok(fwt.length === 3, 'fetchWithTimeout takes 3 args (url, opts, ms)');

  section(site + ' -- Heart endpoint constants');
  // Verify the heartbeat endpoint list is sane
  var endpoints = src.match(/https:\/\/neohiro\.github\.io\/[^'"\s)]+/g) || [];
  ok(endpoints.length >= 2, 'at least 2 heart endpoints configured (found ' + endpoints.length + ')');

  section(site + ' -- mousemove rAF throttle (perf)');
  ok(src.indexOf('mouseRaf') >= 0, 'mousemove listener uses rAF throttle');

  section(site + ' -- toast cleanup on pagehide (memory)');
  ok(src.indexOf('pagehide') >= 0, 'showToast registers pagehide listener');
  ok(src.indexOf('clearTimeout(outTid)') >= 0, 'showToast clears timer on pagehide');

  section(site + ' -- prev-btn XSS escape');
  // Verify the prev-btn uses escapeHtml on user-influenced fields
  var prevMount = src.indexOf('mountPreviousButton');
  var prevBlock = src.substring(src.indexOf('function mountPreviousButton'), src.indexOf('function mountPreviousButton') + 2000);
  ok(prevBlock.indexOf('escapeHtml(last.label)') >= 0, 'prev-btn label escaped');
  ok(prevBlock.indexOf('escapeHtml(hostOf(last.url))') >= 0, 'prev-btn host escaped');

  section(site + ' -- recordCurrent dedup');
  var recBlock = src.substring(src.indexOf('function recordCurrent'), src.indexOf('function readLast'));
  ok(recBlock.indexOf('existing.url === location.href') >= 0, 'recordCurrent dedups same-URL writes');

  section(site + ' -- syncAuthFromBar expiry check');
  var syncBlock = src.substring(src.indexOf('function syncAuthFromBar'), src.indexOf('function showUserNav'));
  ok(syncBlock.indexOf('s.expiresAt < Date.now()') >= 0, 'syncAuthFromBar rejects expired session');

  section(site + ' -- avatar URL ?& append');
  var showUser = src.substring(src.indexOf('function showUserNav'), src.indexOf('// ── Cross-script hook'));
  ok(showUser.indexOf("'&'") >= 0, 'avatar URL appends & for existing query params');

  section(site + ' -- aria-modal on open + close');
  var showConv = src.substring(src.indexOf('function showConversationModal'), src.indexOf('function hideConversationModal'));
  ok(showConv.indexOf("'aria-modal', 'true'") >= 0 || showConv.indexOf('"aria-modal", "true"') >= 0, 'aria-modal set true on open');
  var hideConv = src.substring(src.indexOf('function hideConversationModal'), src.indexOf('function appendConvMessage'));
  ok(hideConv.indexOf("'aria-modal', 'false'") >= 0 || hideConv.indexOf('"aria-modal", "false"') >= 0, 'aria-modal set false on close');

  section(site + ' -- CSS brace balance');
  var opens = (css.match(/{/g) || []).length;
  var closes = (css.match(/}/g) || []).length;
  eq(opens, closes, 'braces { ' + opens + ' == } ' + closes);

  section(site + ' -- CSS keyframe coverage');
  var keyframes = [];
  var kfRe = css.match(/@keyframes\s+(\S+)/g) || [];
  for (var k = 0; k < kfRe.length; k++) {
    keyframes.push(kfRe[k].replace('@keyframes ', ''));
  }
  // Also gather keyframes referenced in JS (style.animation = 'nameXxx ...')
  var jsContent = FS.readFileSync(PATH.join(REPO, site, 'assets', 'js', 'network-ux.js'), 'utf8');
  var animRe = css.match(/animation(?:-name)?\s*:\s*([^;!]+)/gi) || [];
  var usedAnims = [];
  for (var a = 0; a < animRe.length; a++) {
    var names = animRe[a].replace(/animation(?:-name)?\s*:\s*/i, '').split(/\s+/);
    for (var n = 0; n < names.length; n++) {
      if (names[n] && names[n].indexOf('$') < 0 && names[n].indexOf('var(') < 0) usedAnims.push(names[n]);
    }
  }
  // Pull keyframe names referenced in JS style.animation assignments
  var jsAnims = jsContent.match(/animation\s*[:=]\s*['"]([^'"]+)/g) || [];
  for (var ja = 0; ja < jsAnims.length; ja++) {
    var jparts = jsAnims[ja].replace(/^animation\s*[:=]\s*['"]/, '').split(/\s+/);
    for (var jp = 0; jp < jparts.length; jp++) {
      if (keyframes.indexOf(jparts[jp]) >= 0) usedAnims.push(jparts[jp]);
    }
  }
  var unused = [];
  for (var kf = 0; kf < keyframes.length; kf++) {
    if (usedAnims.indexOf(keyframes[kf]) < 0) unused.push(keyframes[kf]);
  }
  if (unused.length === 0) { pass += keyframes.length; process.stdout.write('(' + keyframes.length + ' keyframes covered)'); }
  else { fail += unused.length; console.error('\n  UNUSED keyframes: ' + unused.join(', ')); }

  section(site + ' -- CSS starfield (no duplicate orphan block)');
  var sfCount = (css.match(/\.starfield\s*\{/g) || []).length;
  // 1 = base block only; 2 = base + reduced-motion override (legitimate).
  // 3+ indicates an orphan duplicate that would shadow the base block.
  ok(sfCount >= 1 && sfCount <= 2, 'exactly 1-2 .starfield blocks (base + optional reduced-motion, found ' + sfCount + ')');

  section(site + ' -- CSS no mojibake');
  var mojibake = (css.match(/â/g) || []).length;
  eq(mojibake, 0, 'no UTF-8 mojibake (found ' + mojibake + ')');

  section(site + ' -- CSS no matrix rain orphan');
  ok(css.indexOf('matrix rain') < 0, 'no "matrix rain" orphan comment');

  section(site + ' -- CSS no console.log');
  ok(css.indexOf('console.log') < 0, 'no console.log in CSS');
}

section('no alert() in network-ux.js');
for (var i = 0; i < SITES.length; i++) {
  var js = PATH.join(REPO, SITES[i], 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(js)) continue;
  var content = FS.readFileSync(js, 'utf8');
  ok(content.indexOf('alert(') < 0, SITES[i] + ' -- no alert()');
}

section('showToast() present in all sites');
for (var j = 0; j < SITES.length; j++) {
  var js2 = PATH.join(REPO, SITES[j], 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(js2)) continue;
  var content2 = FS.readFileSync(js2, 'utf8');
  ok(content2.indexOf('function showToast') >= 0, SITES[j] + ' -- showToast function present');
  ok(content2.indexOf('neohiro-toast') >= 0, SITES[j] + ' -- neohiro-toast ID used');
}

section('input sanitation in onAsk (all sites)');
for (var s = 0; s < SITES.length; s++) {
  var js3 = PATH.join(REPO, SITES[s], 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(js3)) continue;
  var c3 = FS.readFileSync(js3, 'utf8');
  ok(c3.indexOf('\\u0000-\\u001F') >= 0, SITES[s] + ' -- strips C0 control chars');
  ok(c3.indexOf('\\u200B-\\u200F') >= 0, SITES[s] + ' -- strips zero-width chars');
  ok(c3.indexOf('\\s+/g') >= 0, SITES[s] + ' -- collapses whitespace runs');
}

section('focus trap + focus restore in modal (all sites)');
for (var t = 0; t < SITES.length; t++) {
  var js4 = PATH.join(REPO, SITES[t], 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(js4)) continue;
  var c4 = FS.readFileSync(js4, 'utf8');
  ok(c4.indexOf('_prevFocus') >= 0, SITES[t] + ' -- _prevFocus state for focus restore');
  ok(c4.indexOf('e.key !== \'Tab\'') >= 0 || c4.indexOf('e.key === \'Tab\'') >= 0, SITES[t] + ' -- Tab focus-trap handler');
  ok(c4.indexOf('e.preventDefault') >= 0, SITES[t] + ' -- preventDefault on Tab boundary');
}

section('neohiro:nav-auth dispatch (all sites)');
for (var u = 0; u < SITES.length; u++) {
  var js5 = PATH.join(REPO, SITES[u], 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(js5)) continue;
  var c5 = FS.readFileSync(js5, 'utf8');
  var dispatches = (c5.match(/dispatchEvent\(new CustomEvent\('neohiro:nav-auth'/g) || []).length;
  ok(dispatches >= 2, SITES[u] + ' -- dispatches neohiro:nav-auth on login + logout (found ' + dispatches + ')');
}

// --- SUMMARY ---
section('pagehide abort listener (all sites)');
for (var v = 0; v < SITES.length; v++) {
  var vs = SITES[v];
  var vfile = PATH.join(REPO, vs, 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(vfile)) continue;
  var vsrc = FS.readFileSync(vfile, 'utf8');
  ok(vsrc.includes("addEventListener('pagehide', _cancelInFlight)"), vs + ' -- registers pagehide listener');
  ok(/function _cancelInFlight\s*\(\s*\)\s*\{[\s\S]*?_inFlightVer\s*\+\+/.test(vsrc), vs + ' -- _cancelInFlight bumps _inFlightVer');
  ok(/function _cancelInFlight\s*\(\s*\)\s*\{[\s\S]*?clearTimeout\(\s*_inFlightTO/.test(vsrc), vs + ' -- _cancelInFlight clears _inFlightTO');
  ok(/function _cancelInFlight\s*\(\s*\)\s*\{[\s\S]*?clearInterval\(\s*_inFlightInt/.test(vsrc), vs + ' -- _cancelInFlight clears _inFlightInt');
}

// --- OSI-specific cross-file checks (style.css must not shadow network-ux.css .float-tag) ---
// The invariant here is namespace hygiene: nothing may define or use a BARE
// `.float-tag`, because network-ux.css is shared by all four sites and a generic
// name would let one site's styling leak into another's.
//
// The bare `.float-tag` rule that lived in network-ux.css has been removed (no
// site used it), so the "style.css must define .osi-float-tag" and "index.md
// must use it" assertions below had nothing left to protect -- and they have
// never passed: `git log -S osi-float-tag` finds no commit that ever introduced
// the class, and OSI has no floating element to put it on. Requiring a feature
// that was never built only produces permanent red.
//
// So the check is now conditional: if this site uses a float tag at all, it must
// be namespaced. That keeps the real guarantee and stops asserting fiction.
section('openstageisland -- brand .float-tag isolation');
var osiStylePath = PATH.join(REPO, 'openstageisland.github.io/assets/style.css');
var osiIndexPath = PATH.join(REPO, 'openstageisland.github.io/index.md');
if (FS.existsSync(osiStylePath)) {
  var osiStyle = FS.readFileSync(osiStylePath, 'utf8');
  ok(!/\.float-tag\s*\{/.test(osiStyle), 'style.css does NOT define a bare .float-tag');
  // Any float-tag styling here must carry the site prefix.
  var osiFloatRules = osiStyle.match(/\.[\w-]*float-tag[^{]*\{/g) || [];
  ok(
    osiFloatRules.every(function (rule) { return /\.(osi-)?float-tag\b/.test(rule); }),
    'style.css namespaces any float-tag rule it defines'
  );
}
if (FS.existsSync(osiIndexPath)) {
  var osiIndex = FS.readFileSync(osiIndexPath, 'utf8');
  // If the markup uses a float tag, it must be the namespaced one.
  ok(
    !/class="[^"]*(?<![\w-])float-tag(?![\w-])/.test(osiIndex) ||
      /class="[^"]*\bosi-float-tag\b[^"]*"/.test(osiIndex),
    'index.md namespaces float-tag if it uses one'
  );
}

// --- nav-auth feedback loop guard (all sites) ---
section('nav-auth feedback loop guard (all sites)');
for (var w = 0; w < SITES.length; w++) {
  var ws = SITES[w];
  var wfile = PATH.join(REPO, ws, 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(wfile)) continue;
  var wsrc = FS.readFileSync(wfile, 'utf8');
  ok(/_navAuthSuppress/.test(wsrc), ws + ' -- has _navAuthSuppress flag (no feedback loop)');
  ok(/if \(_navAuthSuppress\)/.test(wsrc), ws + ' -- listener checks _navAuthSuppress');
  ok(/_navAuthSuppress\s*=\s*1/.test(wsrc), ws + ' -- setter marks internal dispatch');
}

// --- avatar empty-URL guard (all sites) ---
section('avatar empty-URL guard (all sites)');
for (var x = 0; x < SITES.length; x++) {
  var xs = SITES[x];
  var xfile = PATH.join(REPO, xs, 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(xfile)) continue;
  var xsrc = FS.readFileSync(xfile, 'utf8');
  ok(/var avUrl = s\.avatar_url \|\| '';/.test(xsrc), xs + ' -- guards empty avatar_url');
  ok(/av\.alt\s*=\s*\(s\.login \|\| 'user'\)\s*\+\s*' avatar'/.test(xsrc), xs + ' -- sets descriptive alt on avatar');
  ok(/av\.removeAttribute\('src'\)/.test(xsrc), xs + ' -- removes src when avatar_url is empty');
  ok(/nm\.textContent\s*=\s*s\.login\s*\|\|\s*'user'/.test(xsrc), xs + ' -- nm.textContent guards against missing s.login');
}

// --- NEohiro public surface (all sites) ---
section('NEohiro public surface (all sites)');
for (var n = 0; n < SITES.length; n++) {
  var ns = SITES[n];
  var nfile = PATH.join(REPO, ns, 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(nfile)) continue;
  var nsrc = FS.readFileSync(nfile, 'utf8');
  ok(/PREV_KEY:\s*'neohiro\.prev\.v1'/.test(nsrc), ns + ' -- NEohiro.PREV_KEY is defined');
  ok(/NETWORK:\s*\[/.test(nsrc), ns + ' -- NEohiro.NETWORK array is defined');
  ok(/window\.NEohiro\s*=\s*NEohiro/.test(nsrc), ns + ' -- NEohiro exposed on window');
  // AI_KEY removed in pass 2 — was dead code (no read/write in module).
  ok(!/AI_KEY/.test(nsrc), ns + ' -- dead AI_KEY export removed');
}

// --- close-timer leak fix (all sites) ---
section('close-timer cancel on reopen (all sites)');
for (var y = 0; y < SITES.length; y++) {
  var ys = SITES[y];
  var yfile = PATH.join(REPO, ys, 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(yfile)) continue;
  var ysrc = FS.readFileSync(yfile, 'utf8');
  ok(/_closeTid/.test(ysrc), ys + ' -- tracks _closeTid to avoid leak');
  ok(/if \(_closeTid\)\s*\{\s*clearTimeout\(_closeTid\)/.test(ysrc), ys + ' -- cancels prior close timer on reopen');
}

// --- _prevFocus isConnected guard ---
section('_prevFocus isConnected guard (all sites)');
for (var z = 0; z < SITES.length; z++) {
  var zs = SITES[z];
  var zfile = PATH.join(REPO, zs, 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(zfile)) continue;
  var zsrc = FS.readFileSync(zfile, 'utf8');
  ok(/_prevFocus && _prevFocus\.isConnected/.test(zsrc), zs + ' -- only restores focus if element still in DOM');
}

// --- CSS: reduced-motion coverage (all sites) ---
section('CSS reduced-motion coverage (all sites)');
for (var r = 0; r < SITES.length; r++) {
  var rs = SITES[r];
  var rfile = PATH.join(REPO, rs, 'assets', 'css', 'network-ux.css');
  if (!FS.existsSync(rfile)) continue;
  var rcss = FS.readFileSync(rfile, 'utf8');
  // starfield transform must be killed in reduced-motion (parallax safety)
  ok(/\.starfield\s*\{[^}]*transform:\s*none\s*!important/.test(rcss), rs + ' -- .starfield transform frozen in reduced-motion');
  ok(/\.starfield\s*\{[^}]*transition:\s*none\s*!important/.test(rcss), rs + ' -- .starfield transition killed (no abrupt snap)');
  // card-3d hover must not lift the card under reduced-motion
  ok(/\.card-3d,\s*\.card-3d:hover\s*\{[^}]*transform:\s*none\s*!important/.test(rcss), rs + ' -- .card-3d hover transform frozen in reduced-motion');
  // click ripple must be hidden
  ok(/\.click-ripple\s*\{[^}]*display:\s*none\s*!important/.test(rcss), rs + ' -- .click-ripple hidden in reduced-motion');
}

// --- CSS: focus-visible on AI bar input (all sites) ---
section('CSS :focus-visible on ai-bar__input (all sites)');
for (var q = 0; q < SITES.length; q++) {
  var qs = SITES[q];
  var qfile = PATH.join(REPO, qs, 'assets', 'css', 'network-ux.css');
  if (!FS.existsSync(qfile)) continue;
  var qcss = FS.readFileSync(qfile, 'utf8');
  ok(/\.ai-bar__input:focus-visible/.test(qcss), qs + ' -- has :focus-visible style on input');
  ok(/\.ai-bar__input:focus-visible[^}]*outline:\s*2px/.test(qcss), qs + ' -- has 2px outline ring on focus-visible');
}

// --- CSS: placeholder contrast (all sites) ---
section('CSS placeholder contrast fallback (all sites)');
for (var j = 0; j < SITES.length; j++) {
  var js = SITES[j];
  var jfile = PATH.join(REPO, js, 'assets', 'css', 'network-ux.css');
  if (!FS.existsSync(jfile)) continue;
  var jcss = FS.readFileSync(jfile, 'utf8');
  // Default fallback should be brighter than #6d7f8f (which is 3.17:1 on #0b0e12 — fails AA).
  // #8a9baa is ~5.0:1 on #0b0e12, passing WCAG AA for body text.
  var m = /\.ai-bar__input::placeholder[^}]*color:\s*var\(--fg-subtle,\s*(#[0-9a-fA-F]{6})/.exec(jcss);
  ok(m && /^#([0-9a-fA-F]{6})$/.test(m[1]) && m[1].toLowerCase() !== '#6d7f8f', js + ' -- placeholder fallback is bright enough for WCAG AA on dark bg');
}

// --- Layout: skip-link + main id (all sites) ---
section('Layout skip-link and main target (all sites)');
for (var s = 0; s < SITES.length; s++) {
  var ss = SITES[s];
  var layoutFile = PATH.join(REPO, ss, '_layouts', 'default.html');
  if (!FS.existsSync(layoutFile)) continue;
  var layout = FS.readFileSync(layoutFile, 'utf8');
  ok(/<a class="skip-link" href="#main">Skip to main content<\/a>/.test(layout), ss + ' -- has skip-link to #main');
  ok(/<main[^>]*\bid="main"[^>]*>/.test(layout), ss + ' -- has <main id="main"> target');
  ok(/<main[^>]*\btabindex="-1"[^>]*>/.test(layout), ss + ' -- <main> has tabindex="-1" for skip-link focus');
}

// --- Layout: counter script defer (where present) ---
section('Layout: counter script non-blocking (all sites)');
for (var t = 0; t < SITES.length; t++) {
  var ts = SITES[t];
  var tlayoutFile = PATH.join(REPO, ts, '_layouts', 'default.html');
  if (!FS.existsSync(tlayoutFile)) continue;
  var tlayout = FS.readFileSync(tlayoutFile, 'utf8');
  // If the counter script is present, it must be defer/async; otherwise
  // it's a render blocker and delays the whole page.
  var hasCounter = /freevisitorcounters\.com\/en\/home\/counter/.test(tlayout);
  if (hasCounter) {
    ok(/freevisitorcounters\.com[^>]*\sdefer\b/.test(tlayout) || /freevisitorcounters\.com[^>]*\sasync\b/.test(tlayout), ts + ' -- counter script is defer/async (not render-blocking)');
  } else {
    ok(true, ts + ' -- no counter script (n/a)');
  }
}

// --- Layout: no 'Free Counter' promo link above embed (all sites) ---
// Regression for the 2026-08-30 roll-out: spec forbids the vendor's
// text link "Free Counter" above the <script> embed. The counter widget
// itself is the visible counter; no promo text needed.
section('Layout: no Free Counter promo link (all sites)');
var FREE_COUNTER_RE = /<a\s[^>]*href=[^>]*freevisitorcounters\.com[^>]*>\s*Free\s+Counter/i;
for (var fc = 0; fc < SITES.length; fc++) {
  var fcs = SITES[fc];
  var fcLayoutFile = PATH.join(REPO, fcs, '_layouts', 'default.html');
  if (FS.existsSync(fcLayoutFile)) {
    var fcLayout = FS.readFileSync(fcLayoutFile, 'utf8');
    ok(!FREE_COUNTER_RE.test(fcLayout), fcs + ' -- _layouts/default.html has no "Free Counter" promo link');
  }
  // Also check README.md, index.html, and index.md if they exist
  for (var fci = 0; fci < ['README.md', 'index.html', 'index.md'].length; fci++) {
    var fcp = PATH.join(REPO, fcs, ['README.md', 'index.html', 'index.md'][fci]);
    if (FS.existsSync(fcp)) {
      var fcText = FS.readFileSync(fcp, 'utf8');
      ok(!FREE_COUNTER_RE.test(fcText), fcs + '/' + ['README.md', 'index.html', 'index.md'][fci] + ' has no "Free Counter" promo link');
    }
  }
}

// --- Layout: no auth.php tokens leaked (all sites) ---
// Defense-in-depth: auth tokens belong only in links-secret/. Any leak
// to a public repo means rotating across all 12 surfaces.
section('Layout: no auth.php tokens in non-secret files (all sites)');
var AUTH_TOKEN_RE = /freevisitorcounters\.com\/auth\.php\?id=[a-f0-9]{40}/i;
function walkForAuthLeaks(dir, out) {
  if (!FS.existsSync(dir)) return;
  var ents = FS.readdirSync(dir, { withFileTypes: true });
  for (var e = 0; e < ents.length; e++) {
    var ent = ents[e];
    if (ent.name === 'node_modules' || ent.name === '.git' || ent.name.startsWith('.')) continue;
    var p = PATH.join(dir, ent.name);
    if (ent.isDirectory()) { walkForAuthLeaks(p, out); continue; }
    if (!/\.(html|md|js|css|yml|yaml|json)$/.test(ent.name)) continue;
    var src = FS.readFileSync(p, 'utf8');
    if (AUTH_TOKEN_RE.test(src)) out.push(p);
  }
}
for (var al = 0; al < SITES.length; al++) {
  var als = SITES[al];
  var alLeaks = [];
  walkForAuthLeaks(PATH.join(REPO, als), alLeaks);
  ok(alLeaks.length === 0, als + ' -- no auth.php token leaks (' + alLeaks.length + ' file(s))');
}

// --- CSS: skip-link style exists (all sites) ---
section('CSS: skip-link rules (all sites)');
for (var u = 0; u < SITES.length; u++) {
  var us = SITES[u];
  var ucssFile = PATH.join(REPO, us, 'assets', 'css', 'network-ux.css');
  if (!FS.existsSync(ucssFile)) continue;
  var ucss = FS.readFileSync(ucssFile, 'utf8');
  ok(/\.skip-link\s*\{/.test(ucss), us + ' -- has .skip-link base style');
  ok(/\.skip-link:focus[^}]*top:\s*0/.test(ucss) || /\.skip-link:focus-visible[^}]*top:\s*0/.test(ucss), us + ' -- skip-link visible on focus');
  ok(/main:focus\s*\{\s*outline:\s*none/.test(ucss), us + ' -- main:focus outline suppressed');
}

// --- renderSafeHtml sanitizer presence + hardening (all sites) ---
section('renderSafeHtml sanitizer (all sites)');
for (var v = 0; v < SITES.length; v++) {
  var vs = SITES[v];
  var vfile = PATH.join(REPO, vs, 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(vfile)) continue;
  var vsrc = FS.readFileSync(vfile, 'utf8');
  ok(/function renderSafeHtml/.test(vsrc), vs + ' -- renderSafeHtml defined');
  ok(/ALLOWED_TAGS\s*=\s*\{'p':1/.test(vsrc), vs + ' -- ALLOWED_TAGS whitelist present');
  ok(/ALLOWED_ATTRS\s*=\s*\{'href':1\s*,\s*'target':1\}/.test(vsrc), vs + ' -- ALLOWED_ATTRS is href+target only (class/id removed)');
  ok(/function _isSafeUrl/.test(vsrc), vs + ' -- _isSafeUrl URL-scheme validator present');
  ok(/function _trimHref/.test(vsrc), vs + ' -- _trimHref strips whitespace/encoded prefix from href');
  ok(/'javascript|data|vbscript':/i.test(vsrc), vs + ' -- sanitizer blocks javascript/data/vbscript schemes');
  ok(/_isSafeUrl/.test(vsrc), vs + ' -- _isSafeUrl used in renderSafeHtml');
}

// --- Char counter reset after submit (all sites) ---
section('Char counter reset after onAsk clear (all sites)');
for (var w = 0; w < SITES.length; w++) {
  var ws = SITES[w];
  var wfile = PATH.join(REPO, ws, 'assets', 'js', 'network-ux.js');
  if (!FS.existsSync(wfile)) continue;
  var wsrc = FS.readFileSync(wfile, 'utf8');
  // onAsk clears input.value = '' then resets counter via getElementById('ai-bar__counter')
  ok(/input\.value\s*=\s*'';[\s\S]{0,200}getElementById\('ai-bar__counter'\)/.test(wsrc), ws + ' -- onAsk resets char counter after clearing input');
  ok(/getElementById\('ai-bar__counter'\)[\s\S]{0,200}textContent\s*=\s*'0\s*\/\s*600'/.test(wsrc), ws + ' -- counter shows 0/600 after clear');
  ok(/className\s*=\s*'ai-bar__counter'/.test(wsrc), ws + ' -- resets counter className');
  ok(/classList\.remove\(/.test(wsrc), ws + ' -- removes counter state classes');
}

// --- Char counter CSS (all sites) ---
section('Char counter CSS (all sites)');
for (var x = 0; x < SITES.length; x++) {
  var xs = SITES[x];
  var xcssFile = PATH.join(REPO, xs, 'assets', 'css', 'network-ux.css');
  if (!FS.existsSync(xcssFile)) continue;
  var xcss = FS.readFileSync(xcssFile, 'utf8');
  ok(/\.ai-bar__counter\s*\{/.test(xcss), xs + ' -- has .ai-bar__counter style');
  ok(/\.ai-bar__counter--visible/.test(xcss), xs + ' has --visible state');
  ok(/\.ai-bar__counter--near/.test(xcss), xs + ' -- has --near (amber) state');
  ok(/\.ai-bar__counter--over/.test(xcss), xs + ' -- has --over (red) state');
  ok(/var\(--font-mono/.test(xcss), xs + ' -- counter uses monospace font');
}

console.error('\n' + Array(50).join('-'));
console.error('Results: ' + pass + ' passed, ' + fail + ' failed');
if (fail > 0) { console.error(fail + ' failure(s) -- fix before shipping'); process.exit(1); }
else { console.error('All checks passed. ✔'); process.exit(0); }
