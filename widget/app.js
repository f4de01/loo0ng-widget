const heading = document.querySelector('#heading');
const rows = document.querySelector('#rows');
const unreadable = document.querySelector('#unreadable');
const guide = document.querySelector('#settings-error');
const banner = document.querySelector('#scan-error');
// 圆圈与分段进度条共用一套编码，这里只把扫描脚本给的状态换成类名，不判定、不计数。
const SHAPE = {'未生成': 's-unstarted', '已生成': 's-generated', '已确认': 's-confirmed', '不适用': 's-na'};
const SEGMENTS = ['已确认', '已生成', '未生成', '不适用'];
document.body.classList.add(/Mac|iPhone|iPad/.test(navigator.userAgent) ? 'mac' : 'win');
// Start local module loading before the first interaction, shared with polling.
const hostClient = hostState() ? import('./vendor/zebar-3.3.1.js') : null;
if (hostClient) hostClient.catch(showError);

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

function circle(node) {
  const dot = textElement('i', '', 'dot');
  if (SHAPE[node.状态]) dot.classList.add(SHAPE[node.状态]);
  if (node.高亮 === '未清') dot.classList.add('attention');
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
    const name = document.createElement('div');
    name.className = 'name';
    name.append(textElement('h2', row.目录名),
      textElement('span', `${row.进度.已确认} / ${row.进度.总数}`, 'count'));
    const now = document.createElement('div');
    now.className = 'now';
    if (row.当前节点) {
      now.append(circle(row.当前节点),
        textElement('span', `${row.当前模块 ?? '—'} › ${row.当前节点.标题}`));
    } else {
      now.append(textElement('span', '—'));
    }
    article.append(name, segmentedBar(row.进度), now);
    rows.append(article);
  }
  unreadable.replaceChildren();
  for (const failure of data.读不出) {
    const line = textElement('div', '', 'unreadable');
    line.append(textElement('b', failure.目录名), document.createTextNode(`：${failure.原因}`));
    unreadable.append(line);
  }
}

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
