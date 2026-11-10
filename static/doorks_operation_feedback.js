/* Shared save/upload feedback. No storage changes and no speculative success messages. */
(function () {
  'use strict';
  if (window.__doorksOperationFeedbackInstalled) return;
  window.__doorksOperationFeedbackInstalled = true;
  const originalFetch = window.fetch.bind(window);
  let active = 0;
  let errors = 0;
  let bar, message, spinner, hideTimer;
  function mount() {
    if (bar || !document.body) return;
    bar = document.createElement('div');
    bar.id = 'doorks-operation-feedback';
    bar.setAttribute('role', 'status');
    bar.setAttribute('aria-live', 'polite');
    bar.style.cssText = 'position:fixed;left:50%;bottom:20px;transform:translateX(-50%);z-index:2147483000;background:#203b2c;color:#fff;border-radius:14px;padding:12px 18px;box-shadow:0 8px 30px #0004;display:none;align-items:center;gap:10px;font:600 14px system-ui,sans-serif;max-width:calc(100vw - 28px);pointer-events:none';
    spinner = document.createElement('span');
    spinner.style.cssText = 'width:16px;height:16px;border:2px solid #ffffff66;border-top-color:#fff;border-radius:50%;animation:doorks-operation-spin .8s linear infinite;flex:none';
    message = document.createElement('span');
    bar.append(spinner, message);
    const style = document.createElement('style');
    style.textContent = '@keyframes doorks-operation-spin{to{transform:rotate(360deg)}}';
    document.head.append(style);
    document.body.append(bar);
  }
  function show(label, busy) {
    mount();
    if (!bar) return;
    clearTimeout(hideTimer);
    message.textContent = label;
    spinner.style.display = busy ? 'inline-block' : 'none';
    bar.style.display = 'flex';
    if (!busy) hideTimer = setTimeout(() => { if (active === 0) bar.style.display = 'none'; }, 3500);
  }
  function methodOf(input, init) {
    return String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
  }
  function isUpload(input, init) {
    const body = init && init.body;
    if (typeof FormData !== 'undefined' && body instanceof FormData) {
      for (const value of body.values()) if (typeof File !== 'undefined' && value instanceof File) return true;
    }
    const url = typeof input === 'string' ? input : input && input.url || '';
    return /\/(attachments|upload|files)(\/|\?|$)/i.test(url);
  }
  window.fetch = async function (input, init) {
    const method = methodOf(input, init);
    if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') return originalFetch(input, init);
    const uploading = isUpload(input, init);
    active++;
    show((uploading ? 'Uploading file' : 'Saving changes') + '…' + (active > 1 ? ' (' + active + ' requests)' : ''), true);
    try {
      const response = await originalFetch(input, init);
      if (!response.ok) errors++;
      return response;
    } catch (error) {
      errors++;
      throw error;
    } finally {
      active--;
      if (active > 0) show(active + ' operation' + (active === 1 ? '' : 's') + ' still processing…', true);
      else {
        show(errors ? 'Some changes could not be saved. Check the form for details.' : 'Request completed. Check the form for confirmation.', false);
        errors = 0;
      }
    }
  };
})();
