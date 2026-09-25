const heading = document.querySelector('#heading');
const rows = document.querySelector('#rows');
const unreadable = document.querySelector('#unreadable');
const guide = document.querySelector('#settings-error');
const banner = document.querySelector('#scan-error');
const card = document.querySelector('.card');
const listPanes = [document.querySelector('#list-top'), document.querySelector('#list-page')];
const casePage = document.querySelector('#case-page');
const casePanes = [document.querySelector('#case-top'), casePage];
const caseBar = document.querySelector('#case-bar');
const pop = document.querySelector('#pop');
const formButtons = document.querySelectorAll('.forms button');
// 圆圈与分段进度条共用一套编码，这里只把扫描脚本给的状态换成类名，不判定、不计数。
const SHAPE = {'未生成': 's-unstarted', '已生成': 's-generated', '已确认': 's-confirmed', '不适用': 's-na'};
const SEGMENTS = ['已确认', '已生成', '未生成', '不适用'];
// 模块的三态，同样只换类名。
const MODULE_STATE = {'进行中': 'm-active', '已完成': 'm-done', '不适用': 'm-na'};
document.body.classList.add(/Mac|iPhone|iPad/.test(navigator.userAgent) ? 'mac' : 'win');
// Start local module loading before the first interaction, shared with polling.
const hostClient = hostState() ? import('./vendor/zebar-3.3.1.js') : null;
if (hostClient) hostClient.catch(showError);

// 呈现偏好（ADR-0002）：窗口位置（window.js）之外只多这两项，都在 WebView 本地存储里，不碰文件。
// 启动时记住的总是赢；缺失、无效、不可读就回到清单页、回到模块视。
const PLACE = 'loo0ng.place';
const FORM = 'loo0ng.form';
// 案件页的两种形式；表头两枚按钮切换，切换时写下 FORM。
const VIEWS = {module: moduleView, matrix: matrixView};

function recall(key, valid) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return valid(value) ? value : null;
  } catch {
    return null;
  }
}

function keep(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); }
  catch { /* 存不进去就只记在这一次里，翻页照常。 */ }
}

// 停在哪一页哪一案：清单页是 {page: 'list'}，案件页按工作区路径记。
let place = recall(PLACE, value => value?.page === 'list'
  || (value?.page === 'case' && typeof value.path === 'string' && value.path !== ''))
  ?? {page: 'list'};
let form = recall(FORM, value => Object.prototype.hasOwnProperty.call(VIEWS, value)) ?? 'module';
// 用户动过的模块行：键是「工作区路径 + 模块标题」，值是展开与否。没动过的按模块状态默认。
// 只活在这一次里，不进本地存储——呈现偏好只有那三样。
const toggled = new Map();
// 最近一轮扫描的输出，与案件页上一次照着画的那一案的 JSON 串（没画任何一案时是空串）。
let latestScan = null;
let shownSnapshot = null;

function textElement(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

// 四段的宽度比就是四个计数之比：交给 flex-grow，页面不算比例；扫描脚本给 0 的那段不画，
// 免得段间那 2px 的缝替一个空段占着位置。
function segmentedBar(progress) {
  const bar = document.createElement('div');
  bar.className = 'bar';
  bar.setAttribute('aria-hidden', 'true');
  for (const state of SEGMENTS) {
    if (!progress[state]) continue;
    const segment = textElement('i', '', SHAPE[state]);
    segment.style.flexGrow = String(progress[state]);
    bar.append(segment);
  }
  return bar;
}

function countText(progress) {
  return textElement('span', `${progress.已确认} / ${progress.总数}`, 'count');
}

// 圆圈与矩阵格共用的深浅编码：状态换类名，高亮未清再加一个类（圆圈画琥珀圈，矩阵格不画，只进悬浮概览）。
function encode(element, node) {
  if (SHAPE[node.状态]) element.classList.add(SHAPE[node.状态]);
  if (node.高亮 === '未清') element.classList.add('attention');
  return element;
}

function circle(node) {
  const dot = encode(textElement('i', '', 'dot'), node);
  dot.setAttribute('aria-hidden', 'true');
  return dot;
}

function render(data) {
  // 设置错误：整页只剩那段可照做的指引，连顶上的计数都不印。
  guide.textContent = data.设置错误?.原因 ?? '';
  guide.hidden = !data.设置错误;
  heading.hidden = Boolean(data.设置错误);
  document.querySelector('#count').textContent = data.案件数;
  rows.replaceChildren();
  for (const row of data.行) {
    const article = document.createElement('article');
    // .interactive 是交互区的记号：按住它不拖窗（#17），点它进案件页（#18）。
    article.className = 'case-row interactive';
    article.tabIndex = 0;
    article.setAttribute('role', 'button');
    article.addEventListener('click', () => enterCase(row.路径));
    article.addEventListener('keydown', event => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      enterCase(row.路径);
    });
    // 计数紧跟在进度条右边（#24），名字那一行只剩名字。
    const barline = document.createElement('div');
    barline.className = 'barline';
    barline.append(segmentedBar(row.进度), countText(row.进度));
    const now = document.createElement('div');
    now.className = 'now';
    if (row.当前节点) {
      now.append(circle(row.当前节点),
        textElement('span', `${row.当前模块 ?? '—'} › ${row.当前节点.标题}`));
    } else {
      now.append(textElement('span', '—'));
    }
    article.append(textElement('h2', row.目录名), barline, now);
    rows.append(article);
  }
  unreadable.replaceChildren();
  for (const failure of data.读不出) {
    const line = textElement('div', '', 'unreadable');
    line.append(textElement('b', failure.目录名), document.createTextNode(`：${failure.原因}`));
    unreadable.append(line);
  }
  latestScan = data;
  renderCase();
}

// 案件页：表头是返回、分段进度条与计数，正文是选中的形式。那案不在这一轮输出里
// （读不出、被挪走）就清空正文，表头保留上一次画的进度条与计数——不提示、不自动回清单页；
// 启动时还没扫过第一轮，表头也还没有可画的。
// 设置没填好时一案都没有，正文印那段可照做的指引：整张卡片都只该有它，不能藏在清单页里。
function renderCase() {
  // 按工作区路径认出那一案：是查找，不是挑选。一轮输出里路径不重由扫描脚本保证，页面不去保证。
  const row = place.page === 'case' ? latestScan?.行.find(candidate => candidate.路径 === place.path) : null;
  const guidance = latestScan?.设置错误?.原因 ?? '';
  // 这一案的字段一个没变就不重画：展开状态、滚动位置、正停着的悬浮都不被五秒一轮打断。
  const snapshot = row ? JSON.stringify(row) : guidance;
  if (snapshot === shownSnapshot) return;
  shownSnapshot = snapshot;
  hidePop();
  if (!row) {
    casePage.replaceChildren();
    if (guidance) casePage.append(textElement('p', guidance, 'guide'));
    return;
  }
  caseBar.replaceChildren(segmentedBar(row.进度), countText(row.进度));
  casePage.replaceChildren(VIEWS[form](row));
}

function moduleKey(row, module) {
  return `${row.路径}
${module.标题}`;
}

// 模块视：进行中的默认展开，已完成与不适用折叠，允许多开；节点行四段，点了无事。
function moduleView(row) {
  const view = document.createElement('div');
  view.className = 'modules';
  for (const module of row.模块) {
    const key = moduleKey(row, module);
    const section = document.createElement('section');
    section.className = 'module';
    // 模块行做成原生 button：它自己就在交互区里（#17），键盘也按得动。
    const head = document.createElement('button');
    head.type = 'button';
    head.className = 'module-head';
    const state = textElement('span', module.状态, 'state');
    if (MODULE_STATE[module.状态]) state.classList.add(MODULE_STATE[module.状态]);
    head.append(textElement('span', '', 'chevron'), textElement('span', module.标题, 'title'), state,
      countText(module.进度));
    const nodes = document.createElement('div');
    nodes.className = 'nodes';
    for (const node of module.节点) nodes.append(nodeLine(node));
    const setOpen = open => {
      section.classList.toggle('open', open);
      head.setAttribute('aria-expanded', String(open));
    };
    setOpen(toggled.get(key) ?? module.状态 === '进行中');
    head.addEventListener('click', () => {
      const next = !section.classList.contains('open');
      toggled.set(key, next);
      setOpen(next);
    });
    section.append(head, nodes);
    view.append(section);
  }
  return view;
}

// 节点行四段：圆圈 | 标题 | 时限（一行省略，悬浮见全文）| 时间靠右。时间只印扫描脚本给的显示串，
// 它按状态给或不给，页面不判。整行是交互区（.interactive）：点了无事，但按住它不拖窗。
// 行上也挂状态类：不适用的圆圈与未生成一样是空白，靠整行字变淡区分（#24）。
function nodeLine(node) {
  const line = document.createElement('div');
  line.className = 'node interactive';
  if (SHAPE[node.状态]) line.classList.add(SHAPE[node.状态]);
  line.append(circle(node), textElement('span', node.标题, 'title'));
  const deadline = textElement('span', node.时限 ?? '', 'deadline');
  if (node.时限) hoverPop(deadline, [node.时限]);
  const moment = textElement('time', node.时间显示 ?? '');
  if (node.时间) moment.dateTime = node.时间;
  line.append(deadline, moment);
  return line;
}

// 矩阵视（#24）：一块不透明的浅底板，上面一行图例、中间格阵、下面横轴。
// 格阵一个模块一组格，一格一节点，都照扫描输出的图序摆，页面不排；格的颜色是圆圈那一套类。
// 七格一列按列流、模块满了接着占下一列、露出的列数取整、占位格铺到右缘，
// 全在样式表里由布局得出，页面不数节点、不算尺寸、不补占位格。空模块不占列，也是样式表按「组里没有格」收掉的。
// 横轴：每组首列下竖排模块全名；模块最近一次动过的日期不上横轴，只在标签的悬浮里。
function matrixView(row) {
  const view = document.createElement('div');
  view.className = 'matrix';
  const lane = document.createElement('div');
  lane.className = 'lane';
  const strip = document.createElement('div');
  strip.className = 'strip';
  lane.append(strip);
  view.append(legend(row.进度), lane);
  row.模块.forEach((module, moduleIndex) => {
    const group = document.createElement('div');
    group.className = 'group';
    const cells = document.createElement('div');
    cells.className = 'cells';
    module.节点.forEach((node, nodeIndex) => {
      const cell = encode(textElement('div', '', 'cell interactive'), node);
      const lines = [`${module.标题} › ${node.标题}`,
        node.时间显示 ? `${node.状态} · ${node.时间显示}` : node.状态];
      if (node.时限) lines.push(node.时限);
      if (cell.classList.contains('attention')) lines.push('等你看');
      cell.setAttribute('aria-label', lines.join('，'));
      hoverPop(cell, lines);
      cell.addEventListener('click', () => locate(row, moduleIndex, nodeIndex));
      cells.append(cell);
    });
    const label = textElement('div', module.标题, 'axis-label');
    hoverPop(label, module.时间显示 ? [module.标题, module.时间显示] : [module.标题]);
    group.append(cells, label);
    strip.append(group);
  });
  return view;
}

// 图例：色块 + 状态原词 + 计数，数字照扫描脚本给的四个计数印；空白一档把未生成与不适用分开写，页面不做加法。
function legend(progress) {
  const item = (state, swatch) => {
    const span = textElement('span', `${state} ${progress[state]}`, 'legend-item');
    if (swatch) span.prepend(textElement('i', '', `swatch ${SHAPE[state]}`));
    return span;
  };
  const line = document.createElement('div');
  line.className = 'legend';
  // 空白那一档共用一个色块：未生成与不适用挨着写成一项。
  const blank = document.createElement('span');
  blank.append(item('未生成', true), ' · ', item('不适用', false));
  line.append(item('已确认', true), item('已生成', true), blank);
  return line;
}

// 点一个格：切到模块视，展开那个模块，把那个节点行摆到案件页中间，底色闪一次。
// 第几个模块、第几个节点是这一格在输出里的位置，模块视照同一份输出同一个次序画，按位置就找得到。
function locate(row, moduleIndex, nodeIndex) {
  toggled.set(moduleKey(row, row.模块[moduleIndex]), true);
  switchForm('module');
  const line = casePage.querySelectorAll('.module')[moduleIndex]?.querySelectorAll('.node')[nodeIndex];
  if (!line) return;
  const page = casePage.getBoundingClientRect();
  const box = line.getBoundingClientRect();
  casePage.scrollTop += box.top - page.top - (page.height - box.height) / 2;
  // 系统减少动态时样式表不放这段动画，只定位不闪。
  line.classList.add('flash');
  line.addEventListener('animationend', () => line.classList.remove('flash'), {once: true});
}

function switchForm(next) {
  form = next;
  keep(FORM, form);
  markForm();
  // 形式变了，同一案也要照新形式重画一遍。
  shownSnapshot = null;
  casePage.scrollTop = 0;
  renderCase();
}

function markForm() {
  for (const button of formButtons) button.setAttribute('aria-pressed', String(button.dataset.form === form));
}

// 自绘浮层：停上去出现、跟着指针、移开消失；一行一段。
function hoverPop(element, lines) {
  element.addEventListener('mouseenter', event => showPop(lines, event));
  element.addEventListener('mousemove', placePop);
  element.addEventListener('mouseleave', hidePop);
}

function showPop(lines, event) {
  pop.replaceChildren(...lines.map(line => textElement('div', line)));
  pop.hidden = false;
  placePop(event);
}

// 浮层贴着指针右下，碰到卡片边就往回收；这是摆位置，不碰扫描来的数据。
function placePop(event) {
  if (pop.hidden) return;
  const box = card.getBoundingClientRect();
  let x = event.clientX - box.left + 12;
  let y = event.clientY - box.top + 14;
  if (x + pop.offsetWidth > box.width - 8) x = box.width - 8 - pop.offsetWidth;
  if (y + pop.offsetHeight > box.height - 8) y = event.clientY - box.top - pop.offsetHeight - 8;
  pop.style.left = `${Math.max(8, x)}px`;
  pop.style.top = `${Math.max(8, y)}px`;
}

function hidePop() {
  pop.hidden = true;
}

// 两页一窗：一个类把顶行与正文两条轨道一起推过去，180ms，系统减少动态时样式表里不动。
// 不在眼前的那一页设成 inert：键盘走不进去、悬浮碰不到。
function showPage(onCase) {
  card.classList.toggle('on-case', onCase);
  for (const pane of listPanes) pane.inert = onCase;
  for (const pane of casePanes) pane.inert = !onCase;
}

function enterCase(path) {
  place = {page: 'case', path};
  keep(PLACE, place);
  keep(FORM, form);
  casePage.scrollTop = 0;
  renderCase();
  showPage(true);
}

for (const button of formButtons) button.addEventListener('click', () => switchForm(button.dataset.form));

document.querySelector('#back').addEventListener('click', () => {
  place = {page: 'list'};
  keep(PLACE, place);
  hidePop();
  showPage(false);
});

// 启动时回到记住的那一页，不滑：打开卡片就该停在那里，而不是看它从清单页滑过去。
card.classList.add('still');
markForm();
showPage(place.page === 'case');
renderCase();
requestAnimationFrame(() => requestAnimationFrame(() => card.classList.remove('still')));

function showError(error) {
  banner.textContent = error instanceof Error ? error.message : String(error);
  banner.hidden = false;
}

function hostState() {
  if (window.__ZEBAR_STATE) return window.__ZEBAR_STATE;
  try {
    return JSON.parse(sessionStorage.getItem('ZEBAR_STATE'));
  } catch {
    return null;
  }
}

async function scan() {
  const zebar = await hostClient;
  const htmlPath = zebar.currentWidget().htmlPath;
  const script = htmlPath.replace(/[^\\/]+$/, 'scan.py');
  const program = navigator.userAgent.includes('Windows') ? 'python' : 'python3';
  const result = await zebar.shellExec(program, [script]);
  if (result.code !== 0) throw new Error(`扫描失败（${result.code}）：${result.stderr}`);
  return JSON.parse(result.stdout);
}

let busy = false;
async function poll() {
  if (busy) return;
  busy = true;
  try {
    // 失败时不动画面：上一轮的内容留着，横幅压在顶上，下一轮成功即消失。
    render(await scan());
    banner.hidden = true;
  } catch (error) {
    showError(error);
  } finally {
    busy = false;
  }
}

const params = new URLSearchParams(location.search);
if (params.get('dev') === '1') {
  document.querySelector('#development').hidden = false;
  // 宿主里调不上系统模糊的平台看不到 60% 那一层，开发预览用这个参数把它模拟出来看。
  if (params.get('blur') === '1') document.documentElement.dataset.blur = 'preview';
  document.querySelector('#preview').addEventListener('change', async (event) => {
    try {
      for (const file of event.target.files) render(JSON.parse(await file.text()));
      banner.hidden = true;
    } catch (error) { showError(error); }
  });
} else if (!hostState()) {
  showError(new Error('未识别到 Zebar 宿主。请从 Zebar 打开此组件。开发调样式请显式使用 ?dev=1。'));
} else {
  const windowError = error => {
    const message = document.querySelector('#window-error');
    message.textContent = String(error);
    message.hidden = false;
  };
  Promise.all([hostClient, import('./window.js')])
    .then(([zebar, { setupWindow }]) => setupWindow(zebar, windowError))
    .catch(error => windowError(`窗口控件初始化失败：${error}`));
  setInterval(poll, 5000);
  poll();
}
