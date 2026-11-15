(() => {
  'use strict';
  // The fragment is not sent to the server when loading this page.
  const token = decodeURIComponent(location.hash.slice(1));
  history.replaceState(null, '', location.pathname);
  const byId = id => document.getElementById(id);
  const status = byId('status');
  const form = byId('accept-form');
  const button = byId('accept-button');
  const base = '/doorks-assistant/public/estimates/accept/';
  const pdfButton = byId('download-pdf');
  const valid = /^[A-Za-z0-9_-]{30,100}$/.test(token);
  const message = (text) => { status.textContent = text; };
  async function responseJson(response) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(
      response.status === 410 ? 'This link has expired, been revoked, or already been used. Please request a new link.' :
      response.status === 409 ? 'The estimate has changed. Please request a new link.' :
      response.status === 404 ? 'This acceptance link is unavailable.' :
      'We could not complete this request. Please contact the company.'
    );
    return data;
  }
  async function init() {
    if (!valid) { message('This acceptance link is missing or invalid. Please request a new one.'); return; }
    try {
      const response = await fetch(base + encodeURIComponent(token), {cache:'no-store', credentials:'omit'});
      const data = await responseJson(response);
      byId('business').textContent = data.business || '';
      byId('number').textContent = data.document_number || '—';
      const total = Number(data.total);
      byId('amount').textContent = Number.isFinite(total) ? new Intl.NumberFormat('en-US', {style:'currency',currency:'USD'}).format(total) : '—';
      byId('expiry').textContent = data.expires_at ? new Date(data.expires_at).toLocaleString() : '—';
      pdfButton.hidden = false;
      message('Download and review the full estimate before accepting.');
    } catch (err) { message(err.message); }
  }
  pdfButton.addEventListener('click', async () => {
    pdfButton.disabled = true;
    try {
      const response = await fetch('/doorks-assistant/public/estimates/document.pdf', {
        method:'POST', credentials:'omit', cache:'no-store',
        headers:{'Content-Type':'application/json'}, body:JSON.stringify({token})
      });
      if (!response.ok) { await responseJson(response); return; }
      const blob = await response.blob();
      if (blob.type !== 'application/pdf') throw new Error('Estimate document unavailable.');
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = 'estimate.pdf';
      document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      form.hidden = false;
      message('Please review the downloaded estimate before accepting.');
    } catch (err) { message(err.message); }
    finally { pdfButton.disabled = false; }
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity() || !byId('consent').checked) return;
    button.disabled = true;
    message('Recording your acceptance…');
    try {
      const response = await fetch(base + encodeURIComponent(token), {
        method:'POST', headers:{'Content-Type':'application/json'}, credentials:'omit', cache:'no-store',
        body:JSON.stringify({signer_name:byId('signer').value.trim()})
      });
      const result = await responseJson(response);
      form.hidden = true;
      message('Accepted. Estimate ' + result.document_number + ' was recorded successfully.');
    } catch (err) {
      message(err.message + ' If you are unsure whether the response was recorded, please contact the company.');
      button.disabled = false;
    }
  });
  init();
})();
