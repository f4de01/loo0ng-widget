// Window behavior is independent of scanning and only stores window coordinates.
// 材质（ADR-0004）：底是透明窗上自绘的圆角卡片；系统模糊只是可降级的增强，一个平台一行，
// 每行只试一种效果，不按「哪个成功用哪个」去探：`setEffects` 返回成功不等于看得见
// （#13 实测：mica 成功但毫无变化，blur 成功但整窗变深灰黑）。
// Windows：不给行。Acrylic 把整个窗口矩形连同圆角外的四个角磨砂成一块方板，看过截图后裁定不要。
// mac：给 underWindowBackground——它是「窗内容背后那一层」，随系统外观走，配 radius 贴住卡片的
// 圆角；state 取 active，因为这张卡常驻桌面、基本不是活动窗，不能让材质跟着失焦一起淡掉。
// 这一行尚未在 mac 实机上看过：若它同样盖满整个窗口矩形、或压不住浅色卡片，按同一条标准
// 由 mac 交付票删掉这一行（删掉即回到自绘那层，别处不用动）。
const MATERIAL = { mac: { effects: ['underWindowBackground'], state: 'active' } };

// 整卡可拖（#17）：除交互区外，按住卡片哪里都能拖——透明外边距、顶行、空白、进度条、文字都算。
// 交互区是卡片上今天真有的可点元素——窗口按钮连同它那一角（按钮之间那 2px 的缝也不该拖窗）、
// 开发预览的文件选择器——加上页面自己画的行与格：它们没有原生语义，靠 .interactive 这个记号进来
// （清单页的案件行，日后的模块行、节点行、矩阵格）。行若做成原生 button 就不必再标。
const INTERACTIVE = 'button, input, label, .win-controls, .interactive';
// 按下后位移不到这么多 CSS 像素就当点击：窗一格都不动，click 照常落到按下的那个元素上。
const THRESHOLD = 4;

async function applyMaterial(win) {
  const wanted = MATERIAL[document.body.classList.contains('mac') ? 'mac' : 'win'];
  if (!wanted) return;
  try {
    // 系统材质自己的圆角跟着卡片走，不然磨砂会从卡片的圆角外冒出来。
    const radius = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--radius'));
    await win.setEffects(Number.isFinite(radius) ? { ...wanted, radius } : wanted);
    // 调上了才把底色降到 60%，让桌面的模糊透出来。
    document.documentElement.dataset.blur = '1';
  } catch {
    // 失败一言不发：停在自绘的那一层。
  }
}

export async function setupWindow(zebar, reportError) {
  const { PhysicalPosition } = await import('./vendor/tauri-apps_api2.0.2_es2022_dpi.js');
  const widget = zebar.currentWidget();
  const win = widget.tauriWindow;
  applyMaterial(win);
  // 把手不再是某一个元素，而是整张卡片减去交互区：指针事件听在 window 上（透明外边距也在里面），
  // 指针捕获落在 <html> 上——它不像案件行那样每五秒被重绘换掉。
  const root = document.documentElement;
  const minimize = document.querySelector('#minimize');
  const close = document.querySelector('#close');
  const key = 'loo0ng.window-position';
  let position = await win.outerPosition();
  // 按下了、还没过阈值是 press，窗不动；过了阈值才转成 drag。
  let press = null;
  let drag = null;
  let target = null;
  let frame = 0;
  let moving = null;

  function remember() {
    try { localStorage.setItem(key, JSON.stringify({ x: position.x, y: position.y })); }
    catch { /* Storage may be unavailable; dragging still works. */ }
  }

  let saved;
  try { saved = JSON.parse(localStorage.getItem(key)); }
  catch { /* Missing or invalid storage leaves the preset placement intact. */ }
  if (saved && Number.isSafeInteger(saved.x) && Number.isSafeInteger(saved.y)) {
    try {
      await win.setPosition(new PhysicalPosition(saved.x, saved.y));
      position = await win.outerPosition();
    } catch (error) { reportError(`恢复窗口位置失败：${error}`); }
  }

  // Keep the synchronous drag origin current after system moves or display changes.
  await win.onMoved(({ payload }) => {
    if (!drag && !moving && !target) {
      position = payload;
    }
  });

  function schedule() {
    if (!frame && !moving) frame = requestAnimationFrame(flush);
  }

  async function flush() {
    frame = 0;
    if (!target || moving) return;
    const next = target;
    target = null;
    moving = win.setPosition(new PhysicalPosition(next.x, next.y))
      .then(() => { position = next; remember(); })
      .catch(error => reportError(`移动窗口失败：${error}`));
    await moving;
    moving = null;
    if (target) schedule();
  }

  function update(event) {
    if (!drag || event.pointerId !== drag.pointerId) return;
    target = {
      x: Math.round(drag.x + (event.screenX - drag.screenX) * drag.scale),
      y: Math.round(drag.y + (event.screenY - drag.screenY) * drag.scale),
    };
    schedule();
  }

  function owns(event) {
    const active = drag ?? press;
    return Boolean(active) && event.pointerId === active.pointerId;
  }

  // 过阈值才真开始拖：捕获指针（拖快了甩出窗外也不丢事件），窗口原点取此刻的位置，
  // 位移仍从按下那一点算起——阈值那几像素不丢，拖起来还是 1:1 跟手。
  function begin() {
    drag = { pointerId: press.pointerId, screenX: press.screenX, screenY: press.screenY,
      x: position.x, y: position.y, scale: window.devicePixelRatio || 1 };
    press = null;
    // 捕获要不到就算了：窗跟着指针 1:1 走，指针本来也甩不出这扇窗。
    try { root.setPointerCapture(drag.pointerId); } catch { /* 停在没有捕获的那一档。 */ }
    root.classList.add('dragging');
  }

  // 一个收尾管两件事：没过阈值的那一按就此作废，真拖着的就此结束。失焦、指针取消都走这里。
  function finish() {
    press = null;
    if (!drag) return;
    const pointerId = drag.pointerId;
    drag = null;
    root.classList.remove('dragging');
    if (root.hasPointerCapture(pointerId)) root.releasePointerCapture(pointerId);
  }

  // pointerdown is the captured counterpart of mousedown: no import or await here.
  // 按下只记一笔，窗不动；也不调 preventDefault——它会连带吃掉后面的 click，而按下的地方本来就该点得着。
  window.addEventListener('pointerdown', event => {
    if (event.button !== 0 || event.target.closest(INTERACTIVE) || moving || target) return;
    press = { pointerId: event.pointerId, screenX: event.screenX, screenY: event.screenY };
  });
  window.addEventListener('pointermove', event => {
    if (!owns(event)) return;
    // 按键在窗外松开：pointerup 不回来，下一次移动就地结束这一按。
    if (!(event.buttons & 1)) { finish(); return; }
    if (press && (Math.abs(event.screenX - press.screenX) >= THRESHOLD
      || Math.abs(event.screenY - press.screenY) >= THRESHOLD)) begin();
    update(event);
  });
  window.addEventListener('pointerup', event => {
    if (!owns(event)) return;
    update(event);
    finish();
  });
  window.addEventListener('pointercancel', event => { if (owns(event)) finish(); });
  window.addEventListener('lostpointercapture', event => { if (owns(event)) finish(); });
  window.addEventListener('blur', finish);

  async function settle() {
    finish();
    if (moving) await moving;
    if (frame) { cancelAnimationFrame(frame); frame = 0; }
    if (target) await flush();
  }

  minimize.addEventListener('click', async () => {
    try { await settle(); await win.minimize(); }
    catch (error) { reportError(`最小化失败：${error}`); }
  });
  close.addEventListener('click', async () => {
    try { await settle(); await widget.close(); }
    catch (error) { reportError(`关闭失败：${error}`); }
  });
  minimize.disabled = false;
  close.disabled = false;
}
