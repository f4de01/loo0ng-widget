// Window behavior is independent of scanning and only stores window coordinates.
// 材质（ADR-0004）：底是透明窗上自绘的圆角卡片；系统模糊只是可降级的增强，
// 只在它能贴着这张卡片的形状、而且有人在那个平台上真看见过的时候，才往这张表里写一行——
// `setEffects` 返回成功不等于看得见（#13：mica 成功但毫无变化，blur 成功但整窗变深灰黑）。
// Windows：Acrylic 把整个窗口矩形连同圆角外的四个角磨砂成一块方板，看过截图后裁定不要。
// mac：挑哪一种材质、贴不贴得住圆角，归 mac 交付票在实机上看，看过再加一行。
// 表里没有这个平台就一次都不调，卡片停在自绘那层：不报错、不留痕。
const MATERIAL = {};

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
  // 顶行是这一版的拖动把手；整卡可拖归 #17。
  const handle = document.querySelector('#top');
  const minimize = document.querySelector('#minimize');
  const close = document.querySelector('#close');
  const key = 'loo0ng.window-position';
  let position = await win.outerPosition();
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

  function finish() {
    if (!drag) return;
    const pointerId = drag.pointerId;
    drag = null;
    handle.classList.remove('dragging');
    if (handle.hasPointerCapture(pointerId)) handle.releasePointerCapture(pointerId);
  }

  // pointerdown is the captured counterpart of mousedown: no import or await here.
  handle.addEventListener('pointerdown', event => {
    if (event.button !== 0 || event.target.closest('.win-controls') || moving || target) return;
    event.preventDefault();
    handle.setPointerCapture(event.pointerId);
    drag = { pointerId: event.pointerId, screenX: event.screenX, screenY: event.screenY,
      x: position.x, y: position.y, scale: window.devicePixelRatio || 1 };
    handle.classList.add('dragging');
  });
  handle.addEventListener('pointermove', event => {
    if (!(event.buttons & 1)) { finish(); return; }
    update(event);
  });
  handle.addEventListener('pointerup', event => { update(event); finish(); });
  handle.addEventListener('pointercancel', finish);
  handle.addEventListener('lostpointercapture', finish);
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
  handle.classList.add('draggable');
}
