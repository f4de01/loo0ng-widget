// 原型（抛弃式）。页面里含算法只因为这是原型；实现票里页面不许算（不变量 4）。
import { synthetic } from './prototype-data.js';

const VARIANTS = [['A', '纸'], ['B', '雾'], ['C', '墨']];
const params = new URLSearchParams(location.search);
const dev = params.get('dev') === '1';
const html = document.documentElement;
const card = document.querySelector('#card');
const track = document.querySelector('#track');
const listPage = document.querySelector('#list');
const casePage = document.querySelector('#case');
const pop = document.querySelector('#pop');
const diagBox = document.querySelector('#diag');
document.body.classList.add(/Mac|iPhone|iPad/.test(navigator.userAgent) ? 'mac' : 'win');

// 呈现偏好（ADR-0002）：页、案、形式；原型里再加变量名。
const PREF = 'loo0ng.prototype.prefs';
let prefs = { page: 'list', casePath: null, form: 'module', variant: params.get('variant') || 'A', blur: '0' };
try { prefs = { ...prefs, ...JSON.parse(localStorage.getItem(PREF) || '{}') }; } catch { /* 缺失或无效就回预设 */ }
if (params.get('variant')) prefs.variant = params.get('variant');
if (params.get('blur')) prefs.blur = params.get('blur');
function savePrefs() { try { localStorage.setItem(PREF, JSON.stringify(prefs)); } catch { /* 不可写就算了 */ } }

let data = synthetic();
const openModules = new Set();

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}
const STATE_CLASS = { 未生成: 's-unstarted', 已生成: 's-generated', 已确认: 's-confirmed', 不适用: 's-na' };
function mark(kind, node) {
  const m = el('i', `${kind} ${STATE_CLASS[node.状态]}${node.高亮 === '未清' ? ' attention' : ''}`);
  return m;
}
function bar(progress) {
  const b = el('div', 'bar');
  for (const [state, cls] of [['已确认', 's-confirmed'], ['已生成', 's-generated'], ['未生成', 's-unstarted'], ['不适用', 's-na']]) {
    const seg = el('i', cls);
    seg.style.flexGrow = progress[state];
    b.append(seg);
  }
  return b;
}
function count(progress) { return el('span', 'count', `${progress.已确认} / ${progress.总数}`); }

// ---------- 清单页 ----------
function renderList() {
  listPage.replaceChildren();
  listPage.append(el('div', 'top', `在办案件 ${data.案件数}`));
  for (const row of data.行) {
    const r = el('article', 'case-row');
    const name = el('div', 'name');
    name.append(el('h2', null, row.目录名), count(row.进度));
    const now = el('div', 'now');
    if (row.当前节点) {
      now.append(mark('dot', row.当前节点), el('span', null, `${row.当前模块 ?? ''} › ${row.当前节点.标题}`));
    } else {
      now.append(el('span', 'muted', row.进度.总数 === 0 ? '图还是空的' : '没有前方了'));
    }
    r.append(name, bar(row.进度), now);
    r.addEventListener('click', () => { if (!dragMoved) enterCase(row.路径); });
    listPage.append(r);
  }
  for (const failure of data.读不出) {
    const u = el('div', 'unreadable');
    u.append(el('b', null, failure.目录名), document.createTextNode(`：${failure.原因}`));
    listPage.append(u);
  }
}

// ---------- 案件页 ----------
function currentRow() { return data.行.find(r => r.路径 === prefs.casePath) ?? null; }
function renderCase(flashNode) {
  casePage.replaceChildren();
  const row = currentRow();
  if (!row) return; // 那案消失就清空，不提示、不返回
  const head = el('div', 'case-head');
  const back = el('button', 'back', '‹');
  back.addEventListener('click', () => { prefs.page = 'list'; savePrefs(); track.classList.remove('case'); });
  const barline = el('div', 'barline');
  barline.append(bar(row.进度), count(row.进度));
  const seg = el('div', 'seg');
  for (const [form, label] of [['module', '模块'], ['matrix', '矩阵']]) {
    const b = el('button', prefs.form === form ? 'on' : '', label);
    b.addEventListener('click', () => { prefs.form = form; savePrefs(); renderCase(); });
    seg.append(b);
  }
  head.append(back, barline, seg);
  casePage.append(head);
  casePage.append(prefs.form === 'module' ? moduleView(row, flashNode) : matrixView(row));
}

function moduleView(row, flashNode) {
  const wrap = el('div', 'modules');
  for (const m of row.模块) {
    const key = `${row.路径}|${m.标题}`;
    if (!openModules.has(key) && !openModules.has(`closed:${key}`) && m.状态 === '进行中') openModules.add(key);
    const mod = el('section', `mod${openModules.has(key) ? ' open' : ''}`);
    const head = el('div', 'mod-head');
    head.append(el('span', 'chev', '▶'), el('span', 'title', m.标题),
      el('span', `state ${m.状态 === '已完成' ? 's-done' : m.状态 === '不适用' ? 's-na' : ''}`, m.状态), count(m.进度));
    head.addEventListener('click', () => {
      if (dragMoved) return;
      if (openModules.has(key)) { openModules.delete(key); openModules.add(`closed:${key}`); mod.classList.remove('open'); }
      else { openModules.add(key); openModules.delete(`closed:${key}`); mod.classList.add('open'); }
    });
    const nodes = el('div', 'nodes');
    if (m.节点.length === 0) nodes.append(el('div', 'empty-note', '还没有节点'));
    for (const n of m.节点) {
      const line = el('div', 'node');
      const title = el('span', 'title');
      title.append(el('b', null, n.标题));
      if (n.时限) {
        const d = el('span', 'deadline', n.时限);
        hoverable(d, () => [[null, n.时限]]);
        title.append(d);
      }
      line.append(mark('dot', n), title, el('time', null, n.时间显示 ?? ''));
      if (flashNode && flashNode === n) {
        line.classList.add('flash');
        requestAnimationFrame(() => line.scrollIntoView({ block: 'center', behavior: 'smooth' }));
      }
      nodes.append(line);
    }
    mod.append(head, nodes);
    wrap.append(mod);
  }
  return wrap;
}

function matrixView(row) {
  const wrap = el('div', 'matrix-wrap');
  const matrix = el('div', 'matrix');
  matrix.style.setProperty('--n', Math.max(row.模块.length, 1));
  for (const m of row.模块) {
    const col = el('div', `col${m.状态 === '已完成' ? ' s-done' : m.状态 === '不适用' ? ' s-na' : ''}`);
    if (m.节点.length === 0) col.append(el('i', 'cell empty'));
    for (const n of m.节点) {
      const c = mark('cell', n);
      hoverable(c, () => {
        const lines = [['b', `${m.标题} › ${n.标题}`],
          ['sub', n.时间显示 ? `${n.状态} · ${n.时间显示}` : n.状态]];
        if (n.时限) lines.push(['deadline', n.时限]);
        if (n.高亮 === '未清') lines.push(['look', '等你看']);
        return lines;
      });
      c.addEventListener('click', () => {
        if (dragMoved) return;
        prefs.form = 'module'; savePrefs();
        openModules.add(`${row.路径}|${m.标题}`); openModules.delete(`closed:${row.路径}|${m.标题}`);
        hidePop(); renderCase(n);
      });
      col.append(c);
    }
    const label = el('div', 'col-label', m.标题);
    hoverable(label, () => [[null, m.标题]]);
    col.append(label);
    matrix.append(col);
  }
  wrap.append(matrix);
  return wrap;
}

function enterCase(path) {
  prefs.page = 'case'; prefs.casePath = path; savePrefs();
  renderCase();
  track.classList.add('case');
}

// ---------- 悬浮概览 ----------
function hoverable(target, lines) {
  target.addEventListener('mouseenter', event => showPop(lines(), event));
  target.addEventListener('mousemove', event => placePop(event));
  target.addEventListener('mouseleave', hidePop);
}
function showPop(lines, event) {
  pop.replaceChildren();
  for (const [cls, text] of lines) pop.append(el('div', cls, text));
  pop.hidden = false;
  placePop(event);
}
function placePop(event) {
  if (pop.hidden) return;
  const box = card.getBoundingClientRect();
  let x = event.clientX - box.left + 12, y = event.clientY - box.top + 14;
  if (x + pop.offsetWidth > box.width - 8) x = box.width - 8 - pop.offsetWidth;
  if (y + pop.offsetHeight > box.height - 8) y = event.clientY - box.top - pop.offsetHeight - 8;
  pop.style.left = `${Math.max(8, x)}px`; pop.style.top = `${Math.max(8, y)}px`;
}
function hidePop() { pop.hidden = true; }

// ---------- 原型切换条 ----------
const switcher = document.querySelector('#switcher');
function applyVariant() {
  html.dataset.variant = prefs.variant;
  html.dataset.blur = prefs.blur;
  savePrefs();
  if (dev) {
    const url = new URL(location); url.searchParams.set('variant', prefs.variant); history.replaceState(null, '', url);
  }
  renderSwitcher();
}
function cycle(step) {
  const i = VARIANTS.findIndex(([k]) => k === prefs.variant);
  prefs.variant = VARIANTS[(i + step + VARIANTS.length) % VARIANTS.length][0];
  applyVariant();
}
function renderSwitcher() {
  switcher.replaceChildren();
  const prev = el('button', '', '‹'); prev.addEventListener('click', () => cycle(-1));
  const next = el('button', '', '›'); next.addEventListener('click', () => cycle(1));
  const [k, name] = VARIANTS.find(([key]) => key === prefs.variant);
  const blur = el('button', prefs.blur === '1' ? 'on' : '', '60%');
  blur.title = '模拟系统模糊成功：底色降到 60%（浏览器里只模糊页面自己，桌面不会透）';
  blur.addEventListener('click', () => { prefs.blur = prefs.blur === '1' ? '0' : '1'; applyVariant(); });
  switcher.append(prev, el('span', null, `${k} ${name}`), next, blur);
  if (dev) {
    const bg = el('button', '', '背景'); let n = 1;
    bg.addEventListener('click', () => { n = n % 3 + 1; document.body.className = `dev win bg-${n}`; });
    switcher.append(bg);
  }
}
document.addEventListener('keydown', event => {
  if (event.target.matches('input, textarea, [contenteditable]')) return;
  if (event.key === 'ArrowLeft') cycle(-1);
  if (event.key === 'ArrowRight') cycle(1);
  if (event.key === 'b' && bench) bench();
  if (event.key === 'd') { diagBox.hidden = !diagBox.hidden; switcher.hidden = !switcher.hidden; }
  if (event.key === 'm') html.style.setProperty('--margin', html.style.getPropertyValue('--margin') === '0px' ? '' : '0px');
});

// ---------- 启动 ----------
let dragMoved = false;
let bench = null;
function boot() {
  applyVariant();
  renderList();
  if (dev && params.get('case')) {
    prefs.casePath = data.行.find(r => r.目录名 === params.get('case'))?.路径 ?? null;
    prefs.page = 'case'; prefs.form = params.get('form') || prefs.form;
  }
  if (prefs.page === 'case' && currentRow()) {
    // 启动时回到上次那页不动画
    track.style.transition = 'none'; renderCase(); track.classList.add('case');
    requestAnimationFrame(() => requestAnimationFrame(() => { track.style.transition = ''; }));
  } else { prefs.page = 'list'; }
}

function hostState() {
  if (window.__ZEBAR_STATE) return window.__ZEBAR_STATE;
  try { return JSON.parse(sessionStorage.getItem('ZEBAR_STATE')); } catch { return null; }
}

if (dev) {
  document.body.classList.add('dev');
  // 截图用：frame=440x620 把卡片定成那个窗的大小；shot=1 藏起原型工具。
  const frame = params.get('frame')?.match(/^(\d+)x(\d+)$/);
  if (frame) {
    document.body.style.width = `${frame[1]}px`; document.body.style.height = `${frame[2]}px`;
    card.style.inset = 'auto'; card.style.left = card.style.top = 'var(--margin)';
    card.style.width = `${frame[1] - 24}px`; card.style.height = `${frame[2] - 24}px`;
  }
  if (params.get('shot') === '1') { switcher.hidden = true; document.querySelector('#development').hidden = true; }
  if (params.get('shot') !== '1') document.querySelector('#development').hidden = false;
  document.querySelector('#preview').addEventListener('change', async event => {
    for (const file of event.target.files) { data = JSON.parse(await file.text()); boot(); }
  });
  boot();
} else if (hostState()) {
  boot();
  import('./vendor/zebar-3.3.1.js').then(setupHost).catch(error => diag(`宿主客户端载入失败：${error}`));
} else {
  boot();
  diag('未识别到 Zebar 宿主，也没带 ?dev=1：只看样式，没有窗口行为。');
}

// ---------- 宿主：材质 spike、整卡可拖、窗口按钮、基准 ----------
function diag(line) { diagBox.hidden = false; diagBox.textContent += (diagBox.textContent ? '\n' : '') + line; }

async function setupHost(zebar) {
  const { PhysicalPosition, PhysicalSize } = await import('./vendor/tauri-apps_api2.0.2_es2022_dpi.js');
  const widget = zebar.currentWidget();
  const win = widget.tauriWindow;
  let position = await win.outerPosition();
  const size = await win.outerSize();
  const scale = window.devicePixelRatio || 1;
  diag(`窗 ${position.x},${position.y} ${size.width}×${size.height} dpr=${scale} ua=${navigator.userAgent.match(/Edg\S+/)?.[0]}`);

  // 材质：试调一次 Acrylic；失败就一言不发停在自绘层（这里为了 spike 把结果打出来）。
  async function effect(names) {
    const t0 = performance.now();
    try {
      if (names.length) await win.setEffects({ effects: names }); else await win.clearEffects();
      html.dataset.blur = names.length ? '1' : '0';
      prefs.blur = html.dataset.blur;
      return `${names.join('+') || 'none'} ok ${(performance.now() - t0).toFixed(1)}ms`;
    } catch (error) {
      html.dataset.blur = '0';
      return `${names.join('+') || 'none'} FAIL ${(performance.now() - t0).toFixed(1)}ms ${error}`;
    }
  }
  diag(`setEffects: ${await effect(['acrylic'])}`);
  // e 键轮换效果，看哪种在这扇窗里真透出桌面。
  const TRIALS = [
    { effects: ['acrylic'], color: [243, 242, 236, 120] }, { effects: ['mica'] }, { effects: ['blur'] },
    { effects: ['tabbed'] }, { effects: [] }, { effects: ['acrylic'] },
  ];
  let trial = 0;
  document.addEventListener('keydown', async event => {
    if (event.key !== 'e') return;
    const t = TRIALS[trial++ % TRIALS.length];
    const t0 = performance.now();
    try {
      if (t.effects.length) await win.setEffects({ effects: t.effects, color: t.color }); else await win.clearEffects();
      html.dataset.blur = t.effects.length ? '1' : '0';
      diag(`e: ${JSON.stringify(t)} ok ${(performance.now() - t0).toFixed(1)}ms`);
    } catch (error) { html.dataset.blur = '0'; diag(`e: ${JSON.stringify(t)} FAIL ${error}`); }
  });

  // 帧间隔记录：拖动或基准期间每一帧的间隔，算均值与最大值。
  let gaps = null, last = 0, raf = 0;
  function tick(now) { if (last) gaps.push(now - last); last = now; raf = requestAnimationFrame(tick); }
  function startGaps() { gaps = []; last = 0; raf = requestAnimationFrame(tick); }
  function stopGaps() {
    cancelAnimationFrame(raf); raf = 0;
    if (!gaps || !gaps.length) return 'no frames';
    const mean = gaps.reduce((a, b) => a + b, 0) / gaps.length;
    const max = Math.max(...gaps);
    const over = gaps.filter(g => g > 33).length;
    return `${gaps.length} 帧 均 ${mean.toFixed(1)}ms 峰 ${max.toFixed(0)}ms >33ms:${over}`;
  }

  // 整卡可拖：交互区除外，阈值 4px。
  let drag = null;
  document.addEventListener('pointerdown', event => {
    if (event.button !== 0 || event.target.closest('button, .case-row, .mod-head, .node, .cell, .switcher, .diag, input')) return;
    drag = { id: event.pointerId, sx: event.screenX, sy: event.screenY, x: position.x, y: position.y, moved: false, busy: null, next: null };
    dragMoved = false;
  });
  document.addEventListener('pointermove', event => {
    if (!drag || event.pointerId !== drag.id) return;
    const dx = event.screenX - drag.sx, dy = event.screenY - drag.sy;
    if (!drag.moved) {
      if (Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
      drag.moved = true; dragMoved = true; card.classList.add('dragging'); startGaps();
    }
    drag.next = { x: Math.round(drag.x + dx * scale), y: Math.round(drag.y + dy * scale) };
    pump();
  });
  function pump() {
    if (!drag || drag.busy || !drag.next) return;
    const p = drag.next; drag.next = null;
    drag.busy = win.setPosition(new PhysicalPosition(p.x, p.y)).then(() => { position = p; }).catch(() => {}).then(() => { if (drag) { drag.busy = null; pump(); } });
  }
  function endDrag() {
    if (!drag) return;
    if (drag.moved) { card.classList.remove('dragging'); diag(`拖动(${html.dataset.blur === '1' ? 'acrylic' : '自绘'}): ${stopGaps()}`); }
    drag = null;
    setTimeout(() => { dragMoved = false; }, 0);
  }
  document.addEventListener('pointerup', endDrag);
  document.addEventListener('pointercancel', endDrag);
  window.addEventListener('blur', endDrag);
  await win.onMoved(({ payload }) => { if (!drag) position = payload; });

  let resizeGaps = null, benching = false;
  window.addEventListener('resize', () => {
    if (benching) return;
    if (!resizeGaps) { startGaps(); resizeGaps = setTimeout(() => {}, 0); }
    clearTimeout(resizeGaps);
    resizeGaps = setTimeout(() => { resizeGaps = null; diag(`缩放(${html.dataset.blur === '1' ? 'acrylic' : '自绘'}): ${stopGaps()}`); }, 400);
  });

  document.querySelector('#minimize').addEventListener('click', () => win.minimize().catch(e => diag(String(e))));
  document.querySelector('#close').addEventListener('click', () => widget.close().catch(e => diag(String(e))));

  // 基准：按 b 键或 3 秒后自动跑一次。同一段移动与缩放，acrylic 与自绘各跑一遍。
  bench = async () => {
    if (benching) return;
    benching = true;
    for (const names of [['acrylic'], [], ['acrylic']]) {
      diag(`— ${await effect(names)}`);
      const origin = await win.outerPosition();
      startGaps();
      const t0 = performance.now();
      for (let i = 1; i <= 60; i++) await win.setPosition(new PhysicalPosition(origin.x - i * 3, origin.y + (i % 2) * 2));
      const moveMs = performance.now() - t0;
      const moveGaps = stopGaps();
      await win.setPosition(new PhysicalPosition(origin.x, origin.y));
      const base = await win.outerSize();
      startGaps();
      const t1 = performance.now();
      for (let i = 1; i <= 30; i++) await win.setSize(new PhysicalSize(base.width + i * 4, base.height + i * 4));
      for (let i = 30; i >= 0; i--) await win.setSize(new PhysicalSize(base.width + i * 4, base.height + i * 4));
      const sizeMs = performance.now() - t1;
      diag(`  移 60 步 ${moveMs.toFixed(0)}ms (${(moveMs / 60).toFixed(1)}ms/步) ${moveGaps}`);
      diag(`  缩 61 步 ${sizeMs.toFixed(0)}ms (${(sizeMs / 61).toFixed(1)}ms/步) ${stopGaps()}`);
      position = await win.outerPosition();
    }
    diag('基准完');
    benching = false;
  };
  if (!localStorage.getItem('loo0ng.prototype.benched')) { localStorage.setItem('loo0ng.prototype.benched', '1'); setTimeout(() => bench(), 3000); }
}
