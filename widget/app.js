const rows = document.querySelector('#rows');
const unreadable = document.querySelector('#unreadable');
const errorBox = document.querySelector('#error');
const status = document.querySelector('#status');
const refresh = document.querySelector('#refresh');
// 圆圈与分段进度条共用一套编码，这里只把扫描脚本给的状态换成类名，不判定、不计数。
const SHAPE = {'未生成': 'none', '已生成': 'made', '已确认': 'confirmed', '不适用': 'skip'};
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

// 四段的宽度比就是四个计数之比：交给 flex-grow，页面不算比例。
function segmentedBar(progress) {
  const bar = document.createElement('div');
  bar.className = 'bar';
  bar.setAttribute('aria-hidden', 'true');
  for (const state of SEGMENTS) {
    const segment = textElement('span', '', `segment segment-${SHAPE[state]}`);
    segment.style.flexGrow = String(progress[state]);
    bar.append(segment);
  }
  return bar;
}

function circle(node) {
  const dot = textElement('span', '', 'circle');
  if (SHAPE[node.状态]) dot.classList.add(`circle-${SHAPE[node.状态]}`);
  if (node.高亮 === '未清') dot.classList.add('circle-alert');
  dot.setAttribute('aria-hidden', 'true');
  return dot;
}

function render(data) {
  const settingsError = document.querySelector('#settings-error');
  settingsError.textContent = data.设置错误?.原因 ?? '';
  settingsError.hidden = !data.设置错误;
  document.querySelector('#count').textContent = data.案件数;
  document.querySelector('#scanned').textContent = data.扫描时间;
  rows.replaceChildren();
  for (const row of data.行) {
    const article = document.createElement('article');
    article.className = 'case';
    const heading = document.createElement('div');
    heading.className = 'case-heading';
    heading.append(textElement('h2', row.目录名),
      textElement('span', `${row.进度.已确认} / ${row.进度.总数}`, 'progress'));
    const current = document.createElement('p');
    current.className = 'current';
    if (row.当前节点) {
      current.append(circle(row.当前节点),
        textElement('span', `${row.当前模块 ?? '—'} › ${row.当前节点.标题}`, 'current-text'));
    } else {
      current.append(textElement('span', '—', 'current-text'));
    }
    article.append(heading, segmentedBar(row.进度), current);
    rows.append(article);
  }
  unreadable.replaceChildren();
  for (const failure of data.读不出) {
    unreadable.append(textElement('p', `${failure.目录名}：${failure.原因}`, 'unreadable'));
  }
}

function showError(error) {
  errorBox.textContent = error instanceof Error ? error.message : String(error);
  errorBox.hidden = false;
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
  refresh.disabled = true;
  status.textContent = '扫描中…';
  try {
    render(await scan());
    errorBox.hidden = true;
    status.textContent = '每 5 秒更新';
  } catch (error) {
    showError(error);
    status.textContent = '本轮失败，5 秒后重试';
  } finally {
    busy = false;
    refresh.disabled = false;
  }
}

if (new URLSearchParams(location.search).get('dev') === '1') {
  status.textContent = '开发预览，不轮询';
  refresh.disabled = true;
  document.querySelector('#development').hidden = false;
  document.querySelector('#preview').addEventListener('change', async (event) => {
    try {
      for (const file of event.target.files) render(JSON.parse(await file.text()));
      errorBox.hidden = true;
    } catch (error) { showError(error); }
  });
} else if (!hostState()) {
  showError(new Error('未识别到 Zebar 宿主。请从 Zebar 打开此组件。开发调样式请显式使用 ?dev=1。'));
  status.textContent = '未连接宿主';
  refresh.disabled = true;
} else {
  const windowError = error => {
    const message = document.querySelector('#window-error');
    message.textContent = String(error);
    message.hidden = false;
  };
  Promise.all([hostClient, import('./window.js')])
    .then(([zebar, { setupWindow }]) => setupWindow(zebar, windowError))
    .catch(error => windowError(`窗口控件初始化失败：${error}`));
  refresh.addEventListener('click', poll);
  setInterval(poll, 5000);
  poll();
}
