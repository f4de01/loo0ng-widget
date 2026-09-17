// 读取：把「一次扫描」这件事从页面里隔开，两个实现。
//
// 宿主里：调 Zebar 的 shellExec 起 扫描.py，拿它打到 stdout 的那一坨 JSON。
// 浏览器里：读同目录下 扫描结果.json（由 原型/造喂料.py 现生），这样没装宿主也能
//           开着页面改聚合与渲染。这一半是原型的脚手架，不进实现。

const ZEBAR = 'https://esm.sh/zebar@3.3.1';
const 反斜杠 = String.fromCharCode(92);

export function 在宿主里() {
  // Zebar 把组件的状态注到 window.__ZEBAR_STATE，拿不到就退到 sessionStorage；
  // 它自己的 currentWidget() 就是按这两处找的，所以这里照同一条认。
  if (typeof window === 'undefined') return false;
  try {
    return Boolean(window.__ZEBAR_STATE || sessionStorage.getItem('ZEBAR_STATE'));
  } catch (_) {
    return Boolean(window.__ZEBAR_STATE);
  }
}

function 解释器() {
  const ua = navigator.userAgent || '';
  return ua.includes('Windows') ? 'python' : 'python3';
}

function 目录(路径) {
  const i = Math.max(路径.lastIndexOf(反斜杠), 路径.lastIndexOf('/'));
  return i < 0 ? '.' : 路径.slice(0, i);
}

async function 经由宿主() {
  const zebar = await import(ZEBAR);
  const html路径 = zebar.currentWidget().htmlPath;
  const 包目录 = 目录(html路径);
  const 分隔符 = html路径.includes(反斜杠) ? 反斜杠 : '/';
  const 脚本 = 包目录 + 分隔符 + 'scan.py';

  const 卡id = (zebar.currentWidget().id || '?').slice(0, 8);
  const 起 = performance.now();
  const 出 = await zebar.shellExec(解释器(), [脚本, '--标', 卡id]);
  const 耗时 = Math.round(performance.now() - 起);

  if (出.code !== 0) {
    throw new Error('scan.py 退出码 ' + 出.code + '：' + (出.stderr || '').slice(0, 400));
  }
  return Object.assign(JSON.parse(出.stdout), { 耗时, 来源: '宿主', 脚本 });
}

/** 原型期的排障口：页面在宿主里报了错，借 扫描.py 把它写进日志，人才看得见。 */
export async function 报错(消息) {
  if (!在宿主里()) return;
  try {
    const zebar = await import(ZEBAR);
    const html路径 = zebar.currentWidget().htmlPath;
    const 分隔符 = html路径.includes(反斜杠) ? 反斜杠 : '/';
    const 脚本 = 目录(html路径) + 分隔符 + 'scan.py';
    await zebar.shellExec(解释器(), [脚本, '--记', String(消息).slice(0, 500)]);
  } catch (_) {
    // 排障口自己坏了就算了，不要盖住原来的错。
  }
}

async function 经由桩() {
  const 起 = performance.now();
  const r = await fetch('./stub.json', { cache: 'no-store' });
  if (!r.ok) {
    throw new Error('没有 stub.json：先跑 原型/造喂料.py');
  }
  const d = await r.json();
  return Object.assign(d, { 耗时: Math.round(performance.now() - 起), 来源: '桩' });
}

export async function 扫一次() {
  return 在宿主里() ? 经由宿主() : 经由桩();
}
