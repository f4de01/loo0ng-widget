// Window behavior is independent of scanning and only stores window coordinates.
export async function setupWindow(zebar, reportError) {
  const { PhysicalPosition } = await import('./vendor/tauri-apps_api2.0.2_es2022_dpi.js');
  const widget = zebar.currentWidget();
  const win = widget.tauriWindow;
  const header = document.querySelector('header');
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
    header.classList.remove('dragging');
    if (header.hasPointerCapture(pointerId)) header.releasePointerCapture(pointerId);
  }

  // pointerdown is the captured counterpart of mousedown: no import or await here.
  header.addEventListener('pointerdown', event => {
    if (event.button !== 0 || event.target.closest('.window-controls') || moving || target) return;
    event.preventDefault();
    header.setPointerCapture(event.pointerId);
    drag = { pointerId: event.pointerId, screenX: event.screenX, screenY: event.screenY,
      x: position.x, y: position.y, scale: window.devicePixelRatio || 1 };
    header.classList.add('dragging');
  });
  header.addEventListener('pointermove', event => {
    if (!(event.buttons & 1)) { finish(); return; }
    update(event);
  });
  header.addEventListener('pointerup', event => { update(event); finish(); });
  header.addEventListener('pointercancel', finish);
  header.addEventListener('lostpointercapture', finish);
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
  header.classList.add('draggable');
}
