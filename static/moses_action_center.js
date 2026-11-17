/* Moses action center for the existing workspace assistant (not a second chat).
   Every card is sourced from the authenticated, read-only server endpoint. */
(() => {
  'use strict';
  const q = (selector, root = document) => root.querySelector(selector);
  const text = (tag, content, className = '') => {
    const node = document.createElement(tag);
    node.textContent = String(content == null ? '' : content);
    if (className) node.className = className;
    return node;
  };
  const request = async (url) => {
    const response = await fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(String(body.detail || `HTTP ${response.status}`));
    return body;
  };
  let lastWorkspace = '';
  let count = 0;
  function install() {
    const panel = document.getElementById('workspaceMosesPanel');
    if (!panel || q('#mosesActionCenterBtn', panel)) return;
    const header = panel.firstElementChild;
    if (!header) return;
    const button = text('button', 'Action Center', 'btn');
    button.type = 'button';
    button.id = 'mosesActionCenterBtn';
    button.setAttribute('aria-label', 'Moses outstanding actions from saved workspace records');
    const area = document.createElement('section');
    area.id = 'mosesActionCenterArea';
    area.hidden = true;
    area.style.cssText = 'display:grid;gap:10px;padding:12px 0;margin:12px 0;border-top:1px solid #e1e5e9';
    const status = text('small', 'Select Action Center to check verified saved work.');
    status.setAttribute('role', 'status');
    area.append(status);
    const refresh = text('button', 'Refresh saved priorities', 'btn');
    refresh.type = 'button';
    const contents = document.createElement('div');
    contents.style.cssText = 'display:grid;gap:10px';
    area.append(refresh, contents);
    const renderCards = (source, title, actionType) => {
      const section = document.createElement('section');
      section.style.cssText = 'border:1px solid #e1e5e9;border-radius:10px;padding:10px;display:grid;gap:8px';
      const available = source && source.available === true;
      const total = available ? source.count : null;
      const name = text('strong', title + ' · ' + (total == null ? 'Unavailable' : total));
      section.append(name);
      if (!available) {
        section.append(text('small', String(source?.note || 'Saved source unavailable; not counted as zero.')));
      } else if (!total) {
        section.append(text('small', 'Nothing recorded in this queue.'));
      }
      for (const item of (Array.isArray(source?.items) ? source.items : []).slice(0, 12)) {
        const card = document.createElement('article');
        card.style.cssText = 'display:grid;gap:5px;border-top:1px solid #eef1f5;padding-top:8px';
        card.append(text('strong', item.title || item.kind || 'Saved action'));
        card.append(text('small', [item.customer, item.job_number && `Job #${item.job_number}`,
          item.status || item.state].filter(Boolean).join(' · ')));
        if (actionType === 'draft' && item.draft_id) {
          const inspect = text('button', 'View verified draft', 'btn');
          inspect.type = 'button';
          inspect.onclick = async () => {
            inspect.disabled = true;
            try {
              const result = await request('/moses-action-center/pds/drafts/' + encodeURIComponent(item.draft_id));
              const detail = text('small', [result.draft?.scope, result.draft?.parts_required,
                result.next_step].filter(Boolean).join('\n\n'));
              detail.style.whiteSpace = 'pre-wrap';
              card.querySelector('[data-moses-draft-detail]')?.remove();
              detail.dataset.mosesDraftDetail = '1';
              card.append(detail);
              const open = document.getElementById('mosesDraftsLaunch');
              if (open && !open.hidden) {
                const go = text('button', 'Open Moses Drafts workspace', 'btn');
                go.type = 'button';
                go.onclick = () => open.click();
                card.append(go);
              }
            } catch (err) {
              card.append(text('small', 'Saved draft cannot be verified: ' + err.message));
            } finally { inspect.disabled = false; }
          };
          card.append(inspect);
        }
        if (actionType === 'work' && item.record_id && (document.body.dataset.platform || '') === 'pds') {
          const inspect = text('button', 'Inspect saved PDS job', 'btn');
          inspect.type = 'button';
          inspect.onclick = async () => {
            inspect.disabled = true;
            try {
              const result = await request('/moses-action-center/pds/jobs/' + encodeURIComponent(item.record_id) + '/context');
              if (result.workspace !== 'pds' || result.job?.id !== item.record_id) throw new Error('Job identity mismatch');
              const summary = text('small', [
                `${result.job.customer || 'Saved job'} · #${result.job.job_number || '—'} · ${result.job.status || '—'}`,
                `Linked documents: ${result.documents.available ? result.documents.count : 'unavailable'}`,
                `Saved Moses drafts: ${result.moses_drafts.available ? result.moses_drafts.count : 'unavailable'}`,
                ...(result.next_steps || [])
              ].join('\n'));
              summary.style.whiteSpace = 'pre-wrap';
              card.querySelector('[data-moses-job-context]')?.remove();
              summary.dataset.mosesJobContext = '1';
              card.append(summary);
            } catch (err) {
              status.textContent = 'Cannot verify PDS job context: ' + err.message;
            } finally { inspect.disabled = false; }
          };
          card.append(inspect);
        }
        if (actionType === 'approval') {
          const open = text('button', 'Review existing approvals', 'btn');
          open.type = 'button';
          open.onclick = () => {
            const prior = Array.from(panel.querySelectorAll('button')).find(b => b.textContent.trim() === 'Review pending Moses actions');
            if (prior) prior.click();
            else status.textContent = 'Approval interface unavailable. No record changed.';
          };
          card.append(open);
        }
        section.append(card);
      }
      contents.append(section);
    };
    const load = async () => {
      const workspace = document.body.dataset.platform || '';
      const sequence = ++count;
      status.textContent = 'Reading saved business records…';
      refresh.disabled = true;
      try {
        const data = await request('/moses-action-center/overview');
        if (sequence !== count || workspace !== (document.body.dataset.platform || '') || data.workspace !== workspace) {
          status.textContent = 'Workspace changed. Refresh to read the active workspace.';
          return;
        }
        lastWorkspace = workspace;
        contents.replaceChildren();
        if (workspace === 'pds') renderCards(data.drafts, 'Moses draft reviews', 'draft');
        renderCards(data.approvals, 'Awaiting your approval', 'approval');
        if (workspace === 'pds') renderCards(data.work, 'PDS job follow-ups', 'work');
        renderCards(data.delivery, 'Verified delivery exceptions', 'delivery');
        status.textContent = 'Verified read-only from ' + workspace.toUpperCase() + ' saved records. No work was executed.';
      } catch (err) {
        contents.replaceChildren();
        status.textContent = 'Could not verify action center: ' + err.message + '. No records were changed.';
      } finally { refresh.disabled = false; }
    };
    refresh.onclick = load;
    button.onclick = async () => {
      area.hidden = !area.hidden;
      area.style.display = area.hidden ? 'none' : 'grid';
      if (!area.hidden) await load();
    };
    header.insertBefore(button, header.lastElementChild);
    header.after(area);
    // Always refresh when reopening after switching business platforms.
    const onClick = (ev) => {
      if (ev.target?.id === 'workspaceMosesBubble' && lastWorkspace !== (document.body.dataset.platform || '')) {
        area.hidden = true; area.style.display = 'none'; contents.replaceChildren();
      }
    };
    document.addEventListener('click', onClick);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
  // The existing app creates the Moses panel lazily after login/workspace render.
  const observer = new MutationObserver(() => {
    if (document.getElementById('workspaceMosesPanel') && !document.getElementById('mosesActionCenterBtn')) install();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
