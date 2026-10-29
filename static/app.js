(() => {
  const el = (id) => document.getElementById(id);
 
  const usernameInput = el("usernameInput");
  const passwordInput = el("passwordInput");
  const pinInput = el("pinInput");
  const pinStepWrap = el("pinStepWrap");
  const loginBtn = el("loginBtn");
  const pinBtn = el("pinBtn");
  const logoutBtn = el("logoutBtn");
  const loginStatus = el("loginStatus");
  const activeModeChip = el("activeModeChip");
  const headerCalendarBtn = el("headerCalendarBtn");
 
  const loginToggle = el("loginToggle");
  const loginBody = el("loginBody");
  const loginChev = el("loginChev");
 
  const formsToggle = el("formsToggle");
  const formsBody = el("formsBody");
  const formsChev = el("formsChev");
 
  const navFormsTimeCard = el("navFormsTimeCard");
  let navFormsTimeOff = el("navFormsTimeOff");
  const navTakeoffs = el("navTakeoffs");
  let navFormsSignOff = el("navFormsSignOff");
  let navFormsReceipts = el("navFormsReceipts");
  // Delegated navigation: works for both the static button and a re-created Forms sidebar.
  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest("#navFormsReceipts") : null;
    if (!target) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    try {
      Promise.resolve(renderReceiptsView()).catch(error => {
        console.error("Receipts failed to render", error);
        if (workspaceBody) workspaceBody.textContent = `Unable to open Receipts: ${error.message || error}`;
        alert(`Unable to open Receipts: ${error.message || error}`);
      });
    } catch (error) {
      console.error("Receipts navigation failed", error);
      alert(`Unable to open Receipts: ${error.message || error}`);
    }
  }, true);


  const navJobFlow = el("navJobFlow");
  let navToDoList = el("navToDoList");
  const navEstimatePage = el("navEstimatePage");
  const navInvoicePage = el("navInvoicePage");
  const navEstimateInvoice = el("navEstimateInvoice");
  const navCustomers = el("navCustomers");
  const navContacts = el("navContacts");
  let navAllJobs = el("navAllJobs");
  let navPartsList = el("navPartsList");
  let navDoorLogs = el("navDoorLogs");
 
  const navDataCenter = el("navDataCenter");
  const navAccounting = el("navAccounting");
  const navPayroll = el("navPayroll");
  const navEmployees = el("navEmployees");
  const navDataUpload = el("navDataUpload");
  let navPricingSettings = el("navPricingSettings");
  let navSaddleback = el("navSaddleback");
 
  const navNotifications = el("navNotifications");
  const navAtlas = el("navAtlas");
  const navMoses = el("navMoses");
 
  const badgeNotifications = el("badgeNotifications");
  const badgeJobFlow = el("badgeJobFlow");
 
  const primaryEstimateNav = navEstimateInvoice || navEstimatePage;
  if (!navFormsTimeOff) {
    const formsNavCol = document.querySelector("#formsBody .navcol");
    if (formsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navFormsTimeOff";
      btn.innerHTML = `<span>Time Off Request</span><small>Submit / Approve</small>`;
      if (navTakeoffs) formsNavCol.insertBefore(btn, navTakeoffs);
      else formsNavCol.appendChild(btn);
      navFormsTimeOff = btn;
    }
  }
 
  // Keep Forms in the requested order, including dynamically created Time Off Request.
  // Moving existing DOM nodes preserves their event handlers and form behavior.
  const formsOrder = document.querySelector("#formsBody .navcol");
  if (formsOrder) {
    for (const id of ["navFormsSignOff", "navFormsTimeCard", "navFormsReceipts", "navFormsTimeOff", "navTakeoffs"]) {
      const button = document.getElementById(id);
      if (button && button.parentElement === formsOrder) formsOrder.appendChild(button);
    }
  }

  if (!navToDoList) {
    const jobsNavCol = navJobFlow && navJobFlow.parentElement;
    if (jobsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navToDoList";
      btn.innerHTML = `<span>To-Do List</span><small>Assigned Quotes</small><span class="badge" id="badgeToDoList" style="display:none;">0</span>`;
      if (navJobFlow && navJobFlow.nextSibling) jobsNavCol.insertBefore(btn, navJobFlow.nextSibling);
      else jobsNavCol.appendChild(btn);
      navToDoList = btn;
    }
  } else if (!navToDoList.querySelector(".badge")) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.id = "badgeToDoList";
    badge.style.display = "none";
    badge.textContent = "0";
    navToDoList.appendChild(badge);
  }

  if (!navAllJobs) {
    const jobsNavCol = navJobFlow && navJobFlow.parentElement;
    if (jobsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navAllJobs";
      btn.innerHTML = `<span>All Jobs</span><small>Current + Legacy</small>`;
      if (navCustomers) jobsNavCol.insertBefore(btn, navCustomers);
      else jobsNavCol.appendChild(btn);
      navAllJobs = btn;
    }
  }
 
  if (!navFormsSignOff) {
    const formsNavCol = document.querySelector("#formsBody .navcol");
    if (formsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navFormsSignOff";
      btn.innerHTML = `<span>Sign Off</span><small>PDF + Signature</small>`;
      if (navFormsTimeCard) formsNavCol.insertBefore(btn, navFormsTimeCard);
      else if (navTakeoffs) formsNavCol.insertBefore(btn, navTakeoffs);
      else formsNavCol.appendChild(btn);
      navFormsSignOff = btn;
    }
  }

  if (!navPartsList) {
    const jobsNavCol = navJobFlow && navJobFlow.parentElement;
    if (jobsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navPartsList";
      btn.innerHTML = `<span>Parts List</span><small>Catalog + Pricing</small>`;
      if (navCustomers) jobsNavCol.insertBefore(btn, navCustomers);
      else jobsNavCol.appendChild(btn);
      navPartsList = btn;
    }
  }



  if (!navDoorLogs) {
    const jobsNavCol = navJobFlow && navJobFlow.parentElement;
    if (jobsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navDoorLogs";
      btn.innerHTML = `<span>Door Records</span><small>Openings / History</small>`;
      if (navPartsList && navPartsList.nextSibling) jobsNavCol.insertBefore(btn, navPartsList.nextSibling);
      else if (navCustomers) jobsNavCol.insertBefore(btn, navCustomers);
      else jobsNavCol.appendChild(btn);
      navDoorLogs = btn;
    }
  }

  if (navDoorLogs) {
    const bits = navDoorLogs.querySelectorAll("span, small");
    if (bits[0]) bits[0].textContent = "Door Records";
    if (bits[1]) bits[1].textContent = "Openings / History";
    const jobsNavCol = navDoorLogs.parentElement;
    if (jobsNavCol && navPartsList && navPartsList.parentElement === jobsNavCol) {
      if (navDoorLogs.previousElementSibling !== navPartsList) jobsNavCol.insertBefore(navDoorLogs, navPartsList.nextSibling);
    } else if (jobsNavCol && navCustomers && navCustomers.parentElement === jobsNavCol) {
      jobsNavCol.insertBefore(navDoorLogs, navCustomers);
    }
  }
  if (navCustomers) {
    const bits = navCustomers.querySelectorAll("span, small");
    if (bits[0]) bits[0].textContent = "Customers";
    if (bits[1]) bits[1].textContent = "Database";
  }
  if (navContacts) navContacts.style.display = "none";
  if (navFormsTimeOff && !navFormsTimeOff.querySelector('.badge')) {
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.id = 'badgeTimeOff';
    badge.style.display = 'none';
    badge.textContent = '0';
    navFormsTimeOff.appendChild(badge);
  }
 
  if (navEstimateInvoice) {
    if (navEstimatePage) navEstimatePage.style.display = "none";
    if (navInvoicePage) navInvoicePage.style.display = "none";
  } else if (navEstimatePage) {
    const pieces = navEstimatePage.querySelectorAll("span, small");
    if (pieces[0]) pieces[0].textContent = "Estimate/Invoice";
    if (pieces[1]) pieces[1].textContent = "Builder";
    if (navInvoicePage) navInvoicePage.style.display = "none";
  }

  const jobsNavCol = (navJobFlow && navJobFlow.parentElement) || (navEstimateInvoice && navEstimateInvoice.parentElement) || (navEstimatePage && navEstimatePage.parentElement);
  if (jobsNavCol) {
    const estimateBtn = navEstimateInvoice || navEstimatePage;
    [navJobFlow, navToDoList, navAllJobs, navDoorLogs, navCustomers, navContacts, estimateBtn, navPartsList].forEach((node) => {
      if (node && node.parentElement === jobsNavCol) jobsNavCol.appendChild(node);
    });
  }
 
  const workspaceTitle = el("workspaceTitle");
  const workspaceActions = el("workspaceActions");
  const workspaceBody = el("workspaceBody");
  const loginPanel = loginToggle ? loginToggle.closest(".panel") : null;
  const formsPanel = formsToggle ? formsToggle.closest(".panel") : null;
  const jobFlowPanel = navJobFlow ? navJobFlow.closest(".panel") : null;
  const officeFlowPanel = navDataCenter ? navDataCenter.closest(".panel") : null;
  const chatPanel = navAtlas ? navAtlas.closest(".panel") : null;
  const notificationsPanel = navNotifications ? navNotifications.closest(".panel") : null;

  if (!navSaddleback && officeFlowPanel) {
    const navcol = officeFlowPanel.querySelector(".navcol");
    if (navcol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navSaddleback";
      btn.style.display = "none";
      btn.innerHTML = `<span>Saddleback Design Co.</span><small>Orders / Taxes</small>`;
      navcol.appendChild(btn);
      navSaddleback = btn;
    }
  }




  let apiKey = "";
  let currentUser = null;
  let pendingPinUser = null;
 
  const STATUSES = ["Sales Lead", "Dispatch", "Quote", "Quote Sent", "Parts on Order", "Complete/Quote", "Complete", "Done"];
  const JOB_STATUS_OPTIONS = ["Dispatch", "Quote", "Parts on Order", "Complete/Quote", "Complete"];
  const STATUS_META = {
    "Sales Lead": { cls: "s-blue", dot: "#2563eb" },
    "Dispatch": { cls: "s-purple", dot: "#7c3aed" },
    "Quote": { cls: "s-red", dot: "#ef4444" },
    "Quote Sent": { cls: "s-pink", dot: "#ec4899" },
    "Parts on Order": { cls: "s-brown", dot: "#8b5e3c" },
    "Complete/Quote": { cls: "s-yellow", dot: "#f59e0b" },
    "Complete": { cls: "s-green", dot: "#22c55e" },
    "Done": { cls: "s-gray", dot: "#9ca3af" },
  };
 
  const DOOR_TYPES = [
    "Automatic Door", "Man Door", "Storefront Door", "Herculite Door",
    "Roll Up", "Glass", "Roll/Swing Gate", "Other"
  ];
 
  const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  let currentView = null;
 
  function setActiveChip(label) { activeModeChip.textContent = label; }
  function setWorkspace(title) { workspaceTitle.textContent = title; }
  function clearWorkspaceActions() { workspaceActions.innerHTML = ""; }
 
  function setNavActive(btn) {
    [
      navFormsTimeCard, navFormsTimeOff, navTakeoffs, navFormsSignOff, navFormsReceipts,
      navJobFlow, navToDoList, navAllJobs, navPartsList, navDoorLogs, navEstimatePage, navInvoicePage, navEstimateInvoice, navCustomers, navContacts,
      navDataCenter, navAccounting, navPayroll, navEmployees, navPricingSettings, navDataUpload, navSaddleback,
      navNotifications, navAtlas, navMoses
    ].filter(Boolean).forEach(b => b.classList.toggle("navbtn-active", b === btn));
  }
 
  async function fetchJSON(url, opts = {}) {
    const headers = opts.headers || {};
    opts.headers = headers;
    opts.credentials = "same-origin";
 
    const res = await fetch(url, opts);
    const txt = await res.text();
    let data = null;
    try { data = JSON.parse(txt); } catch {}
 
    if (!res.ok) {
      const msg = (data && (data.detail || data.error)) ? (data.detail || data.error) : (txt || `HTTP ${res.status}`);
      if (res.status === 401) {
        currentUser = null;
        applyRoleAccess(null);
        updateLoginUi();
        showLoggedOutSplash("Session expired. Please log in again.");
      }
      throw new Error(msg);
    }
    return data;
  }
 

  // Doorks 2.0 Phase 1: PIN-locked, admin-only platform shells.
  // Non-PDS screens intentionally do not invoke PDS data APIs.
  const platformSwitchWrap = el("platformSwitchWrap");
  const platformSelect = el("platformSelect");
  const platformSidebar = document.querySelector("main.layout > aside.sidebar");
  let activePlatform = "pds";
  let switchingPlatform = false;
  const workspaceKinds = {
    doorks: {customers:"Customers",vendors:"Vendors",work_orders:"Work Orders",estimates_invoices:"Estimates / Invoices",customer_inquiries:"Customer Inquiries",vendor_assignments:"Vendor Assignments",expenses:"Expenses",receivables:"Accounts Receivable",inventory:"Inventory"},
    sdc: {customers:"Customers",orders:"Orders & Production",software_leads:"Doorks Software Sales",products:"Products",expenses:"Expenses",receivables:"Accounts Receivable",inventory:"Inventory"}
  };
  const workspaceFields = {
    customers:["name","contact","email","phone","address","customer_type","preferred_visit_type","notes"], vendors:["name","contact","email","phone","service_area","trade","license_number","insurance_expiration","notes"],
    customer_inquiries:["customer","contact","email","phone","address","service_type","preferred_date","preferred_time","visit_type","description","status","work_order_number","notes"],
    vendor_assignments:["vendor","vendor_email","work_order_number","customer","address","scheduled_date","scheduled_time","status","scope","nte","completion_notes","notes"],
    estimates_invoices:["customer","work_order_number","document_type","document_number","date","amount","status","description","notes"],
    software_leads:["company","contact","email","phone","package","setup_assistance","status","notes"],
    work_orders:["customer","contact","phone","email","address","service_type","request_source","vendor","scheduled_date","scheduled_time","description","status","priority","po_number","nte","amount","notes"],
    orders:["customer","item","order_date","status","total","shipping","tax","notes"],
    products:["name","sku","price","description"],
    expenses:["date","vendor","category","amount","notes"],
    receivables:["customer","invoice_number","date","amount","paid","notes"],
    inventory:["supplier","part_number","description","quantity","unit_cost","notes"]
  };
  function safeWorkspaceText(value) { const e=document.createElement("span");e.textContent=String(value??"");return e.innerHTML; }
  // Phase 2D: business-specific dashboard and record editor. Never uses PDS data endpoints.
  async function renderBusinessCollection(platform,kind,openNew=false) {
    if(activePlatform!==platform)return;
    const labels=workspaceKinds[platform], fields=workspaceFields[kind];
    clearWorkspaceActions();setWorkspace(`${platform==='sdc'?'SDC':'Doorks'} — ${labels[kind]}`);
    workspaceBody.innerHTML=`<div style="max-width:1400px;margin:auto;display:grid;gap:16px"><div class="card"><div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center"><div><h2 style="margin:0">${labels[kind]}</h2></div><button class="btn" id="businessBack">← Dashboard</button></div></div><div class="card"><div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap"><h3 style="margin:0">Saved ${labels[kind]}</h3><button class="btn btn-orange" id="businessNew">+ New ${labels[kind].replace(' & Production','')}</button></div><input class="input" id="businessSearch" type="search" placeholder="Search saved records by any field…" style="width:100%;box-sizing:border-box;margin:14px 0 4px"><div id="businessRecords" aria-live="polite">Loading records…</div></div><section class="card" id="businessEditor" hidden><div style="display:flex;align-items:center;justify-content:space-between;gap:12px"><h3 id="businessFormTitle" style="margin:0">New ${labels[kind]}</h3><button class="btn" id="businessClose" type="button">Close</button></div><form id="businessRecordForm" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:14px"></form><p id="businessSaveMessage" role="status" aria-live="polite"></p></section></div>`;
    const form=el('businessRecordForm'),message=el('businessSaveMessage'),editor=el('businessEditor');
    const endpoint=`/workspaces/${platform}/${kind}`;
    const types={email:'email',phone:'tel',amount:'number',paid:'number',total:'number',tax:'number',shipping:'number',price:'number',unit_cost:'number',quantity:'number',date:'date',order_date:'date',scheduled_date:'date',scheduled_time:'time',preferred_date:'date',preferred_time:'time'};
    const statuses=kind==='orders'?['Open','In Production','Shipped','Delivered']:kind==='work_orders'?['New','Scheduled','In Progress','Completed','Cancelled']:kind==='customer_inquiries'?['New','Contacted','Visit Requested','Scheduled','Converted','Closed']:kind==='vendor_assignments'?['Pending','Offered','Accepted','Declined','Scheduled','In Progress','Completed','Cancelled']:null;
    let records=[],editingId=null;
    for(const field of fields){
      const label=document.createElement('label');label.style.cssText='display:grid;gap:5px;font-size:13px;font-weight:700;text-transform:capitalize;color:#374151';label.textContent=field.replaceAll('_',' ');
      let input;
      if(field==='status'&&statuses){input=document.createElement('select');for(const status of statuses){const option=document.createElement('option');option.value=status;option.textContent=status;input.append(option);}}
      else if(['notes','description'].includes(field)){input=document.createElement('textarea');input.rows=2;}
      else{input=document.createElement('input');input.type=types[field]||'text';if(input.type==='number')input.step='any';}
      input.name=field;input.className='input';input.style.cssText='width:100%;box-sizing:border-box;min-height:38px;padding:9px 11px;font-size:14px;border-radius:9px';if(['notes','description','address'].includes(field))label.style.gridColumn='span 2';label.append(input);form.append(label);
    }
    // AI reads only a draft; the user must explicitly save the record.
    if(['orders','work_orders','customers','vendors','customer_inquiries','vendor_assignments','software_leads','estimates_invoices'].includes(kind)){
      const ai=document.createElement('details');ai.style.cssText='grid-column:1/-1;border:1px solid #d9dee7;border-radius:12px;padding:12px 14px;background:#f8fafc';
      const heading=document.createElement('summary');heading.style.cssText='font-weight:700;cursor:pointer';heading.textContent='Read document with AI (optional)';ai.append(heading);const aiInner=document.createElement('div');aiInner.style.cssText='display:grid;gap:10px;margin-top:12px';ai.append(aiInner);
      const hint=document.createElement('p');hint.className='hint';hint.textContent='Review AI suggestions before saving.';aiInner.append(hint);
      const file=document.createElement('input');file.type='file';file.accept='.pdf,.png,.jpg,.jpeg,.webp';file.className='input';aiInner.append(file);
      const pasted=document.createElement('textarea');pasted.rows=3;pasted.className='input';pasted.placeholder='Or paste email / document text…';aiInner.append(pasted);
      const read=document.createElement('button');read.type='button';read.className='btn';read.textContent='Read with AI';aiInner.append(read);
      const result=document.createElement('p');result.className='hint';result.setAttribute('role','status');aiInner.append(result);
      read.onclick=async()=>{if(!file.files?.length&&!pasted.value.trim()){result.textContent='Select a document or paste an email first.';return;}
        read.disabled=true;result.textContent='Reading document…';try{
          const body=new FormData();if(file.files?.length)body.append('file',file.files[0]);body.append('email_text',pasted.value);
          const response=await fetchJSON(`/workspace-ai/${platform}/${kind}/extract`,{method:'POST',body});
          let filled=0;for(const [key,value] of Object.entries(response.fields||{})){const field=form.elements.namedItem(key);if(field&&value&&!String(field.value||'').trim()){field.value=String(value);filled++;}}
          result.textContent=`AI suggested ${filled} fields. Review all values before saving.`;
        }catch(err){result.textContent=`Unable to read: ${err.message||'Unknown error'}`;}finally{read.disabled=false;}
      };
      form.prepend(ai);
    }
    const actions=document.createElement('div');actions.style.cssText='grid-column:1/-1;display:flex;gap:10px;flex-wrap:wrap';
    const submit=document.createElement('button');submit.type='submit';submit.className='btn btn-orange';submit.textContent='Save record';actions.append(submit);
    const cancel=document.createElement('button');cancel.type='button';cancel.className='btn';cancel.textContent='Cancel';actions.append(cancel);form.append(actions);
    const close=()=>{editor.hidden=true;editingId=null;form.reset();message.textContent='';};
    cancel.onclick=close;el('businessClose').onclick=close;
    el('businessBack').onclick=()=>showPlatformShell(platform);
    const open=(item=null)=>{form.reset();message.textContent='';editingId=item?.id||null;for(const f of fields){const input=form.elements.namedItem(f);if(input&&item)input.value=item[f]??'';}el('businessFormTitle').textContent=(item?'Edit ':'New ')+labels[kind];submit.textContent=item?'Update record':'Save record';editor.hidden=false;editor.scrollIntoView({behavior:'smooth',block:'start'});};
    el('businessNew').onclick=()=>open();
    const search=el('businessSearch');
    function draw(){const host=el('businessRecords');host.replaceChildren();const q=search.value.toLowerCase().trim();const filtered=records.filter(item=>!q||Object.values(item).some(v=>String(v??'').toLowerCase().includes(q)));
      const count=document.createElement('p');count.className='hint';count.textContent=`Showing ${filtered.length} of ${records.length} records`;host.append(count);
      if(!filtered.length){const empty=document.createElement('p');empty.className='hint';empty.textContent=q?'No matching records.':'No records saved yet. Select New to create the first one.';host.append(empty);return;}
      for(const item of filtered.slice().reverse()){
        const row=document.createElement('div');row.style.cssText='padding:16px;margin:10px 0;border:1px solid #d9dee7;border-radius:12px;background:#fff';
        const title=document.createElement('strong');title.textContent=(kind==='work_orders'&&item.work_order_number?item.work_order_number+' · ':'')+(item.customer||item.name||item.item||item.description||item.part_number||'Record');row.append(title);
        const details=document.createElement('div');details.style.cssText='white-space:pre-wrap;margin:10px 0;color:#526071;font-size:14px;line-height:1.55';details.textContent=fields.filter(k=>item[k]!==undefined&&item[k]!=='').map(k=>`${k.replaceAll('_',' ')}: ${item[k]}`).join('\n');if(['customers','vendors'].includes(kind)){const summary=document.createElement('p');summary.className='hint';summary.textContent=[item.contact,item.email,item.phone,item.service_area].filter(Boolean).join(' · ');row.append(summary);details.hidden=true;const view=document.createElement('button');view.type='button';view.className='btn';view.textContent='View Details';view.onclick=()=>{details.hidden=!details.hidden;view.textContent=details.hidden?'View Details':'Hide Details';};row.append(view);}row.append(details);
        if(kind==='expenses'){
          const status=document.createElement('div');status.className='hint';status.textContent=item.authorization_status==='Authorized'?'Authorized':'Pending Authorization';row.append(status);
          const auth=document.createElement('button');auth.type='button';auth.className='btn';auth.textContent=item.authorization_status==='Authorized'?'Unauthorize':'Authorize';auth.onclick=async()=>{if(!confirm(auth.textContent+' this expense receipt?'))return;try{await fetchJSON(endpoint+'/'+encodeURIComponent(item.id)+'/authorization',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({authorized:item.authorization_status!=='Authorized'})});await refresh();}catch(err){alert(err.message||err);}};row.append(auth);
        }
        const edit=document.createElement('button');edit.className='btn';edit.textContent='Edit';edit.onclick=()=>open(item);row.append(edit);
        if(platform==='doorks'&&kind==='customer_inquiries'){
          const convert=document.createElement('button');convert.className='btn';convert.style.marginLeft='8px';convert.textContent=item.work_order_number?'View linked WO':'Create Work Order';
          convert.onclick=async()=>{
            if(item.work_order_number){renderBusinessCollection('doorks','work_orders');return;}
            if(!confirm('Create a new work order from this inquiry? A unique WO number will be assigned.'))return;
            convert.disabled=true;
            try{
              const data={customer:item.customer||'',contact:item.contact||'',email:item.email||'',phone:item.phone||'',address:item.address||'',service_type:item.service_type||'',request_source:'Customer Inquiry',scheduled_date:item.preferred_date||'',scheduled_time:item.preferred_time||'',description:item.description||'',status:'New',notes:'Created from customer inquiry '+item.id};
              const created=await fetchJSON('/workspaces/doorks/work_orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data})});
              await fetchJSON(endpoint+'/'+encodeURIComponent(item.id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({data:{status:'Converted',work_order_number:created.item.work_order_number}})});
              await refresh();alert('Created '+created.item.work_order_number+'. Find it under All Work Orders.');
            }catch(err){alert('Work order creation may have partially completed. Check All Work Orders before retrying. '+(err.message||err));}finally{convert.disabled=false;}
          };row.append(convert);
        }
        if(platform==='doorks'&&kind==='work_orders'){
          const assign=document.createElement('button');assign.className='btn';assign.style.marginLeft='8px';assign.textContent='Prepare Vendor Assignment';
          assign.onclick=()=>{
            const draft={work_order_number:item.work_order_number||'',customer:item.customer||'',address:item.address||'',scheduled_date:item.scheduled_date||'',scheduled_time:item.scheduled_time||'',scope:item.description||'',nte:item.nte||'',vendor:item.vendor||'',status:'Pending'};
            renderBusinessCollection('doorks','vendor_assignments',true).then(()=>{const f=el('businessRecordForm');if(f)for(const [key,value] of Object.entries(draft)){const field=f.elements.namedItem(key);if(field)field.value=value;}});
          };row.append(assign);
        }
        if(['customers','vendors'].includes(kind)){
          const inactive=!!item.deactivated_at;
          if(inactive){const status=document.createElement('span');status.className='hint';status.textContent=' · Inactive';title.append(status);}
          const toggle=document.createElement('button');toggle.type='button';toggle.className='btn';toggle.style.marginLeft='8px';toggle.textContent=inactive?'Reactivate':'Deactivate';
          toggle.onclick=async()=>{if(!confirm(`${inactive?'Reactivate':'Deactivate'} this ${kind.slice(0,-1)}?`))return;try{await fetchJSON(`${endpoint}/${encodeURIComponent(item.id)}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({active:inactive})});await refresh();}catch(e){alert(e.message||e);}};row.append(toggle);
          const remove=document.createElement('button');remove.type='button';remove.className='btn';remove.style.marginLeft='8px';remove.textContent='Delete';remove.onclick=async()=>{if(!confirm('Permanently delete this record? Linked records will prevent deletion.'))return;try{await fetchJSON(`${endpoint}/${encodeURIComponent(item.id)}`,{method:'DELETE'});await refresh();}catch(e){alert(e.message||e);}};row.append(remove);
        }
        if(!['customers','vendors','work_orders'].includes(kind)){const remove=document.createElement('button');remove.type='button';remove.className='btn';remove.style.marginLeft='8px';remove.textContent='Delete';remove.onclick=async()=>{if(!confirm('Permanently delete this record?'))return;try{await fetchJSON(endpoint+'/'+encodeURIComponent(item.id),{method:'DELETE'});await refresh();}catch(err){alert('Delete failed: '+(err.message||err));}};row.append(remove);}
        host.append(row);
      }
    }
    search.oninput=draw;
    async function refresh(){const result=await fetchJSON(endpoint);records=Array.isArray(result.items)?result.items:[];draw();}
    form.onsubmit=async e=>{e.preventDefault();message.textContent='Saving…';const data={};for(const field of fields){const input=form.elements.namedItem(field);data[field]=String(input?.value??'').trim();}submit.disabled=true;
      try{await fetchJSON(editingId?`${endpoint}/${encodeURIComponent(editingId)}`:endpoint,{method:editingId?'PATCH':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data})});await refresh();close();}
      catch(err){message.textContent=`Save failed: ${err.message||'Unknown error'}`;console.error('Workspace save failed',err);}
      finally{submit.disabled=false;}
    };
    try{await refresh();if(openNew)open();}catch(err){el('businessRecords').textContent=`Unable to load records: ${err.message||'Unknown error'}`;}
  }
  // Phase 2F: Doorks-only accounting pilot. No PDS accounting endpoints are used.
  async function renderDoorksAccounting(kind='receivables') {
    if(activePlatform!=='doorks')return;
    const names={receivables:'Accounts Receivable',inventory:'Inventory & Intake',receipts:'Receipts',statements:'Statements'};
    const fields={receivables:['customer','invoice_number','invoice_date','due_date','amount','paid','job_number','notes'],inventory:['supplier','po_number','date','part_number','description','quantity_ordered','quantity_shipped','quantity_backordered','quantity_received','notes'],receipts:['vendor','date','amount','category','receipt_number','card_last4','employee','notes'],statements:['document_type','issuer','period_start','period_end','amount','transaction_summary','notes']};
    clearWorkspaceActions();setWorkspace('Doorks — Accounting');
    workspaceBody.innerHTML='<div style="max-width:1400px;margin:auto;display:grid;gap:14px"><div class="card"><div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap"><h2 style="margin:0">Doorks Accounting</h2><button class="btn" id="dacBack">← Dashboard</button></div><p class="hint">Separate Doorks financial records. PDS Accounting is unchanged.</p><div id="dacTabs" style="display:flex;flex-wrap:wrap;gap:8px"></div></div><div class="card"><div style="display:flex;gap:10px;align-items:end;flex-wrap:wrap;margin-bottom:14px"><label style="display:grid;gap:5px;font-weight:700">Reporting period<select class="input" id="dacPeriod"><option value="month">Month</option><option value="all">All time</option><option value="custom">Custom dates</option></select></label><label style="display:grid;gap:5px;font-weight:700">Month<input class="input" id="dacMonth" type="month"></label><label style="display:grid;gap:5px;font-weight:700">From<input class="input" id="dacStart" type="date"></label><label style="display:grid;gap:5px;font-weight:700">Through<input class="input" id="dacEnd" type="date"></label></div><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><button class="btn btn-orange" id="dacNew">+ New</button><button class="btn" id="dacUpload">Upload / Read with AI</button><button class="btn" id="dacExport">Export CSV</button></div><details style="margin:16px 0"><summary style="font-weight:700;cursor:pointer">Dashboard & Reports</summary><div id="dacReport" style="padding:12px 0"></div></details><input class="input" type="search" id="dacSearch" placeholder="Search all saved record fields…" style="width:100%;box-sizing:border-box"><p class="hint" id="dacCount"></p><div id="dacRecords"></div></div><section class="card" id="dacEditor" hidden><h3 id="dacTitle">New record</h3><p class="hint">AI suggestions are a draft. Review all values before saving.</p><form id="dacForm" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px"></form><p id="dacMessage" role="status"></p></section></div>';
    el('dacBack').onclick=()=>showPlatformShell('doorks');
    for(const [id,label] of Object.entries(names)){const b=document.createElement('button');b.className='btn'+(id===kind?' btn-orange':'');b.textContent=label;b.onclick=()=>renderDoorksAccounting(id);el('dacTabs').append(b);}
    const endpoint='/doorks-accounting/'+kind, form=el('dacForm'),editor=el('dacEditor'),message=el('dacMessage');let records=[],editing=null,uploadFile=null;
    const dacPeriodState=window.__doorksAccountingPeriod||(window.__doorksAccountingPeriod={mode:'month',month:new Date().toISOString().slice(0,7),start:'',end:''});
    const periodMode=el('dacPeriod'),periodMonth=el('dacMonth'),periodStart=el('dacStart'),periodEnd=el('dacEnd');
    periodMode.value=dacPeriodState.mode;periodMonth.value=dacPeriodState.month;periodStart.value=dacPeriodState.start;periodEnd.value=dacPeriodState.end;
    function updatePeriodInputs(){const mode=periodMode.value;periodMonth.parentElement.style.display=mode==='month'?'grid':'none';periodStart.parentElement.style.display=mode==='custom'?'grid':'none';periodEnd.parentElement.style.display=mode==='custom'?'grid':'none';}
    function applyPeriod(){if(periodMode.value==='custom'&&!periodStart.value&&!periodEnd.value){const month=periodMonth.value||new Date().toISOString().slice(0,7);periodStart.value=month+'-01';const [year,m]=month.split('-').map(Number);periodEnd.value=year+'-'+String(m).padStart(2,'0')+'-'+String(new Date(year,m,0).getDate()).padStart(2,'0');}dacPeriodState.mode=periodMode.value;dacPeriodState.month=periodMonth.value;dacPeriodState.start=periodStart.value;dacPeriodState.end=periodEnd.value;updatePeriodInputs();draw();}
    for(const input of [periodMode,periodMonth,periodStart,periodEnd])input.addEventListener('change',applyPeriod);updatePeriodInputs();
    function dateForRecord(item){return String(item.date||item.invoice_date||item.period_end||item.period_start||item.created_at||'').slice(0,10);}
    function periodRecords(){return records.filter(item=>{if(dacPeriodState.mode==='all')return true;const date=dateForRecord(item);if(!date)return false;if(dacPeriodState.mode==='month')return date.slice(0,7)===dacPeriodState.month;return (!dacPeriodState.start||date>=dacPeriodState.start)&&(!dacPeriodState.end||date<=dacPeriodState.end);});}
    const numeric=new Set(['amount','paid','quantity_ordered','quantity_shipped','quantity_backordered','quantity_received']);
    for(const field of fields[kind]){const label=document.createElement('label');label.style.cssText='display:grid;gap:5px;font-weight:600';label.textContent=field.replaceAll('_',' ');const input=field==='notes'||field==='transaction_summary'?document.createElement('textarea'):document.createElement('input');input.name=field;input.className='input';input.style.width='100%';input.style.boxSizing='border-box';if(numeric.has(field)){input.type='number';input.step='any';}else if(['date','invoice_date','due_date','period_start','period_end'].includes(field)){input.type='date';}label.append(input);form.append(label);}
    const attachment=document.createElement('div');attachment.style.cssText='grid-column:1/-1;display:grid;gap:8px';attachment.innerHTML='<strong>Original document (optional)</strong><p class="hint">Attach the original when saving. PDF or image, up to 12 MB.</p>';const fileInput=document.createElement('input');fileInput.type='file';fileInput.accept='.pdf,.jpg,.jpeg,.png,.webp';attachment.append(fileInput);form.append(attachment);
    const save=document.createElement('button');save.className='btn btn-orange';save.type='submit';save.textContent='Save record';form.append(save);
    const cancel=document.createElement('button');cancel.type='button';cancel.className='btn';cancel.textContent='Cancel';form.append(cancel);cancel.onclick=()=>{editor.hidden=true;};
    const open=(item=null)=>{form.reset();uploadFile=null;editing=item?.id||null;for(const field of fields[kind]){const input=form.elements.namedItem(field);if(item&&input)input.value=item[field]??'';}el('dacTitle').textContent=item?'Edit '+names[kind]:'New '+names[kind];message.textContent='';editor.hidden=false;editor.scrollIntoView({block:'start',behavior:'smooth'});};
    el('dacNew').onclick=()=>open();
    el('dacUpload').onclick=()=>{open();fileInput.click();};
    fileInput.onchange=async()=>{if(!fileInput.files?.length)return;uploadFile=fileInput.files[0];message.textContent='Reading with AI…';try{const body=new FormData();body.append('file',uploadFile);const response=await fetchJSON(endpoint+'/extract',{method:'POST',body});let count=0;for(const [field,value] of Object.entries(response.fields||{})){const input=form.elements.namedItem(field);if(input&&value!==null&&value!==undefined&&!String(input.value).trim()){input.value=String(value);count++;}}message.textContent='AI suggested '+count+' fields. Verify against the original before saving.';}catch(err){message.textContent='AI read failed: '+(err.message||err)+'. You can enter values manually.';}};
    function draw(){const q=el('dacSearch').value.trim().toLowerCase();const inPeriod=periodRecords();const shown=inPeriod.filter(r=>!q||JSON.stringify(r).toLowerCase().includes(q));el('dacCount').textContent='Showing '+shown.length+' of '+inPeriod.length+' records in period ('+records.length+' total)';const host=el('dacRecords');host.replaceChildren();const approved=inPeriod.filter(r=>r.authorization_status==='Authorized');const total=(kind==='receipts'?approved:inPeriod).reduce((sum,r)=>sum+(Number(r.amount)||0),0);const pending=inPeriod.length-approved.length;const reports=el('dacReport');reports.replaceChildren();const stats=kind==='receipts'?[['Receipts',inPeriod.length],['Authorized',approved.length],['Pending',pending],['Authorized Total','$'+total.toFixed(2)]]:[[names[kind],inPeriod.length],['Recorded Total','$'+total.toFixed(2)]];const tiles=document.createElement('div');tiles.style.cssText='display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px';for(const [label,value] of stats){const tile=document.createElement('div');tile.style.cssText='border:1px solid #d9dee7;border-radius:12px;padding:18px;background:white;min-height:88px';const small=document.createElement('div');small.className='hint';small.textContent=label;const large=document.createElement('strong');large.style.cssText='display:block;font-size:24px;margin-top:12px';large.textContent=String(value);tile.append(small,large);tiles.append(tile);}reports.append(tiles);for(const item of shown){const box=document.createElement('div');box.style.cssText='border:1px solid #d9dee7;border-radius:12px;padding:15px;margin:10px 0';const title=document.createElement('strong');title.textContent=item.customer||item.vendor||item.supplier||item.issuer||item.invoice_number||'Record';box.append(title);const details=document.createElement('p');details.className='hint';details.style.whiteSpace='pre-wrap';details.textContent=fields[kind].filter(k=>item[k]!==undefined&&item[k]!=='').map(k=>k.replaceAll('_',' ')+': '+item[k]).join(' · ');box.append(details);
      if(kind==='receipts'){
        const summary=document.createElement('div');summary.style.cssText='display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:8px 0';
        const amount=document.createElement('strong');amount.style.fontSize='20px';amount.textContent='$'+Number(item.amount||0).toFixed(2);
        const status=document.createElement('span');status.className='hint';status.textContent=item.authorization_status==='Authorized'?'Authorized':'Pending Authorization';summary.append(amount,status);box.insertBefore(summary,details);
        details.style.display='none';const expand=document.createElement('button');expand.type='button';expand.className='btn';expand.textContent='View Details';expand.onclick=()=>{details.style.display=details.style.display==='none'?'block':'none';expand.textContent=details.style.display==='none'?'View Details':'Hide Details';};box.append(expand);
        const auth=document.createElement('button');auth.type='button';auth.className='btn';auth.style.marginLeft='8px';auth.textContent=item.authorization_status==='Authorized'?'Unauthorize':'Authorize';auth.onclick=async()=>{if(!confirm(auth.textContent+' this receipt?'))return;try{await fetchJSON(endpoint+'/'+encodeURIComponent(item.id)+'/authorization',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({authorized:item.authorization_status!=='Authorized'})});await refresh();}catch(err){alert(err.message||err);}};box.append(auth);
      }
      const edit=document.createElement('button');edit.className='btn';edit.textContent='Edit';edit.onclick=()=>open(item);box.append(edit);const remove=document.createElement('button');remove.type='button';remove.className='btn';remove.style.marginLeft='8px';remove.textContent='Delete';remove.onclick=async()=>{if(!confirm('Permanently delete this '+names[kind]+' record? This cannot be undone.'))return;remove.disabled=true;try{await fetchJSON(endpoint+'/'+encodeURIComponent(item.id),{method:'DELETE'});await refresh();}catch(err){alert('Delete failed: '+(err.message||err));remove.disabled=false;}};box.append(remove);if(item.attachment){const link=document.createElement('a');link.href=endpoint+'/'+encodeURIComponent(item.id)+'/file';link.target='_blank';link.rel='noopener';link.textContent='Open original';link.style.marginLeft='12px';box.append(link);}host.append(box);}}
    el('dacSearch').oninput=draw;
    el('dacExport').onclick=()=>{const cols=['id','created_at',...fields[kind]];const esc=v=>'"'+String(v??'').replaceAll('"','""')+'"';const csv=[cols.join(','),...records.map(r=>cols.map(c=>esc(typeof r[c]==='string'&&/^[=+@-]/.test(r[c])?"'"+r[c]:r[c])).join(','))].join('\r\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='doorks_'+kind+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),500);};
    async function refresh(){const response=await fetchJSON(endpoint);records=response.items||[];draw();}
    form.onsubmit=async e=>{e.preventDefault();save.disabled=true;message.textContent='Saving…';try{const data={};for(const field of fields[kind])data[field]=String(form.elements.namedItem(field)?.value??'').trim();const response=await fetchJSON(editing?endpoint+'/'+encodeURIComponent(editing):endpoint,{method:editing?'PATCH':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data})});const id=response.item.id;const original=fileInput.files?.[0]||uploadFile;if(original){const body=new FormData();body.append('file',original);try{await fetchJSON(endpoint+'/'+encodeURIComponent(id)+'/file',{method:'POST',body});}catch(err){message.textContent='Record saved, but original upload failed: '+err.message;await refresh();return;}}await refresh();editor.hidden=true;}catch(err){message.textContent='Save failed: '+(err.message||err);}finally{save.disabled=false;}};
    try{await refresh();}catch(err){el('dacRecords').textContent='Could not load records: '+(err.message||err);}
  }
  function showPlatformShell(platform,initialView='overview') {
    activePlatform=platform;
    if(platformSelect)platformSelect.value=platform;
    const inPds=platform==='pds';
    if(platformSidebar)platformSidebar.style.display=inPds?'':'none';
    document.body.dataset.platform=platform;
    let businessSide=document.getElementById('doorksBusinessSidebar');
    if(!businessSide){businessSide=document.createElement('aside');businessSide.id='doorksBusinessSidebar';businessSide.className='sidebar';platformSidebar?.parentElement?.insertBefore(businessSide,platformSidebar.nextSibling);}
    businessSide.style.display=platform==='pds'?'none':'flex';
    if(platform==='sdc'){businessSide.innerHTML=`<section class="panel"><div class="panel-hd static">SDC Operations</div><div class="panel-bd" id="sdcNav"></div></section>`;const links=[['Dashboard',()=>showPlatformShell('sdc')],['Orders & Production',()=>renderBusinessCollection('sdc','orders')],['Customers',()=>renderBusinessCollection('sdc','customers')],['Products',()=>renderBusinessCollection('sdc','products')],['Doorks Software Sales',()=>renderBusinessCollection('sdc','software_leads')],['Expenses',()=>renderBusinessCollection('sdc','expenses')],['Accounts Receivable',()=>renderBusinessCollection('sdc','receivables')],['Inventory',()=>renderBusinessCollection('sdc','inventory')]];for(const [label,fn] of links){const b=document.createElement('button');b.className='doorks-side-link';b.textContent=label;b.onclick=fn;document.getElementById('sdcNav').append(b);}}
    if(platform==='doorks'){businessSide.innerHTML=`<section class="panel"><div class="panel-hd static">Job Flow</div><div class="panel-bd" id="dbJobNav"></div></section><section class="panel"><div class="panel-hd static">Office Flow</div><div class="panel-bd" id="dbOfficeNav"></div></section><section class="panel"><div class="panel-hd static">Portals & Inquiries</div><div class="panel-bd" id="dbPortalNav"></div></section>`;const add=(host,label,action)=>{const b=document.createElement('button');b.className='doorks-side-link';b.type='button';b.textContent=label;b.onclick=action;document.getElementById(host).append(b);};add('dbJobNav','Dashboard',()=>showPlatformShell('doorks'));add('dbJobNav','+ New Dispatch',()=>renderBusinessCollection('doorks','work_orders',true));add('dbJobNav','All Work Orders',()=>renderBusinessCollection('doorks','work_orders'));add('dbOfficeNav','Customers',()=>renderBusinessCollection('doorks','customers'));add('dbOfficeNav','Vendors',()=>renderBusinessCollection('doorks','vendors'));add('dbOfficeNav','Estimates / Invoices',()=>renderBusinessCollection('doorks','estimates_invoices'));add('dbOfficeNav','Accounting',()=>renderDoorksAccounting());add('dbPortalNav','Customer Inquiries',()=>renderBusinessCollection('doorks','customer_inquiries'));add('dbPortalNav','Vendor Assignments',()=>renderBusinessCollection('doorks','vendor_assignments'));}
    document.querySelector('main.layout')?.classList.toggle('business-platform-layout',false);
    if(headerCalendarBtn)headerCalendarBtn.style.display=inPds&&currentUser&&currentUser.role==='office_admin'?'inline-flex':'none';
    if(inPds)return;
    clearWorkspaceActions();setWorkspace(platform==='sdc'?'SDC — Saddleback Design Co.':'Doorks — Administration');
    const isSdc=platform==='sdc',name=isSdc?'Saddleback Design Co.':'Doorks Service Network';
    const items=Object.entries(workspaceKinds[platform]);
    if(platform==='doorks'){
      workspaceBody.innerHTML=`<div style="max-width:1400px;margin:auto;display:grid;gap:18px">
        <div class="card"><div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap"><div><h2 style="margin:0">Doorks Productivity Dashboard</h2></div><button class="btn btn-orange" id="doorksNewDispatch" type="button">+ New Dispatch</button></div>
        <div id="doorksMetrics" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:18px"></div></div>
        <div class="card" id="doorksCalendarPanel"><h3 style="margin-top:0">Scheduling Calendar</h3><div id="doorksCalendarBody"></div></div>
        </div>`;
      const metrics=el('doorksMetrics');
      const metricDefinitions=[['Active Work Orders','work_orders',a=>a.filter(x=>!['Completed','Cancelled'].includes(x.status)).length],['In-Person Visits','work_orders',a=>a.filter(x=>x.scheduled_date&&!['Cancelled'].includes(x.status)&&!/remote|video|virtual/i.test(x.visit_type||x.service_type||'')).length],['Remote Visits','work_orders',a=>a.filter(x=>x.scheduled_date&&!['Cancelled'].includes(x.status)&&/remote|video|virtual/i.test(x.visit_type||x.service_type||'')).length],['Open Estimates','estimates_invoices',a=>a.filter(x=>/estimate|quote/i.test(x.document_type||'')&&!/approved|rejected|declined|closed|cancelled/i.test(x.status||'')).length],['Open Invoices','estimates_invoices',a=>a.filter(x=>/invoice/i.test(x.document_type||'')&&!/paid|void|cancelled/i.test(x.status||'')).length]];
      for(const [title,kind,calculate] of metricDefinitions){const card=document.createElement('div');card.style.cssText='padding:16px;border:1px solid #d9dee7;border-radius:12px;background:#fff';const label=document.createElement('p');label.className='hint';label.textContent=title;const value=document.createElement('h2');value.textContent='—';value.style.margin='8px 0 0';card.append(label,value);metrics.append(card);fetchJSON('/workspaces/doorks/'+kind).then(r=>{value.textContent=String(calculate(r.items||[]));}).catch(()=>{value.textContent='—';});}
      let calMonth=new Date();calMonth=new Date(calMonth.getFullYear(),calMonth.getMonth(),1);
      const panel=el('doorksCalendarPanel'),body=el('doorksCalendarBody');
      async function drawCalendar(){body.replaceChildren();const heading=document.createElement('div');heading.style.cssText='display:flex;gap:12px;align-items:center;justify-content:center;margin-bottom:14px';const prev=document.createElement('button');prev.className='btn';prev.textContent='←';const next=document.createElement('button');next.className='btn';next.textContent='→';const month=document.createElement('strong');month.textContent=calMonth.toLocaleString(undefined,{month:'long',year:'numeric'});prev.onclick=()=>{calMonth=new Date(calMonth.getFullYear(),calMonth.getMonth()-1,1);drawCalendar();};next.onclick=()=>{calMonth=new Date(calMonth.getFullYear(),calMonth.getMonth()+1,1);drawCalendar();};heading.append(prev,month,next);body.append(heading);const grid=document.createElement('div');grid.style.cssText='display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px';body.append(grid);for(const day of ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']){const label=document.createElement('strong');label.style.cssText='text-align:center;font-size:12px';label.textContent=day;grid.append(label);}let jobs=[];try{jobs=(await fetchJSON('/workspaces/doorks/work_orders')).items||[];}catch{}const offset=calMonth.getDay(),days=new Date(calMonth.getFullYear(),calMonth.getMonth()+1,0).getDate();for(let i=0;i<offset;i++)grid.append(document.createElement('span'));for(let day=1;day<=days;day++){const date=calMonth.getFullYear()+'-'+String(calMonth.getMonth()+1).padStart(2,'0')+'-'+String(day).padStart(2,'0');const matches=jobs.filter(x=>String(x.scheduled_date||'').slice(0,10)===date);const cell=document.createElement('button');cell.type='button';cell.style.cssText='min-height:70px;min-width:0;border:1px solid #d9dee7;border-radius:9px;background:white;padding:6px;text-align:left;cursor:pointer';cell.textContent=String(day);if(matches.length){const info=document.createElement('div');info.style.cssText='font-size:11px;color:#f97316;font-weight:700;overflow-wrap:anywhere';info.textContent=matches.length+' visit'+(matches.length===1?'':'s');cell.append(info);cell.title=matches.map(x=>x.customer||x.description||'Work order').join(' • ');}cell.onclick=()=>renderBusinessCollection('doorks','work_orders');grid.append(cell);}}
      el('doorksNewDispatch').onclick=()=>renderBusinessCollection('doorks','work_orders',true);drawCalendar();
    }else{
      workspaceBody.innerHTML=`<div style="max-width:1400px;margin:auto;display:grid;gap:18px"><div class="card"><h2 style="margin:0 0 6px">${name}</h2><div id="businessDashboardCards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:20px"></div></div><div class="card"><h3>Workspace</h3><div id="businessNav" style="display:flex;flex-wrap:wrap;gap:10px"></div></div></div>`;
    }
    if(platform==='doorks' && el('businessNav')){const b=document.createElement('button');b.className='btn btn-orange';b.textContent='Accounting — Doorks';b.onclick=()=>renderDoorksAccounting();el('businessNav').prepend(b);const c=document.createElement('button');c.style.cssText='text-align:left;border:1px solid #d9dee7;border-radius:12px;padding:18px;background:#fff;cursor:pointer';c.innerHTML='<strong>Accounting</strong><p class="hint">Independent Doorks receivables, inventory, receipts and statements</p>';c.onclick=()=>renderDoorksAccounting();el('businessDashboardCards').prepend(c);}
    const nav=el('businessNav'),cards=el('businessDashboardCards');
    if(!nav||!cards)return;
    for(const [kind,title] of items){
      const btn=document.createElement('button');btn.className='btn';btn.textContent=title;btn.onclick=()=>renderBusinessCollection(platform,kind);nav.append(btn);
      const card=document.createElement('button');card.type='button';card.style.cssText='text-align:left;border:1px solid #d9dee7;border-radius:12px;padding:18px;background:#fff;cursor:pointer';
      const heading=document.createElement('strong');heading.textContent=title;const count=document.createElement('p');count.className='hint';count.textContent='Loading…';card.append(heading,count);card.onclick=()=>renderBusinessCollection(platform,kind);cards.append(card);
      fetchJSON(`/workspaces/${platform}/${kind}`).then(result=>{count.textContent=`${Array.isArray(result.items)?result.items.length:0} saved records`;}).catch(err=>{count.textContent=`Unable to load: ${err.message||'Error'}`;});
    }
  }
  async function initializePlatform() {
    if (!currentUser) {
      if (platformSwitchWrap) platformSwitchWrap.style.display = "none";
      activePlatform = "pds";
      document.body.dataset.platform="pds";
      document.getElementById("doorksBusinessSidebar")?.remove();
      if (platformSidebar) platformSidebar.style.display = "";
      document.querySelector('main.layout')?.classList.remove('business-platform-layout');
      return;
    }
    const admin = currentUser.role === "office_admin";
    if (platformSwitchWrap) platformSwitchWrap.style.display = admin ? "flex" : "none";
    if (!admin) { showPlatformShell("pds"); return; }
    try {
      const state = await fetchJSON("/platforms/current");
      showPlatformShell(state.platform || "pds");
    } catch (err) { console.warn("Platform selection unavailable", err); showPlatformShell("pds"); }
  }
  if (platformSelect) platformSelect.addEventListener("change", async () => {
    if (switchingPlatform || !currentUser || currentUser.role !== "office_admin") return;
    const target = platformSelect.value;
    platformSelect.value = activePlatform;
    if (target === activePlatform) return;
    const pin = target === "pds" ? "" : prompt(`Enter the ${target === "sdc" ? "SDC" : "Doorks"} platform PIN:`);
    if (pin === null) return;
    switchingPlatform = true;
    try {
      await fetchJSON("/platforms/switch", {method:"POST", headers:{"Content-Type":"application/json"},body:JSON.stringify({platform:target,pin})});
      // A full reload clears the old platform's in-memory UI and cached records.
      window.location.reload();
    } catch (err) { alert(err.message || "Unable to switch platforms"); }
    finally { switchingPlatform = false; }
  });

  function togglePanel(bodyEl, chevEl) {
    const isHidden = bodyEl.style.display === "none";
    bodyEl.style.display = isHidden ? "block" : "none";
    chevEl.innerHTML = isHidden ? "&#9662;" : "&#9656;";
  }
 
  if (loginToggle) loginToggle.addEventListener("click", () => togglePanel(loginBody, loginChev));

 
  function yyyyMmDd(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }
 
  function mmDdYy(yyyy_mm_dd) {
    const [y, m, d] = (yyyy_mm_dd || "").split("-");
    if (!y || !m || !d) return yyyy_mm_dd;
    return `${m}-${d}-${y}`;
  }

  function formatDisplayDate(value) {
    if (!value) return "";
    const s = String(value).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return mmDdYy(s);
    if (/^\d{4}-\d{2}$/.test(s)) {
      const [y, m] = s.split("-");
      return `${m}-${y}`;
    }
    return s;
  }

  function formatTime12(value) {
    const s = String(value || "").trim();
    if (!s) return "";
    const m = s.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
    if (!m) return s;
    let h = Number(m[1]);
    const min = m[2];
    const ampm = h >= 12 ? "PM" : "AM";
    h = h % 12;
    if (h === 0) h = 12;
    return `${h}:${min} ${ampm}`;
  }

  function formatTimeRange12(start, end) {
    const a = formatTime12(start);
    const b = formatTime12(end);
    if (a && b) return `${a} - ${b}`;
    return a || b || "";
  }

  function lunchSummary(item) {
    if (!item || !item.lunch_taken) return "Lunch: No";
    const range = formatTimeRange12(item.lunch_start, item.lunch_end);
    return range ? `Lunch: Yes (${range})` : "Lunch: Yes";
  }
 
  function monthLabel(d) {
    return d.toLocaleString(undefined, { month: "long", year: "numeric" });
  }


  const DEFAULT_SALES_TAX_OPTIONS = [
    { city: "No Sales Tax", rate: 0 },
    { city: "Default / San Diego", rate: 7.75 },
    { city: "San Diego", rate: 7.75 },
    { city: "Escondido", rate: 8.75 },
    { city: "Carlsbad", rate: 7.75 },
    { city: "Oceanside", rate: 8.25 },
    { city: "Vista", rate: 8.25 },
    { city: "San Marcos", rate: 7.75 },
    { city: "Encinitas", rate: 7.75 },
    { city: "Poway", rate: 7.75 },
    { city: "El Cajon", rate: 8.25 },
    { city: "La Mesa", rate: 8.50 },
    { city: "Chula Vista", rate: 8.75 },
    { city: "National City", rate: 8.75 },
    { city: "Imperial Beach", rate: 8.75 },
    { city: "Temecula", rate: 8.75 },
    { city: "Murrieta", rate: 8.75 },
    { city: "Riverside", rate: 8.75 },
    { city: "Irvine", rate: 7.75 },
    { city: "Los Angeles", rate: 9.50 },
  ];
  const DEFAULT_BILLING_TERMS = [
    "Due on Receipt",
    "100% Materials Deposit/Remainder Upon Complete",
    "Net 5",
    "Net 10",
    "Net 15",
    "Net 30",
    "Net 60",
    "Net 90",
  ];
  let SALES_TAX_OPTIONS = loadBillingTaxOptions();
  let BILLING_TERMS_OPTIONS = loadBillingTermsOptions();

  function loadBillingTaxOptions() {
    try {
      const saved = JSON.parse(localStorage.getItem("doorks_sales_tax_options") || "null");
      if (Array.isArray(saved) && saved.length) return saved;
    } catch {}
    return DEFAULT_SALES_TAX_OPTIONS.map(x => ({ ...x }));
  }
  function loadBillingTermsOptions() {
    try {
      const saved = JSON.parse(localStorage.getItem("doorks_billing_terms") || "null");
      if (Array.isArray(saved) && saved.length) return saved.map(String).filter(Boolean);
    } catch {}
    return DEFAULT_BILLING_TERMS.slice();
  }
  function saveBillingTaxOptions(items) {
    SALES_TAX_OPTIONS = (items || []).map(x => ({ city: String(x.city || "").trim(), rate: Number(x.rate || 0) })).filter(x => x.city);
    localStorage.setItem("doorks_sales_tax_options", JSON.stringify(SALES_TAX_OPTIONS));
  }
  function saveBillingTermsOptions(items) {
    BILLING_TERMS_OPTIONS = (items || []).map(x => String(x || "").trim()).filter(Boolean);
    localStorage.setItem("doorks_billing_terms", JSON.stringify(BILLING_TERMS_OPTIONS));
  }
  function applyPricingBillingSettings(pricing = {}) {
    if (Array.isArray(pricing.tax_cities) && pricing.tax_cities.length) {
      const incoming = pricing.tax_cities.map(x => ({ city: String(x.city || "").trim(), rate: Number(x.rate || 0) })).filter(x => x.city);
      const legacyCities = ["No Sales Tax", "Default / San Diego", "San Diego", "Escondido"];
      const isLegacySubset = incoming.length === 4 && incoming.every((x, i) => x.city === legacyCities[i]);
      // The original backend seeded only four cities; never let that old default
      // replace the complete preexisting city/rate list from Doorks.
      SALES_TAX_OPTIONS = isLegacySubset ? DEFAULT_SALES_TAX_OPTIONS.map(x => ({ ...x })) : incoming;
    }
    if (Array.isArray(pricing.billing_terms) && pricing.billing_terms.length) {
      BILLING_TERMS_OPTIONS = pricing.billing_terms.map(String).filter(Boolean);
    }
  }
  function inferTaxCityFromAddress(address) {
    const text = String(address || "").toLowerCase();
    return SALES_TAX_OPTIONS.find(opt => opt.city && !/^no sales tax/i.test(opt.city) && text.includes(String(opt.city).toLowerCase().replace(/ \(alt\)$/i, ""))) || null;
  }
 

  function showDoorksToast(message, kind = "success") {
    const toast = document.createElement("div");
    toast.textContent = message;
    toast.style.position = "fixed";
    toast.style.right = "18px";
    toast.style.bottom = "18px";
    toast.style.zIndex = "999999";
    toast.style.padding = "12px 16px";
    toast.style.borderRadius = "12px";
    toast.style.fontWeight = "900";
    toast.style.boxShadow = "0 16px 40px rgba(0,0,0,.18)";
    toast.style.background = kind === "error" ? "#fee2e2" : "#dcfce7";
    toast.style.color = kind === "error" ? "#991b1b" : "#166534";
    toast.style.border = kind === "error" ? "1px solid #fecaca" : "1px solid #bbf7d0";
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2200);
  }

  function statusPill(status) {
    const meta = STATUS_META[status] || STATUS_META["Dispatch"];
    const pill = document.createElement("span");
    pill.className = `pill ${meta.cls || ""}`;
    pill.textContent = status || "Dispatch";
    const styles = {
      "Sales Lead": ["rgba(37,99,235,.10)", "rgba(37,99,235,.28)", "#1d4ed8"],
      "Dispatch": ["rgba(124,58,237,.10)", "rgba(124,58,237,.28)", "#6d28d9"],
      "Quote": ["rgba(239,68,68,.10)", "rgba(239,68,68,.25)", "#b91c1c"],
      "Quote Sent": ["rgba(236,72,153,.18)", "rgba(236,72,153,.34)", "#be185d"],
      "Parts on Order": ["rgba(139,94,60,.14)", "rgba(139,94,60,.34)", "#7c4a21"],
      "Complete/Quote": ["rgba(245,158,11,.12)", "rgba(245,158,11,.30)", "#b45309"],
      "Complete": ["rgba(34,197,94,.12)", "rgba(34,197,94,.30)", "#166534"],
      "Done": ["rgba(17,24,39,.04)", "rgba(17,24,39,.14)", "#4b5563"],
      "Approved": ["rgba(34,197,94,.12)", "rgba(34,197,94,.30)", "#166534"],
      "Denied": ["rgba(239,68,68,.10)", "rgba(239,68,68,.25)", "#b91c1c"],
      "Pending": ["rgba(245,158,11,.12)", "rgba(245,158,11,.30)", "#b45309"],
    };
    const [bg, border, color] = styles[status] || styles["Dispatch"];
    pill.style.background = bg;
    pill.style.border = `1px solid ${border}`;
    pill.style.color = color;
    return pill;
  }
 
  function dotEl(status) {
    const meta = STATUS_META[status] || STATUS_META["Dispatch"];
    const d = document.createElement("span");
    d.className = "dot";
    d.style.background = meta.dot || "#111827";
    return d;
  }
 
  function styleActionButton(btn, tone = "default", compact = false) {
    btn.className = "btn";
    btn.style.fontWeight = "1000";
    btn.style.borderRadius = compact ? "10px" : "12px";
    btn.style.padding = compact ? "7px 10px" : "10px 13px";
    btn.style.fontSize = compact ? "12px" : "14px";
    btn.style.lineHeight = "1.1";
    btn.style.whiteSpace = "nowrap";
    btn.style.borderWidth = "1px";
    btn.style.borderStyle = "solid";
    if (tone === "green") {
      btn.style.background = "rgba(34,197,94,.12)";
      btn.style.borderColor = "rgba(34,197,94,.35)";
      btn.style.color = "#166534";
    } else if (tone === "blue") {
      btn.style.background = "rgba(37,99,235,.10)";
      btn.style.borderColor = "rgba(37,99,235,.28)";
      btn.style.color = "#1d4ed8";
    } else if (tone === "ghost") {
      btn.style.background = "rgba(17,24,39,.04)";
      btn.style.borderColor = "rgba(17,24,39,.12)";
      btn.style.color = "#374151";
    } else if (tone === "danger") {
      btn.style.background = "rgba(239,68,68,.08)";
      btn.style.borderColor = "rgba(239,68,68,.24)";
      btn.style.color = "#b91c1c";
    } else {
      btn.style.background = "#fff";
      btn.style.borderColor = "var(--line)";
      btn.style.color = "var(--text)";
    }
    return btn;
  }
 
  function makeUploadLabel(text, tone = "ghost", compact = false) {
    const label = document.createElement("label");
    label.style.display = "inline-flex";
    label.style.alignItems = "center";
    label.style.justifyContent = "center";
    label.style.cursor = "pointer";
    styleActionButton(label, tone, compact);
    label.textContent = text;
    return label;
  }
 
  function openDrawer(titleText, renderFn) {
    document.querySelectorAll(".overlay").forEach(o => o.remove());
 
    const overlay = document.createElement("div");
    overlay.className = "overlay";
 
    const drawer = document.createElement("div");
    drawer.className = "drawer";
 
    const hd = document.createElement("div");
    hd.className = "drawer-hd";
 
    const title = document.createElement("div");
    title.className = "drawer-title";
    title.textContent = titleText;
 
    const close = document.createElement("button");
    close.className = "drawer-close";
    close.innerHTML = "&times;";
 
    hd.appendChild(title);
    hd.appendChild(close);
 
    const bd = document.createElement("div");
    bd.className = "drawer-bd";
 
    drawer.appendChild(hd);
    drawer.appendChild(bd);
    overlay.appendChild(drawer);
    document.body.appendChild(overlay);
 
    let lastOverlayOutsideClick = 0;
    overlay.addEventListener("click", (e) => {
      if (e.target !== overlay) return;
      const now = Date.now();
      if (now - lastOverlayOutsideClick < 450) overlay.remove();
      lastOverlayOutsideClick = now;
    });
    close.addEventListener("click", () => overlay.remove());
 
    // A rejected async renderer must be visible instead of silently leaving a blank drawer.
    try {
      Promise.resolve(renderFn(bd, overlay)).catch(error => {
        console.error("Doorks drawer render failed:", titleText, error);
        const message = document.createElement("div");
        message.className = "card";
        message.textContent = `Unable to open ${titleText}: ${error.message || error}`;
        bd.appendChild(message);
      });
    } catch (error) {
      console.error("Doorks drawer render failed:", titleText, error);
      const message = document.createElement("div");
      message.className = "card";
      message.textContent = `Unable to open ${titleText}: ${error.message || error}`;
      bd.appendChild(message);
    }
    return overlay;
  }
 
  async function apiListJobs(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/calendar/jobs?${qs.toString()}`);
    return data.jobs || [];
  }

  async function apiPromoteLegacyJob(recordId, dateValue, jobNumber = "") {
    const qs = new URLSearchParams();
    if (dateValue) qs.set("date", dateValue);
    if (String(jobNumber || "").trim()) qs.set("job_number", String(jobNumber || "").trim());
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    const data = await fetchJSON(`/data/legacy/${encodeURIComponent(recordId)}/promote${suffix}`, {
      method: "POST",
    });
    return data.job;
  }

  function openLegacyImportDrawer(job, onDone) {
    openDrawer("Import Legacy Job", async (drawerBody, overlay) => {
      const card = document.createElement("div");
      card.className = "card";
 
      const dateRow = document.createElement("div");
      dateRow.style.marginTop = "0";
      dateRow.innerHTML = `
        <div class="label">Date</div>
        <input class="input" id="cf_date" type="date" />
      `;
      dateRow.querySelector("#cf_date").value = new Date().toISOString().slice(0, 10);
      card.appendChild(dateRow);
      const defaultDate = String(job.date || "").trim() || new Date().toISOString().slice(0, 10);
      const defaultNumber = String(job.job_number || "").trim();
      card.innerHTML = `
        <div class="grid2">
          <div><div class="label">Dispatch Date</div><input class="input" id="legacy_import_date" type="date" value="${escapeHtml(defaultDate)}" /></div>
          <div><div class="label">Job Number</div><input class="input" id="legacy_import_job_number" value="${escapeHtml(defaultNumber)}" placeholder="Leave blank for next available" /></div>
        </div>
        <div class="hint" style="margin-top:10px;">This creates a live dispatch from the legacy job so it appears on the calendar and can be edited like a normal dispatch.</div>
      `;

      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "12px";
      const save = document.createElement("button");
      save.className = "btn btn-orange";
      save.textContent = "Import to Calendar";
      const cancel = document.createElement("button");
      cancel.className = "btn";
      cancel.textContent = "Cancel";
      actions.append(save, cancel);
      card.appendChild(actions);
      drawerBody.appendChild(card);

      const dateInput = card.querySelector("#legacy_import_date");
      const numInput = card.querySelector("#legacy_import_job_number");

      save.addEventListener("click", async () => {
        try {
          const cleanedDate = String(dateInput.value || "").trim() || defaultDate;
          const cleanedNumber = String(numInput.value || "").trim();
          const created = await apiPromoteLegacyJob(job.id, cleanedDate, cleanedNumber);
          overlay.remove();
          if (typeof onDone === "function") await onDone(created);
        } catch (e) {
          alert(e.message || String(e));
        }
      });
      cancel.addEventListener("click", () => overlay.remove());
    });
  }

 
  async function apiListAllJobs(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/data/all-jobs?${qs.toString()}`);
    if (Array.isArray(data)) return data;
    return Array.isArray(data.jobs) ? data.jobs : [];
  }
 
  async function apiGetJob(jobId) {
    const data = await fetchJSON(`/calendar/jobs/${jobId}`);
    return data.job;
  }
 
  function currentAuditUserName() {
    if (!currentUser) return "";
    return String(currentUser.name || currentUser.full_name || currentUser.username || "").trim();
  }

  async function apiCreateJob(payload) {
    const actor = currentAuditUserName();
    const body = { ...(payload || {}) };
    if (actor) {
      body.created_by = actor;
      body.last_modified_by = actor;
    }
    const data = await fetchJSON("/calendar/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return data.job;
  }
 
  async function apiUpdateJob(jobId, payload) {
    const actor = currentAuditUserName();
    const body = { ...(payload || {}) };
    if (actor) body.last_modified_by = actor;
    const data = await fetchJSON(`/calendar/jobs/${jobId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return data.job;
  }
 
  async function apiDeleteJob(jobId) {
    await fetchJSON(`/calendar/jobs/${jobId}`, { method: "DELETE" });
  }
 
  async function apiAddCompletion(jobId, payload) {
    const data = await fetchJSON(`/calendar/jobs/${jobId}/completion`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.form;
  }
 
  async function apiReplaceCompletionForms(jobId, completionForms) {
    const data = await fetchJSON(`/calendar/jobs/${jobId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ completion_forms: completionForms }),
    });
    return data.job;
  }
 
  async function apiUploadJobAttachments(jobId, files) {
    const formData = new FormData();
    Array.from(files || []).forEach(f => formData.append("files", f));
    const res = await fetch(`/calendar/jobs/${jobId}/attachments`, {
      method: "POST",
      credentials: "same-origin",
      body: formData,
    });
    const txt = await res.text();
    let data = null;
    try { data = JSON.parse(txt); } catch {}
    if (!res.ok) {
      const msg = (data && (data.detail || data.error)) ? (data.detail || data.error) : (txt || `HTTP ${res.status}`);
      if (res.status === 401) {
        currentUser = null;
        applyRoleAccess(null);
        updateLoginUi();
        showLoggedOutSplash("Session expired. Please log in again.");
      }
      throw new Error(msg);
    }
    return data.files || [];
  }
 
  async function apiUploadCompletionAttachments(jobId, formId, files) {
    const formData = new FormData();
    Array.from(files || []).forEach(f => formData.append("files", f));
    const res = await fetch(`/calendar/jobs/${jobId}/completion/${formId}/attachments`, {
      method: "POST",
      credentials: "same-origin",
      body: formData,
    });
    const txt = await res.text();
    let data = null;
    try { data = JSON.parse(txt); } catch {}
    if (!res.ok) {
      const msg = (data && (data.detail || data.error)) ? (data.detail || data.error) : (txt || `HTTP ${res.status}`);
      if (res.status === 401) {
        currentUser = null;
        applyRoleAccess(null);
        updateLoginUi();
        showLoggedOutSplash("Session expired. Please log in again.");
      }
      throw new Error(msg);
    }
    return data.files || [];
  }
 
  async function apiListEmployees() {
    const data = await fetchJSON("/employees");
    return data.items || [];
  }
 
  async function apiCreateEmployee(payload) {
    const data = await fetchJSON("/employees", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }
 
  async function apiDeleteEmployee(id) {
    await fetchJSON(`/employees/${id}`, { method: "DELETE" });
  }

  async function apiUpdateEmployee(id, payload) {
    const data = await fetchJSON(`/employees/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    return data.item;
  }

  async function apiListAuthUsers() {
    const data = await fetchJSON("/auth/users");
    return data.items || [];
  }

  async function apiCreateAuthUser(payload) {
    const data = await fetchJSON("/auth/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiUpdateAuthUser(userId, payload) {
    const data = await fetchJSON(`/auth/users/${userId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiSetAuthUserPassword(userId, password) {
    const data = await fetchJSON(`/auth/users/${userId}/password`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    return data.item;
  }

  async function apiSetAuthUserPin(userId, pin) {
    const data = await fetchJSON(`/auth/users/${userId}/pin`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
    return data.item;
  }

  async function apiSetAuthUserActive(userId, active) {
    const data = await fetchJSON(`/auth/users/${userId}/active`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active }),
    });
    return data.item;
  }

  async function apiDeleteAuthUser(userId) {
    await fetchJSON(`/auth/users/${userId}`, { method: "DELETE" });
  }
 
  async function apiListCustomers() {
    const data = await fetchJSON("/crm/customers");
    return data.items || [];
  }
 
  async function apiCreateCustomer(payload) {
    const data = await fetchJSON("/crm/customers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiUpdateCustomer(id, payload) {
    const data = await fetchJSON(`/crm/customers/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiListAddresses(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/addresses?${qs.toString()}`);
    return data.items || [];
  }

  async function apiCreateAddress(payload) {
    const data = await fetchJSON("/addresses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiUpdateAddress(id, payload) {
    const data = await fetchJSON(`/addresses/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiDeleteAddress(id) {
    const data = await fetchJSON(`/addresses/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    return data.ok;
  }
 
  async function apiListContacts(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/crm/contacts?${qs.toString()}`);
    return data.items || [];
  }
 
  async function apiListParts(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/data/parts?${qs.toString()}`);
    return data.items || [];
  }

  async function apiSavePart(payload) {
    const body = {
      id: payload.id || "",
      manufacturer: payload.manufacturer || payload.Manufacturer || "",
      part_number: payload.part_number || payload.item || payload.Item || "",
      description: payload.description || payload.Description || "",
      price: payload.price ?? payload.Price ?? "",
    };
    const url = body.id ? `/data/parts/${encodeURIComponent(body.id)}` : "/data/parts";
    const method = body.id ? "PUT" : "POST";
    const data = await fetchJSON(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return data.item || data;
  }

  async function apiDeletePart(id) {
    await fetchJSON(`/data/parts/${encodeURIComponent(id)}`, { method: "DELETE" });
  }

  async function apiCreateSignoff(payload) {
    const data = await fetchJSON("/documents/signoff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data;
  }
 
  async function apiCreateContact(payload) {
    const data = await fetchJSON("/crm/contacts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiUpdateContact(id, payload) {
    const data = await fetchJSON(`/crm/contacts/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }
 
  async function apiCreateEstimate(payload) {
    const data = await fetchJSON("/documents/estimate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data;
  }
 
  async function apiCreateInvoice(payload) {
    const data = await fetchJSON("/documents/invoice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data;
  }
 
  async function apiListDocuments(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/documents?${qs.toString()}`);
    return data.items || [];
  }
 
  async function apiUpdateDocument(filename, payload) {
    const data = await fetchJSON(`/documents/${encodeURIComponent(filename)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.doc || data;
  }
 
  async function apiDeleteDocument(filename) {
    await fetchJSON(`/documents/${encodeURIComponent(filename)}`, { method: "DELETE" });
  }


  async function apiListDocumentApprovals() {
    const data = await fetchJSON("/document-approvals");
    const approvals = data.approvals || {};
    return approvals.items || {};
  }

  async function apiSetDocumentApproval(key, payload) {
    const data = await fetchJSON(`/document-approvals/${encodeURIComponent(key)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    return data.approval || data;
  }

  function documentApprovalKey(doc) {
    const number = cleanDocRef(doc?.number || doc?.estimate_number || doc?.estimate_no || "");
    if (number) return `estimate:${number}`;
    const filename = String(doc?.filename || "").trim();
    if (filename) return `file:${filename}`;
    return `doc:${String(doc?.id || doc?.created_at || Math.random()).trim()}`;
  }


  async function apiGetPricing() {
    return await fetchJSON("/pricing");
  }

  async function apiSavePricing(payload) {
    return await fetchJSON("/pricing", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async function apiListDoorLogs() {
    return await fetchJSON("/door-logs");
  }

  async function apiCreateDoorLog(payload) {
    return await fetchJSON("/door-logs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async function apiUpdateDoorLog(id, payload) {
    return await fetchJSON(`/door-logs/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async function apiAppendDoorLogHistory(id, payload) {
    return await fetchJSON(`/door-logs/${encodeURIComponent(id)}/history`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async function apiDeleteDoorLog(id) {
    return await fetchJSON(`/door-logs/${encodeURIComponent(id)}`, { method: "DELETE" });
  }

  async function apiAutoFillDescription(payload) {
    return await fetchJSON("/documents/auto-description", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
 
  async function apiListTimeOff(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/timeoff?${qs.toString()}`);
    return data.items || [];
  }
 
  async function apiCreateTimeOff(payload) {
    const data = await fetchJSON("/timeoff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item || data;
  }
 
  async function apiUpdateTimeOff(id, payload) {
    const data = await fetchJSON(`/timeoff/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item || data;
  }
 
  async function apiDeleteTimeOff(id) {
    await fetchJSON(`/timeoff/${id}`, { method: "DELETE" });
  }
 
  async function apiListTimecards(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/timecards?${qs.toString()}`);
    return data.items || [];
  }
 
  async function apiCreateTimecard(payload) {
    const data = await fetchJSON("/timecards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item || data;
  }

  async function apiUpdateTimecard(itemId, payload) {
    const data = await fetchJSON(`/timecards/${encodeURIComponent(itemId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item || data;
  }
 
  async function apiDeleteTimecard(itemId) {
    await fetchJSON(`/timecards/${itemId}`, { method: "DELETE" });
  }

  async function uploadAdminDataFile(file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/admin/upload-data-file", {
      method: "POST",
      credentials: "same-origin",
      body: form,
    });
    const text = await res.text();
    let data = {};
    try { data = JSON.parse(text); } catch {}
    if (!res.ok) {
      throw new Error(data.detail || text || "Upload failed");
    }
    return data;
  }


  
  function getPtoBankMap() {
    const map = SHARED_SETTINGS_CACHE && SHARED_SETTINGS_CACHE.pto_bank;
    return map && typeof map === "object" ? map : {};
  }

  function setPtoBankHours(employee, hours) {
    const name = String(employee || "").trim();
    if (!name) return;
    const map = { ...getPtoBankMap(), [name]: Number(hours || 0) };
    SHARED_SETTINGS_CACHE.pto_bank = map;
    apiUpdateSharedSettingsSection("pto_bank", map).catch(e => console.warn("PTO bank save failed", e));
  }

  function getPtoBankHours(employee) {
    const map = getPtoBankMap();
    return Number(map[String(employee || "").trim()] || 0);
  }

  function getPtoAccrualMap() {
    const map = SHARED_SETTINGS_CACHE && SHARED_SETTINGS_CACHE.pto_accrual_rates;
    return map && typeof map === "object" ? map : {};
  }

  function setPtoAccrualRate(employee, hours) {
    const name = String(employee || "").trim();
    if (!name) return;
    const map = { ...getPtoAccrualMap(), [name]: Number(hours || 0) };
    SHARED_SETTINGS_CACHE.pto_accrual_rates = map;
    apiUpdateSharedSettingsSection("pto_accrual_rates", map).catch(e => console.warn("PTO accrual save failed", e));
  }

  function getPtoAccrualRate(employee) {
    const map = getPtoAccrualMap();
    return Number(map[String(employee || "").trim()] || 0);
  }

  function addPtoAccrualToBank(employee) {
    const rate = getPtoAccrualRate(employee);
    if (!rate) return 0;
    setPtoBankHours(employee, getPtoBankHours(employee) + rate);
    return rate;
  }

  function getTimecardDoubleTimeHours(entry) { return Math.max(0, Number(entry && (entry.double_time_hours ?? entry.dt_hours) || 0)); }
  function getTimecardHolidayHours(entry) { return Math.max(0, Number(entry && entry.holiday_hours || 0)); }
  function getTimecardPtoHours(entry) { return Math.max(0, Number(entry && entry.pto_hours || 0)); }
  function getTimecardRollupHours(entry, fallbackWorked) {
    if (!entry) return 0;
    const manual = Number(entry.rollup_hours);
    if (Number.isFinite(manual) && manual > 0) return manual;
    const text = `${entry.notes || ""} ${entry.job_type || ""} ${entry.door_type || ""}`.toLowerCase();
    return (entry.is_rollup_timecard || text.includes("roll up") || text.includes("rollup")) ? Math.max(0, Number(fallbackWorked || 0)) : 0;
  }

  function getOtBankMap() {
    const map = SHARED_SETTINGS_CACHE && SHARED_SETTINGS_CACHE.ot_bank;
    return map && typeof map === "object" ? map : {};
  }

  function setOtBankHours(employee, hours) {
    const name = String(employee || "").trim();
    if (!name) return;
    const map = { ...getOtBankMap(), [name]: Number(hours || 0) };
    SHARED_SETTINGS_CACHE.ot_bank = map;
    apiUpdateSharedSettingsSection("ot_bank", map).catch(e => console.warn("OT bank save failed", e));
  }

  function getOtBankHours(employee) {
    const map = getOtBankMap();
    return Number(map[String(employee || "").trim()] || 0);
  }

  function getRollupProfileMap() {
    const map = SHARED_SETTINGS_CACHE && SHARED_SETTINGS_CACHE.rollup_profiles;
    return map && typeof map === "object" ? map : {};
  }

  function getRollupProfile(employee, effectiveDate = "") {
    const map = getRollupProfileMap();
    const row = map[String(employee || "").trim()] || {};
    const legacyWage = Number(row.wage || 0);
    const month = String(effectiveDate || "").slice(0, 7);
    const history = Array.isArray(row.wage_history)
      ? row.wage_history
          .filter(item => item && /^\d{4}-\d{2}$/.test(String(item.effective_month || "")))
          .slice()
          .sort((a, b) => String(a.effective_month).localeCompare(String(b.effective_month)))
      : [];
    let wage = legacyWage;
    if (month) {
      history.forEach(item => {
        if (String(item.effective_month) <= month) wage = Number(item.wage || 0);
      });
    } else if (history.length) {
      wage = Number(history[history.length - 1].wage || 0);
    }
    return {
      wage,
      multiplier: Number(row.multiplier || 0),
      wage_history: history,
    };
  }

  function setRollupProfile(employee, wage, multiplier, effectiveMonth = "") {
    const name = String(employee || "").trim();
    if (!name) return;
    const map = { ...getRollupProfileMap() };
    const previous = map[name] && typeof map[name] === "object" ? { ...map[name] } : {};
    const legacyWage = Number(previous.wage || 0);
    const history = Array.isArray(previous.wage_history) ? previous.wage_history.slice() : [];
    const month = String(effectiveMonth || "").slice(0, 7);

    if (month) {
      const today = new Date();
      const currentCalendarMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
      if (!history.length && month < currentCalendarMonth && legacyWage > 0) {
        history.push({ effective_month: currentCalendarMonth, wage: legacyWage });
      }
      const nextEntry = { effective_month: month, wage: Number(wage || 0) };
      const idx = history.findIndex(item => String(item?.effective_month || "") === month);
      if (idx >= 0) history[idx] = nextEntry;
      else history.push(nextEntry);
      history.sort((a, b) => String(a.effective_month || "").localeCompare(String(b.effective_month || "")));
      map[name] = { ...previous, wage: legacyWage, multiplier: Number(multiplier || 0), wage_history: history };
    } else {
      map[name] = { ...previous, wage: Number(wage || 0), multiplier: Number(multiplier || 0), wage_history: history };
    }

    SHARED_SETTINGS_CACHE.rollup_profiles = map;
    apiUpdateSharedSettingsSection("rollup_profiles", map).catch(e => console.warn("Roll up profile save failed", e));
  }

function ptoHoursFromItem(item) {
    const explicit = Number(item.pto_hours || 0);
    if (!Number.isNaN(explicit) && explicit > 0) return explicit;
    const hrs = Number(item.hours || 0);
    if (!Number.isNaN(hrs) && hrs > 0) return hrs;
    return 8;
  }

  function employeeNameOfItem(item) {
    return String(item.employee || item.employee_name || item.technician_name || "").trim();
  }

  function itemDateOf(item) {
    return item.date || item.start_date || item.created_at || "";
  }
 
  
  let SHARED_SETTINGS_CACHE = {
    rollup_profiles: {},
    pto_bank: {},
    ot_bank: {},
  };

  
  async function apiGetSaddlebackData() {
    const data = await fetchJSON("/saddleback");
    return data.data || { orders: [], expenses: [], purchases: [] };
  }

  async function apiSaveSaddlebackData(payload) {
    const data = await fetchJSON("/saddleback", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || { orders: [], expenses: [], purchases: [] }),
    });
    return data.data || payload;
  }

async function apiGetSharedSettings() {
    const data = await fetchJSON("/shared-settings");
    SHARED_SETTINGS_CACHE = data.settings || SHARED_SETTINGS_CACHE;
    return SHARED_SETTINGS_CACHE;
  }

  async function apiUpdateSharedSettingsSection(section, payload) {
    const data = await fetchJSON(`/shared-settings/${encodeURIComponent(section)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    SHARED_SETTINGS_CACHE = data.settings || SHARED_SETTINGS_CACHE;
    return SHARED_SETTINGS_CACHE;
  }

  async function ensureSharedSettingsLoaded() {
    try { await apiGetSharedSettings(); } catch (e) { console.warn("shared settings unavailable", e); }
  }

async function apiListForms() {
    const data = await fetchJSON("/forms");
    return data.forms || [];
  }
 
  async function downloadFile(url, filename) {
    if (!url) throw new Error("Missing download URL");
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) throw new Error(`Download failed (${r.status})`);
    const blob = await r.blob();
    const u = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = u;
    a.download = filename || "document.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(u), 1500);
  }

  function openFileUrl(url) {
    if (!url) {
      alert("File link is missing.");
      return;
    }
    try {
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e) {
      window.location.href = url;
    }
  }
 
  async function apiAuthMe() {
    const res = await fetch("/auth/me", { credentials: "same-origin" });
    const txt = await res.text();
    try { return JSON.parse(txt); } catch { return { logged_in: false, user: null }; }
  }

  async function apiLogin(username, password) {
    return fetchJSON("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
  }

  async function apiLoginPin(pin) {
    return fetchJSON("/auth/login-pin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
  }

  async function apiLogout() {
    return fetchJSON("/auth/logout", { method: "POST" });
  }

  async function apiListNotifications(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/notifications?${qs.toString()}`);
    return data.items || [];
  }

  async function apiCreateNotification(payload) {
    const data = await fetchJSON("/notifications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiMarkNotificationRead(id, read = true) {
    const data = await fetchJSON(`/notifications/${id}/read`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ read }),
    });
    return data.item;
  }

  async function apiDeleteNotification(id) {
    await fetchJSON(`/notifications/${id}`, { method: "DELETE" });
  }

  async function apiNotificationRecipients() {
    const data = await fetchJSON("/notifications/recipients");
    return data.items || [];
  }

  function setVisible(node, show) {
    if (!node) return;
    node.style.display = show ? "" : "none";
  }

  function accessForRole(role) {
    const all = { calendar: true, forms: true, jobFlow: true, office: true, chat: true, notifications: true, atlas: true, moses: true, payroll: true, employees: true, dataCenter: true, customers: true, estimates: true, parts: true, saddleback: true, dataUpload: true };
    if (role === "office_admin") return all;
    if (role === "office") return { ...all, chat: false, atlas: false, moses: false, dataUpload: false };
    if (role === "lead") return { calendar: true, forms: true, jobFlow: true, office: true, chat: false, notifications: true, atlas: false, moses: false, payroll: false, employees: false, dataCenter: true, customers: true, estimates: true, parts: true, saddleback: false, dataUpload: false };
    if (role === "tech") return { calendar: true, forms: true, jobFlow: true, office: false, chat: false, notifications: true, atlas: false, moses: false, payroll: false, employees: false, dataCenter: false, customers: false, estimates: false, parts: false, saddleback: false, dataUpload: false };
    return { calendar: false, forms: false, jobFlow: false, office: false, chat: false, notifications: false, atlas: false, moses: false, payroll: false, employees: false, dataCenter: false, customers: false, estimates: false, parts: false, saddleback: false, dataUpload: false };
  }

  function applyRoleAccess(role) {
    const perms = accessForRole(role);
    setVisible(formsPanel, !!role && perms.forms);
    setVisible(jobFlowPanel, !!role && perms.jobFlow);
    setVisible(officeFlowPanel, !!role && perms.office);
    // Chat navigation removed in Doorks 2.0; Moses form assistant remains available.
    setVisible(notificationsPanel, !!role && perms.notifications);
    if (headerCalendarBtn) headerCalendarBtn.style.display = role && perms.calendar ? "inline-flex" : "none";
    setVisible(navDataCenter, !!role && perms.dataCenter);
    setVisible(navAccounting, role === "office" || role === "office_admin");
    setVisible(navPayroll, !!role && perms.payroll);
    setVisible(navEmployees, !!role && perms.employees);
    setVisible(navDataUpload, role === "office_admin" && !!perms.dataUpload);
    setVisible(navSaddleback, role === "office_admin" && !!perms.saddleback);
    setVisible(navAtlas, !!role && perms.atlas);
    setVisible(navMoses, !!role && perms.moses);
    setVisible(navCustomers, !!role && perms.customers);
    setVisible(navEstimateInvoice, !!role && perms.estimates);
    setVisible(navPartsList, !!role && perms.parts);
    setVisible(navDoorLogs, !!role && perms.parts);
    setVisible(navToDoList, !!role && ["office", "office_admin", "admin"].includes(String(role || "")));
    setVisible(navPricingSettings, !!role && perms.estimates);
  }

  function updateLoginUi(message = "") {
    const loggedIn = !!currentUser;
    document.body.classList.toggle("doorks-logged-out",!loggedIn);
    if(loggedIn){const aside=document.querySelector("main.layout > aside.sidebar");if(aside)for(const panel of aside.querySelectorAll(".panel"))panel.style.removeProperty("display");}
    const awaitingPin = !loggedIn && !!pendingPinUser;
    if (usernameInput) usernameInput.disabled = loggedIn || awaitingPin;
    if (passwordInput) passwordInput.disabled = loggedIn || awaitingPin;
    if (pinInput) pinInput.disabled = loggedIn || !awaitingPin;
    if (pinStepWrap) pinStepWrap.style.display = awaitingPin ? "grid" : "none";
    if (loginBtn) {
      loginBtn.style.display = loggedIn || awaitingPin ? "none" : "inline-flex";
      loginBtn.textContent = "Next";
    }
    if (pinBtn) pinBtn.style.display = awaitingPin ? "inline-flex" : "none";
    if (logoutBtn) logoutBtn.style.display = loggedIn ? "inline-flex" : "none";
    if (loginStatus) {
      if (loggedIn) {
        loginStatus.textContent = `${currentUser.name || currentUser.username} • ${String(currentUser.role || "").replace(/_/g, " ")}`;
      } else if (awaitingPin) {
        loginStatus.textContent = message || "Enter your 4-digit PIN to continue.";
      } else {
        loginStatus.textContent = message || "Log in to access Doorks.";
      }
    }
  }

  function showLoggedOutSplash(message = "Log in to access Doorks.") {
    setActiveChip("Login");
    setWorkspace("Login");
    clearWorkspaceActions();
    workspaceBody.innerHTML = `<div class="card"><h3>Doorks Login</h3><div class="hint">${escapeHtml(message)}</div><div class="hint" style="margin-top:8px;">Use your seeded admin login to continue.</div></div>`;
    currentView = { refresh: async () => {} };
    if (loginBody) loginBody.style.display = "block";
    document.body.classList.add("doorks-logged-out");
    const aside=document.querySelector("main.layout > aside.sidebar");
    if(aside){for(const panel of aside.querySelectorAll(".panel")){if(!panel.contains(loginBody))panel.style.display="none";}}
  }

  async function handleLogin() {
    const username = usernameInput ? usernameInput.value.trim() : "";
    const password = passwordInput ? passwordInput.value : "";
    if (!username || !password) {
      updateLoginUi("Enter username and password.");
      return;
    }
    try {
      const data = await apiLogin(username, password);
      if (passwordInput) passwordInput.value = "";
      if (data && data.requires_pin) {
        pendingPinUser = data.user || { username };
        updateLoginUi("Username and password accepted. Enter your 4-digit PIN.");
        if (pinInput) {
          pinInput.value = "";
          pinInput.focus();
        }
        return;
      }
      pendingPinUser = null;
      currentUser = data.user || null;
      applyRoleAccess(currentUser ? currentUser.role : null);
      updateLoginUi();
      renderCalendarView();
      initializePlatform();
      refreshBadges();
    } catch (e) {
      pendingPinUser = null;
      updateLoginUi(e.message || "Login failed.");
    }
  }

  async function handlePinLogin() {
    const pin = pinInput ? pinInput.value.trim() : "";
    if (!pin || pin.length !== 4) {
      updateLoginUi("Enter your 4-digit PIN.");
      return;
    }
    try {
      const data = await apiLoginPin(pin);
      pendingPinUser = null;
      currentUser = data.user || null;
      if (pinInput) pinInput.value = "";
      applyRoleAccess(currentUser ? currentUser.role : null);
      updateLoginUi();
      renderCalendarView();
      initializePlatform();
      refreshBadges();
    } catch (e) {
      updateLoginUi(e.message || "PIN verification failed.");
    }
  }

  async function handleLogout() {
    try { await apiLogout(); } catch {}
    currentUser = null;
    pendingPinUser = null;
    if (pinInput) pinInput.value = "";
    applyRoleAccess(null);
    updateLoginUi("Logged out.");
    showLoggedOutSplash("Logged out.");
    initializePlatform();
  }

  async function refreshBadges() {
    try {
      const items = await fetchJSON("/notifications").then(d => d.items || []);
      const unread = items.filter(x => !x.read && !x.is_mine).length;
      badgeNotifications.style.display = unread ? "inline-flex" : "none";
      badgeNotifications.textContent = String(unread);
 
      const statuses = ["Sales Lead", "Dispatch", "Quote", "Parts on Order", "Complete/Quote", "Complete"];
      let total = 0;
      for (const s of statuses) total += (await apiListJobs({ status: s, limit: 5000 })).length;
      badgeJobFlow.style.display = total ? "inline-flex" : "none";
      badgeJobFlow.textContent = String(total);

      const badgeToDoList = document.getElementById("badgeToDoList");
      if (badgeToDoList && isOfficeUser()) {
        const jobs = await apiListJobs({ limit: 5000 }).catch(() => []);
        const assignedCount = assignedQuoteJobs(jobs).length;
        badgeToDoList.style.display = assignedCount ? "inline-flex" : "none";
        badgeToDoList.textContent = String(assignedCount);
      } else if (badgeToDoList) {
        badgeToDoList.style.display = "none";
      }
    } catch {}
  }
 
  function formsOf(job) {
    return Array.isArray(job.completion_forms) ? job.completion_forms : [];
  }
 
  function hasLeadRecommendation(job) {
    return formsOf(job).some(f => String(f.recommendations || "").trim().length > 0 || f.ready_to_quote === true);
  }
 
  function hasJobCompletion(job) {
    return formsOf(job).some(f =>
      String(f.tech_notes || "").trim().length > 0 ||
      String(f.parts_used || "").trim().length > 0 ||
      String(f.additional_recommendations || "").trim().length > 0 ||
      typeof f.time_onsite_hours === "number"
    );
  }
 
  function shouldShowEstimate(job) {
    if (job.kind === "sales_lead") return true;
    if (job.kind === "dispatch") {
      // Estimates/follow-up quotes may be needed even after a job is Complete or Done.
      return true;
    }
    return false;
  }
 
  function shouldShowInvoice(job) {
    if (job.kind !== "dispatch") return false;
    return ["Complete/Quote", "Complete", "Done"].includes(String(job.status || ""));
  }

  function isOfficeUser() {
    return !!(currentUser && ["office", "office_admin", "admin"].includes(String(currentUser.role || "")));
  }

  function isActiveAssignedQuoteJob(job) {
    const assigned = String(job && job.quote_assigned_to || "").trim();
    if (!assigned) return false;
    const status = String(job && job.status || "").trim();
    return ["Quote", "Complete/Quote"].includes(status);
  }

  function assignedQuoteJobs(jobs) {
    return (Array.isArray(jobs) ? jobs : []).filter(isActiveAssignedQuoteJob);
  }

  function initialsForName(name) {
    return String(name || "")
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .map(part => part[0])
      .join("")
      .toUpperCase();
  }

  function normalizeQuoteAssigneeName(raw, people = []) {
    const value = String(raw || "").trim();
    if (!value) return "Unassigned";
    const upper = value.toUpperCase();
    const lower = value.toLowerCase();
    const source = Array.isArray(people) ? people : [];

    const exactOrInitials = source.find(p => {
      const name = String(p.name || p.full_name || p.username || "").trim();
      if (!name) return false;
      return name.toUpperCase() === upper || initialsForName(name) === upper;
    });
    if (exactOrInitials) return String(exactOrInitials.name || exactOrInitials.full_name || exactOrInitials.username || value).trim();

    const partialMatches = source.filter(p => {
      const name = String(p.name || p.full_name || p.username || "").trim();
      if (!name) return false;
      const parts = name.toLowerCase().split(/\s+/).filter(Boolean);
      return parts.includes(lower) || name.toLowerCase().startsWith(lower + " ");
    });
    if (partialMatches.length === 1) {
      const p = partialMatches[0];
      return String(p.name || p.full_name || p.username || value).trim();
    }

    return value;
  }

  function cleanDocRef(value) {
    const s = String(value == null ? "" : value).replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
    if (!s) return "";
    const fixed = fixMojibake(s).replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
    if (!fixed) return "";
    const normalized = fixed
      .replace(/\u00a0/g, " ")
      .replace(/[–—]/g, "-")
      .replace(/Ã¢â‚¬â€|Ã¢â‚¬“/g, "-")
      .trim();
    if (!normalized) return "";
    if (/^(?:-|—|–|Ã¢â‚¬â€|Ã¢â‚¬“|n\/a|na|none|null|undefined)*$/i.test(normalized)) return "";
    return normalized;
  }

  function formatDocRefDisplay(value) {
    return escapeHtml(cleanDocRef(value));
  }

  
function isApprovedEstimateJob(job, monthPrefix = "") {
    const estimateNumber = String(job?.estimate_number || job?.sent_quote_number || "").trim();
    if (!estimateNumber) return false;
    const explicit = String(job?.approved ?? "").toLowerCase();
    if (job?.approved === false || explicit === "false" || explicit === "0" || explicit === "no") return false;
    const approvedStatuses = new Set(["Dispatch", "Parts on Order", "Complete/Quote", "Complete", "Done"]);
    const approvedAt = String(job?.approved_at || "");
    if (job?.approved === true || explicit === "true" || explicit === "1" || explicit === "yes") {
      if (!monthPrefix) return true;
      return approvedAt.startsWith(monthPrefix)
        || String(job?.updated_at || "").startsWith(monthPrefix)
        || String(job?.date || "").startsWith(monthPrefix);
    }
    if (!approvedStatuses.has(String(job?.status || ""))) return false;
    if (!monthPrefix) return true;
    return approvedAt.startsWith(monthPrefix)
      || String(job?.updated_at || "").startsWith(monthPrefix)
      || String(job?.date || "").startsWith(monthPrefix);
  }
 
  async function promptDispatchStatus() {
    return new Promise((resolve) => {
      openDrawer("Select New Job Status", (bd, overlay) => {
        const card = document.createElement("div");
        card.className = "card";
 
        const label = document.createElement("div");
        label.className = "label";
        label.textContent = "Select the updated job status before opening the completion form";
        card.appendChild(label);
 
        const wrap = document.createElement("div");
        wrap.className = "navcol";
        wrap.style.marginTop = "10px";
 
        JOB_STATUS_OPTIONS.forEach(status => {
          const b = document.createElement("button");
          b.className = "navbtn";
          b.innerHTML = `<span>${status}</span>`;
          b.addEventListener("click", () => {
            overlay.remove();
            resolve(status);
          });
          wrap.appendChild(b);
        });
 
        const cancel = document.createElement("button");
        cancel.className = "btn";
        cancel.style.marginTop = "12px";
        cancel.textContent = "Cancel";
        cancel.addEventListener("click", () => {
          overlay.remove();
          resolve(null);
        });
 
        card.appendChild(wrap);
        card.appendChild(cancel);
        bd.appendChild(card);
      });
    });
  }
 
  function buildCustomerDatalist(id, customers) {
    const dl = document.createElement("datalist");
    dl.id = id;
    customers.forEach(c => {
      const o = document.createElement("option");
      o.value = c.company_name || "";
      dl.appendChild(o);
    });
    return dl;
  }
 
  function buildContactDatalist(id, contacts) {
    const dl = document.createElement("datalist");
    dl.id = id;
    contacts.forEach(c => {
      const o = document.createElement("option");
      o.value = c.name || "";
      dl.appendChild(o);
    });
    return dl;
  }
 
  function normalizeText(v) {
    return String(v || "").trim().toLowerCase();
  }
 
  function pickContactPhone(contact) {
    return contact?.phone_number || contact?.cell_phone || "";
  }
 
  function companyMatches(contactCompany, selectedCompany) {
    const a = normalizeText(contactCompany);
    const b = normalizeText(selectedCompany);
    if (!a || !b) return false;
    return a === b || a.includes(b) || b.includes(a);
  }
 
  function findMatchingContact(contacts, name, companyName = "") {
    const n = normalizeText(name);
    if (!n) return null;
    const company = normalizeText(companyName);
    const byName = contacts.filter(c => {
      const cn = normalizeText(c.name);
      return cn === n || cn.includes(n) || n.includes(cn);
    });
    if (!byName.length) return null;
    return byName.find(c => company && companyMatches(c.company_name, company)) || byName[0] || null;
  }
 
  function wireContactAutofill({ contacts, contactInput, phoneInput, emailInput, customerInput, contactListId }) {
    if (!contactInput) return;
    const source = Array.isArray(contacts) ? contacts : [];
    const dl = contactListId ? document.getElementById(contactListId) : null;
 
    const filteredContacts = () => {
      const company = normalizeText(customerInput ? customerInput.value : "");
      return company ? source.filter(c => companyMatches(c.company_name, company)) : source;
    };
 
    const renderOptions = () => {
      if (!dl) return;
      dl.innerHTML = "";
      filteredContacts().forEach(c => {
        const o = document.createElement("option");
        o.value = c.name || "";
        o.label = c.company_name ? `${c.name || ""}  -  ${c.company_name}` : (c.name || "");
        dl.appendChild(o);
      });
    };
 
    const applyFromContact = (force = false) => {
      const match = findMatchingContact(filteredContacts(), contactInput.value, customerInput ? customerInput.value : "");
      if (!match) return;
      if (phoneInput && (force || !String(phoneInput.value || "").trim())) phoneInput.value = pickContactPhone(match) || "";
      if (emailInput && (force || !String(emailInput.value || "").trim())) emailInput.value = match.email || "";
      if (customerInput && !customerInput.value.trim() && match.company_name) customerInput.value = match.company_name;
    };
 
    const onCustomerChange = () => {
      renderOptions();
      const match = findMatchingContact(filteredContacts(), contactInput.value, customerInput ? customerInput.value : "");
      if (match) {
        applyFromContact(true);
      }
      // Preserve manually entered contact/phone/email if this is not a saved CRM contact.
    };
 
    renderOptions();
    ["change", "blur"].forEach(evt => contactInput.addEventListener(evt, () => applyFromContact(true)));
    if (customerInput) ["change", "blur", "input"].forEach(evt => customerInput.addEventListener(evt, onCustomerChange));
  }
 
  function uid(prefix = "id") {
    return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
  }
 
  function buildAddressDatalist(id, addresses) {
    const dl = document.createElement("datalist");
    dl.id = id;
    Array.from(new Set((addresses || []).map(v => String(v || "").trim()).filter(Boolean))).slice(0, 500).forEach(addr => {
      const o = document.createElement("option");
      o.value = addr;
      dl.appendChild(o);
    });
    return dl;
  }
 
  function wireGoogleAddressAutocomplete(input) {
    return false;
  }
 
  function wireAddressSuggestions(input, addresses = []) {
    if (!input) return;
    if (wireGoogleAddressAutocomplete(input)) return;
 
    const listId = uid("addrlist");
    input.setAttribute("list", listId);
    const dl = buildAddressDatalist(listId, addresses);
    if (input.parentElement) input.parentElement.appendChild(dl);
 
    const retryBind = () => {
      if (wireGoogleAddressAutocomplete(input)) {
        input.removeEventListener("focus", retryBind);
        input.removeEventListener("click", retryBind);
        window.removeEventListener("doorks:google-ready", retryBind);
      }
    };
 
    input.addEventListener("focus", retryBind);
    input.addEventListener("click", retryBind);
    window.addEventListener("doorks:google-ready", retryBind);
    setTimeout(retryBind, 1200);
    setTimeout(retryBind, 2500);
    setTimeout(retryBind, 5000);
  }

  function normalizeAddressText(v) {
    return String(v || "").replace(/\s+/g, " ").trim().toLowerCase();
  }

  function findMatchingAddress(addresses, value) {
    const typed = normalizeAddressText(value);
    if (!typed) return null;
    const source = Array.isArray(addresses) ? addresses : [];
    // IMPORTANT:
    // Only treat the address as selected when it exactly matches a saved option.
    // Do NOT use partial matching here, because partial matching can overwrite a
    // manually typed new address with the first saved address in the list.
    return source.find(a => {
      const addr = normalizeAddressText(a.address || a.formatted_address || a.job_site_address || "");
      return addr && addr === typed;
    }) || null;
  }

  function addressDisplayValue(a) {
    return a ? (a.address || a.formatted_address || a.job_site_address || "") : "";
  }

  function addressCustomerValue(a) {
    return a ? (a.company_name || a.customer || a.customer_name || "") : "";
  }

  function combinedAddressStrings(customerAddresses = [], knownAddresses = []) {
    const fromCustomers = (customerAddresses || []).map(v => String(v || "").trim()).filter(Boolean);
    const fromKnown = (knownAddresses || []).map(a => addressDisplayValue(a)).filter(Boolean);
    return Array.from(new Set([...fromCustomers, ...fromKnown]));
  }

  function addressBelongsToCustomer(addr, customerName) {
    const selected = normalizeText(customerName || "");
    if (!selected) return true;
    const owner = normalizeText(addressCustomerValue(addr));
    return !!owner && owner === selected;
  }

  function filteredAddressObjectsForCustomer(knownAddresses = [], customerName = "") {
    const selected = normalizeText(customerName || "");
    if (!selected) return Array.isArray(knownAddresses) ? knownAddresses : [];
    return (Array.isArray(knownAddresses) ? knownAddresses : []).filter(a => addressBelongsToCustomer(a, selected));
  }

  function customerSpecificAddressStrings(customerAddresses = [], knownAddresses = [], customerName = "") {
    const filteredKnown = filteredAddressObjectsForCustomer(knownAddresses, customerName);
    return combinedAddressStrings(customerAddresses, filteredKnown);
  }

  function wireKnownAddressAutofill({ input, customerInput = null, knownAddresses = [], extraAddresses = [] }) {
    if (!input) return;
    if (wireGoogleAddressAutocomplete(input)) return;

    const listId = uid("addrlist");
    input.setAttribute("list", listId);
    let dl = buildAddressDatalist(listId, []);
    if (input.parentElement) input.parentElement.appendChild(dl);

    const getCustomer = () => customerInput ? String(customerInput.value || "").trim() : "";
    const renderOptions = () => {
      // Restore full address search: show all known/saved/customer-list addresses.
      // Manual typing still works, and exact matches still autofill city/state/zip.
      const values = combinedAddressStrings((extraAddresses || []), (knownAddresses || []));
      const next = buildAddressDatalist(listId, values);
      if (dl && dl.parentElement) dl.parentElement.replaceChild(next, dl);
      dl = next;
    };

    renderOptions();
    if (customerInput) ["input", "change", "blur"].forEach(evt => customerInput.addEventListener(evt, renderOptions));

    const apply = () => {
      const matchSource = knownAddresses || [];
      const match = findMatchingAddress(matchSource, input.value);
      if (!match) return;
      const addr = addressDisplayValue(match);
      if (addr) input.value = addr;
      const customer = addressCustomerValue(match);
      if (customerInput && customer && !String(customerInput.value || "").trim()) customerInput.value = customer;
    };
    // Apply only on explicit change/selection. Do not apply on blur because that
    // can overwrite manually typed addresses that are not yet saved.
    input.addEventListener("change", apply);
  }
 
  function collectJobTechSummary(job) {
    const forms = formsOf(job);
    const rollupForms = forms.filter(f => String(f.door_type || "").toLowerCase() === "roll up");
    const source = rollupForms.length ? rollupForms : forms;
    if (!source.length) return [];
    const byTech = new Map();
    source.forEach(f => {
      const name = String(f.technician_name || "").trim();
      const hrs = Number(f.time_onsite_hours || 0);
      if (!name && !hrs) return;
      const key = name || "Tech";
      byTech.set(key, (byTech.get(key) || 0) + hrs);
    });
    const out = [];
    if (rollupForms.length) out.push("Roll Up");
    byTech.forEach((hrs, name) => {
      out.push(`${name} - ${Number(hrs || 0).toFixed(2)} hrs`);
    });
    return out;
  }
 
  function getTaxableSubtotal(items) {
    return (items || []).reduce((sum, item) => {
      if (item.taxable === false) return sum;
      return sum + (Number(item.qty || 0) * Number(item.rate || 0));
    }, 0);
  }
 
  function formatDocNumber(prefix, num) {
    return `${prefix}${String(Math.max(1, Number(num || 1))).padStart(5, "0")}`;
  }
 
  function nextDocNumberFromStorage(kind) {
    const key = kind === "estimate" ? "doorks_estimate_next" : "doorks_invoice_next";
    const prefix = kind === "estimate" ? "RE" : "JS";
    const floor = kind === "estimate" ? 75 : 20;
    let cur = Number(localStorage.getItem(key) || String(floor));
    if (!Number.isFinite(cur) || cur < floor) cur = floor;
    localStorage.setItem(key, String(cur + 1));
    return formatDocNumber(prefix, cur);
  }
 
  function formatBytes(bytes) {
    const n = Number(bytes || 0);
    if (!Number.isFinite(n) || n <= 0) return "0 B";
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }
 
  function formatStamp(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  }
 
  function fixMojibake(v) {
    return String(v || "")
      .replace(/ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â/g, "Ã¢â‚¬â€")
      .replace(/ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“/g, "Ã¢â‚¬“")
      .replace(/ÃƒÂ¢Ã¢â€šÂ¬Ã‹Å“/g, "Ã¢â‚¬Ëœ")
      .replace(/ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢/g, "Ã¢â‚¬™")
      .replace(/ÃƒÂ¢Ã¢â€šÂ¬Ã…“/g, "Ã¢â‚¬Å“")
      .replace(/ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â/g, "Ã¢â‚¬Â")
      .replace(/Ãƒâ€š/g, "")
      .replace(/Ã‚ /g, " ");
  }
 
  function escapeHtml(v) {
    return fixMojibake(v).replace(/[&<>"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch] || ch));
  }
 
  function isImageFilename(name) {
    return /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(String(name || ""));
  }
 
  function buildJobAttachmentUrl(jobId, filename) {
    return `/calendar/jobs/${encodeURIComponent(jobId)}/attachments/${encodeURIComponent(filename || "")}`;
  }
 
  function buildCompletionAttachmentUrl(jobId, formId, filename) {
    return `/calendar/jobs/${encodeURIComponent(jobId)}/completion/${encodeURIComponent(formId)}/attachments/${encodeURIComponent(filename || "")}`;
  }
 
  function openImagePreview(title, url) {
    openDrawer(title || "Preview", async (drawerBody) => {
      const img = document.createElement("img");
      img.src = url;
      img.alt = title || "Preview";
      img.style.maxWidth = "100%";
      img.style.borderRadius = "12px";
      drawerBody.appendChild(img);
    });
  }
 
  
  function formatFormDate(value) {
    if (!value) return "";
    const s = String(value || "").slice(0, 10);
    const p = s.split("-");
    if (p.length === 3) return `${p[1]}/${p[2]}/${p[0]}`;
    return s;
  }

function renderAttachmentSection(titleText, items, options = {}) {
    const wrap = document.createElement("div");
    wrap.style.marginTop = "10px";

    const title = document.createElement("div");
    title.className = "label";
    title.textContent = titleText;
    wrap.appendChild(title);

    const list = Array.isArray(items) ? items : [];
    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "No attachments uploaded yet.";
      empty.style.marginTop = "6px";
      wrap.appendChild(empty);
      return wrap;
    }

    const carouselFiles = list.map(file => ({
      ...file,
      url: typeof options.urlBuilder === "function" ? options.urlBuilder(file) : ""
    }));

    const box = document.createElement("div");
    box.style.display = "grid";
    box.style.gap = "8px";
    box.style.marginTop = "8px";

    list.forEach((file, i) => {
      const filename = file.filename || "Attachment";
      const url = carouselFiles[i].url || "";
      const row = document.createElement("div");
      row.className = "jobrow";

      const top = document.createElement("div");
      top.className = "jobrow-top";
      const name = document.createElement("div");
      name.className = "jobrow-name";
      name.textContent = filename;
      const meta = document.createElement("div");
      meta.className = "hint";
      meta.textContent = formatBytes(file.bytes || 0);
      top.appendChild(name);
      top.appendChild(meta);

      const stamp = document.createElement("div");
      stamp.className = "jobrow-addr";
      stamp.textContent = formatStamp(file.created_at) || "Saved";

      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "8px";
      actions.style.flexWrap = "wrap";

      if (url) {
        const viewBtn = document.createElement("button");
        styleActionButton(viewBtn, "blue", true);
        viewBtn.textContent = "Open";
        viewBtn.addEventListener("click", () => openAttachmentCarousel(carouselFiles, i));
        actions.appendChild(viewBtn);
      }

      row.appendChild(top);
      row.appendChild(stamp);
      if (actions.childNodes.length) row.appendChild(actions);
      box.appendChild(row);
    });

    wrap.appendChild(box);
    return wrap;
  }

  function openAttachmentCarousel(files, startIndex = 0) {
    const attachments = (Array.isArray(files) ? files : []).filter(f => f && f.url);
    if (!attachments.length) return;

    let index = Math.max(0, Math.min(startIndex, attachments.length - 1));

    const overlay = document.createElement("div");
    overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:99999;display:flex;align-items:center;justify-content:center;padding:22px;";

    const close = document.createElement("button");
    close.textContent = "×";
    close.style.cssText = "position:absolute;top:14px;right:18px;font-size:38px;line-height:1;color:#fff;background:transparent;border:0;cursor:pointer;font-weight:900;";

    const left = document.createElement("button");
    left.textContent = "‹";
    left.style.cssText = "position:absolute;left:18px;top:50%;transform:translateY(-50%);font-size:56px;color:#fff;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.25);border-radius:999px;width:58px;height:58px;cursor:pointer;";

    const right = document.createElement("button");
    right.textContent = "›";
    right.style.cssText = "position:absolute;right:18px;top:50%;transform:translateY(-50%);font-size:56px;color:#fff;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.25);border-radius:999px;width:58px;height:58px;cursor:pointer;";

    const content = document.createElement("div");
    content.style.cssText = "max-width:92vw;max-height:88vh;display:flex;flex-direction:column;align-items:center;gap:10px;color:white;";

    const mediaWrap = document.createElement("div");
    mediaWrap.style.cssText = "max-width:92vw;max-height:78vh;display:flex;align-items:center;justify-content:center;";

    const caption = document.createElement("div");
    caption.style.cssText = "font-weight:800;text-align:center;color:#fff;";

    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;gap:8px;justify-content:center;";

    function render() {
      const file = attachments[index];
      const inlineUrl = `${file.url}${String(file.url).includes("?") ? "&" : "?"}inline=1`;
      mediaWrap.innerHTML = "";
      if (isImageFilename(file.filename || "")) {
        const img = document.createElement("img");
        img.src = inlineUrl;
        img.alt = file.filename || "Attachment";
        img.style.cssText = "max-width:92vw;max-height:78vh;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.55);background:white;";
        mediaWrap.appendChild(img);
      } else {
        const frame = document.createElement("iframe");
        frame.src = inlineUrl;
        frame.style.cssText = "width:88vw;height:76vh;background:white;border:0;border-radius:12px;";
        mediaWrap.appendChild(frame);
      }
      caption.textContent = `${index + 1} of ${attachments.length} — ${file.filename || "Attachment"}`;
      actions.innerHTML = "";
      const openLink = document.createElement("a");
      openLink.className = "btn";
      openLink.href = inlineUrl;
      openLink.target = "_blank";
      openLink.rel = "noopener noreferrer";
      openLink.textContent = "Open in New Tab";
      actions.appendChild(openLink);
      left.style.display = attachments.length > 1 ? "block" : "none";
      right.style.display = attachments.length > 1 ? "block" : "none";
    }

    function prev() { index = (index - 1 + attachments.length) % attachments.length; render(); }
    function next() { index = (index + 1) % attachments.length; render(); }
    function cleanup() { document.removeEventListener("keydown", keyHandler); overlay.remove(); }
    function keyHandler(e) {
      if (e.key === "Escape") cleanup();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    }

    close.addEventListener("click", cleanup);
    left.addEventListener("click", (e) => { e.stopPropagation(); prev(); });
    right.addEventListener("click", (e) => { e.stopPropagation(); next(); });
    overlay.addEventListener("click", (e) => { if (e.target === overlay) cleanup(); });
    document.addEventListener("keydown", keyHandler);

    content.appendChild(mediaWrap);
    content.appendChild(caption);
    content.appendChild(actions);
    overlay.appendChild(close);
    overlay.appendChild(left);
    overlay.appendChild(right);
    overlay.appendChild(content);
    document.body.appendChild(overlay);
    render();
  }

  function openEditSavedForm(job, formIndex, container, ctx) {
    const f = formsOf(job)[formIndex];
    if (!f) return;
 
    const isSalesLead = job.kind === "sales_lead";
    let employeesPromise = apiListEmployees().catch(() => []);
 
    openDrawer(`Edit ${isSalesLead ? "Recommendation" : "Completion"} Form`, async (drawerBody, overlay) => {
      const employees = await employeesPromise;
 
      const card = document.createElement("div");
      card.className = "card";

      const dateRow = document.createElement("div");
      dateRow.style.marginTop = "0";
      dateRow.innerHTML = `
        <div class="label">Date</div>
        <input class="input" id="ef_date" type="date" />
      `;
      dateRow.querySelector("#ef_date").value = String(f.date || f.created_at || new Date().toISOString()).slice(0, 10);
      card.appendChild(dateRow);
 
      let stSel = null;
      if (!isSalesLead) {
        const statusWrap = document.createElement("div");
        statusWrap.innerHTML = `<div class="label">Status</div>`;
        stSel = document.createElement("select");
        stSel.className = "input";
        JOB_STATUS_OPTIONS.forEach(s => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.textContent = s;
          stSel.appendChild(opt);
        });
        stSel.value = f.status_update || "Dispatch";
        statusWrap.appendChild(stSel);
        card.appendChild(statusWrap);
      }
 
      const techRow = document.createElement("div");
      techRow.className = "grid2";
      techRow.style.marginTop = "10px";
      techRow.innerHTML = `
        <div><div class="label">Technician Name</div><select class="input" id="ef_tech"></select></div>
        <div><div class="label">Door Type</div><select class="input" id="ef_door_type"></select></div>
      `;
 
      const techSel = techRow.querySelector("#ef_tech");
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "-- Select Technician --";
      techSel.appendChild(empty);
      employees.forEach(e => {
        const opt = document.createElement("option");
        opt.value = e.name;
        opt.textContent = e.name;
        techSel.appendChild(opt);
      });
      techSel.value = f.technician_name || "";
 
      const doorSel = techRow.querySelector("#ef_door_type");
      const doorBlank = document.createElement("option");
      doorBlank.value = "";
      doorBlank.textContent = "-- Select Door Type --";
      doorSel.appendChild(doorBlank);
      DOOR_TYPES.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        doorSel.appendChild(opt);
      });
      doorSel.value = f.door_type || "";
 
      const locRow = document.createElement("div");
      locRow.style.marginTop = "10px";
      locRow.innerHTML = `
        <div class="label">Door Location</div>
        <input class="input" id="ef_door_loc" />
      `;
      locRow.querySelector("#ef_door_loc").value = f.door_location || "";
 
      card.appendChild(techRow);
      card.appendChild(locRow);

      const editTimeClockRow = document.createElement("div");
      editTimeClockRow.className = "grid2";
      editTimeClockRow.style.marginTop = "10px";
      editTimeClockRow.innerHTML = `
        <div><div class="label">Time In</div><input class="input" id="ef_time_in" type="time" /></div>
        <div><div class="label">Time Out</div><input class="input" id="ef_time_out" type="time" /></div>
      `;
      editTimeClockRow.querySelector("#ef_time_in").value = f.time_in || "";
      editTimeClockRow.querySelector("#ef_time_out").value = f.time_out || "";
      card.appendChild(editTimeClockRow);

      const calculateEditOnsiteHours = (timeIn, timeOut) => {
        const parseMinutes = (value) => {
          const parts = String(value || "").split(":");
          if (parts.length !== 2) return null;
          const h = Number(parts[0]);
          const m = Number(parts[1]);
          if (!Number.isFinite(h) || !Number.isFinite(m)) return null;
          return (h * 60) + m;
        };
        const start = parseMinutes(timeIn);
        let end = parseMinutes(timeOut);
        if (start === null || end === null) return null;
        if (end <= start) end += 24 * 60;
        return Math.max(0, Math.round(((end - start) / 60) * 2) / 2);
      };

      const updateRollupLunchVisibility = () => {
        const wrap = card.querySelector("#ef_rollup_lunch_wrap");
        if (!wrap) return;
        const isRollup = String(doorSel.value || "").toLowerCase() === "roll up";
        wrap.style.display = isRollup && !isSalesLead ? "block" : "none";
        if (!isRollup) {
          const sel = card.querySelector("#ef_rollup_lunch");
          if (sel) sel.value = "";
        }
      };
      doorSel.addEventListener("change", updateRollupLunchVisibility);
 
      let techNotes = null;
      let partsUsed = null;
      let addRecs = null;
      let timeInput = null;
      let recs = null;
      let partsReq = null;
      let timeReq = null;
      let ready = null;
 
      if (isSalesLead) {
        const block = document.createElement("div");
        block.style.marginTop = "10px";
        block.innerHTML = `
          <div class="label">Recommendations</div>
          <textarea id="ef_recs"></textarea>
          <div class="grid2" style="margin-top:10px;">
            <div><div class="label">Parts Required</div><textarea id="ef_parts_req"></textarea></div>
            <div><div class="label">Time Required</div><input class="input" id="ef_time_req" /></div>
          </div>
          <label style="display:flex; align-items:center; gap:8px; margin-top:12px; font-weight:1000;">
            <input type="checkbox" id="ef_ready" /> Ready to Quote
          </label>
        `;
        recs = block.querySelector("#ef_recs");
        partsReq = block.querySelector("#ef_parts_req");
        timeReq = block.querySelector("#ef_time_req");
        ready = block.querySelector("#ef_ready");
 
        recs.value = f.recommendations || "";
        partsReq.value = f.parts_required || "";
        timeReq.value = f.time_required || "";
        ready.checked = !!f.ready_to_quote;
 
        card.appendChild(block);
      } else {
        const block = document.createElement("div");
        block.style.marginTop = "10px";
        block.innerHTML = `
          <div><div class="label">Time Onsite (hours)</div><input class="input" id="ef_time" type="number" step="0.5" min="0" /></div>
          <div class="hint">For newer forms, Time Onsite is calculated from Time In and Time Out. Older forms without those times keep their saved Time Onsite.</div>
          <div id="ef_rollup_lunch_wrap" style="display:none; margin-top:10px;">
            <div class="label">Lunch Taken While Working Roll Up?</div>
            <select class="input" id="ef_rollup_lunch"><option value="">-- Select Yes or No --</option><option value="yes">Yes</option><option value="no">No</option></select>
          </div>
          <div style="margin-top:10px;"><div class="label">Tech Notes</div><textarea id="ef_tech_notes"></textarea></div>
          <div class="grid2" style="margin-top:10px;">
            <div><div class="label">Parts Used</div><textarea id="ef_parts"></textarea></div>
            <div><div class="label">Additional Recommendations</div><textarea id="ef_add_recs"></textarea></div>
          </div>
        `;
        timeInput = block.querySelector("#ef_time");
        techNotes = block.querySelector("#ef_tech_notes");
        partsUsed = block.querySelector("#ef_parts");
        addRecs = block.querySelector("#ef_add_recs");
        const lunchSelect = block.querySelector("#ef_rollup_lunch");
 
        timeInput.value = typeof f.time_onsite_hours === "number" ? String(f.time_onsite_hours) : "";
        techNotes.value = f.tech_notes || "";
        partsUsed.value = f.parts_used || "";
        addRecs.value = f.additional_recommendations || "";
        if (lunchSelect) {
          if (f.rollup_includes_lunch === true) lunchSelect.value = "yes";
          else if (f.rollup_includes_lunch === false) lunchSelect.value = "no";
          else lunchSelect.value = "";
        }
 
        card.appendChild(block);
      }
      const syncEditTimeOnsite = () => {
        if (isSalesLead || !timeInput) return;
        const timeIn = card.querySelector("#ef_time_in")?.value || "";
        const timeOut = card.querySelector("#ef_time_out")?.value || "";
        if (!timeIn || !timeOut) return;
        const hours = calculateEditOnsiteHours(timeIn, timeOut);
        if (hours !== null) timeInput.value = String(hours);
      };
      card.querySelector("#ef_time_in")?.addEventListener("change", syncEditTimeOnsite);
      card.querySelector("#ef_time_out")?.addEventListener("change", syncEditTimeOnsite);
      syncEditTimeOnsite();
      updateRollupLunchVisibility();
 
      // Existing saved forms use a separate editor from new forms.
      // Give both workflows the same attachment and save-review controls.
      const editExtras = document.createElement("div");
      editExtras.style.cssText = "margin-top:12px;padding:12px;border:1px solid #cbd5e1;border-radius:8px";
      editExtras.innerHTML = `<div class="label">Add Photos / Files (optional)</div>
        <input class="input" type="file" id="ef_files" multiple accept="image/*,application/pdf" />
        <div class="hint">New uploads are attached to this saved form.</div>
        <div class="label" style="margin-top:12px">Before Saving</div>
        <label style="display:block"><input type="checkbox" id="ef_confirm_review" /> I uploaded the relevant images and documents.</label>
        <label style="display:block"><input type="checkbox" id="ef_confirm_signoff" /> Sign-off completed, or not applicable.</label>
        <label style="display:block"><input type="checkbox" id="ef_confirm_checkin" /> Check-in / check-out completed, or not applicable.</label>`;
      card.appendChild(editExtras);

      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "12px";
 
      const save = document.createElement("button");
      save.className = "btn btn-orange";
      save.textContent = "Save Changes";
 
      const cancel = document.createElement("button");
      cancel.className = "btn";
      cancel.textContent = "Cancel";
 
      const del = document.createElement("button");
      del.className = "btn";
      del.textContent = "Delete Form";
      del.style.borderColor = "#fecaca";
      del.style.color = "#b91c1c";
 
      actions.appendChild(save);
      actions.appendChild(cancel);
      actions.appendChild(del);
      card.appendChild(actions);
 
      drawerBody.appendChild(card);
 
      cancel.addEventListener("click", () => overlay.remove());
 
      del.addEventListener("click", async () => {
        if (!confirm("Delete this saved form?")) return;
        try {
          const updatedForms = [...formsOf(job)];
          updatedForms.splice(formIndex, 1);
          const updatedJob = await apiReplaceCompletionForms(job.id, updatedForms);
          overlay.remove();
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updatedJob, ctx);
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
 
      save.addEventListener("click", async () => {
        try {
          const updatedForms = [...formsOf(job)];
          const next = { ...updatedForms[formIndex] };
 
          next.date = card.querySelector("#ef_date")?.value || next.date || new Date().toISOString().slice(0,10);
          next.technician_name = techSel.value;
          if (!doorSel.value.trim()) { alert("Door type is required"); return; }
          next.door_type = doorSel.value;
          next.door_location = locRow.querySelector("#ef_door_loc").value.trim();
          const editTimeIn = card.querySelector("#ef_time_in")?.value || "";
          const editTimeOut = card.querySelector("#ef_time_out")?.value || "";
          if (editTimeIn || editTimeOut) {
            if (!editTimeIn || !editTimeOut) { alert("Enter both Time In and Time Out, or leave both blank for an older form."); return; }
            next.time_in = editTimeIn;
            next.time_out = editTimeOut;
          }
 
          if (!doorSel.value) throw new Error("Door type is required.");

          if (stSel && stSel.value === "Parts on Order") {
            const supplier = prompt("Supplier:", job.parts_order?.supplier || "") || "";
            const poNumber = prompt("PO #:", job.parts_order?.po_number || job.po_number || "") || "";
            const orderDate = prompt("Order Date (YYYY-MM-DD):", job.parts_order?.order_date || "") || "";
            const etaDate = prompt("Expected Arrival Date (YYYY-MM-DD):", job.parts_order?.expected_arrival_date || "") || "";
            const notesVal = prompt("Notes:", job.parts_order?.notes || "") || "";
            next.parts_order = { supplier, po_number: poNumber, order_date: orderDate, expected_arrival_date: etaDate, notes: notesVal };
          }

          if (isSalesLead) {
            next.recommendations = recs.value.trim();
            next.parts_required = partsReq.value.trim();
            next.time_required = timeReq.value.trim();
            next.ready_to_quote = !!ready.checked;
          } else {
            next.status_update = stSel ? stSel.value : next.status_update;
            const editCalculatedHours = (editTimeIn && editTimeOut) ? calculateEditOnsiteHours(editTimeIn, editTimeOut) : null;
            next.time_onsite_hours = editCalculatedHours !== null ? editCalculatedHours : (timeInput.value.trim() === "" ? null : Number(timeInput.value.trim()));
            if (String(doorSel.value || "").toLowerCase() === "roll up") {
              const lunchVal = card.querySelector("#ef_rollup_lunch")?.value || "";
              if (!lunchVal) { alert("Please select Yes or No for lunch taken while working roll up."); card.querySelector("#ef_rollup_lunch")?.focus(); return; }
              next.rollup_includes_lunch = lunchVal === "yes";
            } else {
              next.rollup_includes_lunch = false;
            }
            next.tech_notes = techNotes.value.trim();
            next.parts_used = partsUsed.value.trim();
            next.additional_recommendations = addRecs.value.trim();
          }
 
          if (!["ef_confirm_review", "ef_confirm_signoff", "ef_confirm_checkin"].every(id => card.querySelector(`#${id}`)?.checked)) {
            alert("Please complete the save confirmation checklist.");
            return;
          }
          const editFiles = Array.from(card.querySelector("#ef_files")?.files || []);
          updatedForms[formIndex] = next;
          const updatedJob = await apiReplaceCompletionForms(job.id, updatedForms);
          if (editFiles.length) {
            const saved = formsOf(updatedJob)[formIndex];
            const formId = saved?.id || next.id || f.id;
            if (!formId) {
              alert("Form changes saved, but an attachment ID was not returned. No files were uploaded.");
            } else {
              try { await apiUploadCompletionAttachments(job.id, formId, editFiles); }
              catch (uploadError) { alert(`Form saved, but attachment upload failed: ${uploadError.message || uploadError}`); }
            }
          }
 
          overlay.remove();
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updatedJob, ctx);
        } catch (e) {
          alert(e.message || String(e));
        }
      });
    });
  }
 
  function renderDocumentsSection(job) {
    const wrap = document.createElement("div");
    wrap.style.marginTop = "10px";
 
    const title = document.createElement("div");
    title.className = "label";
    title.textContent = "Saved Estimate / Invoice Documents";
    wrap.appendChild(title);
 
    const loading = document.createElement("div");
    loading.className = "hint";
    loading.style.marginTop = "6px";
    loading.textContent = "Loading documents...";
    wrap.appendChild(loading);
 
    apiListDocuments({ job_id: job.id }).then(items => {
      wrap.innerHTML = "";
      wrap.appendChild(title);
      if (!items.length) {
        const empty = document.createElement("div");
        empty.className = "hint";
        empty.style.marginTop = "6px";
        empty.textContent = "No saved estimate/invoice documents yet.";
        wrap.appendChild(empty);
        return;
      }
      const box = document.createElement("div");
      box.style.display = "grid";
      box.style.gap = "8px";
      box.style.marginTop = "8px";
      items.forEach(doc => {
        const row = document.createElement("div");
        row.className = "jobrow";
        const top = document.createElement("div");
        top.className = "jobrow-top";
        const name = document.createElement("div");
        name.className = "jobrow-name";
        name.textContent = `${doc.type === "invoice" ? "Invoice" : "Estimate"} ${doc.number || ""}`.trim();
        top.appendChild(name);
        if (doc.type) top.appendChild(statusPill(doc.type === "invoice" ? "Done" : "Quote Sent"));
        const sub = document.createElement("div");
        sub.className = "jobrow-addr";
        sub.textContent = [doc.customer || "", formatStamp(doc.created_at || "")].filter(Boolean).join(" - ");
        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "8px";
        const openLink = document.createElement("a");
        openLink.href = doc.download_url || "#";
        openLink.target = "_blank";
        openLink.rel = "noopener noreferrer";
        openLink.textContent = "Open PDF";
        styleActionButton(openLink, "blue", true);
        actions.appendChild(openLink);
        const emailBtn = document.createElement("button");
        emailBtn.type = "button";
        emailBtn.textContent = "Email";
        styleActionButton(emailBtn, "green", true);
        emailBtn.addEventListener("click", () => {
          openEstimateInvoiceEmail({
            ...doc,
            email: job && job.email ? job.email : (doc.email || ""),
            job_number: doc.job_number || (job && job.job_number) || "",
            po_number: doc.po_number || (job && job.po_number) || "",
            invoice_number: doc.type === "invoice" ? (doc.number || doc.invoice_number || "") : (doc.invoice_number || ""),
            estimate_number: doc.type === "estimate" ? (doc.number || doc.estimate_number || "") : (doc.estimate_number || ""),
          }, doc.type || "invoice");
        });
        actions.appendChild(emailBtn);
        row.appendChild(top);
        row.appendChild(sub);
        row.appendChild(actions);
        box.appendChild(row);
      });
      wrap.appendChild(box);
    }).catch(() => {
      loading.textContent = "Unable to load saved documents.";
    });
 
    return wrap;
  }
 
  function renderSavedForms(job, container, ctx) {
    const wrap = document.createElement("div");
    wrap.className = "form-summary";
 
    const title = document.createElement("div");
    title.className = "label";
    title.textContent = "Saved Forms";
    wrap.appendChild(title);
 
    const forms = formsOf(job);
    if (!forms.length) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "No saved completion/recommendation forms yet.";
      wrap.appendChild(empty);
      return wrap;
    }
 
    forms.forEach((f, idx) => {
      const item = document.createElement("div");
      item.className = "form-summary-item";
 
      const top = document.createElement("div");
      top.className = "jobrow-top";
 
      const left = document.createElement("div");
      left.className = "jobrow-name";
      left.textContent = `${job.kind === "sales_lead" ? "Recommendation" : "Completion"} Form #${idx + 1}`;
 
      top.appendChild(left);
      if (f.status_update) top.appendChild(statusPill(f.status_update));
 
      const body = document.createElement("div");
      body.className = "jobrow-addr";
      body.style.whiteSpace = "pre-wrap";
 
      const lines = [];
      if (f.date || f.created_at) lines.push(`Date: ${formatFormDate(f.date || f.created_at)}`);
      if (f.technician_name) lines.push(`Tech: ${f.technician_name}`);
      if (f.door_type) lines.push(`Door Type: ${f.door_type}`);
      if (f.door_location) lines.push(`Door Location: ${f.door_location}`);
      if (f.time_in) lines.push(`Time In: ${formatTime12(f.time_in)}`);
      if (f.time_out) lines.push(`Time Out: ${formatTime12(f.time_out)}`);
      if (typeof f.time_onsite_hours === "number") lines.push(`Time: ${f.time_onsite_hours} hrs`);
      if (f.tech_notes) lines.push(`Tech Notes: ${f.tech_notes}`);
      if (f.recommendations) lines.push(`Recommendations: ${f.recommendations}`);
      if (f.parts_used) lines.push(`Parts Used: ${f.parts_used}`);
      if (f.parts_required) lines.push(`Parts Required: ${f.parts_required}`);
      if (f.additional_recommendations) lines.push(`Additional Recommendations: ${f.additional_recommendations}`);
      if (f.time_required) lines.push(`Time Required: ${f.time_required}`);
      if (f.ready_to_quote) lines.push(`Ready to Quote: Yes`);
      body.textContent = lines.join("\n");
 
      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "8px";
      actions.style.flexWrap = "wrap";
 
      const editBtn = document.createElement("button");
      editBtn.className = "btn";
      editBtn.textContent = "Edit Form";
      editBtn.addEventListener("click", () => openEditSavedForm(job, idx, container, ctx));
 
      const uploadLabel = makeUploadLabel("Upload", "ghost", false);
      const uploadInput = document.createElement("input");
      uploadInput.type = "file";
      uploadInput.multiple = true;
      uploadInput.style.display = "none";
      uploadLabel.appendChild(uploadInput);
      uploadInput.addEventListener("change", async () => {
        try {
          if (!uploadInput.files || !uploadInput.files.length) return;
          await apiUploadCompletionAttachments(job.id, f.id, uploadInput.files);
          const updatedJob = await apiGetJob(job.id);
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updatedJob, ctx);
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        } finally {
          uploadInput.value = "";
        }
      });
 
      actions.appendChild(editBtn);
      actions.appendChild(uploadLabel);
 
      item.appendChild(top);
      item.appendChild(body);
      item.appendChild(actions);
      item.appendChild(renderAttachmentSection("Form Attachments", f.attachments || [], {
        urlBuilder: (file) => buildCompletionAttachmentUrl(job.id, f.id, file.filename),
      }));
      wrap.appendChild(item);
    });
 
    return wrap;
  }
 

  async function promptUpdateQuoteTracking(job, refreshFn) {
    const assigned = prompt("Who is working on this quote?", job.quote_assigned_to || "");
    if (assigned === null) return;
    const sentQuote = prompt("Sent estimate number:", job.sent_quote_number || "");
    if (sentQuote === null) return;
    try {
      const updated = await apiUpdateJob(job.id, {
        quote_assigned_to: String(assigned || "").trim(),
        sent_quote_number: String(sentQuote || "").trim(),
      });
      showDoorksToast("Quote tracking saved ✓");
      if (refreshFn) await refreshFn();
      if (!refreshFn && currentView && currentView.refresh) await currentView.refresh();
      return updated;
    } catch (e) { alert(e.message || String(e)); }
  }

  function openFollowUpJobFromQuote(originalJob, container, ctx = {}) {
    openDrawer("Create Follow-Up Job", async (drawerBody, overlay) => {
      const card = document.createElement("div");
      card.className = "card";
      const latestRec = (Array.isArray(originalJob.completion_forms) ? originalJob.completion_forms : []).slice().reverse().find(f => f && (f.recommendations || f.additional_recommendations || f.parts_required));
      const recText = latestRec ? [latestRec.recommendations || latestRec.additional_recommendations || "", latestRec.parts_required ? `Parts Required: ${latestRec.parts_required}` : "", latestRec.time_required ? `Time Required: ${latestRec.time_required}` : ""].filter(Boolean).join("\n") : "";
      card.innerHTML = `
        <h3 style="margin:0;">Create Follow-Up Job</h3>
        <div class="hint" style="margin-top:6px;">Creates a new dispatch from this sent quote and moves the original job to Done.</div>
        <div class="grid2" style="margin-top:12px;">
          <div><div class="label">Date</div><input class="input" id="fq_date" type="date" value="${new Date().toISOString().slice(0,10)}" /></div>
          <div><div class="label">Job #</div><input class="input" id="fq_job" placeholder="Required" /></div>
          <div><div class="label">Customer</div><input class="input" id="fq_customer" value="${escapeHtml(originalJob.customer || "")}" /></div>
          <div><div class="label">Address</div><input class="input" id="fq_address" value="${escapeHtml(originalJob.address || "")}" /></div>
          <div><div class="label">Contact</div><input class="input" id="fq_contact" value="${escapeHtml(originalJob.contact || "")}" /></div>
          <div><div class="label">Phone</div><input class="input" id="fq_phone" value="${escapeHtml(originalJob.phone || "")}" /></div>
          <div><div class="label">Email</div><input class="input" id="fq_email" value="${escapeHtml(originalJob.email || "")}" /></div>
          <div><div class="label">PO #</div><input class="input" id="fq_po" value="${escapeHtml(originalJob.po_number || "")}" /></div>
          <div><div class="label">Estimate #</div><input class="input" id="fq_est" value="${escapeHtml(originalJob.sent_quote_number || "")}" /></div>
          <div><div class="label">Original Job #</div><input class="input" id="fq_parent" value="${escapeHtml(originalJob.job_number || "")}" disabled /></div>
        </div>
        <div style="margin-top:12px;"><div class="label">Job Notes</div><textarea id="fq_notes" style="min-height:120px;">${escapeHtml([`Follow-up dispatch created from quote sent on job #${originalJob.job_number || ""}.`, recText].filter(Boolean).join("\n\n"))}</textarea></div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:12px;"><button class="btn btn-orange" id="fq_save">Create Job + Move Original to Done</button><button class="btn" id="fq_cancel">Cancel</button></div>
      `;
      drawerBody.appendChild(card);
      card.querySelector("#fq_cancel").addEventListener("click", () => overlay.remove());
      card.querySelector("#fq_save").addEventListener("click", async () => {
        const jobNumber = card.querySelector("#fq_job").value.trim();
        if (!jobNumber) { alert("Job # is required."); card.querySelector("#fq_job").focus(); return; }
        try {
          const created = await apiCreateJob({
            kind: "dispatch", status: "Dispatch", date: card.querySelector("#fq_date").value, job_number: jobNumber,
            customer: card.querySelector("#fq_customer").value.trim(), address: card.querySelector("#fq_address").value.trim(),
            contact: card.querySelector("#fq_contact").value.trim(), phone: card.querySelector("#fq_phone").value.trim(), email: card.querySelector("#fq_email").value.trim(),
            po_number: card.querySelector("#fq_po").value.trim(), estimate_number: card.querySelector("#fq_est").value.trim(),
            job_notes: card.querySelector("#fq_notes").value.trim(), office_notes: `Created from original job #${originalJob.job_number || ""}`,
            source_job_id: originalJob.id || "", source_job_number: originalJob.job_number || "",
          });
          await apiUpdateJob(originalJob.id, { status: "Done", followup_job_id: created.id || "", followup_job_number: created.job_number || jobNumber });
          overlay.remove(); showDoorksToast("Follow-up job created ✓");
          if (ctx && ctx.afterSave) await ctx.afterSave();
          if (container) renderJobDetails(container, created, ctx);
          refreshBadges();
        } catch (e) { alert(e.message || String(e)); }
      });
    });
  }

  function renderJobDetails(container, job, ctx) {
    container.innerHTML = "";
 
    const card = document.createElement("div");
    card.className = "card";
 
    const header = document.createElement("div");
    header.style.display = "flex";
    header.style.justifyContent = "space-between";
    header.style.alignItems = "center";
    header.style.gap = "10px";
 
    const left = document.createElement("div");
    const idLabel = job.kind === "sales_lead" ? "Sales Lead #" : "Job #";
    left.innerHTML = `
      <h3 style="margin:0;">${job.customer || `${idLabel}${job.job_number || ""}`}</h3>
      <div class="hint" style="margin-top:4px;"><b>${idLabel}${job.job_number || ""}</b> - ${mmDdYy(job.date)}</div>
    `;
 
    const right = document.createElement("div");
    right.appendChild(statusPill(job.status));
 
    header.appendChild(left);
    header.appendChild(right);
 
    const fields = document.createElement("div");
    fields.className = "grid2";
    fields.style.marginTop = "10px";
    fields.innerHTML = `
      <div><div class="label">${job.kind === "sales_lead" ? "Sales Lead #" : "Job #"}</div><div class="field">${job.job_number || ""}</div></div>
      <div><div class="label">Address</div><div class="field">${job.address || ""}</div></div>
      <div><div class="label">Contact</div><div class="field">${job.contact || ""}</div></div>
      <div><div class="label">Phone</div><div class="field">${job.phone || ""}</div></div>
      <div><div class="label">Email</div><div class="field">${job.email || ""}</div></div>
      <div><div class="label">PO #</div><div class="field">${job.po_number || ""}</div></div>
      <div><div class="label">Estimate #</div><div class="field">${job.estimate_number || ""}</div></div>
      <div><div class="label">Sent Estimate #</div><div class="field">${job.sent_quote_number || ""}</div></div>
      <div><div class="label">Quote Assigned To</div><div class="field">${job.quote_assigned_to || ""}</div></div>
      <div><div class="label">Invoice #</div><div class="field">${job.invoice_number || ""}</div></div>
    `;
 
    const officeNotes = document.createElement("div");
    officeNotes.style.marginTop = "10px";
    officeNotes.innerHTML = `<div class="label">Office Notes</div><div class="field" style="white-space:pre-wrap;">${job.office_notes || ""}</div>`;
 
    const notes = document.createElement("div");
    notes.style.marginTop = "10px";
    notes.innerHTML = `<div class="label">Job Notes</div><div class="field" style="white-space:pre-wrap;">${job.job_notes || ""}</div>`;

    const audit = document.createElement("div");
    audit.style.marginTop = "12px";
    const createdBy = String(job.created_by || "").trim();
    const modifiedBy = String(job.last_modified_by || "").trim();
    const createdStamp = createdBy ? formatStamp(job.created_at) : "";
    const modifiedStamp = modifiedBy ? formatStamp(job.last_modified_at || job.updated_at) : "";
    if (createdBy || modifiedBy) {
      audit.innerHTML = `
        <div class="label">Record History</div>
        <div class="grid2" style="margin-top:6px;">
          <div><div class="label">Created By</div><div class="field">${escapeHtml(createdBy || "—")}</div></div>
          <div><div class="label">Created</div><div class="field">${escapeHtml(createdStamp || "—")}</div></div>
          <div><div class="label">Last Modified By</div><div class="field">${escapeHtml(modifiedBy || createdBy || "—")}</div></div>
          <div><div class="label">Last Modified</div><div class="field">${escapeHtml(modifiedStamp || createdStamp || "—")}</div></div>
        </div>`;
    }
 
    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.flexDirection = "column";
    actions.style.alignItems = "flex-start";
    actions.style.gap = "8px";
    actions.style.marginTop = "12px";
 
    const primaryActions = document.createElement("div");
    primaryActions.style.display = "flex";
    primaryActions.style.gap = "8px";
    primaryActions.style.flexWrap = "wrap";
 
    const secondaryActions = document.createElement("div");
    secondaryActions.style.display = "flex";
    secondaryActions.style.gap = "8px";
    secondaryActions.style.flexWrap = "wrap";
 
    const btnEdit = document.createElement("button");
    btnEdit.className = "btn btn-orange";
    btnEdit.textContent = "Edit";
    primaryActions.appendChild(btnEdit);
 
    const btnForm = document.createElement("button");
    styleActionButton(btnForm, "green", false);
    btnForm.textContent = (job.kind === "sales_lead") ? "Recommendation Form" : "Completion Form";
    primaryActions.appendChild(btnForm);
 
    const jobUploadLabel = makeUploadLabel("Upload", "blue", true);
    const jobUploadInput = document.createElement("input");
    jobUploadInput.type = "file";
    jobUploadInput.multiple = true;
    jobUploadInput.style.display = "none";
    jobUploadLabel.appendChild(jobUploadInput);
    jobUploadInput.addEventListener("change", async () => {
      try {
        if (!jobUploadInput.files || !jobUploadInput.files.length) return;
        await apiUploadJobAttachments(job.id, jobUploadInput.files);
        const updatedJob = await apiGetJob(job.id);
        if (ctx && ctx.afterSave) await ctx.afterSave();
        renderJobDetails(container, updatedJob, ctx);
        refreshBadges();
      } catch (e) {
        alert(e.message || String(e));
      } finally {
        jobUploadInput.value = "";
      }
    });
    secondaryActions.appendChild(jobUploadLabel);
 
    if (job.kind === "sales_lead") {
      const canTurnToJob = !!(currentUser && ["office", "office_admin", "admin"].includes(String(currentUser.role || "")));
      if (canTurnToJob) {
        const btnTurnToJob = document.createElement("button");
        btnTurnToJob.className = "btn";
        btnTurnToJob.textContent = "Turn to Job";
        btnTurnToJob.addEventListener("click", async () => {
          try {
            const manualJobNumber = prompt("Enter Job # for this dispatch:");
            if (manualJobNumber === null) return;
            const cleanJobNumber = String(manualJobNumber || "").trim();
            if (!cleanJobNumber) {
              alert("Job # is required to turn a sales lead into a dispatch.");
              return;
            }
            if (!confirm(`Turn this Sales Lead into Dispatch Job #${cleanJobNumber}?`)) return;
            const updated = await apiUpdateJob(job.id, {
              kind: "dispatch",
              status: "Dispatch",
              job_number: cleanJobNumber
            });
            renderJobDetails(container, updated, ctx);
            if (ctx && ctx.afterSave) await ctx.afterSave();
            refreshBadges();
          } catch (e) {
            alert(e.message || String(e));
          }
        });
        primaryActions.appendChild(btnTurnToJob);
      }

      if (String(job.status || "") === "Quote Sent") {
        const btnPartsOnOrder = document.createElement("button");
        btnPartsOnOrder.className = "btn";
        btnPartsOnOrder.textContent = "Parts on Order";
        btnPartsOnOrder.addEventListener("click", async () => {
          try {
            const updated = await apiUpdateJob(job.id, {
              kind: "dispatch",
              status: "Parts on Order"
            });
            renderJobDetails(container, updated, ctx);
            if (ctx && ctx.afterSave) await ctx.afterSave();
            refreshBadges();
          } catch (e) {
            alert(e.message || String(e));
          }
        });
        primaryActions.appendChild(btnPartsOnOrder);
      }
    }
 
    if (shouldShowEstimate(job)) {
      const b = document.createElement("button");
      styleActionButton(b, "blue", true);
      b.textContent = "Estimate";
      b.addEventListener("click", () => openEstimateDrawer(job, container, ctx));
      secondaryActions.appendChild(b);
    }
 
    if (shouldShowInvoice(job)) {
      const b = document.createElement("button");
      styleActionButton(b, "blue", true);
      b.textContent = "Invoice";
      b.addEventListener("click", () => openInvoiceDrawer(job, container, ctx));
      secondaryActions.appendChild(b);
    }
 

    if (["Quote", "Complete/Quote"].includes(String(job.status || ""))) {
      const qt = document.createElement("button");
      qt.className = "btn";
      qt.textContent = "Edit";
      qt.addEventListener("click", () => promptUpdateQuoteTracking(job, async () => {
        const updated = await apiGetJob(job.id);
        renderJobDetails(container, updated, ctx);
        if (ctx && ctx.afterSave) await ctx.afterSave();
      }));
      primaryActions.appendChild(qt);
    }

    if (String(job.status || "") === "Quote Sent") {
      const follow = document.createElement("button");
      follow.className = "btn btn-orange";
      follow.textContent = "Create Follow-Up Job";
      follow.addEventListener("click", () => openFollowUpJobFromQuote(job, container, ctx));
      primaryActions.appendChild(follow);
    }

    actions.appendChild(primaryActions);
    if (secondaryActions.childNodes.length) actions.appendChild(secondaryActions);
 
    card.appendChild(header);
    card.appendChild(fields);
    card.appendChild(officeNotes);
    if (job.parts_order && Object.values(job.parts_order).some(v => String(v || "").trim())) {
      const poCard = document.createElement("div");
      poCard.style.marginTop = "10px";
      poCard.innerHTML = `<div class="label">Parts on Order</div><div class="field" style="white-space:pre-wrap;">Supplier: ${job.parts_order.supplier || ""}
PO #: ${job.parts_order.po_number || ""}
Order Date: ${job.parts_order.order_date || ""}
Expected Arrival: ${job.parts_order.expected_arrival_date || ""}
Notes: ${job.parts_order.notes || ""}</div>`;
      card.appendChild(poCard);
    }
    card.appendChild(notes);
    if (createdBy || modifiedBy) card.appendChild(audit);
    card.appendChild(actions);
    card.appendChild(renderAttachmentSection(job.kind === "sales_lead" ? "Lead Attachments" : "Job Attachments", job.attachments || [], {
      urlBuilder: (file) => buildJobAttachmentUrl(job.id, file.filename),
    }));
    card.appendChild(renderDocumentsSection(job));
    card.appendChild(renderSavedForms(job, container, ctx));
 
    container.appendChild(card);
 
    btnEdit.addEventListener("click", () => openEditJob(job, container, ctx));
    btnForm.addEventListener("click", async () => {
      if (job.kind === "dispatch") {
        const nextStatus = await promptDispatchStatus();
        if (!nextStatus) return;
        const updated = await apiUpdateJob(job.id, { status: nextStatus });
        renderJobDetails(container, updated, ctx);
        await openCompletionOrRecommendation(updated, container, ctx);
      } else {
        await openCompletionOrRecommendation(job, container, ctx);
      }
    });
  }
 
  function openEditJob(job, container, ctx) {
    openDrawer("Edit Job", async (drawerBody, overlay) => {
      const customers = await apiListCustomers().catch(() => []);
      const contacts = await apiListContacts().catch(() => []);
      const knownAddresses = await apiListAddresses({ limit: 1500 }).catch(() => []);
 
      const customerListId = `cust-${Math.random().toString(36).slice(2)}`;
      const contactListId = `cont-${Math.random().toString(36).slice(2)}`;
 
      drawerBody.innerHTML = "";
      const card = document.createElement("div");
      card.className = "card";
 
      const row0 = document.createElement("div");
      row0.className = "grid2";
      row0.innerHTML = `
        <div><div class="label">Status</div><select class="input" id="ej_status"></select></div>
        <div><div class="label">Date</div><input class="input" id="ej_date" type="date" /></div>
      `;
 
      const stSel = row0.querySelector("#ej_status");
      STATUSES.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = s;
        stSel.appendChild(opt);
      });
      stSel.value = job.status || (job.kind === "sales_lead" ? "Sales Lead" : "Dispatch");
      row0.querySelector("#ej_date").value = job.date;
 
      const rowJob = document.createElement("div");
      rowJob.className = "grid2";
      rowJob.innerHTML = `
        <div><div class="label">${job.kind === "sales_lead" ? "Sales Lead #" : "Job #"}</div><input class="input" id="ej_job_number" /></div>
        <div><div class="label">Customer</div><input class="input" id="ej_customer" list="${customerListId}" /></div>
      `;
      rowJob.querySelector("#ej_job_number").value = job.job_number || "";
      rowJob.querySelector("#ej_customer").value = job.customer || "";
 
      const row1 = document.createElement("div");
      row1.className = "grid2";
      row1.innerHTML = `
        <div><div class="label">Address</div><input class="input" id="ej_address" /></div>
        <div><div class="label">Contact</div><input class="input" id="ej_contact" list="${contactListId}" /></div>
      `;
      row1.querySelector("#ej_address").value = job.address || "";
      row1.querySelector("#ej_contact").value = job.contact || "";
 
      const row2 = document.createElement("div");
      row2.className = "grid2";
      row2.innerHTML = `
        <div><div class="label">Phone</div><input class="input" id="ej_phone" /></div>
        <div><div class="label">Email</div><input class="input" id="ej_email" /></div>
      `;
      row2.querySelector("#ej_phone").value = job.phone || "";
      row2.querySelector("#ej_email").value = job.email || "";
 
      const row3 = document.createElement("div");
      row3.className = "grid2";
      row3.innerHTML = `
        <div><div class="label">PO #</div><input class="input" id="ej_po" /></div>
        <div><div class="label">Estimate #</div><input class="input" id="ej_est" /></div>
      `;
      row3.querySelector("#ej_po").value = job.po_number || "";
      row3.querySelector("#ej_est").value = job.estimate_number || "";
 
      const row4 = document.createElement("div");
      row4.className = "grid2";
      row4.innerHTML = `
        <div><div class="label">Invoice #</div><input class="input" id="ej_inv" /></div>
        <div><div class="label">Office Notes</div><input class="input" id="ej_office_notes" /></div>
      `;
      row4.querySelector("#ej_inv").value = job.invoice_number || "";
      row4.querySelector("#ej_office_notes").value = job.office_notes || "";

      const rowQuote = document.createElement("div");
      rowQuote.className = "grid2";
      rowQuote.innerHTML = `
        <div><div class="label">Quote Assigned To</div><input class="input" id="ej_quote_assigned" /></div>
        <div><div class="label">Sent Estimate #</div><input class="input" id="ej_sent_quote" /></div>
      `;
      rowQuote.querySelector("#ej_quote_assigned").value = job.quote_assigned_to || "";
      rowQuote.querySelector("#ej_sent_quote").value = job.sent_quote_number || "";
 
      const notes = document.createElement("div");
      notes.innerHTML = `<div class="label">Job Notes</div>`;
      const ta = document.createElement("textarea");
      ta.value = job.job_notes || "";
      notes.appendChild(ta);
 
      const addWrap = document.createElement("div");
      addWrap.className = "grid3";
      addWrap.style.marginTop = "12px";
      addWrap.style.display = "grid";
      addWrap.style.gridTemplateColumns = "repeat(auto-fit, minmax(160px, 1fr))";
      addWrap.style.gap = "10px";
      addWrap.innerHTML = `
        <div><button class="btn" id="ej_add_customer">Add Customer</button></div>
        <div><button class="btn" id="ej_add_address">Add Address</button></div>
        <div><button class="btn" id="ej_add_contact">Add Contact</button></div>
      `;
 
      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "10px";
      actions.style.flexWrap = "wrap";
 
      const btnSave = document.createElement("button");
      btnSave.className = "btn btn-orange";
      btnSave.textContent = "Save";
 
      const btnCancel = document.createElement("button");
      btnCancel.className = "btn";
      btnCancel.textContent = "Cancel";
 
      const btnDelete = document.createElement("button");
      btnDelete.className = "btn";
      btnDelete.textContent = "Delete";
      btnDelete.style.borderColor = "#fecaca";
      btnDelete.style.color = "#b91c1c";
 
      actions.appendChild(btnSave);
      actions.appendChild(btnCancel);
      actions.appendChild(btnDelete);
 
      card.appendChild(buildCustomerDatalist(customerListId, customers));
      card.appendChild(buildContactDatalist(contactListId, contacts));
      const editCustomerInput = rowJob.querySelector("#ej_customer");
      const editContactInput = row1.querySelector("#ej_contact");
      const editPhoneInput = row2.querySelector("#ej_phone");
      const editEmailInput = row2.querySelector("#ej_email");
      const editContactList = card.querySelector(`#${contactListId}`);
      let editLiveContacts = Array.isArray(contacts) ? [...contacts] : [];
      const renderEditContacts = () => {
        if (!editContactList) return;
        editContactList.innerHTML = editLiveContacts.map(c => `<option value="${escapeHtml(c.name || "")}" label="${escapeHtml(c.company_name ? `${c.name || ""}  -  ${c.company_name}` : (c.name || ""))}"></option>`).join("");
      };
      const refreshEditContacts = async (forceClear = false) => {
        const company = editCustomerInput.value.trim();
        const loaded = await apiListContacts(company ? { company_name: company } : {}).catch(() => contacts);
        editLiveContacts = Array.isArray(loaded) ? loaded.filter(c => {
          const cc = normalizeText(c.company_name || "");
          const selected = normalizeText(company);
          return selected ? (cc && cc === selected) : true;
        }) : [];
        renderEditContacts();
        const exact = editLiveContacts.find(c => normalizeText(c.name) === normalizeText(editContactInput.value));
        if (exact) {
          if (!String(editPhoneInput.value || "").trim()) editPhoneInput.value = pickContactPhone(exact) || "";
          if (!String(editEmailInput.value || "").trim()) editEmailInput.value = exact.email || "";
        }
        // Preserve manually entered contact/phone/email if this is not a saved CRM contact.
      };
      wireContactAutofill({
        contacts: editLiveContacts,
        customerInput: editCustomerInput,
        contactInput: editContactInput,
        phoneInput: editPhoneInput,
        emailInput: editEmailInput,
        contactListId,
      });
      ["change", "blur"].forEach(evt => editCustomerInput.addEventListener(evt, () => refreshEditContacts(true)));
      let editContactTimer = null;
      editCustomerInput.addEventListener("input", () => {
        clearTimeout(editContactTimer);
        editContactTimer = setTimeout(() => refreshEditContacts(false), 150);
      });
      refreshEditContacts(false);
      card.appendChild(row0);
      card.appendChild(rowJob);
      card.appendChild(row1);
      card.appendChild(row2);
      card.appendChild(row3);
      card.appendChild(row4);
      card.appendChild(rowQuote);
      card.appendChild(notes);
      card.appendChild(addWrap);
      card.appendChild(actions);
      drawerBody.appendChild(card);
 
      addWrap.querySelector("#ej_add_customer").addEventListener("click", async () => {
        const name = prompt("New customer company name:");
        if (!name) return;
        try {
          await apiCreateCustomer({ company_name: name.trim() });
          alert("Customer added.");
        } catch (e) {
          alert(e.message || String(e));
        }
      });
 
      const editAddAddressBtn = addWrap.querySelector("#ej_add_address");
      if (editAddAddressBtn) {
        editAddAddressBtn.addEventListener("click", async () => {
          const address = prompt("New job-site address:", row1.querySelector("#ej_address").value.trim());
          if (!address || !address.trim()) return;
          const customerName = prompt("Customer for this address:", editCustomerInput.value.trim());
          const label = prompt("Label / Location (optional):", "");
          const notes = prompt("Notes (optional):", "");
          try {
            const created = await apiCreateAddress({
              customer: (customerName || "").trim(),
              company_name: (customerName || "").trim(),
              address: address.trim(),
              label: (label || "").trim(),
              notes: (notes || "").trim(),
            });
            const item = created && created.item ? created.item : created;
            row1.querySelector("#ej_address").value = (item && item.address) || address.trim();
            if (editCustomerInput && customerName && !editCustomerInput.value.trim()) editCustomerInput.value = customerName.trim();
            alert("Address added.");
          } catch (e) {
            alert(e.message || String(e));
          }
        });
      }

      addWrap.querySelector("#ej_add_contact").addEventListener("click", async () => {
        const name = prompt("Contact name:");
        if (!name) return;
        try {
          await apiCreateContact({
            name: name.trim(),
            company_name: rowJob.querySelector("#ej_customer").value.trim(),
            phone_number: row2.querySelector("#ej_phone").value.trim(),
            email: row2.querySelector("#ej_email").value.trim(),
          });
          alert("Contact added.");
        } catch (e) {
          alert(e.message || String(e));
        }
      });
 
      btnCancel.addEventListener("click", () => overlay.remove());
 
      btnSave.addEventListener("click", async () => {
        try {
          const payload = {
            status: stSel.value,
            date: row0.querySelector("#ej_date").value,
            job_number: rowJob.querySelector("#ej_job_number").value.trim(),
            customer: rowJob.querySelector("#ej_customer").value.trim(),
            address: row1.querySelector("#ej_address").value.trim(),
            contact: row1.querySelector("#ej_contact").value.trim(),
            phone: row2.querySelector("#ej_phone").value.trim(),
            email: row2.querySelector("#ej_email").value.trim(),
            po_number: row3.querySelector("#ej_po").value.trim(),
            estimate_number: row3.querySelector("#ej_est").value.trim(),
            invoice_number: row4.querySelector("#ej_inv").value.trim(),
            office_notes: row4.querySelector("#ej_office_notes").value.trim(),
            job_notes: ta.value.trim(),
            quote_assigned_to: rowQuote.querySelector("#ej_quote_assigned").value.trim(),
            sent_quote_number: rowQuote.querySelector("#ej_sent_quote").value.trim(),
          };
          const updated = await apiUpdateJob(job.id, payload);
          overlay.remove();
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updated, ctx);
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
 
      btnDelete.addEventListener("click", async () => {
        if (!confirm("Delete this job?")) return;
        try {
          await apiDeleteJob(job.id);
          overlay.remove();
          if (ctx && ctx.afterDelete) await ctx.afterDelete();
          container.innerHTML = `<div class="hint">Job deleted.</div>`;
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
    });
  }
 
  async function openCompletionOrRecommendation(job, container, ctx) {
    const isSalesLead = job.kind === "sales_lead";
    let employees = [];
    try { employees = await apiListEmployees(); } catch { employees = []; }
 
    openDrawer(isSalesLead ? "Recommendation Form" : "Completion Form", async (drawerBody, overlay) => {
      drawerBody.innerHTML = "";
      const card = document.createElement("div");
      card.className = "card";

      const formDateRow = document.createElement("div");
      formDateRow.style.marginTop = "0";
      formDateRow.innerHTML = `
        <div class="label">Date</div>
        <input class="input" id="cf_form_date" type="date" />
      `;
      formDateRow.querySelector("#cf_form_date").value = new Date().toISOString().slice(0, 10);
      card.appendChild(formDateRow);
 
      let stSel = null;
      if (!isSalesLead) {
        const statusWrap = document.createElement("div");
        statusWrap.innerHTML = `<div class="label">Status</div>`;
        stSel = document.createElement("select");
        stSel.className = "input";
        JOB_STATUS_OPTIONS.forEach(s => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.textContent = s;
          stSel.appendChild(opt);
        });
        stSel.value = job.status || "Dispatch";
        statusWrap.appendChild(stSel);
        card.appendChild(statusWrap);
      }
 
      const techRow = document.createElement("div");
      techRow.className = "grid2";
      techRow.style.marginTop = "10px";
      techRow.innerHTML = `
        <div><div class="label">Technician Name</div><select class="input" id="cf_tech"></select></div>
        <div><div class="label">Door Type</div><select class="input" id="cf_door_type"></select></div>
      `;
 
      const techSel = techRow.querySelector("#cf_tech");
      const opt0 = document.createElement("option");
      opt0.value = "";
      opt0.textContent = "-- Select Technician --";
      techSel.appendChild(opt0);
      employees.forEach(e => {
        const opt = document.createElement("option");
        opt.value = e.name;
        opt.textContent = e.name;
        techSel.appendChild(opt);
      });
 
      const doorSel = techRow.querySelector("#cf_door_type");
      const doorBlank = document.createElement("option");
      doorBlank.value = "";
      doorBlank.textContent = "-- Select Door Type --";
      doorSel.appendChild(doorBlank);
      DOOR_TYPES.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        doorSel.appendChild(opt);
      });
      doorSel.value = "";
 
      const locRow = document.createElement("div");
      locRow.style.marginTop = "10px";
      locRow.innerHTML = `
        <div class="label">Door Location</div>
        <input class="input" id="cf_door_loc" placeholder="e.g., Front Entry / Back Roll-Up" />
      `;
 
      card.appendChild(techRow);
      card.appendChild(locRow);

      const timeClockRow = document.createElement("div");
      timeClockRow.className = "grid2";
      timeClockRow.style.marginTop = "10px";
      timeClockRow.innerHTML = `
        <div><div class="label">Time In</div><input class="input" id="cf_time_in" type="time" required /></div>
        <div><div class="label">Time Out</div><input class="input" id="cf_time_out" type="time" required /></div>
      `;
      card.appendChild(timeClockRow);

      const calculateOnsiteHours = (timeIn, timeOut) => {
        const parseMinutes = (value) => {
          const parts = String(value || "").split(":");
          if (parts.length !== 2) return null;
          const h = Number(parts[0]);
          const m = Number(parts[1]);
          if (!Number.isFinite(h) || !Number.isFinite(m)) return null;
          return (h * 60) + m;
        };
        const start = parseMinutes(timeIn);
        let end = parseMinutes(timeOut);
        if (start === null || end === null) return null;
        if (end <= start) end += 24 * 60;
        const rawHours = (end - start) / 60;
        return Math.max(0, Math.round(rawHours * 2) / 2);
      };
 
      const updateRollupLunchVisibility = () => {
        const wrap = card.querySelector("#cf_rollup_lunch_wrap");
        if (!wrap) return;
        const isRollup = String(doorSel.value || "").toLowerCase() === "roll up";
        wrap.style.display = isRollup && !isSalesLead ? "block" : "none";
        if (!isRollup) {
          const sel = card.querySelector("#cf_rollup_lunch") || card.querySelector("#ef_rollup_lunch");
          if (sel) sel.value = "";
        }
      };
      doorSel.addEventListener("change", updateRollupLunchVisibility);
      updateRollupLunchVisibility();


      if (isSalesLead) {
        const leadBlock = document.createElement("div");
        leadBlock.style.marginTop = "10px";
        leadBlock.innerHTML = `
          <div class="label">Recommendations</div>
          <textarea id="cf_lead_recs" placeholder="Recommendations"></textarea>
          <div class="grid2" style="margin-top:10px;">
            <div><div class="label">Parts Required</div><textarea id="cf_lead_parts" placeholder="Parts required"></textarea></div>
            <div><div class="label">Time Required</div><input class="input" id="cf_lead_time" placeholder="e.g., 2 hours, 1 trip, etc." /></div>
          </div>
          <label style="display:flex; align-items:center; gap:8px; margin-top:12px; font-weight:1000;">
            <input type="checkbox" id="cf_ready" /> Ready to Quote
          </label>
        `;
        card.appendChild(leadBlock);
      } else {
        const timeRow = document.createElement("div");
        timeRow.style.marginTop = "10px";
        timeRow.innerHTML = `
          <div class="label">Time Onsite (hours)</div>
          <input class="input" id="cf_time" type="number" step="0.5" min="0" placeholder="Auto-calculated" readonly />
          <div class="hint">Auto-calculated from Time In and Time Out.</div>
          <div id="cf_rollup_lunch_wrap" style="display:none; margin-top:10px;">
            <div class="label">Lunch Taken While Working Roll Up?</div>
            <select class="input" id="cf_rollup_lunch"><option value="">-- Select Yes or No --</option><option value="yes">Yes</option><option value="no">No</option></select>
            <div class="hint">Required for roll-up completion forms.</div>
          </div>
        `;
 
        const techNotes = document.createElement("div");
        techNotes.style.marginTop = "10px";
        techNotes.innerHTML = `<div class="label">Tech Notes</div><textarea id="cf_tech_notes"></textarea>`;
 
        const partsRecs = document.createElement("div");
        partsRecs.className = "grid2";
        partsRecs.style.marginTop = "10px";
        partsRecs.innerHTML = `
          <div><div class="label">Parts Used</div><textarea id="cf_parts" placeholder="Parts used"></textarea></div>
          <div><div class="label">Additional Recommendations</div><textarea id="cf_add_recs" placeholder="Additional recommendations"></textarea></div>
        `;
 
        card.appendChild(timeRow);
        card.appendChild(techNotes);
        card.appendChild(partsRecs);
      }

      const syncTimeOnsite = () => {
        if (isSalesLead) return;
        const timeIn = card.querySelector("#cf_time_in")?.value || "";
        const timeOut = card.querySelector("#cf_time_out")?.value || "";
        const hours = calculateOnsiteHours(timeIn, timeOut);
        const onsiteInput = card.querySelector("#cf_time");
        if (onsiteInput) onsiteInput.value = hours === null ? "" : String(hours);
      };
      card.querySelector("#cf_time_in")?.addEventListener("change", syncTimeOnsite);
      card.querySelector("#cf_time_out")?.addEventListener("change", syncTimeOnsite);

      let doorRecordLogs = [];
      const doorRecordPanel = document.createElement("div");
      doorRecordPanel.className = "card";
      doorRecordPanel.style.marginTop = "12px";
      doorRecordPanel.style.background = "#f8fafc";
      doorRecordPanel.innerHTML = `
        <div style="display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;">
          <div>
            <div style="font-weight:1000;">Door Records</div>
            <div class="hint">Optionally link this ${isSalesLead ? "recommendation" : "completion"} form to an existing door or create a new door record.</div>
          </div>
          <button type="button" class="btn" id="cf_door_record_toggle">Add to Door Records</button>
        </div>
        <div id="cf_door_record_body" style="display:none; margin-top:12px;">
          <div class="grid2">
            <div>
              <div class="label">Record Action</div>
              <select class="input" id="cf_door_record_mode">
                <option value="">-- Do Not Add --</option>
                <option value="existing">Add to Existing Door</option>
                <option value="new">Create New Door Record</option>
              </select>
            </div>
            <div id="cf_existing_door_wrap" style="display:none;">
              <div class="label">Existing Door</div>
              <select class="input" id="cf_existing_door"><option value="">-- Select Door --</option></select>
            </div>
          </div>
          <div id="cf_new_door_wrap" style="display:none; margin-top:10px;">
            <div class="grid2">
              <div><div class="label">Door ID</div><input class="input" id="cf_new_door_id" placeholder="Required, e.g. AMB-AUTO-01" /></div>
              <div><div class="label">Manufacturer</div><input class="input" id="cf_new_manufacturer" /></div>
              <div><div class="label">Model</div><input class="input" id="cf_new_model" /></div>
              <div><div class="label">Serial Number</div><input class="input" id="cf_new_serial" /></div>
            </div>
          </div>
        </div>
      `;
      card.appendChild(doorRecordPanel);

      const doorToggle = doorRecordPanel.querySelector("#cf_door_record_toggle");
      const doorBody = doorRecordPanel.querySelector("#cf_door_record_body");
      const doorMode = doorRecordPanel.querySelector("#cf_door_record_mode");
      const existingDoorWrap = doorRecordPanel.querySelector("#cf_existing_door_wrap");
      const newDoorWrap = doorRecordPanel.querySelector("#cf_new_door_wrap");
      const existingDoorSelect = doorRecordPanel.querySelector("#cf_existing_door");

      const renderDoorChoices = () => {
        const customer = normalizeText(job.customer || "");
        const address = normalizeText(job.address || "");
        const matching = doorRecordLogs.filter(item => {
          const sameCustomer = customer && normalizeText(item.customer || "") === customer;
          const sameAddress = address && normalizeText(item.address || "") === address;
          return sameCustomer || sameAddress;
        });
        const choices = matching.length ? matching : doorRecordLogs;
        existingDoorSelect.innerHTML = `<option value="">-- Select Door --</option>` + choices.map(item => {
          const label = [item.door_id, item.door_location, item.door_type, item.address].filter(Boolean).join(" — ") || item.customer || "Door Record";
          return `<option value="${escapeHtml(item.id || "")}">${escapeHtml(label)}</option>`;
        }).join("");
      };

      doorToggle.addEventListener("click", async () => {
        const opening = doorBody.style.display === "none";
        doorBody.style.display = opening ? "block" : "none";
        doorToggle.textContent = opening ? "Hide Door Records" : "Add to Door Records";
        if (opening && !doorRecordLogs.length) {
          doorRecordLogs = await apiListDoorLogs().catch(() => []);
          renderDoorChoices();
        }
      });
      doorMode.addEventListener("change", () => {
        existingDoorWrap.style.display = doorMode.value === "existing" ? "block" : "none";
        newDoorWrap.style.display = doorMode.value === "new" ? "block" : "none";
      });
      existingDoorSelect.addEventListener("change", () => {
        const selected = doorRecordLogs.find(item => String(item.id || "") === String(existingDoorSelect.value || ""));
        if (!selected) return;
        if (selected.door_type && DOOR_TYPES.includes(selected.door_type)) {
          doorSel.value = selected.door_type;
          updateRollupLunchVisibility();
        }
        if (selected.door_location) locRow.querySelector("#cf_door_loc").value = selected.door_location;
      });
 
      // Moses: one transcript, then OpenAI proposes structured form fields for review.
      const speechCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
      const speechPanel=document.createElement("div");speechPanel.className="card";
      speechPanel.style.cssText="margin:12px 0;padding:14px";
      const speechTitle=document.createElement("strong");speechTitle.textContent="Moses — Voice Form Assistant";speechPanel.appendChild(speechTitle);
      const speechHint=document.createElement("p");speechHint.className="hint";
      speechHint.textContent="Describe the work, parts, and recommendations in one recording. Review the transcript, then let AI fill the form. Nothing saves automatically.";speechPanel.appendChild(speechHint);
      const transcript=document.createElement("textarea");transcript.className="input";transcript.rows=4;transcript.placeholder="Speak or type your full job description here...";transcript.setAttribute("aria-label","Voice transcript");speechPanel.appendChild(transcript);
      const voiceActions=document.createElement("div");voiceActions.style.cssText="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px";speechPanel.appendChild(voiceActions);
      const speechBtn=document.createElement("button");speechBtn.type="button";speechBtn.className="btn";speechBtn.textContent="Start Recording";voiceActions.appendChild(speechBtn);
      const aiBtn=document.createElement("button");aiBtn.type="button";aiBtn.className="btn btn-orange";aiBtn.textContent="Fill Form with OpenAI";voiceActions.appendChild(aiBtn);
      if(!speechCtor){speechBtn.disabled=true;speechHint.textContent="Voice recognition is unavailable in this browser. Type notes below and select Fill Form with OpenAI.";}
      else {let recognition=null,active=false,finalText="";
        speechBtn.addEventListener("click",()=>{
          if(active){recognition?.stop();return;}
          recognition=new speechCtor();recognition.lang="en-US";recognition.continuous=true;recognition.interimResults=true;
          finalText=transcript.value.trim();
          recognition.onresult=(e)=>{let interim="";for(let i=e.resultIndex;i<e.results.length;i++){const part=e.results[i][0]?.transcript||"";if(e.results[i].isFinal)finalText=[finalText,part].filter(Boolean).join(" ");else interim+=part;}transcript.value=[finalText,interim].filter(Boolean).join(" ");};
          recognition.onerror=(e)=>{speechHint.textContent=`Recording error: ${e.error||"microphone error"}. You can type notes manually.`;};
          recognition.onend=()=>{active=false;speechBtn.textContent="Start Recording";speechHint.textContent="Recording stopped. Review the transcript, then select Fill Form with OpenAI.";};
          try{recognition.start();active=true;speechBtn.textContent="Stop Recording";speechHint.textContent="Recording... press Stop Recording when finished.";}catch(e){speechHint.textContent=`Could not record: ${e.message||e}`;}
        });
      }
      aiBtn.addEventListener("click",async()=>{
        const text=transcript.value.trim();if(!text){alert("Record or type your notes first.");return;}
        aiBtn.disabled=true;aiBtn.textContent="Organizing notes...";
        try{
          const result=await fetchJSON("/moses/form-assist",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({transcript:text,form_type:isSalesLead?"recommendation":"completion"})});
          const fields=result.fields||{};
          const mapping=isSalesLead?[["recommendations","#cf_lead_recs"],["parts_used","#cf_lead_parts"]]:[["work_performed","#cf_tech_notes"],["parts_used","#cf_parts"],["recommendations","#cf_add_recs"]];
          for(const [key,selector] of mapping){const el=card.querySelector(selector);if(el&&fields[key]){el.value=String(fields[key]);el.dispatchEvent(new Event("input",{bubbles:true}));}}
          if(fields.door_location){const locationInput=card.querySelector("#cf_door_loc");if(locationInput){locationInput.value=String(fields.door_location);locationInput.dispatchEvent(new Event("input",{bubbles:true}));}}
          if(fields.door_type && DOOR_TYPES.includes(fields.door_type)){doorSel.value=fields.door_type;doorSel.dispatchEvent(new Event("change",{bubbles:true}));}
          speechHint.textContent="AI draft filled in, including stated door details. Review every field and correct anything inaccurate before saving.";
          if(result.message) speechHint.textContent=result.message;
        }catch(e){speechHint.textContent=`AI assistance failed: ${e.message||e}. Your transcript is still available.`;}
        finally{aiBtn.disabled=false;aiBtn.textContent="Fill Form with OpenAI";}
      });
      // Identify the form author from the authenticated session; do not use AI to guess.
      if(currentUser){
        const candidates=[currentUser.name,currentUser.full_name,currentUser.username].map(v=>String(v||"").trim()).filter(Boolean);
        const norm=v=>String(v||"").toLowerCase().replace(/[^a-z0-9]/g,"");
        let match=Array.from(techSel.options).find(o=>o.value && candidates.some(c=>norm(o.value)===norm(c)));
        if(!match && candidates.length){
          const candidateTokens=candidates[0].toLowerCase().split(/\s+/).filter(Boolean);
          match=Array.from(techSel.options).find(o=>o.value && candidateTokens.length>1 && candidateTokens.every(t=>o.value.toLowerCase().split(/\s+/).includes(t)));
        }
        if(match){techSel.value=match.value;techSel.dispatchEvent(new Event("change",{bubbles:true}));}
        else if(candidates.length){
          // Keep a valid employee option even when the account name isn't in the employee directory.
          const option=document.createElement("option");option.value=candidates[0];option.textContent=candidates[0]+" (signed-in user)";techSel.appendChild(option);techSel.value=option.value;
        }
        if(["tech","lead"].includes(String(currentUser.role||""))){techSel.title="Technician from signed-in account";}
      }
      card.insertBefore(speechPanel,card.firstChild);
      const uploadPanel = document.createElement("div");
      uploadPanel.style.cssText = "margin-top:12px;padding:12px;border:1px solid #cbd5e1;border-radius:8px";
      uploadPanel.innerHTML = `<div class="label">Photos / Files (optional)</div><input class="input" type="file" id="cf_files" multiple accept="image/*,application/pdf" /><div class="hint">Attachments are linked to this saved form.</div>`;
      card.appendChild(uploadPanel);
      const checklist = document.createElement("div");
      checklist.style.marginTop = "12px";
      checklist.innerHTML = `<div class="label">Before Saving</div>
        <label style="display:block;"><input type="checkbox" id="cf_confirm_review" /> I uploaded the relevant images and documents.</label>
        <label style="display:block;"><input type="checkbox" id="cf_confirm_signoff" /> Sign-off completed, or not applicable.</label>
        <label style="display:block;"><input type="checkbox" id="cf_confirm_checkin" /> Check-in / check-out completed, or not applicable.</label>`;
      card.appendChild(checklist);

      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "10px";
 
      const btnSave = document.createElement("button");
      btnSave.className = "btn btn-orange";
      btnSave.textContent = "Save Form";
 
      const btnClose = document.createElement("button");
      btnClose.className = "btn";
      btnClose.textContent = "Close";
 
      actions.appendChild(btnSave);
      actions.appendChild(btnClose);
      card.appendChild(actions);
 
      drawerBody.appendChild(card);
 
      btnClose.addEventListener("click", () => overlay.remove());
 
      btnSave.addEventListener("click", async () => {
        try {
          const selectedDate = (card.querySelector("#cf_form_date")?.value || "").trim();
          if (!selectedDate) { alert("Date is required."); card.querySelector("#cf_form_date")?.focus(); return; }
          if (!techSel.value.trim()) { alert("Technician is required."); techSel.focus(); return; }
          if (!doorSel.value.trim()) { alert("Door type is required"); return; }
          const timeIn = card.querySelector("#cf_time_in")?.value || "";
          const timeOut = card.querySelector("#cf_time_out")?.value || "";
          if (!timeIn) { alert("Time In is required."); card.querySelector("#cf_time_in")?.focus(); return; }
          if (!timeOut) { alert("Time Out is required."); card.querySelector("#cf_time_out")?.focus(); return; }
          const calculatedHours = calculateOnsiteHours(timeIn, timeOut);
          if (calculatedHours === null || calculatedHours <= 0) { alert("Time In and Time Out must create a valid onsite time."); return; }
          const payload = {
            date: selectedDate,
            form_date: selectedDate,
            technician_name: techSel.value,
            door_type: doorSel.value,
            door_location: locRow.querySelector("#cf_door_loc").value.trim(),
            time_in: timeIn,
            time_out: timeOut,
          };
 
          if (isSalesLead) {
            payload.recommendations = card.querySelector("#cf_lead_recs").value.trim();
            payload.parts_required = card.querySelector("#cf_lead_parts").value.trim();
            payload.time_required = card.querySelector("#cf_lead_time").value.trim();
            payload.ready_to_quote = !!card.querySelector("#cf_ready").checked;
          } else {
            payload.status_update = stSel ? stSel.value : job.status;
            payload.time_onsite_hours = calculatedHours;
            if (String(doorSel.value || "").toLowerCase() === "roll up") {
              const lunchVal = card.querySelector("#cf_rollup_lunch")?.value || "";
              if (!lunchVal) { alert("Please select Yes or No for lunch taken while working roll up."); card.querySelector("#cf_rollup_lunch")?.focus(); return; }
              payload.rollup_includes_lunch = lunchVal === "yes";
            } else {
              payload.rollup_includes_lunch = false;
            }
            payload.tech_notes = card.querySelector("#cf_tech_notes").value.trim();
            payload.parts_used = card.querySelector("#cf_parts").value.trim();
            payload.additional_recommendations = card.querySelector("#cf_add_recs").value.trim();
          }
 
          if (!card.querySelector("#cf_confirm_review").checked || !card.querySelector("#cf_confirm_signoff").checked || !card.querySelector("#cf_confirm_checkin").checked) {
            alert("Please complete the save confirmation checklist."); return;
          }
          const selectedFiles = Array.from(card.querySelector("#cf_files")?.files || []);
          const savedForm = await apiAddCompletion(job.id, payload);
          if (selectedFiles.length) {
            try {
              if (!savedForm?.id) throw new Error("Saved form did not return an attachment ID");
              await apiUploadCompletionAttachments(job.id, savedForm.id, selectedFiles);
            }
            catch (uploadError) { alert(`Form saved, but attachments could not be uploaded: ${uploadError.message || uploadError}`); }
          }

          if (doorRecordPanel) {
            const mode = doorRecordPanel.querySelector("#cf_door_record_mode")?.value || "";
            if (mode) {
              const sourceType = isSalesLead ? "recommendation_form" : "completion_form";
              const recommendations = isSalesLead
                ? (savedForm.recommendations || payload.recommendations || "")
                : (savedForm.additional_recommendations || payload.additional_recommendations || "");
              const summary = isSalesLead
                ? (savedForm.recommendations || payload.recommendations || "")
                : (savedForm.tech_notes || payload.tech_notes || "");
              const parts = isSalesLead
                ? (savedForm.parts_required || payload.parts_required || "")
                : (savedForm.parts_used || payload.parts_used || "");
              const historyEntry = {
                source_key: `${sourceType}:${job.id}:${savedForm.id || ""}`,
                source_type: sourceType,
                job_id: job.id,
                job_number: job.job_number || "",
                completion_form_id: savedForm.id || "",
                date: savedForm.form_date || savedForm.date || payload.form_date || payload.date || "",
                technician: savedForm.technician_name || payload.technician_name || "",
                door_type: savedForm.door_type || payload.door_type || "",
                door_location: savedForm.door_location || payload.door_location || "",
                summary,
                parts_used: parts,
                recommendations,
                ready_to_quote: !!(savedForm.ready_to_quote || payload.ready_to_quote),
              };
              try {
                if (mode === "existing") {
                  const recordId = doorRecordPanel.querySelector("#cf_existing_door")?.value || "";
                  if (!recordId) throw new Error("Select an existing Door Record or choose Create New Door Record.");
                  await apiAppendDoorLogHistory(recordId, historyEntry);
                  await apiUpdateDoorLog(recordId, {
                    job_number: job.job_number || "",
                    door_location: payload.door_location || "",
                    door_type: payload.door_type || "",
                    work_performed: summary,
                    repairs: summary,
                    additional_recommendations: recommendations,
                    has_recommendations: !!recommendations,
                    needs_follow_up: !!(recommendations || payload.ready_to_quote),
                    last_service_date: historyEntry.date,
                    last_technician: historyEntry.technician,
                  });
                } else if (mode === "new") {
                  const doorId = doorRecordPanel.querySelector("#cf_new_door_id")?.value.trim() || "";
                  if (!doorId) throw new Error("Door ID is required when creating a new Door Record.");
                  await apiCreateDoorLog({
                    customer: job.customer || "",
                    address: job.address || "",
                    project: job.po_number || "",
                    job_number: job.job_number || "",
                    door_location: payload.door_location || "",
                    door_id: doorId,
                    door_type: payload.door_type || "",
                    manufacturer: doorRecordPanel.querySelector("#cf_new_manufacturer")?.value.trim() || "",
                    model: doorRecordPanel.querySelector("#cf_new_model")?.value.trim() || "",
                    serial_number: doorRecordPanel.querySelector("#cf_new_serial")?.value.trim() || "",
                    pass_fail: "",
                    work_type: "Other",
                    work_performed: summary,
                    repairs: summary,
                    has_recommendations: !!recommendations,
                    needs_follow_up: !!(recommendations || payload.ready_to_quote),
                    additional_recommendations: recommendations,
                    last_service_date: historyEntry.date,
                    last_technician: historyEntry.technician,
                    notes: `Created from ${isSalesLead ? "recommendation" : "completion"} form.`,
                    history: [historyEntry],
                  });
                }
              } catch (doorRecordError) {
                alert(`${isSalesLead ? "Recommendation" : "Completion"} form saved, but Door Records was not updated: ${doorRecordError.message || doorRecordError}`);
              }
            }
          }
 
          overlay.remove();
          const updatedJob = await apiGetJob(job.id);
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updatedJob, ctx);
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
    });
  }
 
  function calcTimeHours(startTime, endTime, lunchTaken, lunchStart, lunchEnd) {
    if (!startTime || !endTime) return 0;
    const toMin = (t) => {
      const [h, m] = String(t).split(":").map(Number);
      return h * 60 + m;
    };
    let total = toMin(endTime) - toMin(startTime);
    if (total < 0) total = 0;
 
    if (lunchTaken && lunchStart && lunchEnd) {
      const lunch = toMin(lunchEnd) - toMin(lunchStart);
      if (lunch > 0) total -= lunch;
    }
    if (total < 0) total = 0;
    return +(total / 60).toFixed(2);
  }
 
  function renderCalendarView() {
    setNavActive(null);
    setActiveChip("Calendar");
    setWorkspace("Calendar");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const top = document.createElement("div");
    top.className = "calendar-top";
 
    const left = document.createElement("div");
    left.className = "cal-left";
 
    const btnPrev = document.createElement("button");
    btnPrev.className = "iconbtn";
    btnPrev.innerHTML = "&larr;";
 
    const btnNext = document.createElement("button");
    btnNext.className = "iconbtn";
    btnNext.innerHTML = "&rarr;";
 
    const label = document.createElement("div");
    label.className = "cal-month";
    left.style.display = "flex";
    left.style.alignItems = "center";
    left.style.gap = "14px";
    left.style.flex = "1";
    left.style.justifyContent = "center";
    label.style.flex = "0 0 auto";
    label.style.minWidth = "220px";
    label.style.textAlign = "center";
 
    left.appendChild(btnPrev);
    left.appendChild(label);
    left.appendChild(btnNext);
 
    const btnNew = document.createElement("button");
    btnNew.className = "btn btn-orange";
    btnNew.textContent = "New Dispatch";
 
    top.appendChild(left);
    top.appendChild(btnNew);
 
    const grid = document.createElement("div");
    grid.className = "cal-grid";
 
    root.appendChild(top);
    root.appendChild(grid);
 
    let cur = new Date();
    cur.setDate(1);
 
    let calendarRequestId = 0;
    async function refresh() {
      const requestId = ++calendarRequestId;
      label.textContent = monthLabel(cur);
      grid.innerHTML = "";
 
      for (const d of DAYS) {
        const h = document.createElement("div");
        h.className = "cal-dow";
        h.textContent = d;
        grid.appendChild(h);
      }
 
      const start = new Date(cur);
      start.setDate(start.getDate() - start.getDay());
 
      const end = new Date(cur);
      end.setMonth(end.getMonth() + 1);
      end.setDate(0);
      end.setDate(end.getDate() + (6 - end.getDay()));
 
      let jobs;
      try {
        // Calendar-only request: never use the unfiltered, capped job list.
        // Keep all historical months available by requesting their visible dates.
        const qs = new URLSearchParams({
          date_from: yyyyMmDd(start),
          date_to: yyyyMmDd(end),
          limit: "1000"
        });
        const response = await fetchJSON(`/calendar/jobs?${qs.toString()}`);
        if (requestId !== calendarRequestId) return; // Ignore stale month responses.
        jobs = Array.isArray(response.jobs) ? response.jobs : [];
        console.info(`[Doorks Calendar] ${qs.toString()} — ${jobs.length} jobs`);
      } catch (err) {
        if (requestId !== calendarRequestId) return;
        const msg = document.createElement("div");
        msg.className = "hint";
        msg.textContent = `Calendar could not load: ${err.message || err}`;
        grid.appendChild(msg);
        return;
      }
      const byDate = {};
      for (const j of jobs) {
        const dt = j.date;
        if (!byDate[dt]) byDate[dt] = [];
        byDate[dt].push(j);
      }
 
      const day = new Date(start);
      while (day <= end) {
        const cell = document.createElement("div");
        cell.className = "cal-cell";
 
        const inMonth = day.getMonth() === cur.getMonth();
        if (!inMonth) cell.classList.add("cal-cell-muted");
 
        const dayNum = document.createElement("div");
        dayNum.className = "cal-daynum";
        dayNum.textContent = String(day.getDate());
 
        const items = document.createElement("div");
        items.className = "cal-items";
 
        const dt = yyyyMmDd(day);
        const dayJobs = (byDate[dt] || []).slice();
 
        dayJobs.slice(0, 5).forEach(j => {
          const it = document.createElement("div");
          it.className = "cal-item";
          it.appendChild(dotEl(j.status));
 
          const txt = document.createElement("span");
          txt.textContent = j.customer || (j.kind === "sales_lead" ? `Sales Lead ${j.job_number}` : j.job_number);
          it.appendChild(txt);
 
          items.appendChild(it);
        });
 
        cell.appendChild(dayNum);
        cell.appendChild(items);
 
        cell.addEventListener("click", () => openDailySchedule(dt, dayJobs));
        grid.appendChild(cell);
        day.setDate(day.getDate() + 1);
      }
 
      refreshBadges();
    }
 
    function openDailySchedule(dateStr, preloadedJobs = null) {
      openDrawer(`Daily Schedule (${mmDdYy(dateStr)})`, async (container) => {
        let jobs = preloadedJobs;
        if (!jobs) jobs = await apiListJobs({ date: dateStr, limit: 2000 });
 
        if (!jobs.length) {
          container.innerHTML = `<div class="hint">No jobs scheduled for this day.</div>`;
          return;
        }
 
        container.innerHTML = "";
        jobs.forEach(j => {
          const row = document.createElement("div");
          row.className = "jobrow";
 
          const top = document.createElement("div");
          top.className = "jobrow-top";
 
          const name = document.createElement("div");
          name.className = "jobrow-name";
          name.textContent = j.customer || (j.kind === "sales_lead" ? `Sales Lead ${j.job_number}` : j.job_number);
 
          top.appendChild(name);
          top.appendChild(statusPill(j.status));
 
          const addr = document.createElement("div");
          addr.className = "jobrow-addr";
          addr.textContent = j.address || "";
 
          row.appendChild(top);
          row.appendChild(addr);
 
          row.addEventListener("click", async () => {
            const full = await apiGetJob(j.id);
            renderJobDetails(container, full, { afterSave: refresh, afterDelete: refresh });
          });
 
          container.appendChild(row);
        });
      });
    }
 
    async function openNewDispatch(defaultDate) {
      let customers = [];
      let contacts = [];
      let knownAddresses = [];
      try { customers = await apiListCustomers(); } catch (e) { customers = []; }
      try { contacts = await apiListContacts(); } catch (e) { contacts = []; }
      try { knownAddresses = await apiListAddresses({ limit: 1500 }); } catch (e) { knownAddresses = []; }
 
      openDrawer("New Dispatch", (container, overlay) => {
        const customerListId = `cust-${Math.random().toString(36).slice(2)}`;
        const contactListId = `cont-${Math.random().toString(36).slice(2)}`;
 
        container.innerHTML = "";
        const card = document.createElement("div");
        card.className = "card";
 
        const row0 = document.createElement("div");
        row0.className = "grid2";
        row0.innerHTML = `
          <div><div class="label">Status</div><select class="input" id="nj_status"></select></div>
          <div><div class="label">Date</div><input class="input" id="nj_date" type="date" /></div>
        `;
 
        const stSel = row0.querySelector("#nj_status");
        ["Dispatch", "Sales Lead"].forEach(s => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.textContent = s;
          stSel.appendChild(opt);
        });
        stSel.value = "Dispatch";
 
        const row1 = document.createElement("div");
        row1.className = "grid2";
        row1.innerHTML = `
          <div><div class="label">Customer</div><input class="input" id="nj_customer" list="${customerListId}" placeholder="Customer name" /></div>
          <div><div class="label">Street Address</div><input class="input" id="nj_address" name="dispatch_street_address" placeholder="Start typing address" autocomplete="off" autocapitalize="off" spellcheck="false" data-lpignore="true" data-1p-ignore="true" /></div>
        `;
 
        const row1b = document.createElement("div");
        row1b.style.display = "grid";
        row1b.style.gridTemplateColumns = "1.4fr .6fr .7fr";
        row1b.style.gap = "10px";
        row1b.innerHTML = `
        `;
 
        const row2 = document.createElement("div");
        row2.className = "grid2";
        row2.innerHTML = `
          <div><div class="label">Contact</div><input class="input" id="nj_contact" list="${contactListId}" placeholder="Contact name" /></div>
          <div><div class="label">Phone</div><input class="input" id="nj_phone" placeholder="Phone" /></div>
        `;
 
        const row3 = document.createElement("div");
        row3.className = "grid2";
        row3.innerHTML = `
          <div><div class="label">Email</div><input class="input" id="nj_email" placeholder="Email" /></div>
          <div><div class="label">Office Notes</div><input class="input" id="nj_office_notes" placeholder="Office notes" /></div>
        `;
 
        const row4 = document.createElement("div");
        row4.className = "grid2";
        row4.innerHTML = `
          <div><div class="label">Job #</div><input class="input" id="nj_job_number" placeholder="Required for dispatch" /></div>
          <div><div class="label">PO #</div><input class="input" id="nj_po" placeholder="PO #" /></div>
          <div><div class="label">Estimate #</div><input class="input" id="nj_est" placeholder="Estimate #" /></div>
          <div><div class="label">Invoice #</div><input class="input" id="nj_inv" placeholder="Invoice #" /></div>
          <div><div class="label">Upload</div><input class="input" id="nj_files" type="file" multiple /></div>
        `;
 
        const notes = document.createElement("div");
        notes.innerHTML = `<div class="label">Job Notes</div>`;
        const ta = document.createElement("textarea");
        notes.appendChild(ta);
 
        const addWrap = document.createElement("div");
        addWrap.className = "grid3";
        addWrap.style.marginTop = "12px";
        addWrap.style.display = "grid";
        addWrap.style.gridTemplateColumns = "repeat(auto-fit, minmax(160px, 1fr))";
        addWrap.style.gap = "10px";
        addWrap.innerHTML = `
          <div><button class="btn" id="nj_add_customer">+ New Customer</button></div>
          <div><button class="btn" id="nj_add_address">+ New Address</button></div>
          <div><button class="btn" id="nj_add_contact">+ New Contact</button></div>
        `;
 
        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "10px";
 
        const btnSave = document.createElement("button");
        btnSave.className = "btn btn-orange";
        btnSave.textContent = "Save";
 
        const btnCancel = document.createElement("button");
        btnCancel.className = "btn";
        btnCancel.textContent = "Cancel";
 
        actions.appendChild(btnSave);
        actions.appendChild(btnCancel);
 
        card.appendChild(buildCustomerDatalist(customerListId, customers));
        card.appendChild(buildContactDatalist(contactListId, contacts));
        const newJobCustomerInput = row1.querySelector("#nj_customer");
        const newJobContactInput = row2.querySelector("#nj_contact");
        const newJobPhoneInput = row2.querySelector("#nj_phone");
        const newJobEmailInput = row3.querySelector("#nj_email");
        const newJobContactList = card.querySelector(`#${contactListId}`);
        let liveContacts = Array.isArray(contacts) ? [...contacts] : [];
        const renderNewJobContacts = () => {
          if (!newJobContactList) return;
          newJobContactList.innerHTML = liveContacts.map(c => `<option value="${escapeHtml(c.name || "")}" label="${escapeHtml(c.company_name ? `${c.name || ""}  -  ${c.company_name}` : (c.name || ""))}"></option>`).join("");
        };
        const refreshNewJobContacts = async (forceClear = false) => {
          const company = newJobCustomerInput.value.trim();
          const loaded = await apiListContacts(company ? { company_name: company } : {}).catch(() => contacts);
          const filtered = Array.isArray(loaded) ? loaded.filter(c => {
            const cc = normalizeText(c.company_name || "");
            const selected = normalizeText(company);
            return selected ? (cc && cc === selected) : true;
          }) : [];
          liveContacts.splice(0, liveContacts.length, ...filtered);
          renderNewJobContacts();
          const exact = liveContacts.find(c => normalizeText(c.name) === normalizeText(newJobContactInput.value));
          if (exact) {
            if (!String(newJobPhoneInput.value || "").trim()) newJobPhoneInput.value = pickContactPhone(exact) || "";
            if (!String(newJobEmailInput.value || "").trim()) newJobEmailInput.value = exact.email || "";
          }
          // Preserve manually entered contact/phone/email if this is not a saved CRM contact.
        };
        wireContactAutofill({
          contacts: liveContacts,
          customerInput: newJobCustomerInput,
          contactInput: newJobContactInput,
          phoneInput: newJobPhoneInput,
          emailInput: newJobEmailInput,
          contactListId,
        });
        ["change", "blur"].forEach(evt => newJobCustomerInput.addEventListener(evt, () => refreshNewJobContacts(true)));
        let newJobContactTimer = null;
        newJobCustomerInput.addEventListener("input", () => {
          clearTimeout(newJobContactTimer);
          newJobContactTimer = setTimeout(() => refreshNewJobContacts(false), 150);
        });
        refreshNewJobContacts(false);
        const existingAddresses = customers.map(c => c.address || c.site_address || c.job_address || "").filter(Boolean);
        const addressInput = row1.querySelector("#nj_address");
        const cityInput = row1b.querySelector("#nj_city");
        const stateInput = row1b.querySelector("#nj_state");
        const zipInput = row1b.querySelector("#nj_zip");
        wireKnownAddressAutofill({
          input: addressInput,
          customerInput: newJobCustomerInput,
          knownAddresses,
          extraAddresses: existingAddresses,
        });
        addressInput.addEventListener("change", () => {
          const match = findMatchingAddress(knownAddresses, addressInput.value);
          if (!match) return;
          if (cityInput && !cityInput.value) cityInput.value = match.city || "";
          if (stateInput && !stateInput.value) stateInput.value = match.state || "";
          if (zipInput && !zipInput.value) zipInput.value = match.zip || "";
        });
        addressInput.addEventListener("doorks:address-selected", (ev) => {
          const d = (ev && ev.detail) || {};
          if (d.formatted_address) addressInput.value = d.formatted_address;
          if (cityInput) cityInput.value = d.city || cityInput.value || "";
          if (stateInput) stateInput.value = d.state || stateInput.value || "";
          if (zipInput) zipInput.value = d.zip || zipInput.value || "";
        });
        // Optional AI intake: never creates a job or overwrites populated fields without review.
        const aiPanel=document.createElement("details");
        aiPanel.className="card";
        aiPanel.style.cssText="padding:14px;margin-bottom:14px;border:1px solid #d9dfe8";
        aiPanel.innerHTML=`<summary style="font-weight:700;cursor:pointer">Read document with AI (optional)</summary><div style="margin-top:12px"><p class="hint">Upload a work order, estimate, or email. Review suggested fields before saving.</p><input class="input" id="nj_ai_file" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" style="margin:8px 0"><textarea class="input" id="nj_ai_email" placeholder="Optional: paste work order or email text here" rows="4" style="width:100%;box-sizing:border-box"></textarea><button class="btn btn-orange" type="button" id="nj_ai_read">Read with AI</button><div id="nj_ai_status" class="hint" role="status" style="margin-top:8px"></div></div>`;
        aiPanel.querySelector("#nj_ai_read").addEventListener("click",async()=>{
          const button=aiPanel.querySelector("#nj_ai_read"),statusBox=aiPanel.querySelector("#nj_ai_status");
          const file=aiPanel.querySelector("#nj_ai_file").files?.[0],email=aiPanel.querySelector("#nj_ai_email").value.trim();
          if(!file&&!email){statusBox.textContent="Select a document or paste an email first.";return;}
          const fd=new FormData();if(file)fd.append("file",file);fd.append("email_text",email);
          button.disabled=true;statusBox.textContent="Reading document…";
          try{
            const response=await fetch("/dispatch-ai/extract",{method:"POST",credentials:"same-origin",body:fd});
            const result=await response.json();if(!response.ok)throw Error(result.detail||"AI extraction failed");
            const fields=result.fields||{};
            const mapping={customer:"#nj_customer",address:"#nj_address",contact:"#nj_contact",phone:"#nj_phone",email:"#nj_email",po_number:"#nj_po",estimate_number:"#nj_est",invoice_number:"#nj_inv",job_number:"#nj_job_number",office_notes:"#nj_office_notes"};
            let count=0;
            for(const [key,selector] of Object.entries(mapping)){
              const input=card.querySelector(selector),value=fields[key];
              if(input&&typeof value==="string"&&value.trim()&&!input.value.trim()){
                input.value=value.trim();input.dispatchEvent(new Event("input",{bubbles:true}));count++;
              }
            }
            if(fields.job_notes&&!ta.value.trim()){ta.value=String(fields.job_notes);count++;}
            if(fields.date&&!row0.querySelector("#nj_date").value)row0.querySelector("#nj_date").value=fields.date;
            statusBox.textContent=`AI suggested ${count} fields. Review the entire form before saving. ${result.message||""}`;
            // Preserve the document as a job attachment when Save is clicked.
            if(file){const existing=row4.querySelector("#nj_files");if(existing&&(!existing.files||!existing.files.length)){
              try{const dt=new DataTransfer();dt.items.add(file);existing.files=dt.files;}catch(_){statusBox.textContent+=" Select the document again under Upload to attach it to the saved job.";}
            }}
          }catch(err){statusBox.textContent=`Unable to read: ${err.message||err}. Enter details manually.`;}
          finally{button.disabled=false;}
        });
        card.appendChild(aiPanel);
        card.appendChild(row0);
        card.appendChild(row1);
        card.appendChild(row1b);
        card.appendChild(row2);
        card.appendChild(row3);
        card.appendChild(row4);
        card.appendChild(notes);
        card.appendChild(addWrap);
        card.appendChild(actions);
 
        container.appendChild(card);

        const addCustomerBtn = addWrap.querySelector("#nj_add_customer");
        const addAddressBtn = addWrap.querySelector("#nj_add_address");
        const addContactBtn = addWrap.querySelector("#nj_add_contact");

        if (addCustomerBtn) {
          addCustomerBtn.addEventListener("click", async () => {
            const companyName = prompt("New customer name:", newJobCustomerInput.value.trim());
            if (!companyName || !companyName.trim()) return;
            const address = prompt("Customer address:", addressInput ? addressInput.value.trim() : "");
            const phone = prompt("Customer phone:", "");
            const email = prompt("Customer email:", "");
            try {
              const created = await apiCreateCustomer({
                company_name: companyName.trim(),
                address: (address || "").trim(),
                phone_number: (phone || "").trim(),
                email: (email || "").trim(),
              });
              const item = created && created.item ? created.item : created;
              customers.push(item || { company_name: companyName.trim(), address: (address || "").trim() });
              newJobCustomerInput.value = (item && item.company_name) || companyName.trim();
              if (addressInput && item && item.address && !addressInput.value.trim()) addressInput.value = item.address;
              alert("Customer added.");
            } catch (e) {
              alert(e.message || String(e));
            }
          });
        }

        if (addAddressBtn) {
          addAddressBtn.addEventListener("click", async () => {
            const address = prompt("New job-site address:", addressInput ? addressInput.value.trim() : "");
            if (!address || !address.trim()) return;
            const customerName = prompt("Customer for this address:", newJobCustomerInput.value.trim());
            const label = prompt("Label / Location (optional):", "");
            const notes = prompt("Notes (optional):", "");
            try {
              const created = await apiCreateAddress({
                customer: (customerName || "").trim(),
                company_name: (customerName || "").trim(),
                address: address.trim(),
                label: (label || "").trim(),
                notes: (notes || "").trim(),
              });
              const item = created && created.item ? created.item : created;
              if (addressInput) addressInput.value = (item && item.address) || address.trim();
              if (newJobCustomerInput && customerName && !newJobCustomerInput.value.trim()) newJobCustomerInput.value = customerName.trim();
              if (Array.isArray(knownAddresses)) knownAddresses.push(item || { address: address.trim(), customer: (customerName || "").trim(), source: "saved" });
              alert("Address added.");
            } catch (e) {
              alert(e.message || String(e));
            }
          });
        }

        if (addContactBtn) {
          addContactBtn.addEventListener("click", async () => {
            const contactName = prompt("New contact name:", newJobContactInput.value.trim());
            if (!contactName || !contactName.trim()) return;
            const phone = prompt("Contact phone:", newJobPhoneInput.value.trim());
            const email = prompt("Contact email:", newJobEmailInput.value.trim());
            const companyName = newJobCustomerInput.value.trim();
            try {
              const created = await apiCreateContact({
                name: contactName.trim(),
                company_name: companyName,
                phone_number: (phone || "").trim(),
                email: (email || "").trim(),
              });
              const item = created && created.item ? created.item : created;
              const contactItem = item || {
                name: contactName.trim(),
                company_name: companyName,
                phone_number: (phone || "").trim(),
                email: (email || "").trim(),
              };
              contacts.push(contactItem);
              liveContacts.push(contactItem);
              renderNewJobContacts();
              newJobContactInput.value = contactItem.name || contactName.trim();
              newJobPhoneInput.value = pickContactPhone(contactItem) || (phone || "").trim();
              newJobEmailInput.value = contactItem.email || (email || "").trim();
              alert("Contact added.");
            } catch (e) {
              alert(e.message || String(e));
            }
          });
        }

 
        row0.querySelector("#nj_date").value = defaultDate;
        const newJobNumberInput = row4.querySelector("#nj_job_number");
        // Dispatch job numbers are manual now. No auto-fill is applied.
 
        btnCancel.addEventListener("click", () => overlay.remove());
 
        btnSave.addEventListener("click", async () => {
          try {
            const status = stSel.value;
            const manualJobNumber = row4.querySelector("#nj_job_number").value.trim();
            if (status !== "Sales Lead" && !manualJobNumber) {
              alert("Job # is required for dispatch.");
              row4.querySelector("#nj_job_number").focus();
              return;
            }
            const payload = {
              kind: status === "Sales Lead" ? "sales_lead" : "dispatch",
              date: row0.querySelector("#nj_date").value,
              status,
              customer: row1.querySelector("#nj_customer").value.trim(),
              address: row1.querySelector("#nj_address").value.trim(),
              city: "",
              state: "",
              zip: "",
              contact: row2.querySelector("#nj_contact").value.trim(),
              phone: row2.querySelector("#nj_phone").value.trim(),
              email: row3.querySelector("#nj_email").value.trim(),
              office_notes: row3.querySelector("#nj_office_notes").value.trim(),
              job_number: (typeof manualJobNumber !== "undefined" ? manualJobNumber : row4.querySelector("#nj_job_number").value.trim()),
              po_number: row4.querySelector("#nj_po").value.trim(),
              estimate_number: row4.querySelector("#nj_est").value.trim(),
              invoice_number: row4.querySelector("#nj_inv").value.trim(),
              job_notes: ta.value.trim(),
            };
            const created = await apiCreateJob(payload);
            const files = row4.querySelector("#nj_files").files;
            if (created && created.id && files && files.length) {
              await apiUploadJobAttachments(created.id, files);
            }
            overlay.remove();
            await refresh();
          } catch (e) {
            alert(e.message || String(e));
          }
        });
      });
    }
 
    btnPrev.addEventListener("click", async () => {
      cur.setMonth(cur.getMonth() - 1);
      await refresh();
    });
 
    btnNext.addEventListener("click", async () => {
      cur.setMonth(cur.getMonth() + 1);
      await refresh();
    });
 
    btnNew.addEventListener("click", () => openNewDispatch(yyyyMmDd(new Date())));
 
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    currentView = { refresh };
    refresh();
  }
 
  function renderToDoListView() {
    if (!isOfficeUser()) {
      showLoggedOutSplash("You do not have access to the To-Do List.");
      return;
    }
    setNavActive(navToDoList);
    setActiveChip("Work Flow");
    setWorkspace("To-Do List");
    clearWorkspaceActions();

    const root = document.createElement("div");
    const header = document.createElement("div");
    header.className = "card";
    header.innerHTML = `
      <h3 style="margin:0;">Assigned Quote To-Do List</h3>
      <div class="hint" style="margin-top:6px;">Assigned jobs and sales leads currently in Quote or Complete/Quote status.</div>
    `;
    root.appendChild(header);

    const list = document.createElement("div");
    list.style.marginTop = "12px";
    root.appendChild(list);

    async function refresh() {
      try {
        const jobs = await apiListJobs({ limit: 5000 });
        const employees = await apiListEmployees().catch(() => []);
        const assigned = assignedQuoteJobs(jobs);
        const groups = new Map();
        assigned.forEach(j => {
          const rawAssigned = String(j.quote_assigned_to || "Unassigned").trim() || "Unassigned";
          const name = normalizeQuoteAssigneeName(rawAssigned, employees);
          if (!groups.has(name)) groups.set(name, []);
          groups.get(name).push(j);
        });

        list.innerHTML = "";
        if (!assigned.length) {
          list.innerHTML = `<div class="card"><div class="hint">No assigned quote tasks found.</div></div>`;
          refreshBadges();
          return;
        }

        Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0])).forEach(([assignedTo, items]) => {
          const section = document.createElement("div");
          section.className = "card";
          section.style.marginBottom = "12px";
          section.innerHTML = `
            <div style="display:flex; justify-content:space-between; gap:10px; align-items:center; flex-wrap:wrap;">
              <h3 style="margin:0;">${escapeHtml(assignedTo)}</h3>
              <span class="badge" style="display:inline-flex;">${items.length}</span>
            </div>
            <div class="hint" style="margin-top:4px;">Assigned quote tasks</div>
          `;

          const rows = document.createElement("div");
          rows.style.marginTop = "12px";
          rows.style.display = "grid";
          rows.style.gap = "10px";

          items
            .slice()
            .sort((a, b) => String(b.updated_at || b.created_at || b.date || "").localeCompare(String(a.updated_at || a.created_at || a.date || "")))
            .forEach(j => {
              const row = document.createElement("div");
              row.className = "jobrow";
              row.style.cursor = "pointer";
              const status = String(j.status || "");

              const top = document.createElement("div");
              top.className = "jobrow-top";

              const nameEl = document.createElement("div");
              nameEl.className = "jobrow-name";
              nameEl.textContent = j.customer || "No Customer";
              top.appendChild(nameEl);
              top.appendChild(statusPill(status));
              row.appendChild(top);

              const addr = document.createElement("div");
              addr.className = "jobrow-addr";
              addr.textContent = j.address || "";
              row.appendChild(addr);

              const meta = document.createElement("div");
              meta.className = "hint";
              meta.style.marginTop = "6px";
              const parts = [
                `${j.kind === "sales_lead" ? "Sales Lead" : "Job"} #${j.job_number || ""}`,
                j.sent_quote_number ? `Sent Estimate #${j.sent_quote_number}` : "",
                j.estimate_number ? `Estimate #${j.estimate_number}` : "",
                j.updated_at ? `Updated ${formatDisplayDate(String(j.updated_at).slice(0,10))}` : "",
              ].filter(Boolean);
              meta.textContent = parts.join(" | ");
              row.appendChild(meta);

              row.addEventListener("click", async () => {
                try {
                  const full = await apiGetJob(j.id);
                  openDrawer("Job Details", (drawerBody) => {
                    const local = document.createElement("div");
                    drawerBody.appendChild(local);
                    renderJobDetails(local, full, { afterSave: refresh, afterDelete: refresh });
                  });
                } catch (e) {
                  alert(e.message || String(e));
                }
              });
              rows.appendChild(row);
            });

          section.appendChild(rows);
          list.appendChild(section);
        });

        refreshBadges();
      } catch (e) {
        list.innerHTML = `<div class="card"><div class="hint">${escapeHtml(e.message || String(e))}</div></div>`;
      }
    }

    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    currentView = { refresh };
    refresh();
  }

  function renderJobFlowView(initialStatus = "Dispatch", standalone = false) {
    setNavActive(initialStatus === "__ALL__" ? navAllJobs : navJobFlow);
    setActiveChip("Work Flow");
    setWorkspace(initialStatus === "__ALL__" ? "All Jobs" : "Job Flow");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const tabsRow = document.createElement("div");
    tabsRow.style.display = "flex";
    tabsRow.style.gap = "8px";
    tabsRow.style.flexWrap = "wrap";
    tabsRow.style.marginBottom = "10px";
 
    const tabDefs = [
      { name: "Sales Lead", status: "Sales Lead" },
      { name: "Dispatch", status: "Dispatch" },
      { name: "Quote", status: "Quote" },
      { name: "Quote Sent", status: "Quote Sent" },
      { name: "Parts on Order", status: "Parts on Order" },
      { name: "Complete/Quote", status: "Complete/Quote" },
      { name: "Complete", status: "Complete" },
    ];
 
    let active = initialStatus;
    let allJobsQuery = "";
    const list = document.createElement("div");
    const searchWrap = document.createElement("div");
    searchWrap.style.display = "none";
    searchWrap.style.gap = "8px";
    searchWrap.style.marginBottom = "10px";
    searchWrap.style.alignItems = "center";
    searchWrap.innerHTML = `<input class="input" id="all_jobs_search" placeholder="Search by customer, contact, address, job #, estimate #, invoice #, or PO #" /><button class="btn" id="all_jobs_refresh">Search</button>`;
 
    function openAnyJobCard(job) {
      if (!job) return;
      const sourceLabel = String(job.source || "").toUpperCase();
      if (sourceLabel.startsWith("LEGACY") || !job.id) {
        openDrawer(`Legacy Job ${job.job_number || "Details"}`, async (drawerBody) => {
          const card = document.createElement("div");
          card.className = "card";
          card.innerHTML = `
            <h3 style="margin:0;">${escapeHtml(job.customer || job.customer_name || "Legacy Job")}</h3>
            <div class="hint" style="margin-top:6px;">${escapeHtml(job.job_number || "")}${job.date ? ` - ${escapeHtml(job.date)}` : ""}${job.source ? ` - ${escapeHtml(String(job.source).toUpperCase())}` : ""}</div>
            <div class="grid2" style="margin-top:12px;">
              <div><div class="label">Customer</div><div class="field">${escapeHtml(job.customer || job.customer_name || "")}</div></div>
              <div><div class="label">Job #</div><div class="field">${escapeHtml(job.job_number || "")}</div></div>
              <div><div class="label">Estimate #</div><div class="field">${formatDocRefDisplay(job.estimate_number || job.estimate_no || "")}</div></div>
              <div><div class="label">Invoice #</div><div class="field">${formatDocRefDisplay(job.invoice_number || job.invoice_no || "")}</div></div>
              <div><div class="label">PO #</div><div class="field">${formatDocRefDisplay(job.po_number || job.po_no || "")}</div></div>
              <div><div class="label">Address</div><div class="field">${escapeHtml(job.address || "")}</div></div>
              <div><div class="label">Date</div><div class="field">${escapeHtml(job.date || "")}</div></div>
              <div><div class="label">Status</div><div class="field">${escapeHtml(job.status || "")}</div></div>
              <div><div class="label">Contact</div><div class="field">${escapeHtml(job.contact || job.contact_name || "")}</div></div>
            </div>
            <div style="margin-top:10px;"><div class="label">Job Notes</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.job_notes || job.tech_notes || job.description || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Work Performed</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.work_performed || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Additional Recommendations</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.additional_recommendations || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Parts Used</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.parts_used || "")}</div></div>
          `;
          const actions = document.createElement("div");
          actions.style.display = "flex";
          actions.style.gap = "8px";
          actions.style.marginTop = "12px";
          actions.style.justifyContent = "flex-end";

          const promoteBtn = document.createElement("button");
          promoteBtn.className = "btn btn-orange";
          promoteBtn.textContent = "Import to Calendar";
          promoteBtn.addEventListener("click", async () => {
            openLegacyImportDrawer(job, async (created) => {
              drawerBody.innerHTML = "";
              const local = document.createElement("div");
              drawerBody.appendChild(local);
              renderJobDetails(local, created, { afterSave: refresh, afterDelete: refresh });
              await refresh();
            });
          });

          actions.appendChild(promoteBtn);
          card.appendChild(actions);
          drawerBody.appendChild(card);
        });
        return;
      }
      apiGetJob(job.id).then(full => {
        openDrawer("Job Details", (drawerBody) => {
          const local = document.createElement("div");
          drawerBody.appendChild(local);
          renderJobDetails(local, full, { afterSave: refresh, afterDelete: refresh });
        });
      }).catch(e => alert(e.message || String(e)));
    }
 
    function makeTab(def) {
      const b = document.createElement("button");
      b.className = "navbtn";
      b.style.width = "auto";
      b.style.minWidth = "150px";
      b.style.display = "inline-flex";
      b.style.alignItems = "center";
      b.style.gap = "10px";
      b.style.justifyContent = "space-between";
 
      const left = document.createElement("div");
      left.innerHTML = `<span>${def.name}</span>`;
      const pill = def.status === "__ALL__" ? statusPill("Dispatch") : statusPill(def.status);
      if (def.status === "__ALL__") pill.textContent = "All";
 
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.style.display = (def.status === "Done" || def.status === "Quote Sent") ? "none" : "inline-flex";
      badge.textContent = "0";
 
      b.appendChild(left);
      b.appendChild(pill);
      b.appendChild(badge);
 
      b.addEventListener("click", async () => {
        active = def.status;
        await refresh();
      });
 
      return { btn: b, badge, def };
    }
 
    const tabEls = tabDefs.map(makeTab);
    tabEls.forEach(x => tabsRow.appendChild(x.btn));
 
    function renderAllJobsRows(jobs) {
      list.innerHTML = "";
      if (!jobs.length) {
        list.innerHTML = `<div class="hint">No jobs found.</div>`;
        refreshBadges();
        return;
      }
      jobs.forEach(j => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        const customer = j.customer || j.customer_name || "Job";
        const estimate = cleanDocRef(j.estimate_number || j.estimate_no || "");
        const invoice = cleanDocRef(j.invoice_number || j.invoice_no || "");
        const poNumber = cleanDocRef(j.po_number || j.po_no || "");
        const sourceLabel = j.source ? String(j.source).toUpperCase() : "CURRENT";
        row.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(customer)} (${escapeHtml(j.job_number || "")})</div>
            <div style="display:flex; gap:8px; align-items:center;">${statusPill(j.status || "Dispatch").outerHTML}<span class="badge">${escapeHtml(sourceLabel)}</span></div>
          </div>
          <div class="jobrow-addr">${escapeHtml(j.date || j.date_display || "")} - ${escapeHtml(j.address || "")}</div>
          <div class="hint" style="margin-top:6px; font-weight:900;">Estimate: ${formatDocRefDisplay(estimate)} | Invoice: ${formatDocRefDisplay(invoice)} | PO: ${formatDocRefDisplay(poNumber)}</div>
        `;
        row.addEventListener("click", () => openAnyJobCard(j));
        list.appendChild(row);
      });
    }
 
    async function refresh() {
      tabEls.forEach(x => x.btn.classList.toggle("navbtn-active", x.def.status === active));
      for (const t of tabEls) {
        if (t.def.status === "Done" || t.def.status === "Quote Sent") continue;
        if (t.def.status === "__ALL__") {
          const js = await apiListAllJobs({ q: allJobsQuery, limit: 5000 }).catch(() => []);
          t.badge.textContent = String(js.length);
          continue;
        }
        const js = await apiListJobs({ status: t.def.status, limit: 5000 });
        t.badge.textContent = String(js.length);
      }
 
      searchWrap.style.display = active === "__ALL__" ? "flex" : "none";
 
      if (active === "__ALL__") {
        const jobs = await apiListAllJobs({ q: allJobsQuery, limit: 5000 }).catch(() => []);
        renderAllJobsRows(jobs);
        refreshBadges();
        return;
      }
 
      const jobs = await apiListJobs({ status: active, limit: 5000 });
      list.innerHTML = "";
      if (!jobs.length) {
        list.innerHTML = `<div class="hint">No items in ${active}.</div>`;
        refreshBadges();
        return;
      }
 
      jobs.forEach(j => {
        const row = document.createElement("div");
        row.className = "jobrow";
 
        const top = document.createElement("div");
        top.className = "jobrow-top";
 
        const name = document.createElement("div");
        name.className = "jobrow-name";
        const idLine = j.kind === "sales_lead" ? `Sales Lead #${j.job_number}` : `Job #${j.job_number}`;
        name.textContent = j.customer ? `${j.customer} (${idLine})` : idLine;
 
        top.appendChild(name);
        top.appendChild(statusPill(j.status));
 
        const addr = document.createElement("div");
        addr.className = "jobrow-addr";
        addr.textContent = `${mmDdYy(j.date)} - ${j.address || ""}`;
 
        row.appendChild(top);
        row.appendChild(addr);

        if (["Quote", "Complete/Quote"].includes(String(j.status || ""))) {
          const quoteMeta = document.createElement("div");
          quoteMeta.className = "hint";
          quoteMeta.style.marginTop = "6px";
          quoteMeta.style.fontWeight = "900";
          quoteMeta.textContent = `Quote By: ${j.quote_assigned_to || "Not Assigned"} | Sent Estimate #: ${j.sent_quote_number || ""}`;
          row.appendChild(quoteMeta);
          const quoteBtn = document.createElement("button");
          quoteBtn.className = "btn";
          quoteBtn.textContent = "Edit";
          quoteBtn.style.marginTop = "8px";
          quoteBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const full = await apiGetJob(j.id);
            await promptUpdateQuoteTracking(full, refresh);
          });
          row.appendChild(quoteBtn);
        }
 
        const techSummary = collectJobTechSummary(j);
        if (techSummary.length && ["Complete/Quote", "Complete", "Done"].includes(j.status)) {
          const meta = document.createElement("div");
          meta.className = "hint";
          meta.style.marginTop = "6px";
          meta.style.fontWeight = "900";
          meta.textContent = techSummary.join(" - ");
          row.appendChild(meta);
        }
 
        row.addEventListener("click", async () => {
          const full = await apiGetJob(j.id);
          openDrawer("Job Details", (drawerBody) => {
            const local = document.createElement("div");
            drawerBody.appendChild(local);
            renderJobDetails(local, full, { afterSave: refresh, afterDelete: refresh });
          });
        });
 
        list.appendChild(row);
      });
 
      refreshBadges();
    }
 
    root.appendChild(tabsRow);
    root.appendChild(searchWrap);
    root.appendChild(list);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    const allJobsInput = searchWrap.querySelector("#all_jobs_search");
    const allJobsBtn = searchWrap.querySelector("#all_jobs_refresh");
    allJobsInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        allJobsQuery = allJobsInput.value.trim();
        refresh();
      }
    });
    allJobsBtn.addEventListener("click", () => {
      allJobsQuery = allJobsInput.value.trim();
      refresh();
    });
 
    currentView = { refresh };
    refresh();
  }
 
  function renderAllJobsView() {
 
    setNavActive(navAllJobs);
    setActiveChip("Work Flow");
    setWorkspace("All Jobs");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const searchWrap = document.createElement("div");
    searchWrap.style.display = "flex";
    searchWrap.style.gap = "8px";
    searchWrap.style.marginBottom = "10px";
    searchWrap.style.alignItems = "center";
    searchWrap.innerHTML = `<input class="input" id="all_jobs_search" placeholder="Search by customer, contact, address, job #, estimate #, invoice #, or PO #" /><button class="btn" id="all_jobs_refresh">Search</button>`;
 
    const list = document.createElement("div");
    let allJobsQuery = "";
 
    function openAnyJobCard(job) {
      if (!job) return;
      const sourceLabel = String(job.source || "").toUpperCase();
      if (sourceLabel.startsWith("LEGACY") || !job.id) {
        openDrawer(`Legacy Job ${job.job_number || "Details"}`, async (drawerBody) => {
          const card = document.createElement("div");
          card.className = "card";
          const techName = job.tech_name || job.technician_name || (Array.isArray(job.completion_forms) && job.completion_forms[0] && job.completion_forms[0].technician_name) || "";
          const onsiteHours = job.time_onsite_hours || (Array.isArray(job.completion_forms) && job.completion_forms[0] && job.completion_forms[0].time_onsite_hours) || "";
          card.innerHTML = `
            <h3 style="margin:0;">${escapeHtml(job.customer || job.customer_name || "Legacy Job")}</h3>
            <div class="hint" style="margin-top:6px;">${escapeHtml(job.job_number || "")}${job.date ? ` - ${escapeHtml(job.date)}` : ""}${job.source ? ` - ${escapeHtml(String(job.source).toUpperCase())}` : ""}</div>
            <div class="grid2" style="margin-top:12px;">
              <div><div class="label">Customer</div><div class="field">${escapeHtml(job.customer || job.customer_name || "")}</div></div>
              <div><div class="label">Job #</div><div class="field">${escapeHtml(job.job_number || "")}</div></div>
              <div><div class="label">Estimate #</div><div class="field">${formatDocRefDisplay(job.estimate_number || job.estimate_no || "")}</div></div>
              <div><div class="label">Invoice #</div><div class="field">${formatDocRefDisplay(job.invoice_number || job.invoice_no || "")}</div></div>
              <div><div class="label">PO #</div><div class="field">${formatDocRefDisplay(job.po_number || job.po_no || "")}</div></div>
              <div><div class="label">Address</div><div class="field">${escapeHtml(job.address || "")}</div></div>
              <div><div class="label">Date</div><div class="field">${escapeHtml(job.date || "")}</div></div>
              <div><div class="label">Status</div><div class="field">${escapeHtml(job.status || "History")}</div></div>
              <div><div class="label">Contact</div><div class="field">${escapeHtml(job.contact || job.contact_name || "")}</div></div>
              <div><div class="label">Technician</div><div class="field">${escapeHtml(techName || "")}</div></div>
              <div><div class="label">Time Onsite</div><div class="field">${escapeHtml(String(onsiteHours || ""))}</div></div>
            </div>
            <div style="margin-top:10px;"><div class="label">Job Notes</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.job_notes || job.tech_notes || job.description || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Work Performed</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.work_performed || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Additional Recommendations</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.additional_recommendations || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Parts Used</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.parts_used || "")}</div></div>
          `;
          const actions = document.createElement("div");
          actions.style.display = "flex";
          actions.style.gap = "8px";
          actions.style.marginTop = "12px";
          actions.style.justifyContent = "flex-end";

          const promoteBtn = document.createElement("button");
          promoteBtn.className = "btn btn-orange";
          promoteBtn.textContent = "Import to Calendar";
          promoteBtn.addEventListener("click", async () => {
            openLegacyImportDrawer(job, async (created) => {
              drawerBody.innerHTML = "";
              const local = document.createElement("div");
              drawerBody.appendChild(local);
              renderJobDetails(local, created, { afterSave: refresh, afterDelete: refresh });
              await refresh();
            });
          });

          actions.appendChild(promoteBtn);
          card.appendChild(actions);
          drawerBody.appendChild(card);
        });
        return;
      }
      apiGetJob(job.id).then(full => {
        openDrawer("Job Details", (drawerBody) => {
          const local = document.createElement("div");
          drawerBody.appendChild(local);
          renderJobDetails(local, full, { afterSave: refresh, afterDelete: refresh });
        });
      }).catch(e => alert(e.message || String(e)));
    }
 
    function renderRows(jobs) {
      list.innerHTML = "";
      if (!jobs.length) {
        list.innerHTML = `<div class="hint">No jobs found.</div>`;
        return;
      }
      jobs.forEach(j => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        const customer = j.customer || j.customer_name || "Job";
        const estimate = cleanDocRef(j.estimate_number || j.estimate_no || "");
        const invoice = cleanDocRef(j.invoice_number || j.invoice_no || "");
        const sourceLabel = j.source ? String(j.source).toUpperCase() : "CURRENT";
        row.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(customer)} (${escapeHtml(j.job_number || "")})</div>
            <div style="display:flex; gap:8px; align-items:center;"><span class="badge">${escapeHtml(sourceLabel)}</span></div>
          </div>
          <div class="jobrow-addr">${escapeHtml(j.date || j.date_display || "")} - ${escapeHtml(j.address || "")}</div>
          <div class="hint" style="margin-top:6px; font-weight:900;">Estimate: ${formatDocRefDisplay(estimate)} | Invoice: ${formatDocRefDisplay(invoice)} | PO: ${formatDocRefDisplay(j.po_number || j.po_no || "")}</div>
        `;
        row.addEventListener("click", () => openAnyJobCard(j));
        list.appendChild(row);
      });
    }
 
    async function refresh() {
      const jobs = await apiListAllJobs({ q: allJobsQuery, limit: 5000 }).catch(() => []);
      renderRows(jobs);
      refreshBadges();
    }
 
    root.appendChild(searchWrap);
    root.appendChild(list);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    const allJobsInput = searchWrap.querySelector("#all_jobs_search");
    const allJobsBtn = searchWrap.querySelector("#all_jobs_refresh");
    allJobsInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        allJobsQuery = allJobsInput.value.trim();
        refresh();
      }
    });
    allJobsBtn.addEventListener("click", () => {
      allJobsQuery = allJobsInput.value.trim();
      refresh();
    });
 
    currentView = { refresh };
    refresh();
  }
 
  function renderPartsListView() {
    setNavActive(navPartsList);
    setActiveChip("Work Flow");
    setWorkspace("Parts List");
    clearWorkspaceActions();

    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>Parts List</h3><div class="hint">Manage manufacturer, part #, description, and price.</div>`;

    const controls = document.createElement("div");
    controls.style.display = "flex";
    controls.style.gap = "8px";
    controls.style.marginTop = "12px";
    controls.innerHTML = `<input class="input" id="parts_search" placeholder="Search manufacturer, part #, or description" /><button class="btn btn-orange" id="parts_add">Add Part</button>`;

    const list = document.createElement("div");
    list.style.display = "grid";
    list.style.gap = "8px";
    list.style.marginTop = "12px";

    async function openPartEditor(item = null) {
      openDrawer(item ? "Edit Part" : "Add Part", (drawerBody, overlay) => {
        const part = item || { id: "", Manufacturer: "", Item: "", Description: "", Price: "" };
        const wrap = document.createElement("div");
        wrap.className = "card";
        wrap.innerHTML = `
          <div class="grid2">
            <div><div class="label">Manufacturer</div><input class="input" id="part_mfg" value="${escapeHtml(part.Manufacturer || part.manufacturer || "")}" /></div>
            <div><div class="label">Part #</div><input class="input" id="part_item" value="${escapeHtml(part.Item || part.item || "")}" /></div>
          </div>
          <div style="margin-top:10px;"><div class="label">Description</div><textarea id="part_desc">${escapeHtml(part.Description || part.description || "")}</textarea></div>
          <div style="margin-top:10px;"><div class="label">Price</div><input class="input" id="part_price" type="number" step="0.01" min="0" value="${escapeHtml(String(part.Price || part.price || ""))}" /></div>
        `;
        const actions = document.createElement("div");
        actions.style.display = "flex"; actions.style.gap = "8px"; actions.style.marginTop = "12px";
        const save = document.createElement("button"); save.className = "btn btn-orange"; save.textContent = "Save";
        const cancel = document.createElement("button"); cancel.className = "btn"; cancel.textContent = "Cancel";
        actions.append(save, cancel);
        if (part.id) { const del = document.createElement("button"); del.className = "btn"; del.textContent = "Delete"; del.style.borderColor = "#fecaca"; del.style.color = "#b91c1c"; del.addEventListener("click", async ()=>{ if(!confirm("Delete this part?")) return; await apiDeletePart(part.id); overlay.remove(); refresh(); }); actions.appendChild(del); }
        wrap.appendChild(actions);
        drawerBody.appendChild(wrap);
        cancel.addEventListener("click", ()=> overlay.remove());
        save.addEventListener("click", async ()=>{
          await apiSavePart({
            id: part.id || "",
            manufacturer: wrap.querySelector("#part_mfg").value.trim(),
            item: wrap.querySelector("#part_item").value.trim(),
            description: wrap.querySelector("#part_desc").value.trim(),
            price: Number(wrap.querySelector("#part_price").value || 0),
          });
          overlay.remove();
          refresh();
        });
      });
    }

    async function refresh() {
      const q = controls.querySelector("#parts_search").value.trim();
      const items = await apiListParts({ q, limit: 500 }).catch(() => []);
      list.innerHTML = "";
      if (!items.length) { list.innerHTML = `<div class="hint">No saved parts yet.</div>`; return; }
      items.forEach(p => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(p.Item || p.item || "")}</div><div class="hint">$${money(p.Price || p.price || 0)}</div></div><div class="jobrow-addr">${escapeHtml(p.Manufacturer || p.manufacturer || "")} - ${escapeHtml(p.Description || p.description || "")}</div>`;
        row.addEventListener("click", ()=> openPartEditor(p));
        list.appendChild(row);
      });
    }

    controls.querySelector("#parts_add").addEventListener("click", ()=> openPartEditor());
    controls.querySelector("#parts_search").addEventListener("keydown", e=>{ if(e.key === "Enter") refresh(); });

    root.appendChild(card);
    root.appendChild(controls);
    root.appendChild(list);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    currentView = { refresh };
    refresh();
  }

  async function openSignOffView(job = null) {
    const [customers, employees] = await Promise.all([
      apiListCustomers().catch(() => []),
      apiListEmployees().catch(() => []),
    ]);
    let contacts = await apiListContacts(job?.customer ? { company_name: job.customer } : {}).catch(() => []);
    openDrawer("Sign Off", (drawerBody, overlay) => {
      const card = document.createElement("div");
      card.className = "card";
      const customerListId = `so-customer-${Math.random().toString(36).slice(2)}`;
      const techListId = `so-tech-${Math.random().toString(36).slice(2)}`;
      const contactListId = `so-contact-${Math.random().toString(36).slice(2)}`;
      card.innerHTML = `
        <div class="grid2">
          <div><div class="label">Job #</div><input class="input" id="so_job" value="${escapeHtml(job?.job_number || "")}" /></div>
          <div><div class="label">Customer</div><input class="input" id="so_customer" list="${customerListId}" value="${escapeHtml(job?.customer || "")}" /></div>
          <div><div class="label">Date</div><input class="input" id="so_date" type="date" value="${yyyyMmDd(new Date())}" /></div>
          <div><div class="label">Tech</div><input class="input" id="so_techs" list="${techListId}" /></div>
          <div><div class="label">Contact Name</div><input class="input" id="so_contact" list="${contactListId}" value="${escapeHtml(job?.contact || "")}" /></div>
          <div><div class="label">Arrival / Departure</div><input class="input" id="so_times" placeholder="8:00 AM - 10:30 AM" /></div>
        </div>
        <div style="margin-top:10px;"><label style="display:flex; align-items:center; gap:8px; font-weight:700;"><input type="checkbox" id="so_additional" /><span>Additional Techs Onsite</span></label></div>
        <div style="margin-top:10px;"><div class="label">Signature</div><canvas id="so_sig" width="700" height="180" style="width:100%; border:1px solid var(--line); border-radius:12px; background:#fff;"></canvas></div>
      `;
      card.appendChild(buildCustomerDatalist(customerListId, customers));
      const techList = document.createElement('datalist'); techList.id = techListId; techList.innerHTML = employees.map(e => `<option value="${escapeHtml(e.name || '')}"></option>`).join(''); card.appendChild(techList);
      const contactList = document.createElement('datalist'); contactList.id = contactListId; card.appendChild(contactList);
      const renderContactOptions = () => {
        contactList.innerHTML = contacts.map(c => `<option value="${escapeHtml(c.name || '')}"></option>`).join('');
      };
      renderContactOptions();
      const customerInput = card.querySelector('#so_customer');
      customerInput.addEventListener('change', async () => {
        contacts = await apiListContacts({ company_name: customerInput.value.trim() }).catch(() => []);
        renderContactOptions();
      });
      const actions = document.createElement("div");
      actions.style.display = "flex"; actions.style.gap = "8px"; actions.style.marginTop = "12px";
      const clearBtn = document.createElement("button"); clearBtn.className = "btn"; clearBtn.textContent = "Clear Signature";
      const saveBtn = document.createElement("button"); saveBtn.className = "btn btn-orange"; saveBtn.textContent = "Generate Sign Off";
      const cancelBtn = document.createElement("button"); cancelBtn.className = "btn"; cancelBtn.textContent = "Cancel";
      actions.append(clearBtn, saveBtn, cancelBtn);
      card.appendChild(actions);
      drawerBody.appendChild(card);
      const canvas = card.querySelector("#so_sig"); const ctx = canvas.getContext("2d"); let drawing = false;
      const pos = e => { const r = canvas.getBoundingClientRect(); const t = e.touches ? e.touches[0] : e; return { x:(t.clientX-r.left)*(canvas.width/r.width), y:(t.clientY-r.top)*(canvas.height/r.height) }; };
      const start = e => { drawing = true; const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x,p.y); e.preventDefault(); };
      const move = e => { if(!drawing) return; const p = pos(e); ctx.lineWidth = 2; ctx.lineCap = "round"; ctx.strokeStyle = "#111827"; ctx.lineTo(p.x,p.y); ctx.stroke(); e.preventDefault(); };
      const stop = e => { drawing = false; e && e.preventDefault && e.preventDefault(); };
      canvas.addEventListener("mousedown", start); canvas.addEventListener("mousemove", move); canvas.addEventListener("mouseup", stop); canvas.addEventListener("mouseleave", stop);
      canvas.addEventListener("touchstart", start, {passive:false}); canvas.addEventListener("touchmove", move, {passive:false}); canvas.addEventListener("touchend", stop, {passive:false});
      clearBtn.addEventListener("click", ()=> ctx.clearRect(0,0,canvas.width,canvas.height));
      cancelBtn.addEventListener("click", ()=> overlay.remove());
      saveBtn.addEventListener("click", async ()=> {
        const payload = {
          job_id: job?.id || "",
          job_number: card.querySelector("#so_job").value.trim(),
          customer: card.querySelector("#so_customer").value.trim(),
          date: card.querySelector("#so_date").value,
          techs: card.querySelector("#so_techs").value.trim() + (card.querySelector('#so_additional').checked ? ' + Additional Techs Onsite' : ''),
          contact_name: card.querySelector("#so_contact").value.trim(),
          arrival_time: card.querySelector("#so_times").value.trim(),
          departure_time: "",
          signature_data: canvas.toDataURL("image/png"),
        };
        const resp = await apiCreateSignoff(payload);
        overlay.remove();
        alert("Sign off generated.");
        if (resp && resp.doc && resp.doc.open_url) window.open(resp.doc.open_url, "_blank");
        if (currentView && currentView.refresh) currentView.refresh();
      });
    });
  }

  function renderSignOffLibraryView() {
    setNavActive(navFormsSignOff || navTakeoffs);
    setActiveChip("Forms");
    setWorkspace("Saved Sign Offs");
    clearWorkspaceActions();
    const root = document.createElement('div');
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<h3>Saved Sign Offs</h3><div class="hint">Search and open previously generated sign off PDFs.</div>`;
    const controls = document.createElement('div');
    controls.style.display = 'flex'; controls.style.gap = '8px'; controls.style.marginTop = '12px';
    controls.innerHTML = `<input class="input" id="so_search" placeholder="Search job # or customer" /><button class="btn btn-orange" id="so_new">New Sign Off</button>`;
    const list = document.createElement('div'); list.style.display = 'grid'; list.style.gap = '8px'; list.style.marginTop = '12px';
    async function refresh() {
      const q = controls.querySelector('#so_search').value.trim().toLowerCase();
      const docs = await apiListDocuments().catch(() => []);
      const items = docs.filter(d => String(d.type || '').toLowerCase() === 'signoff').filter(d => {
        if (!q) return true;
        return [d.number, d.job_number, d.customer].some(v => String(v || '').toLowerCase().includes(q));
      });
      list.innerHTML = '';
      if (!items.length) { list.innerHTML = `<div class="hint">No saved sign offs yet.</div>`; return; }
      items.sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||''))).forEach(doc => {
        const row = document.createElement('div'); row.className = 'jobrow'; row.style.cursor = 'pointer';
        const cleanJob = String(doc.job_number || doc.number || '').replace(/^SIGNOFF[_-]?/i, '').replace(/_?\d{8}_\d{6}$/, '');
        row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">Job #${escapeHtml(cleanJob || '')}</div><div class="hint">${escapeHtml(formatDisplayDate(doc.date || doc.created_at || ''))}</div></div><div class="jobrow-addr">${escapeHtml(doc.customer || '')}</div><div class="hint">${escapeHtml(doc.completed_by ? 'Tech: ' + doc.completed_by : '')}</div>`;
        row.addEventListener('click', () => window.open(doc.open_url || doc.download_url, '_blank'));
        list.appendChild(row);
      });
    }
    controls.querySelector('#so_search').addEventListener('input', refresh);
    controls.querySelector('#so_new').addEventListener('click', ()=> openSignOffView());
    root.append(card, controls, list); workspaceBody.innerHTML=''; workspaceBody.appendChild(root); currentView={ refresh }; refresh();
  }

  async function renderAccountingRecords(section, host) {
    const kind = section === "stock" ? "receiving" : section;
    if(section==="statements")fetchJSON("/receipts/categories").then(d=>{window.__doorksAcctCategories=d.items||[];}).catch(()=>{});
    const titles = {receiving:"Inventory & Intake",statements:"Statements",receivables:"Accounts Receivable"};
    host.innerHTML="";
    const h=document.createElement("h3");h.textContent=titles[kind];host.appendChild(h);
    const note=document.createElement("p");note.className="hint";
    note.textContent=kind==="receiving"?"Record packing slips and partial deliveries. Stock is not automatically adjusted.":kind==="statements"?"Upload credit card statements, vendor bills, and other accounting documents. Review AI-extracted line items before saving; documents are not automatically matched to receipts.":"Track manually entered customer invoice balances. These are separate from the existing invoice builder until reconciled.";
    host.appendChild(note);
    const actions=document.createElement("div");actions.style.cssText="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0";host.appendChild(actions);
    const exportLink=document.createElement("a");exportLink.className="btn";exportLink.textContent="Export CSV";exportLink.href=`/accounting/${kind}/export.csv`;actions.appendChild(exportLink);
    if(kind==="receivables") {
      const records=await fetchJSON("/accounting/receivables");const items=records.items||[];
      const balance=r=>Math.max(0,Number(r.invoice_total||0)-Number(r.paid_amount||0));
      const periodItems=items.filter(r=>window.__doorksAcctInPeriod?.(r.invoice_date||r.due_date));
      const total=periodItems.reduce((sum,r)=>sum+Number(r.invoice_total||0),0);
      const paid=periodItems.reduce((sum,r)=>sum+Number(r.paid_amount||0),0);
      const outstanding=periodItems.reduce((sum,r)=>sum+balance(r),0);
      const today=new Date().toISOString().slice(0,10);
      const overdue=periodItems.filter(r=>r.due_date&&r.due_date<today&&balance(r)>0);
      const stats=document.createElement("div");stats.className="grid2";
      for(const [label,value] of [["Invoiced",total],["Payments recorded",paid],["Outstanding",outstanding],["Overdue",overdue.reduce((sum,r)=>sum+balance(r),0)]]){
        const card=document.createElement("div");card.className="card";const cap=document.createElement("div");cap.className="hint";cap.textContent=label;const val=document.createElement("h2");val.textContent="$"+value.toFixed(2);card.append(cap,val);stats.appendChild(card);
      }
      host.appendChild(stats);
      const caution=document.createElement("p");caution.className="hint";caution.textContent="These balances reflect manually entered Accounting records, not automatically reconciled Doorks invoices or bank payments.";host.appendChild(caution);
    }
    // Section-specific dashboards use saved records, not unverified AI extraction previews.
    if(kind==="statements" || kind==="receiving") {
      const snapshot=await fetchJSON(`/accounting/${kind}`);
      const records=(snapshot.items||[]).filter(r=>window.__doorksAcctInPeriod?.(kind==="statements"?(r.period_end||r.period_start):r.date));
      const stats=document.createElement("div");stats.className="grid2";
      const addStat=(label,value)=>{const c=document.createElement("div");c.className="card";const t=document.createElement("div");t.className="hint";t.textContent=label;const v=document.createElement("h2");v.textContent=value;c.append(t,v);stats.appendChild(c);};
      if(kind==="statements") {
        const txs=records.flatMap(r=>(r.transactions||[]).map(t=>({...t,_statement:r.issuer||""})));
        const amount=txs.filter(t=>!t.exclude_from_expenses).reduce((n,t)=>n+(Number(t.amount)||0),0);
        addStat("Statements",String(records.length));addStat("Extracted transactions",String(txs.length));
        addStat("Net statement activity",amount.toLocaleString(undefined,{style:"currency",currency:"USD"}));
        addStat("Uncategorized transactions",String(txs.filter(t=>!t.category||t.category==="Other").length));
        host.appendChild(stats);
        const by=(key)=>{const totals=new Map();for(const t of txs.filter(t=>!t.exclude_from_expenses)){const k=String(t[key]||"Unassigned");totals.set(k,(totals.get(k)||0)+(Number(t.amount)||0));}return [...totals.entries()].sort((a,b)=>Math.abs(b[1])-Math.abs(a[1]));};
        for(const [key,title] of [["category","Statement activity by category"],["employee","Statement activity by employee"],["card_last4","Statement activity by card"]]) {
          const h=document.createElement("h4");h.textContent=title;host.appendChild(h);
          const table=document.createElement("table");table.style.cssText="width:100%;border-collapse:collapse";
          for(const [label,total] of by(key)){const tr=document.createElement("tr");const name=document.createElement("td");name.textContent=label;name.style.padding="5px";const amt=document.createElement("td");amt.textContent=total.toLocaleString(undefined,{style:"currency",currency:"USD"});amt.style.cssText="text-align:right;padding:5px";tr.append(name,amt);table.appendChild(tr);}host.appendChild(table);
        }
        const caution=document.createElement("p");caution.className="hint";caution.textContent="Statement transactions are separate from receipt expenses. They are NOT added to the Overview expense total, preventing double counting. Verify card payments, refunds, transfers, and categories before using these figures for taxes.";host.appendChild(caution);
      } else {
        const lines=records.flatMap(r=>r.lines||[]);
        addStat("Receiving records",String(records.length));addStat("Recorded part lines",String(lines.length));
        addStat("Partial deliveries",String(records.filter(r=>String(r.status||"").toLowerCase().includes("partial")).length));
        addStat("Pending review",String(records.filter(r=>String(r.status||"").toLowerCase().includes("pending")).length));
        host.appendChild(stats);
      }
    }
    const form=document.createElement("form");form.className="card";host.appendChild(form);
    const title=document.createElement("h4");title.textContent=`New ${kind==="receiving"?"receiving record":kind==="statements"?"accounting document":"receivable"}`;form.appendChild(title);
    const fields=kind==="receiving"?[["supplier","Supplier"],["date","Date"],["po_number","PO #"],["job_number","Job #"],["status","Status"],["notes","Notes"]]:kind==="statements"?[["document_type","Document type (Credit Card Statement, Vendor Bill, Bank Statement, Other)"],["issuer","Issuer / vendor / account"],["period_start","Period start"],["period_end","Period end"],["notes","Notes"]]:[["customer","Customer"],["invoice_number","Invoice #"],["invoice_date","Invoice date"],["due_date","Due date"],["job_number","Job #"],["invoice_total","Invoice total"],["paid_amount","Payments received"],["notes","Notes"]];
    const inputs={};
    for(const [key,label] of fields){
      const wrap=document.createElement("div");wrap.style.marginBottom="8px";
      const l=document.createElement("label");l.className="label";l.textContent=label;wrap.appendChild(l);
      let input;
      if(key==="status") {input=document.createElement("select");for(const status of ["Pending review","Partial","Received"]){const o=document.createElement("option");o.value=status;o.textContent=status;input.appendChild(o);}}
      else {input=document.createElement(key==="notes"?"textarea":"input");if(key.includes("date")||key==="period_start"||key==="period_end")input.type="date";if(key.includes("total")||key==="paid_amount"){input.type="number";input.step="0.01";}}
      input.className="input";input.name=key;inputs[key]=input;wrap.appendChild(input);form.appendChild(wrap);
    }
    let lines;
    if(kind!=="receivables"){
      const label=document.createElement("label");label.className="label";label.textContent=kind==="receiving"?"Parts lines (JSON array: part_number, description, quantity_ordered, quantity_shipped, quantity_backordered, quantity_received)":"Line items (JSON array: date, vendor, employee, card_last4, receipt_number, category, amount, notes)";form.appendChild(label);
      lines=document.createElement("textarea");lines.className="input";lines.rows=8;lines.value="[]";form.appendChild(lines);
      const help=document.createElement("p");help.className="hint";help.textContent="AI fills these entries as editable JSON. Review and correct each line before saving.";form.appendChild(help);
      const upload=document.createElement("input");upload.type="file";upload.accept=".jpg,.jpeg,.png,.webp,.pdf";form.appendChild(upload);
      const scan=document.createElement("button");scan.type="button";scan.className="btn";scan.textContent="Read with AI";form.appendChild(scan);
      scan.addEventListener("click",async()=>{
        if(!upload.files?.length){alert("Select a document first");return;}
        scan.disabled=true;scan.textContent="Reading…";
        try{
          const body=new FormData();body.append("file",upload.files[0]);
          const resp=await fetch(`/accounting/${kind}/extract`,{method:"POST",credentials:"same-origin",body});
          const data=await resp.json();if(!resp.ok)throw Error(data.detail||"Could not read document");
          for(const [k,v] of Object.entries(data.fields||{})){if(inputs[k])inputs[k].value=v??"";}
          lines.value=JSON.stringify(data.fields?.[kind==="receiving"?"lines":"transactions"]||[],null,2);
          if(kind==="statements" && !(data.fields?.transactions||[]).length){alert("No transaction lines were extracted. For a bill or tax notice, enter the billed amount and due date manually after reviewing the original. Do not save an empty transaction list as an extracted accounting record.");}else{alert(data.message||"Review the extracted information before saving.");}
        }catch(e){alert(`Document reading failed: ${e.message||e}`);}finally{scan.disabled=false;scan.textContent="Read with AI";}
      });
      form._upload=upload;
    } else {
      const fileLabel=document.createElement("label");fileLabel.className="label";fileLabel.textContent="Invoice / bill attachment (PDF or image)";form.appendChild(fileLabel);
      const upload=document.createElement("input");upload.type="file";upload.accept=".jpg,.jpeg,.png,.webp,.pdf";form.appendChild(upload);form._upload=upload;
    }
    const save=document.createElement("button");save.className="btn btn-orange";save.textContent="Save Record";form.appendChild(save);
    const searchWrap=document.createElement("label");searchWrap.className="label";searchWrap.style.cssText="display:grid;gap:7px;margin:20px 0 12px";
    searchWrap.textContent=`Search saved ${titles[kind]}`;
    const savedSearch=document.createElement("input");savedSearch.type="search";savedSearch.className="input";
    savedSearch.placeholder=kind==="receiving"?"Supplier, PO, job, part number, description, status…":kind==="statements"?"Issuer, vendor, card, amount, transaction, category…":"Customer, invoice, job, date, amount, notes…";
    searchWrap.appendChild(savedSearch);host.appendChild(searchWrap);
    const list=document.createElement("div");host.appendChild(list);
    let cachedItems=[];
    const drawSaved=()=>{list.innerHTML="";
      // The saved section heading sits above the search field.
      const q=savedSearch.value.trim().toLowerCase();
      const matching=cachedItems.filter(item=>!q||JSON.stringify(item).toLowerCase().includes(q));
      const count=document.createElement("p");count.className="hint";count.textContent=`Showing ${matching.length} of ${cachedItems.length} saved records`;
      list.appendChild(count);
      if(!matching.length){const empty=document.createElement("p");empty.className="hint";empty.textContent="No matching saved records.";list.appendChild(empty);}
      for(const item of matching){
        const row=document.createElement("div");row.className="card";row.style.marginBottom="8px";
        const summary=document.createElement("strong");summary.textContent=kind==="receiving"?`${item.date||""} ${item.supplier||""} PO ${item.po_number||""} (${item.status||""})`:kind==="statements"?`${item.document_type||"Credit Card Statement"} — ${item.issuer||""} ${item.period_start||""} — ${item.period_end||""} (${(item.transactions||[]).length} line items)`: `${item.customer||""} Invoice ${item.invoice_number||""} — $${Number(item.invoice_total||0).toFixed(2)} / Paid $${Number(item.paid_amount||0).toFixed(2)}`;
        row.appendChild(summary);
        if(kind==="receiving") {
          const parts=Array.isArray(item.lines)?item.lines:[];
          const qty=(key)=>parts.reduce((s,p)=>s+Number(p[key]||0),0);
          const info=document.createElement("div");info.style.cssText="display:flex;gap:12px;flex-wrap:wrap;margin:10px 0;color:#586477;font-size:13px";
          for(const [label,value] of [["Supplier",item.supplier||"—"],["PO",item.po_number||"—"],["Job",item.job_number||"—"],["Date",item.date||"—"],["Status",item.status||"Pending review"]]){
            const tag=document.createElement("span");const b=document.createElement("strong");b.textContent=label+": ";tag.append(b,document.createTextNode(value));if(label==="Status")tag.dataset.receivingStatus="1";info.appendChild(tag);
          }
          row.appendChild(info);
          const summaryLine=document.createElement("p");summaryLine.style.cssText="margin:8px 0;font-size:13px";
          summaryLine.textContent=`${parts.length} part lines · Ordered ${qty("quantity_ordered")} · Shipped ${qty("quantity_shipped")} · Backordered ${qty("quantity_backordered")} · Recorded received ${qty("quantity_received")}`;
          row.appendChild(summaryLine);
          const detail=document.createElement("details");detail.style.margin="8px 0";
          const toggle=document.createElement("summary");toggle.textContent=`View ${parts.length} item lines`;detail.appendChild(toggle);
          const wrap=document.createElement("div");wrap.style.overflowX="auto";
          const table=document.createElement("table");table.style.cssText="width:100%;border-collapse:collapse;font-size:13px;margin-top:8px";
          const cols=[["part_number","Part #"],["description","Description"],["quantity_ordered","Ordered"],["quantity_shipped","Shipped"],["quantity_backordered","Backordered"],["quantity_received","Received"]];
          const head=document.createElement("tr");for(const [,label] of cols){const th=document.createElement("th");th.textContent=label;th.style.cssText="text-align:left;padding:8px;border-bottom:1px solid #ccd3dc";head.appendChild(th);}table.appendChild(head);
          // Inline receiving controls persist through the existing accounting PATCH endpoint.
          // Checkboxes are quick toggles; numeric inputs support multi-unit/partial deliveries.
          let savingLine=false;
          const saveReceiving=async(changedLine, key, value, control)=>{
            if(savingLine)return;
            const previous=Number(changedLine[key]||0);
            changedLine[key]=value;
            const allReceived=parts.length>0&&parts.every(p=>Number(p.quantity_ordered||0)>0&&Number(p.quantity_received||0)>=Number(p.quantity_ordered||0));
            const anyActivity=parts.some(p=>Number(p.quantity_received||0)>0||Number(p.quantity_shipped||0)>0||Number(p.quantity_backordered||0)>0);
            const nextStatus=allReceived?"Received":anyActivity?"Partial":"Pending review";
            savingLine=true;control.disabled=true;
            try{
              const result=await fetchJSON(`/accounting/receiving/${encodeURIComponent(item.id)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({...item,lines:parts,status:nextStatus})});
              item.lines=result.item.lines;item.status=result.item.status;
              summary.textContent=`${item.date||""} ${item.supplier||""} PO ${item.po_number||""} (${item.status||""})`;
              summaryLine.textContent=`${parts.length} part lines · Ordered ${qty("quantity_ordered")} · Shipped ${qty("quantity_shipped")} · Backordered ${qty("quantity_backordered")} · Recorded received ${qty("quantity_received")}`;
              info.querySelector('[data-receiving-status]')?.replaceChildren(document.createTextNode(`Status: ${item.status}`));
              control.title="Saved to Render";
            }catch(e){changedLine[key]=previous;alert(`Could not save quantity: ${e.message||e}`);}
            finally{savingLine=false;control.disabled=false;}
          };
          for(const p of parts){
            const tr=document.createElement("tr");
            for(const [key] of cols){
              const td=document.createElement("td");td.style.cssText="padding:8px;border-bottom:1px solid #e3e7eb";
              if(["quantity_shipped","quantity_backordered","quantity_received"].includes(key)){
                const holder=document.createElement("label");holder.style.cssText="display:flex;align-items:center;gap:5px;white-space:nowrap";
                const cb=document.createElement("input");cb.type="checkbox";cb.checked=Number(p[key]||0)>0;cb.setAttribute("aria-label",`${key.replace('quantity_','')} ${p.part_number||p.description||'part'}`);
                const count=document.createElement("input");count.type="number";count.min="0";count.step="1";count.className="input";count.style.cssText="width:68px;padding:4px";count.value=String(p[key]||0);count.setAttribute("aria-label",`${key.replace('quantity_','')} quantity`);
                cb.addEventListener("change",async()=>{
                  const amount=cb.checked?Math.max(1,Math.min(Number(p.quantity_ordered||1),Number(p[key]||1))):0;
                  await saveReceiving(p,key,amount,cb);cb.checked=Number(p[key]||0)>0;count.value=String(p[key]||0);
                });
                count.addEventListener("change",async()=>{
                  const amount=Number(count.value);
                  if(!Number.isFinite(amount)||amount<0){count.value=String(p[key]||0);return;}
                  await saveReceiving(p,key,amount,count);cb.checked=Number(p[key]||0)>0;count.value=String(p[key]||0);
                });
                holder.append(cb,count);td.appendChild(holder);
              }else td.textContent=String(p[key]??"—");
              tr.appendChild(td);
            }
            table.appendChild(tr);
          }
          wrap.appendChild(table);detail.appendChild(wrap);row.appendChild(detail);
          if(item.notes){const notes=document.createElement("p");notes.style.cssText="font-size:13px;white-space:pre-wrap;color:#586477";notes.textContent=item.notes;row.appendChild(notes);}
        }
        if(kind==="statements") {
          const txs=item.transactions||[];
          const total=txs.filter(t=>!t.exclude_from_expenses).reduce((sum,t)=>sum+Number(t.amount||0),0);
          const detail=document.createElement("details");detail.style.marginTop="10px";
          const toggle=document.createElement("summary");toggle.textContent=`View ${txs.length} transactions — net $${total.toFixed(2)}`;detail.appendChild(toggle);
          const wrap=document.createElement("div");wrap.style.cssText="overflow-x:auto;margin-top:8px";
          const table=document.createElement("table");table.style.cssText="width:100%;border-collapse:collapse;font-size:13px";
          const cols=[["date","Date"],["vendor","Vendor"],["employee","Employee"],["card_last4","Card last 4"],["receipt_number","Receipt #"],["category","Category"],["amount","Amount"],["notes","Notes"]];
          const header=document.createElement("tr");for(const [,label] of cols){const th=document.createElement("th");th.textContent=label;th.style.cssText="text-align:left;padding:6px;border-bottom:1px solid #aaa";header.appendChild(th);}const categoryHead=document.createElement("th");categoryHead.textContent="Change category";categoryHead.style.padding="6px";header.appendChild(categoryHead);const excludeHead=document.createElement("th");excludeHead.textContent="Exclude from totals";excludeHead.style.padding="6px";header.appendChild(excludeHead);table.appendChild(header);
          for(const [txIndex,tx] of txs.entries()){const tr=document.createElement("tr");for(const [key] of cols){const td=document.createElement("td");td.textContent=key==="amount"?Number(tx[key]||0).toFixed(2):String(tx[key]||"");td.style.cssText="padding:6px;border-bottom:1px solid #ddd";tr.appendChild(td);}
            const catCell=document.createElement("td");const dropdown=document.createElement("select");dropdown.className="input";dropdown.setAttribute("aria-label","Change transaction category");
            const options=[...new Set([tx.category||"",...(window.__doorksAcctCategories||[]),"Parts & Materials","Tools & Equipment","Fuel","Vehicle Maintenance","Office Supplies","Shipping & Freight","Meals","Travel","Stock / Inventory","Business & Licensing Fees","Other","Card Payment / Transfer","Refund / Credit","Personal / Nonbusiness","Uncategorized"])];
            for(const c of options){const o=document.createElement("option");o.value=c;o.textContent=c||"Uncategorized";dropdown.appendChild(o);}dropdown.value=tx.category||"";
            dropdown.addEventListener("change",async()=>{dropdown.disabled=true;const previous=tx.category;try{const updated=txs.map((t,i)=>i===txIndex?{...t,category:dropdown.value}:t);await fetchJSON(`/accounting/statements/${encodeURIComponent(item.id)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({...item,transactions:updated})});tx.category=dropdown.value;txs[txIndex]={...txs[txIndex],category:dropdown.value};tr.children[5].textContent=dropdown.value;dropdown.title="Saved";}catch(e){dropdown.value=previous||"";alert(`Category update failed: ${e.message||e}`);}finally{dropdown.disabled=false;}});
            catCell.appendChild(dropdown);tr.appendChild(catCell);
            const excludeCell=document.createElement("td");excludeCell.style.padding="6px";const exclude=document.createElement("input");exclude.type="checkbox";exclude.checked=!!tx.exclude_from_expenses;exclude.setAttribute("aria-label","Exclude this transaction from totals");
            exclude.addEventListener("change",async()=>{exclude.disabled=true;const previous=!!tx.exclude_from_expenses;try{const updated=txs.map((t,i)=>i===txIndex?{...t,exclude_from_expenses:exclude.checked}:t);await fetchJSON(`/accounting/statements/${encodeURIComponent(item.id)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({...item,transactions:updated})});tx.exclude_from_expenses=exclude.checked;txs[txIndex]={...txs[txIndex],exclude_from_expenses:exclude.checked};tr.style.opacity=exclude.checked?"0.5":"1";toggle.textContent=`View ${txs.length} transactions — included net $${txs.filter(t=>!t.exclude_from_expenses).reduce((sum,t)=>sum+Number(t.amount||0),0).toFixed(2)}`;}catch(e){exclude.checked=previous;alert(`Could not save exclusion: ${e.message||e}`);}finally{exclude.disabled=false;}});
            excludeCell.appendChild(exclude);tr.appendChild(excludeCell);if(exclude.checked)tr.style.opacity="0.5";table.appendChild(tr);}
          if(!txs.length){const p=document.createElement("p");p.className="hint";p.textContent="No transactions were saved for this statement. Select Edit to inspect the saved JSON.";wrap.appendChild(p);}
          wrap.appendChild(table);detail.appendChild(wrap);row.appendChild(detail);
        }
        const edit=document.createElement("button");edit.className="btn";edit.textContent="Edit";edit.style.marginLeft="12px";row.appendChild(edit);
        edit.addEventListener("click",()=>{for(const [k,input] of Object.entries(inputs))input.value=item[k]??"";if(lines)lines.value=JSON.stringify(item[kind==="receiving"?"lines":"transactions"]||[],null,2);form.dataset.editId=item.id;save.textContent="Update Record";form.scrollIntoView({behavior:"smooth",block:"start"});});
        if(item.attachment){const a=document.createElement("a");a.href=`/accounting/${kind}/${encodeURIComponent(item.id)}/file`;a.textContent=" Open original";a.target="_blank";row.appendChild(a);}
        const del=document.createElement("button");del.type="button";del.className="btn";del.textContent="Delete";del.style.marginLeft="8px";row.appendChild(del);
        del.addEventListener("click",async()=>{if(!confirm(`Delete this ${kind.slice(0,-1)} record from Accounting? The original document will be retained for recovery.`))return;del.disabled=true;try{await fetchJSON(`/accounting/${kind}/${encodeURIComponent(item.id)}`,{method:"DELETE"});if(form.dataset.editId===item.id){form.reset();delete form.dataset.editId;save.textContent="Save Record";}await draw();}catch(e){alert(`Delete failed: ${e.message||e}`);del.disabled=false;}});
        list.appendChild(row);
      }
    };
    const draw=async()=>{const res=await fetchJSON(`/accounting/${kind}`);cachedItems=Array.isArray(res.items)?res.items:[];drawSaved();};
    savedSearch.addEventListener("input",drawSaved);
    form.addEventListener("submit",async event=>{
      event.preventDefault();save.disabled=true;
      try{
        const payload=Object.fromEntries(Object.entries(inputs).map(([k,input])=>[k,input.value]));
        if(lines)payload[kind==="receiving"?"lines":"transactions"]=JSON.parse(lines.value||"[]");
        const id=form.dataset.editId;const url=id?`/accounting/${kind}/${encodeURIComponent(id)}`:`/accounting/${kind}`;
        const result=await fetchJSON(url,{method:id?"PATCH":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
        if(form._upload?.files?.length){const body=new FormData();body.append("file",form._upload.files[0]);const resp=await fetch(`/accounting/${kind}/${encodeURIComponent(result.item.id)}/file`,{method:"POST",credentials:"same-origin",body});if(!resp.ok)throw Error("Record saved, but original attachment upload failed");}
        form.reset();if(lines)lines.value="[]";delete form.dataset.editId;save.textContent="Save Record";await draw();
      }catch(e){alert(`Could not save: ${e.message||e}`);}finally{save.disabled=false;}
    });
    // 2.0: saved records and search come first; new entry stays collapsed until requested.
    const newRecordPanel=document.createElement("details");
    newRecordPanel.style.cssText="margin:12px 0";
    const newRecordTitle=document.createElement("summary");newRecordTitle.textContent="Record editor";
    newRecordTitle.style.display="none";newRecordPanel.appendChild(newRecordTitle);
    form.parentNode.insertBefore(newRecordPanel,form);newRecordPanel.appendChild(form);
    const savedTop=document.createElement("div");savedTop.style.cssText="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin:12px 0";
    const savedHeading=document.createElement("h4");savedHeading.textContent=`Saved ${titles[kind]}`;savedHeading.style.margin="0";savedTop.appendChild(savedHeading);
    const newBtn=document.createElement("button");newBtn.type="button";newBtn.className="btn btn-orange";newBtn.textContent=kind==="receiving"?"+ New Intake":kind==="statements"?"+ New Statement":"+ New Receivable";
    const uploadBtn=document.createElement("button");uploadBtn.type="button";uploadBtn.className="btn";uploadBtn.textContent="Upload Document";
    const btns=document.createElement("div");btns.style.cssText="display:flex;gap:8px;flex-wrap:wrap";btns.append(newBtn,uploadBtn);savedTop.appendChild(btns);
    host.insertBefore(savedTop,searchWrap);
    host.insertBefore(searchWrap,newRecordPanel);
    host.insertBefore(list,newRecordPanel);
    const openEditor=(uploadMode=false)=>{
      newRecordPanel.open=true;
      if(!form.dataset.editId){form.reset();if(lines)lines.value="[]";save.textContent="Save Record";}
      form._upload?.parentElement?.scrollIntoView?.({behavior:"smooth",block:"center"});
      if(uploadMode){form._upload?.focus();form._upload?.click();}
      else newRecordPanel.scrollIntoView({behavior:"smooth",block:"start"});
    };
    newBtn.addEventListener("click",()=>openEditor(false));
    uploadBtn.addEventListener("click",()=>openEditor(true));
    // Edit buttons in saved cards already use the existing form; reveal it first.
    list.addEventListener("click",event=>{if(event.target?.textContent==="Edit")newRecordPanel.open=true;},true);
    const summaries=document.createElement("details");summaries.style.cssText="margin:10px 0";
    const sumLabel=document.createElement("summary");sumLabel.textContent="Dashboard & Reports";sumLabel.style.cssText="cursor:pointer;font-weight:700;padding:10px";summaries.appendChild(sumLabel);
    const toMove=[...host.children].filter(el=>el!==h&&el!==note&&el!==actions&&el!==savedTop&&el!==searchWrap&&el!==list&&el!==newRecordPanel);
    for(const el of toMove)summaries.appendChild(el);
    host.insertBefore(summaries,searchWrap);
    host.insertBefore(btns,summaries);
    savedTop.remove();
    await draw();
  }

  async function renderAccountingView(section = "overview") {
    try {
      const access = await fetchJSON("/accounting/access");
      if (!access.unlocked) {
        const pin = prompt("Accounting — enter office PIN:");
        if (pin === null) return;
        await fetchJSON("/accounting/unlock", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({pin})});
      }
    } catch (err) { alert(`Accounting access denied: ${err.message || err}`); return; }
    setNavActive(navAccounting);
    setActiveChip("Office Flow");
    setWorkspace("Accounting");
    clearWorkspaceActions();
    workspaceBody.innerHTML = `<div class="card"><h3>Accounting</h3><div class="hint">Expenses and document tracking. Amounts are based on saved receipts, not bank balances.</div><div id="acct_tabs" style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0;"></div></div><div id="acct_content" class="card">Loading accounting data…</div>`;
    const periodState = window.__doorksAcctPeriod || (window.__doorksAcctPeriod={mode:"month",month:new Date().toLocaleDateString("en-CA").slice(0,7),start:"",end:""});
    const inPeriod = (date) => { const d=String(date||"").slice(0,10); if(periodState.mode==="all")return true; if(!d)return false; if(periodState.mode==="month")return d.startsWith(periodState.month); return (!periodState.start||d>=periodState.start)&&(!periodState.end||d<=periodState.end); };
    window.__doorksAcctInPeriod=inPeriod;
    const periodBar=document.createElement("div");periodBar.className="card";periodBar.style.cssText="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0";
    periodBar.innerHTML='<strong>Reporting period</strong><select class="input" id="acct_period_mode"><option value="month">Month</option><option value="custom">Custom period</option><option value="all">All time</option></select><input class="input" id="acct_period_month" type="month"/><input class="input" id="acct_period_start" type="date"/><span>to</span><input class="input" id="acct_period_end" type="date"/>';
    workspaceBody.insertBefore(periodBar, workspaceBody.querySelector("#acct_content"));
    const pm=periodBar.querySelector("#acct_period_mode"),mm=periodBar.querySelector("#acct_period_month"),ps=periodBar.querySelector("#acct_period_start"),pe=periodBar.querySelector("#acct_period_end");
    pm.value=periodState.mode;mm.value=periodState.month;ps.value=periodState.start;pe.value=periodState.end;
    const periodUpdate=()=>{periodState.mode=pm.value;periodState.month=mm.value;periodState.start=ps.value;periodState.end=pe.value;renderAccountingView(section);};
    [pm,mm,ps,pe].forEach(el=>el.addEventListener("change",periodUpdate));
    mm.style.display=periodState.mode==="month"?"":"none";ps.style.display=pe.style.display=periodState.mode==="custom"?"":"none";
    periodBar.querySelector("span").style.display=periodState.mode==="custom"?"":"none";
    const host = workspaceBody.querySelector("#acct_content");
    const tabs = workspaceBody.querySelector("#acct_tabs");
    const lockButton=document.createElement("button");lockButton.className="btn";lockButton.textContent="Lock Accounting";
    lockButton.addEventListener("click",async()=>{try{await fetchJSON("/accounting/lock",{method:"POST"});workspaceBody.innerHTML="";setWorkspace("Office Flow");}catch(e){alert(e.message||e);}});
    tabs.parentElement.appendChild(lockButton);
    for (const [id, title] of [["overview","Overview"],["receivables","Accounts Receivable"],["stock","Inventory"],["receipts","Receipts"],["statements","Statements"],["categories","Categories"]]) {
      const b = document.createElement("button"); b.className = "btn"; b.textContent = title;
      if (id === section) b.classList.add("btn-orange");
      b.addEventListener("click", () => renderAccountingView(id)); tabs.appendChild(b);
    }
    try {
      if (["stock","statements","receivables"].includes(section)) {
        await renderAccountingRecords(section, host);
        currentView={refresh:()=>renderAccountingView(section)};
        return;
      }
      const [res, cat] = await Promise.all([fetchJSON("/receipts"), fetchJSON("/receipts/categories")]);
      const items = (res.items || []).filter(r => !r.deleted_at); const categories = cat.items || [];
      const periodReceipts=items.filter(r=>inPeriod(r.date));
      const money = n => "$" + Number(n || 0).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2});
      const total = periodReceipts.filter(r=>r.authorization_status==="Authorized").reduce((sum, r) => sum + Number(r.amount || 0), 0);
      const month = new Date().toISOString().slice(0,7);
      const monthly = items.filter(r => String(r.date || "").startsWith(month));
      const monthTotal = monthly.filter(r=>r.authorization_status==="Authorized").reduce((sum,r) => sum + Number(r.amount || 0),0);
      const make = (tag, text, parent=host) => { const node = document.createElement(tag); node.textContent = text; parent.appendChild(node); return node; };
      host.innerHTML = "";
      if (section === "overview") {
        const overviewActions=document.createElement("div");
        overviewActions.style.cssText="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 16px";
        const quickNew=document.createElement("button");quickNew.type="button";quickNew.className="btn btn-orange";quickNew.textContent="+ New Input";
        const quickLabel=document.createElement("span");quickLabel.className="hint";quickLabel.textContent="Upload a document and review the AI results before saving.";
        overviewActions.append(quickNew,quickLabel);host.appendChild(overviewActions);
        quickNew.addEventListener("click",()=>{
          const chooser=document.createElement("div");chooser.className="card";chooser.style.cssText="margin:10px 0 16px;padding:16px";
          const heading=document.createElement("strong");heading.textContent="What would you like to upload?";chooser.appendChild(heading);
          const buttons=document.createElement("div");buttons.style.cssText="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px";
          for(const [label,target] of [["New Intake","stock"],["New Receipt","receipts"],["New Statement","statements"]]){
            const b=document.createElement("button");b.type="button";b.className="btn";b.textContent=label;
            b.addEventListener("click",async()=>{
              await renderAccountingView(target);
              const content=workspaceBody;
              const upload=[...content.querySelectorAll("button")].find(x=>/Upload Document|Upload Receipt \/ Read with AI/.test(x.textContent||""));
              if(upload)upload.click();
            });buttons.appendChild(b);
          }
          const cancel=document.createElement("button");cancel.type="button";cancel.className="btn";cancel.textContent="Cancel";cancel.addEventListener("click",()=>chooser.remove());buttons.appendChild(cancel);
          chooser.appendChild(buttons);overviewActions.after(chooser);quickNew.disabled=true;
          cancel.addEventListener("click",()=>{quickNew.disabled=false;});
        });
        const stats = make("div", ""); stats.className="grid2";
        for (const [label, value] of [["Expenses in period",money(total)],["Authorized receipts",String(periodReceipts.filter(r=>r.authorization_status==="Authorized").length)],["Pending authorization",String(periodReceipts.filter(r=>r.authorization_status!=="Authorized").length)],["This month",money(monthTotal)],["Receipts in period",String(periodReceipts.length)],["Employees in period",String(new Set(periodReceipts.map(r=>r.employee).filter(Boolean)).size)]]) {
          const box = document.createElement("div"); box.className="card"; box.innerHTML=`<div class="hint">${escapeHtml(label)}</div><h2>${escapeHtml(value)}</h2>`; stats.appendChild(box);
        }
        try {
          const [recv, ar, statements] = await Promise.all([fetchJSON("/accounting/receiving"),fetchJSON("/accounting/receivables"),fetchJSON("/accounting/statements")]);
          const receivables=ar.items||[];
          const outstanding=receivables.reduce((sum,r)=>sum+Math.max(0,Number(r.invoice_total||0)-Number(r.paid_amount||0)),0);
          const extra=make("div", "");extra.className="grid2";
          for(const [label,value] of [["Receiving records",String((recv.items||[]).length)],["Statements uploaded",String((statements.items||[]).length)],["Tracked receivables",String(receivables.length)],["Outstanding A/R (manual)",money(outstanding)]]){
            const card=document.createElement("div");card.className="card";card.innerHTML=`<div class="hint">${escapeHtml(label)}</div><h2>${escapeHtml(value)}</h2>`;extra.appendChild(card);
          }
        }catch(error){make("p",`Accounting summaries unavailable: ${error.message||error}`);}
        make("h3", "Spending by category");
        const grouped = {}; periodReceipts.filter(r=>r.authorization_status==="Authorized").forEach(r => { const k = r.category || "Other"; grouped[k] = (grouped[k]||0)+Number(r.amount||0); });
        Object.entries(grouped).sort((a,b)=>b[1]-a[1]).forEach(([name,amount]) => make("div", `${name}: ${money(amount)}`));
        make("h3", "Spending by employee");
        const employees = {}; periodReceipts.filter(r=>r.authorization_status==="Authorized").forEach(r => { const k = r.employee || "Unassigned"; employees[k] = (employees[k]||0)+Number(r.amount||0); });
        Object.entries(employees).sort((a,b)=>b[1]-a[1]).forEach(([name,amount]) => make("div", `${name}: ${money(amount)}`));
      } else if (section === "receipts") {
        const dashboard=document.createElement("div");dashboard.className="grid2";host.appendChild(dashboard);
        const byCategory={};periodReceipts.filter(r=>r.authorization_status==="Authorized").forEach(r=>{const k=r.category||"Uncategorized";byCategory[k]=(byCategory[k]||0)+Number(r.amount||0);});
        for(const [label,value] of [["Receipts in period",String(periodReceipts.length)],["Expenses in period",money(total)],["Employees",String(new Set(periodReceipts.map(r=>r.employee).filter(Boolean)).size)],["Categories",String(Object.keys(byCategory).length)]]){const c=document.createElement("div");c.className="card";c.innerHTML=`<div class="hint">${escapeHtml(label)}</div><h2>${escapeHtml(value)}</h2>`;dashboard.appendChild(c);}
        const categoryTitle=make("h4","Spending by category");
        for(const [name,value] of Object.entries(byCategory).sort((a,b)=>b[1]-a[1]))make("div",`${name}: ${money(value)}`);
        // Office receipt submission uses the same /receipts storage and AI extraction as Forms.
        const uploadBox=document.createElement("div");uploadBox.className="card";uploadBox.style.margin="12px 0";uploadBox.style.display="none";
        
        const uploadForm=document.createElement("form");uploadForm.style.marginTop="12px";
        uploadForm.innerHTML=`<div class="grid2"><label>Date<input class="input" type="date" name="date" required></label><label>Employee<input class="input" name="employee" required></label><label>Vendor<input class="input" name="vendor" required></label><label>Amount ($)<input class="input" type="number" min="0" step="0.01" name="amount" required></label><label>Card last 4<input class="input" name="card_last4" maxlength="4" pattern="[0-9]{4}"></label><label>Receipt #<input class="input" name="receipt_number"></label><label>Category<select class="input" name="category"></select></label></div><label>Notes<textarea class="input" name="notes" rows="2"></textarea></label><label>Photo / PDF<input class="input" type="file" name="file" accept="image/*,application/pdf" required></label><p class="hint" data-receipt-status>Select a file for AI reading. Review before saving.</p><button class="btn btn-orange" type="submit">Save Receipt</button>`;
        uploadBox.appendChild(uploadForm);host.appendChild(uploadBox);
        const receiptStatus=uploadForm.querySelector('[data-receipt-status]');
        uploadForm.elements.date.value=new Date().toISOString().slice(0,10);
        uploadForm.elements.employee.value=currentUser?.name||currentUser?.username||"";
        const receiptCategories=uploadForm.elements.category;
        for(const c of categories||["Other"]){const o=document.createElement("option");o.value=c;o.textContent=c;receiptCategories.appendChild(o);}
        uploadForm.elements.file.addEventListener("change",async()=>{
          const file=uploadForm.elements.file.files?.[0];if(!file)return;
          receiptStatus.textContent="Reading receipt with AI…";
          try{const fd=new FormData();fd.append("file",file);const response=await fetch("/receipts/extract",{method:"POST",credentials:"same-origin",body:fd});const data=await response.json();if(!response.ok)throw Error(data.detail||"Could not read receipt");
            if(uploadForm.elements.file.files?.[0]!==file)return;
            const fields=data.fields||{};
            for(const k of ["vendor","amount","receipt_number","card_last4"]){if(fields[k]&&!uploadForm.elements[k].value)uploadForm.elements[k].value=String(fields[k]);}
            if(fields.date&&uploadForm.elements.date.value===new Date().toISOString().slice(0,10))uploadForm.elements.date.value=fields.date;
            receiptStatus.textContent="AI extraction complete. Check all values against the receipt before saving.";
          }catch(e){receiptStatus.textContent=`AI unavailable: ${e.message||e}. Enter details manually.`;}
        });
        uploadForm.addEventListener("submit",async(e)=>{
          e.preventDefault();const btn=uploadForm.querySelector('button[type="submit"]');btn.disabled=true;receiptStatus.textContent="Saving receipt…";
          try{const response=await fetch("/receipts",{method:"POST",credentials:"same-origin",body:new FormData(uploadForm)});const data=await response.json();if(!response.ok)throw Error(data.detail||"Save failed");await renderAccountingView("receipts");}
          catch(err){receiptStatus.textContent=`Could not save: ${err.message||err}`;}finally{btn.disabled=false;}
        });
        const bar = make("div", ""); bar.style.cssText="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px";
        const search = document.createElement("input"); search.className="input"; search.placeholder="Search vendor, employee, category, receipt #"; bar.appendChild(search);
        const exportBtn = document.createElement("a"); exportBtn.className="btn"; exportBtn.href="/receipts/export.csv"; exportBtn.textContent="Export CSV";
        const list = make("div", "");
        function draw() {
          list.innerHTML="";
          const q=search.value.trim().toLowerCase();
          periodReceipts.filter(r=>[r.vendor,r.employee,r.category,r.receipt_number,r.date].some(v=>String(v||"").toLowerCase().includes(q))).forEach(r=>{
            const line=document.createElement("div"); line.className="card";line.style.cssText="padding:14px;margin:10px 0;border:1px solid #d9dfe8;border-radius:12px";
            const name=document.createElement("div");name.style.cssText="display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center";
            const info=document.createElement("div");const heading=document.createElement("strong");heading.textContent=r.vendor||"Unknown vendor";info.appendChild(heading);
            const meta=document.createElement("div");meta.className="hint";meta.textContent=[r.date,r.employee,r.category,r.receipt_number?`Receipt # ${r.receipt_number}`:"",r.card_last4?`Card •••• ${r.card_last4}`:""].filter(Boolean).join(" · ");info.appendChild(meta);
            const amount=document.createElement("strong");amount.textContent=money(r.amount);amount.style.fontSize="18px";name.append(info,amount);
            const controls=document.createElement("div");controls.style.cssText="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px";
            const edit=document.createElement("button"); edit.className="btn"; edit.textContent="Edit"; edit.style.marginLeft="12px";
            edit.addEventListener("click",()=>{
              const editor=document.createElement("form"); editor.className="card";
              for(const [key,label] of [["date","Date"],["employee","Employee"],["vendor","Vendor"],["amount","Amount"],["category","Category"],["card_last4","Card last 4"],["receipt_number","Receipt #"],["notes","Notes"]]){
                const wrap=document.createElement("div"); const lbl=document.createElement("label"); lbl.className="label"; lbl.textContent=label; wrap.appendChild(lbl);
                let input;
                if(key==="category") { input=document.createElement("select"); [...new Set([...categories,r.category||"Other"])].forEach(c=>{const o=document.createElement("option");o.value=c;o.textContent=c;input.appendChild(o);}); }
                else {input=document.createElement("input");input.type=key==="amount"?"number":key==="date"?"date":"text";if(key==="amount")input.step="0.01";}
                input.className="input"; input.name=key; input.value=r[key]??"";wrap.appendChild(input);editor.appendChild(wrap);
              }
              const save=document.createElement("button");save.className="btn btn-orange";save.textContent="Save Changes";editor.appendChild(save);
              const cancel=document.createElement("button");cancel.type="button";cancel.className="btn";cancel.textContent="Cancel";cancel.addEventListener("click",()=>editor.remove());editor.appendChild(cancel);
              editor.addEventListener("submit",async e=>{e.preventDefault();save.disabled=true;try{const values=Object.fromEntries(new FormData(editor).entries());await fetchJSON(`/receipts/${encodeURIComponent(r.id)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(values)});await renderAccountingView("receipts");}catch(err){alert(`Could not save: ${err.message||err}`);save.disabled=false;}});
              line.appendChild(editor);
            });
            const view=document.createElement("a");view.href=`/receipts/${encodeURIComponent(r.id)}/file`;view.target="_blank";view.rel="noopener";view.textContent="Open original";view.style.marginLeft="12px";
            const del=document.createElement("button");del.className="btn";del.textContent="Delete";del.style.marginLeft="12px";
            del.addEventListener("click",async()=>{
              if(!confirm(`Remove receipt ${r.receipt_number||r.vendor||r.id} from Accounting? The original will be retained for recovery.`))return;
              try{await fetchJSON(`/receipts/${encodeURIComponent(r.id)}`,{method:"DELETE"});await renderAccountingView("receipts");}
              catch(err){alert(`Delete failed: ${err.message||err}`);}
            });
            const approval=document.createElement('span');approval.className='hint';approval.textContent=r.authorization_status==='Authorized'?`Authorized by ${r.authorized_by||'office'} ${r.authorized_at||''}`:'Pending Authorization';controls.append(approval);
            {const authorize=document.createElement('button');authorize.className='btn';authorize.textContent=r.authorization_status==='Authorized'?'Unauthorize':'Authorize';authorize.onclick=async()=>{if(!confirm(authorize.textContent+' this receipt?'))return;try{await fetchJSON(`/receipts/${encodeURIComponent(r.id)}/${r.authorization_status==='Authorized'?'unauthorize':'authorize'}`,{method:'POST'});await renderAccountingView('receipts');}catch(e){alert(e.message||e);}};controls.append(authorize);}
            const detailButton=document.createElement('button');detailButton.type='button';detailButton.className='btn';detailButton.textContent='View Details';detailButton.onclick=()=>{const existing=line.querySelector('.receipt-detail-panel');if(existing){existing.remove();return;}const panel=document.createElement('div');panel.className='receipt-detail-panel';panel.style.cssText='padding:16px;margin-top:10px;background:#f7f8fa;border:1px solid #d9dee7;border-radius:12px;white-space:pre-wrap';panel.textContent=[['Vendor',r.vendor],['Date',r.date],['Amount',money(r.amount)],['Employee',r.employee],['Category',r.category],['Receipt #',r.receipt_number],['Card',r.card_last4?'•••• '+r.card_last4:''],['Notes',r.notes],['Authorization',r.authorization_status||'Pending Authorization'],['Authorized by',r.authorized_by],['Authorized at',r.authorized_at]].filter(x=>x[1]).map(x=>x[0]+': '+x[1]).join('\n');line.append(panel);};controls.append(detailButton);
            controls.append(edit,view,del);line.append(name,controls);list.appendChild(line);
          });
        }
        // Receipts: saved records first, compact action buttons, optional summaries.
        const receiptActions=document.createElement("div");receiptActions.style.cssText="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:12px 0";
        const newReceipt=document.createElement("button");newReceipt.type="button";newReceipt.className="btn btn-orange";newReceipt.textContent="+ New Receipt";
        const uploadReceipt=document.createElement("button");uploadReceipt.type="button";uploadReceipt.className="btn";uploadReceipt.textContent="Upload Receipt / Read with AI";
        receiptActions.append(newReceipt,uploadReceipt);
        host.insertBefore(receiptActions,bar);
        host.insertBefore(bar,dashboard);
        host.insertBefore(list,dashboard);
        host.appendChild(uploadBox);
        const summaryDetails=document.createElement("details");summaryDetails.style.margin="12px 0";
        const summaryToggle=document.createElement("summary");summaryToggle.textContent="Receipt dashboard & category breakdown";summaryToggle.style.cssText="cursor:pointer;font-weight:700;padding:10px";summaryDetails.appendChild(summaryToggle);
        const breakdownNodes=[];let next=categoryTitle.nextSibling;
        while(next&&next!==uploadBox){const following=next.nextSibling;breakdownNodes.push(next);next=following;}
        summaryDetails.append(dashboard,categoryTitle,...breakdownNodes);
        summaryToggle.textContent="Dashboard & Reports";
        host.insertBefore(summaryDetails,bar);
        host.insertBefore(receiptActions,summaryDetails);
        receiptActions.appendChild(exportBtn);
        const showReceiptEditor=(withUpload)=>{
          uploadBox.style.display="block";
          uploadBox.scrollIntoView({behavior:"smooth",block:"start"});
          if(withUpload)uploadForm.elements.file.click();
          else uploadForm.elements.vendor.focus();
        };
        newReceipt.addEventListener("click",()=>showReceiptEditor(false));
        uploadReceipt.addEventListener("click",()=>showReceiptEditor(true));
        search.placeholder="Search saved receipts: vendor, date, employee, amount, card, category, notes…";
        search.addEventListener("input",draw);draw();
      } else if (section === "categories") {
        make("h3", "Expense categories");make("p", "Add categories here. Existing receipts retain their saved category.");
        const list=make("div",categories.join(" • "));list.style.marginBottom="12px";
        const input=document.createElement("input");input.className="input";input.placeholder="New category";host.appendChild(input);
        const add=document.createElement("button");add.className="btn btn-orange";add.textContent="Add Category";host.appendChild(add);
        add.addEventListener("click",async()=>{const name=input.value.trim();if(!name||categories.some(c=>c.toLowerCase()===name.toLowerCase()))return;try{await fetchJSON("/receipts/categories",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({items:[...categories,name]})});renderAccountingView("categories");}catch(e){alert(e.message||e);}});
      } else {
        make("h3", section==="stock"?"Inventory & Intake":"Accounts Receivable");
        make("p", section==="stock"?"Coming in the next accounting phase: packing-slip scanning, quantities received, supplier and PO tracking. No inventory quantities have been inferred from receipts.":"Coming in the next accounting phase: invoice balances, payment tracking and aging. Existing invoices have not been treated as paid or unpaid without payment records.");
      }
    } catch(e) { host.textContent=`Unable to load Accounting: ${e.message||e}`; }
    currentView={refresh:()=>renderAccountingView(section)};
  }

  async function renderReceiptsView() {
    setNavActive(navFormsReceipts);
    setActiveChip("Receipts");
    setWorkspace("Receipts");
    clearWorkspaceActions();
    workspaceBody.innerHTML = "";
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>Submit Receipt</h3>
      <div class="hint">Upload a photo or PDF. Enter only the last four digits of the card, never the full card number.</div>
      <form id="receipt_submit_form">
        <div class="grid2">
          <div><div class="label">Date</div><input class="input" type="date" name="date" required /></div>
          <div><div class="label">Employee</div><input class="input" name="employee" required /></div>
          <div><div class="label">Vendor</div><input class="input" name="vendor" required /></div>
          <div><div class="label">Amount ($)</div><input class="input" type="number" min="0" step="0.01" name="amount" required /></div>
          <div><div class="label">Card last 4 digits</div><input class="input" name="card_last4" maxlength="4" inputmode="numeric" pattern="[0-9]{4}" placeholder="1234" /></div>
          <div><div class="label">Receipt Number</div><input class="input" name="receipt_number" /></div>
          <div><div class="label">Expense Category</div><select class="input" name="category" id="receipt_category"><option>Other</option></select></div>
        </div>
        <div class="label">Notes</div><textarea class="input" name="notes" rows="2"></textarea>
        <div class="label">Receipt Photo / PDF</div><input class="input" type="file" name="file" accept="image/*,application/pdf" required />
        <div class="hint" id="receipt_scan_status">Selecting a file will attempt to read its details. Review all fields before saving.</div></div>
        <div style="margin-top:12px;"><button class="btn btn-orange" type="submit">Save Receipt</button></div>
      </form>
      <div id="receipt_feedback" class="hint" style="margin-top:8px;"></div>`;
    workspaceBody.appendChild(card);
    const history = document.createElement("div");
    history.className = "card";
    history.innerHTML = `<h3>Saved Receipts</h3><div class="hint">Loading…</div>`;
    workspaceBody.appendChild(history);
    const form = card.querySelector("#receipt_submit_form");
    form.elements.date.value = new Date().toISOString().slice(0, 10);
    form.elements.employee.value = currentUser?.name || currentUser?.username || "";
    try { const cats = await fetchJSON("/receipts/categories"); form.elements.category.innerHTML = ""; (cats.items || ["Other"]).forEach(c => { const o = document.createElement("option"); o.value = c; o.textContent = c; form.elements.category.appendChild(o); }); form.elements.category.value = "Other"; } catch(e) { console.warn("Receipt categories unavailable", e); }
    const receiptFileInput = form.elements.file;
    receiptFileInput.addEventListener("change", async () => {
      const file = receiptFileInput.files?.[0];
      const status = card.querySelector("#receipt_scan_status");
      if (!file) { status.textContent = "Select a receipt to read its details."; return; }
      const selectedFile = file;
      status.textContent = "Reading receipt…";
      try {
        const upload = new FormData();
        upload.append("file", file);
        const response = await fetch("/receipts/extract", { method: "POST", credentials: "same-origin", body: upload });
        const result = await response.json();
        if (receiptFileInput.files?.[0] !== selectedFile) return;
        if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
        const fields = result.fields || {};
        const populated = [];
        for (const key of ["vendor", "date", "amount", "receipt_number", "card_last4"]) {
          if (fields[key] !== undefined && fields[key] !== null && String(fields[key]).trim() && !String(form.elements[key]?.value || "").trim()) {
            form.elements[key].value = String(fields[key]);
            populated.push(key.replace("_", " "));
          }
        }
        // Date defaults to today, so replace it only when the user has not changed it.
        if (fields.date && form.elements.date.value === new Date().toISOString().slice(0, 10)) {
          form.elements.date.value = fields.date;
          if (!populated.includes("date")) populated.push("date");
        }
        status.textContent = populated.length
          ? `Read ${populated.join(", ")}. Please verify against the receipt before saving.`
          : (result.message || "Could not identify fields automatically. Please enter them manually.");
      } catch (error) {
        if (receiptFileInput.files?.[0] === selectedFile) status.textContent = `Automatic reading unavailable: ${error.message || error}. You can still enter details manually.`;
      }
    });
    async function refreshReceipts() {
      try {
        const result = await fetchJSON("/receipts");
        const items = result.items || [];
        history.innerHTML = `<h3>Saved Receipts (${items.length})</h3>`;
        if (!items.length) history.appendChild(Object.assign(document.createElement("div"), {className:"hint", textContent:"No receipts saved yet."}));
        for (const item of items) {
          const line = document.createElement("div");
          line.style.cssText = "padding:10px 0;border-bottom:1px solid #ddd";
          const heading = document.createElement("div");
          heading.textContent = `${item.date || ""} — ${item.vendor || ""} — $${Number(item.amount || 0).toFixed(2)} — ${item.employee || ""}`;
          const detail = document.createElement("div");
          detail.className = "hint";
          detail.textContent = `${item.category || "Other"} | Card •••• ${item.card_last4 || "N/A"} | Receipt # ${item.receipt_number || "N/A"} | ${item.notes || ""}`;
          const link = document.createElement("a");
          link.href = `/receipts/${encodeURIComponent(item.id)}/file`;
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = "Open receipt";
          line.append(heading, detail, link);
          history.appendChild(line);
        }
      } catch (err) { history.textContent = `Unable to load receipts: ${err.message || err}`; }
    }
    form.addEventListener("submit", async event => {
      event.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      const feedback = card.querySelector("#receipt_feedback");
      feedback.textContent = "Saving…";
      try {
        const res = await fetch("/receipts", {method:"POST", credentials:"same-origin", body:new FormData(form)});
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || `HTTP ${res.status}`);
        feedback.textContent = "Receipt saved.";
        form.reset();
        form.elements.date.value = new Date().toISOString().slice(0,10);
        form.elements.employee.value = currentUser?.name || currentUser?.username || "";
        await refreshReceipts();
      } catch (err) { feedback.textContent = `Unable to save receipt: ${err.message || err}`; }
      finally { btn.disabled = false; }
    });
    await refreshReceipts();
    currentView = {refresh: refreshReceipts};
  }

  function renderTakeoffsView() {
 
    setNavActive(navTakeoffs);
    setActiveChip("Forms");
    setWorkspace("Takeoffs");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>Takeoffs</h3><div class="hint">Download takeoff and order files here.</div>`;
    const list = document.createElement("div");
    list.style.marginTop = "12px";
 
    async function refresh() {
      const forms = await apiListForms();
      list.innerHTML = "";
      if (!forms.length) {
        list.innerHTML = `<div class="hint">No files available.</div>`;
        return;
      }
      forms.forEach(f => {
        const item = document.createElement("div");
        item.className = "jobrow";
 
        const top = document.createElement("div");
        top.className = "jobrow-top";
 
        const name = document.createElement("div");
        name.className = "jobrow-name";
        name.textContent = f.title || f.id;
 
        const btn = document.createElement("button");
        btn.className = "btn";
        btn.textContent = "Open / Download";
        btn.addEventListener("click", () => {
          const url = f.open_url || `${f.download_url || ""}${String(f.download_url || "").includes("?") ? "&" : "?"}inline=1`;
          openFileUrl(url);
        });
 
        top.appendChild(name);
        top.appendChild(btn);
 
        const desc = document.createElement("div");
        desc.className = "jobrow-addr";
        desc.textContent = f.description || "";
 
        item.appendChild(top);
        item.appendChild(desc);
        list.appendChild(item);
      });
    }
 
    root.appendChild(card);
    root.appendChild(list);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    currentView = { refresh };
    refresh();
  }
 
 
  function openTimecardEditor(item, refreshFn) {
    openDrawer("Edit Time Card", async (drawerBody, overlay) => {
      const selfOnly = currentUser && ["tech", "lead"].includes(String(currentUser.role || ""));
      const selfName = (currentUser && (currentUser.name || currentUser.username)) ? String(currentUser.name || currentUser.username) : "";
      const ownerName = String(item.technician_name || item.employee_name || item.employee || "").trim();
      const canEdit = !selfOnly || ownerName.toLowerCase() === selfName.toLowerCase();

      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h3 style="margin:0;">Edit Time Card</h3>
        <div class="hint" style="margin-top:6px;">${escapeHtml(ownerName || "Time Card")}</div>
        ${!canEdit ? `<div class="hint" style="margin-top:8px; color:#b91c1c; font-weight:900;">You can only edit your own time cards.</div>` : ""}
        <div class="grid2" style="margin-top:12px;">
          <div><div class="label">Employee</div><input class="input" id="et_employee" value="${escapeHtml(ownerName)}" ${selfOnly ? "disabled" : ""} /></div>
          <div><div class="label">Date</div><input class="input" id="et_date" type="date" value="${escapeHtml(String(item.date || "").slice(0,10))}" /></div>
          <div><div class="label">Start Time</div><input class="input" id="et_start" type="time" value="${escapeHtml(item.start_time || "")}" /></div>
          <div><div class="label">End Time</div><input class="input" id="et_end" type="time" value="${escapeHtml(item.end_time || "")}" /></div>
          <div><div class="label">Lunch Taken</div><select class="input" id="et_lunch_taken"><option value="no">No</option><option value="yes">Yes</option></select></div>
          <div><div class="label">Use PTO</div><select class="input" id="et_use_pto"><option value="no">No</option><option value="yes">Yes</option></select></div>
          <div><div class="label">Lunch Start</div><input class="input" id="et_lunch_start" type="time" value="${escapeHtml(item.lunch_start || "")}" /></div>
          <div><div class="label">Lunch End</div><input class="input" id="et_lunch_end" type="time" value="${escapeHtml(item.lunch_end || "")}" /></div>
          <div><div class="label">PTO Hours</div><input class="input" id="et_pto_hours" type="number" step="0.25" value="${escapeHtml(String(item.pto_hours || ""))}" /></div>
          <div><div class="label">Holiday Hours</div><input class="input" id="et_holiday_hours" type="number" step="0.25" value="${escapeHtml(String(item.holiday_hours || ""))}" /></div>
          <div><div class="label">Double Time Hours</div><input class="input" id="et_double_time_hours" type="number" step="0.25" value="${escapeHtml(String(item.double_time_hours || item.dt_hours || ""))}" /></div>
          <div><div class="label">Holiday Entry</div><select class="input" id="et_is_holiday"><option value="no">No</option><option value="yes">Yes</option></select></div>
        </div>
        <div style="margin-top:12px;"><div class="label">Notes</div><textarea id="et_notes">${escapeHtml(item.notes || "")}</textarea></div>
      `;
      drawerBody.appendChild(card);
      card.querySelector("#et_lunch_taken").value = item.lunch_taken ? "yes" : "no";
      card.querySelector("#et_use_pto").value = item.use_pto ? "yes" : "no";
      card.querySelector("#et_is_holiday").value = item.is_holiday ? "yes" : "no";

      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "12px";
      actions.style.flexWrap = "wrap";

      const save = document.createElement("button");
      save.className = "btn btn-orange";
      save.textContent = "Save Changes";
      save.disabled = !canEdit;
      save.addEventListener("click", async () => {
        if (!canEdit || save.disabled) return;
        const oldText = save.textContent;
        try {
          save.disabled = true;
          save.textContent = "Saving...";
          await apiUpdateTimecard(item.id, {
            technician_name: selfOnly ? selfName : card.querySelector("#et_employee").value.trim(),
            date: card.querySelector("#et_date").value,
            start_time: card.querySelector("#et_start").value,
            end_time: card.querySelector("#et_end").value,
            lunch_taken: card.querySelector("#et_lunch_taken").value === "yes",
            lunch_start: card.querySelector("#et_lunch_start").value,
            lunch_end: card.querySelector("#et_lunch_end").value,
            use_pto: card.querySelector("#et_use_pto").value === "yes",
            pto_hours: Number(card.querySelector("#et_pto_hours").value || 0),
            is_holiday: card.querySelector("#et_is_holiday").value === "yes",
            holiday_hours: Number(card.querySelector("#et_holiday_hours").value || 0),
            double_time_hours: Number(card.querySelector("#et_double_time_hours").value || 0),
            notes: card.querySelector("#et_notes").value.trim(),
          });
          save.textContent = "Saved ✓";
          showDoorksToast("Time card updated ✓");
          await refreshFn();
          setTimeout(() => { if (overlay && overlay.remove) overlay.remove(); }, 550);
        } catch (e) {
          save.disabled = false;
          save.textContent = oldText;
          alert(e.message || String(e));
        }
      });

      const close = document.createElement("button");
      close.className = "btn";
      close.textContent = "Close";
      close.addEventListener("click", () => { if (overlay && overlay.remove) overlay.remove(); });

      const del = document.createElement("button");
      del.className = "btn";
      del.textContent = "Delete Time Card";
      del.style.borderColor = "#fecaca";
      del.style.color = "#b91c1c";
      del.disabled = !canEdit;
      del.addEventListener("click", async () => {
        if (!canEdit) return;
        if (!confirm("Delete this time card?")) return;
        try {
          await apiDeleteTimecard(item.id);
          if (overlay && overlay.remove) overlay.remove();
          await refreshFn();
        } catch (e) { alert(e.message || String(e)); }
      });

      actions.appendChild(save);
      actions.appendChild(close);
      actions.appendChild(del);
      card.appendChild(actions);
    });
  }

  function renderTimeCardView() {
    setNavActive(navFormsTimeCard);
    setActiveChip("Forms");
    setWorkspace("Time Card");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>Time Card</h3><div class="hint">Fill out and save time card entries.</div>`;
 
    const form = document.createElement("div");
    form.className = "grid2";
    form.style.marginTop = "10px";
    form.innerHTML = `
      <div><div class="label">Employee</div><select class="input" id="tc_employee"></select></div>
      <div><div class="label">Date</div><input class="input" id="tc_date" type="date" /></div>
      <div><div class="label">Start Time</div><input class="input" id="tc_start" type="time" /></div>
      <div><div class="label">End Time</div><input class="input" id="tc_end" type="time" /></div>
      <div><div class="label">Lunch Taken</div><select class="input" id="tc_lunch_taken"><option value="no">No</option><option value="yes">Yes</option></select></div>
      <div><div class="label">Use PTO</div><select class="input" id="tc_use_pto"><option value="no">No</option><option value="yes">Yes</option></select></div>
      <div><div class="label">Lunch Start</div><input class="input" id="tc_lunch_start" type="time" /></div>
      <div><div class="label">Lunch End</div><input class="input" id="tc_lunch_end" type="time" /></div>
      <div><div class="label">PTO Hours</div><input class="input" id="tc_pto_hours" type="number" step="0.25" placeholder="0.00" /></div>
      <div><div class="label">Holiday Entry</div><select class="input" id="tc_is_holiday"><option value="no">No</option><option value="yes">Yes</option></select></div>
      <div><div class="label">Holiday Hours</div><input class="input" id="tc_holiday_hours" type="number" step="0.25" placeholder="0.00" /></div>
      <div><div class="label">Double Time Hours</div><input class="input" id="tc_double_time_hours" type="number" step="0.25" placeholder="0.00" /></div>
    `;
 
    const notes = document.createElement("div");
    notes.style.marginTop = "10px";
    notes.innerHTML = `<div class="label">Notes</div>`;
    const ta = document.createElement("textarea");
    notes.appendChild(ta);
 
    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "8px";
    actions.style.marginTop = "10px";
 
    const btnSave = document.createElement("button");
    btnSave.className = "btn btn-orange";
    btnSave.textContent = "Save Time Card";
 
    const btnRefresh = document.createElement("button");
    btnRefresh.className = "btn";
    btnRefresh.textContent = "Refresh";

    const filterWrap = document.createElement("div");
    filterWrap.style.display = "grid";
    filterWrap.style.gridTemplateColumns = "minmax(220px,320px)";
    filterWrap.style.gap = "8px";
    filterWrap.style.marginTop = "14px";
    filterWrap.innerHTML = `<div><div class="label">Filter by Technician</div><select class="input" id="tc_filter"><option value="">All Technicians</option></select></div>`;
 
    actions.appendChild(btnSave);
    actions.appendChild(btnRefresh);
 
    const list = document.createElement("div");
    list.style.marginTop = "14px";
 
    async function refresh() {
      const employees = await apiListEmployees().catch(() => []);
      const tcSel = form.querySelector("#tc_employee");
      const selfOnly = currentUser && ["tech", "lead"].includes(String(currentUser.role || ""));
      const selfName = (currentUser && (currentUser.name || currentUser.username)) ? String(currentUser.name || currentUser.username) : "";
      const current = tcSel.value;
      if (selfOnly) {
        tcSel.innerHTML = selfName ? `<option value="${escapeHtml(selfName)}">${escapeHtml(selfName)}</option>` : `<option value="">-- Select Employee --</option>`;
        tcSel.value = selfName;
        tcSel.disabled = true;
      } else {
        tcSel.disabled = false;
        tcSel.innerHTML = `<option value="">-- Select Employee --</option>`;
        employees.forEach(e => {
          const opt = document.createElement("option");
          opt.value = e.name;
          opt.textContent = e.name;
          tcSel.appendChild(opt);
        });
        if (current) tcSel.value = current;
      }

      const filterSel = filterWrap.querySelector("#tc_filter");
      const prevFilter = filterSel.value;
      if (selfOnly) {
        filterWrap.style.display = "none";
        filterSel.innerHTML = selfName ? `<option value="${escapeHtml(selfName)}">${escapeHtml(selfName)}</option>` : `<option value="">My Entries</option>`;
        filterSel.value = selfName;
      } else {
        filterWrap.style.display = "grid";
        filterSel.innerHTML = `<option value="">All Technicians</option>` + employees.map(e => `<option value="${escapeHtml(e.name || "")}">${escapeHtml(e.name || "")}</option>`).join("");
        if (prevFilter) filterSel.value = prevFilter;
      }
 
      try {
        const items = await apiListTimecards({ limit: 5000, ...(selfOnly && selfName ? { technician: selfName } : {}) });
        const activeFilter = (selfOnly ? selfName : filterSel.value).trim().toLowerCase();
        const filteredItems = activeFilter
          ? items.filter(t => String(t.technician_name || t.employee_name || t.employee || "").trim().toLowerCase() === activeFilter)
          : items;
        list.innerHTML = "";
        if (!filteredItems.length) {
          list.innerHTML = `<div class="hint">No time cards yet.</div>`;
          return;
        }
        filteredItems.forEach(t => {
          const hrs = calcTimeHours(
            t.start_time,
            t.end_time,
            !!t.lunch_taken,
            t.lunch_start,
            t.lunch_end
          );
 
          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `
            <div class="jobrow-top">
              <div class="jobrow-name">${escapeHtml(t.technician_name || t.employee_name || t.employee || "")}</div>
              <div class="hint">${hrs} hrs</div>
            </div>
            <div class="jobrow-addr">
              ${escapeHtml(formatDisplayDate(t.date || ""))} - ${escapeHtml(formatTimeRange12(t.start_time, t.end_time))}${t.notes ? ` - ${escapeHtml(t.notes)}` : ""}
            </div>
            <div class="hint" style="margin-top:6px;">${escapeHtml(lunchSummary(t))}${t.supervisor_approved ? ' - Supervisor Approved' : ''}${t.use_pto ? ` - PTO ${escapeHtml(String(t.pto_hours || 0))} hrs` : ''}${t.is_holiday ? ` - Holiday ${escapeHtml(String(t.holiday_hours || 0))} hrs` : ''}${getTimecardDoubleTimeHours(t) ? ` - DT ${escapeHtml(String(getTimecardDoubleTimeHours(t).toFixed(2)))} hrs` : ''}</div>
          `;
          row.addEventListener("click", () => openTimecardEditor(t, refresh));
          list.appendChild(row);
        });
      } catch (e) {
        list.innerHTML = `<div class="hint">Time cards unavailable: ${e.message || e}</div>`;
      }
    }
 
    btnSave.addEventListener("click", async () => {
      if (btnSave.disabled) return;
      const originalSaveText = btnSave.textContent || "Save";
      try {
        btnSave.disabled = true;
        btnSave.textContent = "Saving...";
        await apiCreateTimecard({
          technician_name: ((currentUser && ["tech", "lead"].includes(String(currentUser.role || ""))) ? String(currentUser.name || currentUser.username || "") : form.querySelector("#tc_employee").value.trim()),
          date: form.querySelector("#tc_date").value,
          start_time: form.querySelector("#tc_start").value,
          end_time: form.querySelector("#tc_end").value,
          lunch_taken: form.querySelector("#tc_lunch_taken").value === "yes",
          lunch_start: form.querySelector("#tc_lunch_start").value,
          lunch_end: form.querySelector("#tc_lunch_end").value,
          use_pto: form.querySelector("#tc_use_pto").value === "yes",
          pto_hours: Number(form.querySelector("#tc_pto_hours").value || 0),
          is_holiday: form.querySelector("#tc_is_holiday").value === "yes",
          holiday_hours: Number(form.querySelector("#tc_holiday_hours").value || 0),
          double_time_hours: Number(form.querySelector("#tc_double_time_hours").value || 0),
          notes: ta.value.trim(),
        });
        btnSave.textContent = "Saved ✓";
        showDoorksToast("Time card saved ✓");
        ta.value = "";
        form.querySelector("#tc_start").value = "";
        form.querySelector("#tc_end").value = "";
        form.querySelector("#tc_lunch_taken").value = "no";
        form.querySelector("#tc_lunch_start").value = "";
        form.querySelector("#tc_lunch_end").value = "";
        form.querySelector("#tc_pto_hours").value = "";
        form.querySelector("#tc_use_pto").value = "no";
        form.querySelector("#tc_date").value = new Date().toISOString().slice(0, 10);
        await refresh();
        setTimeout(() => {
          btnSave.disabled = false;
          btnSave.textContent = originalSaveText;
        }, 1600);
      } catch (e) {
        btnSave.disabled = false;
        btnSave.textContent = originalSaveText;
        alert(e.message || String(e));
      }
    });
 
    btnRefresh.addEventListener("click", refresh);
    filterWrap.querySelector("#tc_filter").addEventListener("change", refresh);
 
    root.appendChild(card);
    root.appendChild(form);
    root.appendChild(notes);
    root.appendChild(actions);
    root.appendChild(filterWrap);
    root.appendChild(list);
 
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    currentView = { refresh };
    refresh();
  }
 





  function renderPayrollView() {
    setNavActive(navPayroll);
    setActiveChip("Office Flow");
    setWorkspace("Payroll");
    clearWorkspaceActions();

    const exportBtn = document.createElement("button");
    exportBtn.className = "btn btn-orange";
    exportBtn.textContent = "Export Crew Payroll";
    workspaceActions.appendChild(exportBtn);

    const root = document.createElement("div");

    const controls = document.createElement("div");
    controls.className = "grid2";
    controls.style.marginTop = "12px";
    controls.innerHTML = `
      <div><div class="label">Month</div><input class="input" id="pay_month" type="month" /></div>
      <div>
        <div class="label">Custom Pay Period</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
          <input class="input" id="pay_start" type="date" />
          <input class="input" id="pay_end" type="date" />
        </div>
        <div class="hint">Optional: use start/end dates when pay period crosses months.</div>
      </div>
    `;
    root.appendChild(controls);

    const summaryWrap = document.createElement("div");
    summaryWrap.style.display = "grid";
    summaryWrap.style.gridTemplateColumns = "repeat(auto-fit, minmax(190px, 1fr))";
    summaryWrap.style.gap = "12px";
    summaryWrap.style.marginTop = "14px";
    root.appendChild(summaryWrap);

    const list = document.createElement("div");
    list.style.marginTop = "14px";
    root.appendChild(list);

    const metricCard = (label, value, hint = "") => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.padding = "14px";
      card.innerHTML = `
        <div style="font-size:12px;font-weight:800;opacity:.75;">${escapeHtml(label)}</div>
        <div style="font-size:30px;font-weight:900;line-height:1;">${escapeHtml(value)}</div>
        <div class="hint" style="margin-top:6px;">${escapeHtml(hint)}</div>
      `;
      return card;
    };

    const monthIncludesDate = (monthVal, dateStr) => {
      if (!monthVal) return true;
      if (!dateStr) return false;
      return String(dateStr).slice(0, 7) === monthVal;
    };

    const dateRangeIncludesDate = (startDate, endDate, dateStr) => {
      const d = String(dateStr || "").slice(0, 10);
      if (!d) return false;
      if (startDate && d < startDate) return false;
      if (endDate && d > endDate) return false;
      return true;
    };

    const getPayrollPeriod = () => {
      const monthVal = controls.querySelector("#pay_month")?.value || "";
      const startDate = controls.querySelector("#pay_start")?.value || "";
      const endDate = controls.querySelector("#pay_end")?.value || "";
      const hasRange = !!(startDate || endDate);
      const label = hasRange
        ? `${startDate || "Start"} to ${endDate || "End"}`
        : (monthVal || "Current");
      return { monthVal, startDate, endDate, hasRange, label };
    };

    const calcHoursForCard = (t) => calcTimeHours(
      t.start_time,
      t.end_time,
      !!t.lunch_taken,
      t.lunch_start,
      t.lunch_end
    );

    const dailyRegularHours = (hours) => Math.min(8, Math.max(0, hours));
    const dailyOtHours = (hours) => Math.max(0, hours - 8);

    function entryHoursBreakdown(entry) {
      const worked = calcHoursForCard(entry);
      const pto = entry && entry.use_pto ? getTimecardPtoHours(entry) : 0;
      const holiday = entry && entry.is_holiday ? getTimecardHolidayHours(entry) : 0;
      const doubleTime = getTimecardDoubleTimeHours(entry);
      const regularBase = Math.max(0, worked - doubleTime);
      const ot = dailyOtHours(regularBase);
      const regular = Math.max(0, dailyRegularHours(regularBase));
      const rollup = 0;
      return {
        worked,
        regular,
        ot,
        doubleTime,
        pto,
        holiday,
        rollup,
        total: worked + pto + holiday,
      };
    }

    function entriesBreakdown(entries) {
      return entries.reduce((acc, t) => {
        const b = entryHoursBreakdown(t);
        acc.worked += b.worked;
        acc.regular += b.regular;
        acc.ot += b.ot;
        acc.doubleTime += b.doubleTime;
        acc.pto += b.pto;
        acc.holiday += b.holiday;
        acc.rollup += b.rollup;
        acc.total += b.total;
        return acc;
      }, { worked: 0, regular: 0, ot: 0, doubleTime: 0, pto: 0, holiday: 0, rollup: 0, total: 0 });
    }

    async function payrollRollupDataForPeriod(period) {
      const jobs = await apiListJobs({ limit: 5000, _ts: Date.now() }).catch(() => []);
      const rows = [];
      const totals = {};
      const includeDate = (d) => {
        const date = String(d || "");
        if (!date) return false;
        return period && period.hasRange
          ? dateRangeIncludesDate(period.startDate, period.endDate, date)
          : monthIncludesDate(period && period.monthVal, date);
      };
      jobs.forEach(j => {
        formsOf(j).forEach(f => {
          const doorType = String(f.door_type || f.doorType || "").trim().toLowerCase();
          if (doorType !== "roll up") return;
          const d = f.date || f.form_date || f.created_at || j.date || j.created_at || "";
          if (!includeDate(d)) return;
          const tech = String(f.technician_name || f.tech || f.technician || "Unassigned").trim() || "Unassigned";
          const hrs = Math.max(0, Number(f.rollup_adjusted_hours ?? f.time_onsite_hours ?? f.hours ?? f.time ?? 0));
          if (!totals[tech]) totals[tech] = 0;
          totals[tech] += hrs;
          rows.push({
            date: d,
            employee: tech,
            customer: j.customer || j.customer_name || "",
            address: j.street_address || j.address || "",
            job_number: j.job_number || j.job || "",
            door_location: f.door_location || "",
            hours: hrs,
          });
        });
      });
      return { rows, totals, total: Object.values(totals).reduce((sum, v) => sum + Number(v || 0), 0) };
    }

    function approvedPtoHoursForEmployee(emp, approvedPto, approvedTimecards) {
      const timeoffHours = approvedPto
        .filter(t => employeeNameOfItem(t) === emp && !!t.use_pto)
        .reduce((sum, t) => sum + ptoHoursFromItem(t), 0);
      const tcHours = approvedTimecards
        .filter(t => employeeNameOfItem(t) === emp && !!t.use_pto)
        .reduce((sum, t) => sum + ptoHoursFromItem(t), 0);
      return timeoffHours + tcHours;
    }

    function buildCrewCsv(monthVal, filtered, approvedPto, rollupTotals = {}) {
      const employees = {};
      filtered.forEach(t => {
        const emp = employeeNameOfItem(t);
        if (!emp) return;
        if (!employees[emp]) employees[emp] = [];
        employees[emp].push(t);
      });
      let csv = "Employee,Period,Total Hours,Hours Worked,Regular Hours,OT Hours,Double Time Hours,Holiday Hours,PTO Bank,PTO Accrual Rate,PTO Used,PTO Remaining,Roll Up Hours,Approved Cards,Pending Cards\n";
      Object.keys(employees).sort((a,b)=>a.localeCompare(b)).forEach(emp => {
        const entries = employees[emp];
        const breakdown = entriesBreakdown(entries);
        const approvedCards = entries.filter(t => !!t.supervisor_approved).length;
        const pendingCards = entries.filter(t => !t.supervisor_approved).length;
        const ptoBank = getPtoBankHours(emp);
        const ptoUsed = approvedPtoHoursForEmployee(emp, approvedPto, entries.filter(t => !!t.supervisor_approved));
        const ptoRemaining = ptoBank - ptoUsed;
        const accrualRate = getPtoAccrualRate(emp);
        const rollupHours = Number(rollupTotals[emp] || 0);
        csv += `${emp},${monthVal || ""},${breakdown.total.toFixed(2)},${breakdown.worked.toFixed(2)},${breakdown.regular.toFixed(2)},${breakdown.ot.toFixed(2)},${breakdown.doubleTime.toFixed(2)},${breakdown.holiday.toFixed(2)},${ptoBank.toFixed(2)},${accrualRate.toFixed(2)},${ptoUsed.toFixed(2)},${ptoRemaining.toFixed(2)},${rollupHours.toFixed(2)},${approvedCards},${pendingCards}\n`;
      });
      return csv;
    }

    function downloadCsv(filename, csv) {
      const blob = new Blob(["\ufeff" + String(csv || "")], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || "export.csv";
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        try { document.body.removeChild(a); } catch (e) {}
        try { URL.revokeObjectURL(url); } catch (e) {}
      }, 500);
    }

    async function openTechBreakdown(emp, entries, period, approvedPto, rollupHours = 0, rollupRows = []) {
      const timeoffItems = await apiListTimeOff({ employee_name: emp, limit: 500 }).catch(() => []);
      const monthVal = period && period.monthVal ? period.monthVal : "";
      const monthTimeoff = timeoffItems.filter(t => {
        const d = itemDateOf(t);
        return period && period.hasRange ? dateRangeIncludesDate(period.startDate, period.endDate, d) : monthIncludesDate(monthVal, d);
      });

      openDrawer(`${emp} Payroll Breakdown`, (drawerBody, overlay) => {
        const wrap = document.createElement("div");
        wrap.className = "card";
        wrap.innerHTML = `<h3>${escapeHtml(emp)}</h3><div class="hint">${escapeHtml((period && period.label) || monthVal || "Current Month")}</div>`;

        const buttonRow = document.createElement("div");
        buttonRow.style.display = "flex";
        buttonRow.style.gap = "8px";
        buttonRow.style.marginTop = "12px";
        buttonRow.style.flexWrap = "wrap";

        const exportEmpBtn = document.createElement("button");
        exportEmpBtn.className = "btn btn-orange";
        exportEmpBtn.textContent = "Export Employee Report";
        exportEmpBtn.addEventListener("click", () => {
          const breakdown = entriesBreakdown(entries);
          const ptoBank = getPtoBankHours(emp);
          const ptoUsed = approvedPtoHoursForEmployee(emp, approvedPto, entries.filter(t => !!t.supervisor_approved));
          const ptoRemaining = ptoBank - ptoUsed;
          const otBank = getOtBankHours(emp);
          const otTotal = breakdown.ot + otBank;
          let csv = "Employee,Period,Total Hours,Hours Worked,Regular Hours,OT Hours,Double Time Hours,Holiday Hours,PTO Bank,PTO Accrual Rate,PTO Used,PTO Remaining,Roll Up Hours\n";
          csv += `${emp},${monthVal || ""},${breakdown.total.toFixed(2)},${breakdown.worked.toFixed(2)},${breakdown.regular.toFixed(2)},${breakdown.ot.toFixed(2)},${breakdown.doubleTime.toFixed(2)},${breakdown.holiday.toFixed(2)},${ptoBank.toFixed(2)},${getPtoAccrualRate(emp).toFixed(2)},${ptoUsed.toFixed(2)},${ptoRemaining.toFixed(2)},${Number(rollupHours || 0).toFixed(2)}\n\n`;
          csv += "Date,Time Range,Total Hours,Worked Hours,Regular Hours,OT Hours,Double Time Hours,Holiday Hours,PTO Used,PTO Hours,Approved,Notes\n";
          entries.slice().sort((a,b)=>String(itemDateOf(a)).localeCompare(String(itemDateOf(b)))).forEach(t => {
            const b = entryHoursBreakdown(t);
            csv += `${itemDateOf(t)},${formatTimeRange12(t.start_time, t.end_time)},${b.total.toFixed(2)},${b.worked.toFixed(2)},${b.regular.toFixed(2)},${b.ot.toFixed(2)},${b.doubleTime.toFixed(2)},${b.holiday.toFixed(2)},${t.use_pto ? "YES":"NO"},${Number(t.pto_hours || 0).toFixed(2)},${t.supervisor_approved ? "YES":"NO"},"${String(t.notes || "").replace(/"/g,'""')}"\n`;
          });
          csv += "\nRoll Up Detail From Data Center\n";
          csv += "Date,Customer,Address,Job Number,Door Location,Hours\n";
          rollupRows.slice().sort((a,b)=>String(a.date).localeCompare(String(b.date))).forEach(r => {
            const esc = (v) => `"${String(v || "").replace(/"/g, '""')}"`;
            csv += [esc(r.date), esc(r.customer), esc(r.address), esc(r.job_number), esc(r.door_location), Number(r.hours || 0).toFixed(2)].join(",") + "\n";
          });
          downloadCsv(`${emp.replace(/\s+/g, "_").toLowerCase()}_payroll_report.csv`, csv);
        });

        const ptoBankBtn = document.createElement("button");
        ptoBankBtn.className = "btn";
        ptoBankBtn.textContent = "PTO Bank";
        ptoBankBtn.addEventListener("click", () => {
          const current = getPtoBankHours(emp);
          const next = prompt(`Enter PTO hours available for ${emp}:`, String(current.toFixed(2)));
          if (next === null) return;
          const val = Number(next || 0);
          if (Number.isNaN(val)) return alert("Enter a valid PTO hour amount.");
          setPtoBankHours(emp, val);
          if (overlay && overlay.remove) overlay.remove();
          refresh();
        });

        const ptoAccrualBtn = document.createElement("button");
        ptoAccrualBtn.className = "btn";
        ptoAccrualBtn.textContent = "PTO Accrual";
        ptoAccrualBtn.addEventListener("click", () => {
          const current = getPtoAccrualRate(emp);
          const next = prompt(`Enter PTO accrual hours per pay period for ${emp}:`, String(current.toFixed(2)));
          if (next === null) return;
          const val = Number(next || 0);
          if (Number.isNaN(val)) return alert("Enter a valid PTO accrual rate.");
          setPtoAccrualRate(emp, val);
          if (overlay && overlay.remove) overlay.remove();
          refresh();
        });

        const applyAccrualBtn = document.createElement("button");
        applyAccrualBtn.className = "btn";
        applyAccrualBtn.textContent = "Apply PTO Accrual";
        applyAccrualBtn.addEventListener("click", () => {
          const added = addPtoAccrualToBank(emp);
          if (!added) return alert("Set a PTO accrual rate first.");
          if (overlay && overlay.remove) overlay.remove();
          refresh();
        });

        const otBankBtn = document.createElement("button");
        otBankBtn.className = "btn";
        otBankBtn.textContent = "Manual OT Adj";
        otBankBtn.addEventListener("click", () => {
          const current = getOtBankHours(emp);
          const next = prompt(`Enter manual OT adjustment hours for ${emp}:`, String(current.toFixed(2)));
          if (next === null) return;
          const val = Number(next || 0);
          if (Number.isNaN(val)) return alert("Enter a valid OT adjustment.");
          setOtBankHours(emp, val);
          if (overlay && overlay.remove) overlay.remove();
          refresh();
        });

        buttonRow.appendChild(exportEmpBtn);
        buttonRow.appendChild(ptoBankBtn);
        buttonRow.appendChild(ptoAccrualBtn);
        buttonRow.appendChild(applyAccrualBtn);
        buttonRow.appendChild(otBankBtn);
        wrap.appendChild(buttonRow);

        const totals = document.createElement("div");
        totals.style.display = "grid";
        totals.style.gridTemplateColumns = "repeat(auto-fit, minmax(150px, 1fr))";
        totals.style.gap = "10px";
        totals.style.marginTop = "12px";

        const breakdown = entriesBreakdown(entries);
        const approvedCount = entries.filter(t => !!t.supervisor_approved).length;
        const pendingCount = entries.filter(t => !t.supervisor_approved).length;
        const ptoUsed = approvedPtoHoursForEmployee(emp, approvedPto, entries.filter(t => !!t.supervisor_approved));
        const ptoBank = getPtoBankHours(emp);
        const ptoRemaining = ptoBank - ptoUsed;
        const otBank = getOtBankHours(emp);
        const otTotal = breakdown.ot + otBank;

        [
          metricCard("Total Hours", breakdown.total.toFixed(2), "Worked + PTO + holiday"),
          metricCard("Worked", breakdown.worked.toFixed(2)),
          metricCard("Regular", breakdown.regular.toFixed(2), "Up to 8 per day"),
          metricCard("OT", breakdown.ot.toFixed(2), "Over 8 per day"),
          metricCard("Double Time", breakdown.doubleTime.toFixed(2)),
          metricCard("Holiday", breakdown.holiday.toFixed(2)),
          metricCard("Roll Up Hours", Number(rollupHours || 0).toFixed(2), "From Roll Up Data Center"),
          metricCard("Manual OT Adj", otBank.toFixed(2)),
          metricCard("OT Total", otTotal.toFixed(2)),
          metricCard("Approved", `${approvedCount}/${entries.length}`),
          metricCard("Pending", String(pendingCount)),
          metricCard("PTO Bank", ptoBank.toFixed(2)),
          metricCard("PTO Accrual", getPtoAccrualRate(emp).toFixed(2), "Per pay period"),
          metricCard("PTO Used", ptoUsed.toFixed(2)),
          metricCard("PTO Remaining", ptoRemaining.toFixed(2)),
        ].forEach(c => totals.appendChild(c));
        wrap.appendChild(totals);

        const rows = document.createElement("div");
        rows.style.display = "grid";
        rows.style.gap = "8px";
        rows.style.marginTop = "12px";

        if (!entries.length) {
          rows.innerHTML = `<div class="hint">No time cards for this month.</div>`;
        } else {
          entries.slice().sort((a,b)=>String(itemDateOf(b)).localeCompare(String(itemDateOf(a)))).forEach(t => {
            const b = entryHoursBreakdown(t);
            const row = document.createElement("div");
            row.className = "jobrow";
            row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(formatDisplayDate(itemDateOf(t)) || "")}</div><div class="hint">${b.worked.toFixed(2)} hrs</div></div><div class="jobrow-addr">${escapeHtml(formatTimeRange12(t.start_time, t.end_time))}${t.notes ? ` - ${escapeHtml(t.notes)}` : ""}</div><div class="hint" style="margin-top:6px;">Total ${b.total.toFixed(2)} | Regular ${b.regular.toFixed(2)} | OT ${b.ot.toFixed(2)} | DT ${b.doubleTime.toFixed(2)} | Holiday ${b.holiday.toFixed(2)}${t.supervisor_approved ? ' - Supervisor Approved' : ' - Awaiting Approval'}${t.use_pto ? ` - PTO ${escapeHtml(String(Number(t.pto_hours || 0).toFixed(2)))} hrs` : ''}</div>`;
            const actions = document.createElement("div");
            actions.style.display = "flex";
            actions.style.gap = "8px";
            actions.style.marginTop = "8px";

            const viewBtn = document.createElement("button");
            viewBtn.className = "btn";
            viewBtn.textContent = "View Timecard";
            viewBtn.addEventListener("click", (e) => { e.stopPropagation(); openTimecardEditor(t, refresh); });

            const approveBtn = document.createElement("button");
            approveBtn.className = t.supervisor_approved ? "btn btn-orange" : "btn";
            approveBtn.textContent = t.supervisor_approved ? "Supervisor Approved" : "Supervisor Approval";
            approveBtn.addEventListener("click", async (e) => {
              e.stopPropagation();
              try {
                const payload = { ...t, supervisor_approved: !t.supervisor_approved, supervisor_approved_at: !t.supervisor_approved ? new Date().toISOString() : "" };
                await fetchJSON(`/timecards/${t.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
                const updatedEntries = entries.map(entry => entry.id === t.id ? { ...entry, supervisor_approved: payload.supervisor_approved, supervisor_approved_at: payload.supervisor_approved_at } : entry);
                if (overlay && overlay.remove) overlay.remove();
                await refresh();
                openTechBreakdown(emp, updatedEntries, period, approvedPto, rollupHours, rollupRows);
              } catch (e2) {
                alert(e2.message || String(e2));
              }
            });

            actions.appendChild(viewBtn);
            actions.appendChild(approveBtn);
            row.appendChild(actions);
            row.addEventListener("click", () => openTimecardEditor(t, refresh));
            rows.appendChild(row);
          });
        }
        wrap.appendChild(rows);
        drawerBody.appendChild(wrap);

        const rollupCard = document.createElement("div");
        rollupCard.className = "card";
        rollupCard.style.marginTop = "12px";
        rollupCard.innerHTML = `<h3>Roll Up Detail</h3><div class="hint">Pulled from Completion Forms / Data Center Roll Up, not manual timecard entry.</div>`;
        const rollRows = document.createElement("div");
        rollRows.style.display = "grid";
        rollRows.style.gap = "8px";
        rollRows.style.marginTop = "10px";
        if (!rollupRows.length) {
          rollRows.innerHTML = `<div class="hint">No roll up completion forms found for this pay period.</div>`;
        } else {
          rollupRows.slice().sort((a,b)=>String(b.date).localeCompare(String(a.date))).forEach(r => {
            const row = document.createElement("div");
            row.className = "jobrow";
            row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(formatDisplayDate(r.date) || "")}</div><div class="hint">${Number(r.hours || 0).toFixed(2)} hrs</div></div><div class="jobrow-addr">${escapeHtml(r.customer || "")}${r.job_number ? ` - Job #${escapeHtml(r.job_number)}` : ""}${r.door_location ? ` - ${escapeHtml(r.door_location)}` : ""}</div><div class="hint" style="margin-top:6px;">${escapeHtml(r.address || "")}</div>`;
            rollRows.appendChild(row);
          });
        }
        rollupCard.appendChild(rollRows);
        drawerBody.appendChild(rollupCard);

        const ptoCard = document.createElement("div");
        ptoCard.className = "card";
        ptoCard.style.marginTop = "12px";
        ptoCard.innerHTML = `<h3>PTO / Time Off</h3>`;
        const ptoRows = document.createElement("div");
        ptoRows.style.display = "grid";
        ptoRows.style.gap = "8px";
        ptoRows.style.marginTop = "10px";
        if (!monthTimeoff.length) {
          ptoRows.innerHTML = `<div class="hint">No time off entries for this month.</div>`;
        } else {
          monthTimeoff.slice().sort((a,b)=>String(itemDateOf(b)).localeCompare(String(itemDateOf(a)))).forEach(t => {
            const row = document.createElement("div");
            row.className = "jobrow";
            row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(formatDisplayDate(itemDateOf(t)) || "")}</div><div class="hint">${escapeHtml(t.status || "")}</div></div><div class="jobrow-addr">${escapeHtml(t.kind || "Time Off")}${t.use_pto ? ` - PTO ${escapeHtml(String(Number(t.pto_hours || 0).toFixed(2)))} hrs` : ''}${t.reason ? ` - ${escapeHtml(t.reason)}` : ""}</div>`;
            ptoRows.appendChild(row);
          });
        }
        ptoCard.appendChild(ptoRows);
        drawerBody.appendChild(ptoCard);
      });
    }

    async function refresh() {
      await ensureSharedSettingsLoaded();
      const items = await apiListTimecards({ limit: 5000 }).catch(() => []);
      const timeoff = await apiListTimeOff({ limit: 500 }).catch(() => []);
      const period = getPayrollPeriod();
      const monthVal = period.monthVal;

      const filtered = period.hasRange
        ? items.filter(t => dateRangeIncludesDate(period.startDate, period.endDate, itemDateOf(t)))
        : (monthVal ? items.filter(t => monthIncludesDate(monthVal, itemDateOf(t))) : items.slice());
      const employees = {};
      filtered.forEach(t => {
        const emp = employeeNameOfItem(t);
        if (!emp) return;
        if (!employees[emp]) employees[emp] = [];
        employees[emp].push(t);
      });

      const monthPto = period.hasRange
        ? timeoff.filter(t => dateRangeIncludesDate(period.startDate, period.endDate, itemDateOf(t)))
        : (monthVal ? timeoff.filter(t => monthIncludesDate(monthVal, itemDateOf(t))) : timeoff.slice());
      const approvedPto = monthPto.filter(t => String(t.status || "").toLowerCase() === "approved");
      const rollupData = await payrollRollupDataForPeriod(period);
      const rollupTotals = rollupData.totals || {};
      const rollupRows = rollupData.rows || [];

      const allBreakdowns = Object.values(employees).map(entriesBreakdown);
      const totalHours = allBreakdowns.reduce((sum, b) => sum + b.worked, 0);
      const totalRegular = allBreakdowns.reduce((sum, b) => sum + b.regular, 0);
      const totalOTWorked = allBreakdowns.reduce((sum, b) => sum + b.ot, 0);
      const totalDoubleTime = allBreakdowns.reduce((sum, b) => sum + b.doubleTime, 0);
      const totalHoliday = allBreakdowns.reduce((sum, b) => sum + b.holiday, 0);
      const totalRollup = Number(rollupData.total || 0);
      const totalPayrollHours = allBreakdowns.reduce((sum, b) => sum + b.total, 0);
      const totalOTBank = Object.keys(employees).reduce((sum, emp) => sum + getOtBankHours(emp), 0);
      const totalOT = totalOTWorked + totalOTBank;
      const totalPtoBank = Object.keys(employees).reduce((sum, emp) => sum + getPtoBankHours(emp), 0);
      const totalPtoUsed = Object.keys(employees).reduce((sum, emp) => sum + approvedPtoHoursForEmployee(emp, approvedPto, (employees[emp] || []).filter(t => !!t.supervisor_approved)), 0);
      const totalPtoRemaining = totalPtoBank - totalPtoUsed;
      const timecardEmployeeCount = Object.keys(employees).length;
      Object.keys(rollupTotals).forEach(emp => { if (emp && !employees[emp]) employees[emp] = []; });
      const uniqueEmployees = Object.keys(employees);
      const totalDaysOff = approvedPto.length;
      const pendingCards = filtered.filter(t => !t.supervisor_approved).length;
      const approvedCards = filtered.filter(t => !!t.supervisor_approved).length;
      const approvalRate = filtered.length ? Math.round((approvedCards / filtered.length) * 100) : 0;

      exportBtn.onclick = () => {
        const csv = buildCrewCsv(period.label, filtered, approvedPto, rollupTotals);
        downloadCsv("payroll_report.csv", csv);
      };

      summaryWrap.innerHTML = "";
      [
        metricCard("Employees", String(timecardEmployeeCount), "With timecards"),
        metricCard("Total Hours", totalPayrollHours.toFixed(2), "Worked + PTO + holiday"),
        metricCard("Hours Worked", totalHours.toFixed(2), period.label),
        metricCard("Regular Hours", totalRegular.toFixed(2), "Up to 8 per day"),
        metricCard("OT Hours", totalOT.toFixed(2), `Worked ${totalOTWorked.toFixed(2)} + Manual Adj ${totalOTBank.toFixed(2)}`),
        metricCard("Double Time", totalDoubleTime.toFixed(2), "Manual DT"),
        metricCard("Holiday Hours", totalHoliday.toFixed(2), "Timecard holiday"),
        metricCard("Roll Up Hours", totalRollup.toFixed(2), "From Data Center Roll Up"),
        metricCard("PTO Bank", totalPtoBank.toFixed(2), "Entered in payroll"),
        metricCard("PTO Used", totalPtoUsed.toFixed(2), "Approved PTO only"),
        metricCard("PTO Remaining", totalPtoRemaining.toFixed(2), "Bank minus used"),
        metricCard("Days Off", String(totalDaysOff), "Approved entries"),
        metricCard("Cards Pending", String(pendingCards), "Awaiting approval"),
        metricCard("Approval Rate", `${approvalRate}%`, `${approvedCards}/${filtered.length || 0} approved`),
      ].forEach(c => summaryWrap.appendChild(c));

      list.innerHTML = "";
      if (!uniqueEmployees.length) {
        list.innerHTML = `<div class="card"><div class="hint">No employee totals found for this month.</div></div>`;
        return;
      }

      const rows = document.createElement("div");
      rows.style.display = "grid";
      rows.style.gap = "10px";

      uniqueEmployees.sort((a,b)=>a.localeCompare(b)).forEach(emp => {
        const entries = employees[emp] || [];
        const breakdown = entriesBreakdown(entries);
        const empApproved = entries.filter(t => !!t.supervisor_approved).length;
        const empPending = entries.filter(t => !t.supervisor_approved).length;
        const empPtoItems = approvedPto.filter(t => employeeNameOfItem(t) === emp);
        const empDaysOff = empPtoItems.length;
        const empPtoBank = getPtoBankHours(emp);
        const empPtoUsed = approvedPtoHoursForEmployee(emp, approvedPto, entries.filter(t => !!t.supervisor_approved));
        const empPtoRemaining = empPtoBank - empPtoUsed;
        const empOtBank = getOtBankHours(emp);
        const empOtTotal = breakdown.ot + empOtBank;
        const empAccrualRate = getPtoAccrualRate(emp);
        const empRollup = Number(rollupTotals[emp] || 0);
        const latest = entries.slice().sort((a,b)=>String(itemDateOf(b)).localeCompare(String(itemDateOf(a))))[0] || null;
        const lastCardLabel = latest ? (formatDisplayDate(itemDateOf(latest)) || "—") : "—";

        const row = document.createElement("div");
        row.className = "jobrow";
        row.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(emp)}</div>
            <div class="hint">${breakdown.total.toFixed(2)} total hrs</div>
          </div>
          <div class="jobrow-addr">Worked ${breakdown.worked.toFixed(2)} | Regular ${breakdown.regular.toFixed(2)} | OT ${breakdown.ot.toFixed(2)} | DT ${breakdown.doubleTime.toFixed(2)} | Holiday ${breakdown.holiday.toFixed(2)} | Roll Up ${empRollup.toFixed(2)} | PTO Remaining ${empPtoRemaining.toFixed(2)} | PTO Accrual ${empAccrualRate.toFixed(2)}</div>
          <div class="hint" style="margin-top:6px;">Approved ${empApproved}/${entries.length} | Pending ${empPending} | Days Off ${empDaysOff} | Last card: ${escapeHtml(lastCardLabel)}</div>
        `;
        row.addEventListener("click", () => openTechBreakdown(emp, entries, period, approvedPto, empRollup, rollupRows.filter(r => r.employee === emp)));
        rows.appendChild(row);
      });

      list.appendChild(rows);
    }

    const monthInput = controls.querySelector("#pay_month");
    const startInput = controls.querySelector("#pay_start");
    const endInput = controls.querySelector("#pay_end");
    if (monthInput) {
      const now = new Date();
      monthInput.value = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2, "0")}`;
      monthInput.addEventListener("change", refresh);
    }
    if (startInput) startInput.addEventListener("change", refresh);
    if (endInput) endInput.addEventListener("change", refresh);

    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    refresh();
  }

  function renderDataCenterView() {
    setNavActive(navDataCenter);
    setActiveChip("Office Flow");
    const leadEstimatorOnly = !!(currentUser && currentUser.role === "lead");
    setWorkspace(leadEstimatorOnly ? "Data Center - Estimator Activity" : "Data Center");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const tabs = document.createElement("div");
    tabs.style.display = "flex";
    tabs.style.gap = "8px";
    tabs.style.flexWrap = "wrap";
 
    const btnDashboard = document.createElement("button"); btnDashboard.className = "btn btn-orange"; btnDashboard.textContent = "Productivity";
    const btnRollUp = document.createElement("button"); btnRollUp.className = "btn"; btnRollUp.textContent = "Roll Up";
    const btnEstimator = document.createElement("button"); btnEstimator.className = leadEstimatorOnly ? "btn btn-orange" : "btn"; btnEstimator.textContent = "Estimator Activity";
    if (leadEstimatorOnly) {
      tabs.appendChild(btnEstimator);
    } else {
      [btnDashboard, btnRollUp, btnEstimator].forEach(b => tabs.appendChild(b));
    }
 
    const monthBar = document.createElement("div");
    monthBar.style.display = "flex";
    monthBar.style.justifyContent = "space-between";
    monthBar.style.alignItems = "center";
    monthBar.style.margin = "12px 0";
    const prevBtn = document.createElement("button"); prevBtn.className = "btn"; prevBtn.innerHTML = "&larr; Prev Month";
    const monthText = document.createElement("div"); monthText.style.fontWeight = "1000"; monthText.style.fontSize = "18px";
    const nextBtn = document.createElement("button"); nextBtn.className = "btn"; nextBtn.innerHTML = "Next Month &rarr;";
    monthBar.append(prevBtn, monthText, nextBtn);
 
    const body = document.createElement("div");
    root.append(tabs, monthBar, body);
 
    let currentMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    let activeTab = leadEstimatorOnly ? "estimator" : "dashboard";
 
    const monthKey = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`;
    const monthPretty = d => d.toLocaleDateString(undefined,{month:"long", year:"numeric"});
    const setTab = () => { [[btnDashboard,"dashboard"],[btnRollUp,"rollup"],[btnEstimator,"estimator"]].forEach(([b,k]) => { b.className = activeTab===k ? "btn btn-orange" : "btn"; }); };
 
    async function loadData() {
      await ensureSharedSettingsLoaded();
      const month = monthKey(currentMonth);
      const [jobs, timecards, docs, documentApprovals] = await Promise.all([
        apiListJobs({ limit: 5000 }).catch(() => []),
        apiListTimecards({ limit: 5000 }).catch(() => []),
        apiListDocuments().catch(() => []),
        apiListDocumentApprovals().catch(() => ({})),
      ]);
      return {
        month,
        monthJobs: jobs.filter(j => String(j.date || j.created_at || "").startsWith(month)),
        monthTimecards: timecards.filter(t => String(t.date || t.created_at || "").startsWith(month)),
        monthDocs: docs.filter(d => String(d.created_at || "").startsWith(month)),
        documentApprovals: documentApprovals || {},
      };
    }

    async function resolveDataCenterJob(ref) {
      if (!ref) return null;
      const refId = String(ref.id || ref.job_id || "").trim();
      const refJobNumber = String(ref.job_number || "").trim();
      const refEstimate = cleanDocRef(ref.estimate_number || ref.number || "");
      const refCustomer = String(ref.customer || ref.customer_name || "").trim().toLowerCase();
      const jobs = await apiListJobs({ limit: 5000 }).catch(() => []);
      let match = null;
      if (refId) match = jobs.find(j => String(j.id || "").trim() === refId) || null;
      if (!match && refEstimate) {
        match = jobs.find(j => cleanDocRef(j.estimate_number || "") === refEstimate) || null;
      }
      if (!match && refJobNumber) {
        const candidates = jobs.filter(j => String(j.job_number || "").trim() === refJobNumber);
        match = candidates.sort((a,b) => String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || "")))[0] || null;
      }
      if (!match && refCustomer && refEstimate) {
        match = jobs.find(j => String(j.customer || "").trim().toLowerCase() === refCustomer && cleanDocRef(j.estimate_number || "") === refEstimate) || null;
      }
      return match || ref || null;
    }

    async function openDataCenterJob(ref) {
      const resolved = await resolveDataCenterJob(ref);
      if (!resolved) return;
      if (resolved.id) {
        try {
          const full = await apiGetJob(resolved.id);
          openDrawer("Job Details", (drawerBody) => {
            const local = document.createElement("div");
            drawerBody.appendChild(local);
            renderJobDetails(local, full, { afterSave: renderActiveTab, afterDelete: renderActiveTab });
          });
          return;
        } catch (e) {}
      }
      openDrawer(`Job ${resolved.job_number || "Details"}`, async (drawerBody) => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
          <h3 style="margin:0;">${escapeHtml(resolved.customer || resolved.customer_name || resolved.job_number || "Job")}</h3>
          <div class="hint" style="margin-top:6px;">${escapeHtml(resolved.job_number || "")}${resolved.estimate_number ? ` - Est ${escapeHtml(resolved.estimate_number)}` : ""}</div>
          <div class="grid2" style="margin-top:12px;">
            <div><div class="label">Customer</div><div class="field">${escapeHtml(resolved.customer || resolved.customer_name || "")}</div></div>
            <div><div class="label">Job #</div><div class="field">${escapeHtml(resolved.job_number || "")}</div></div>
            <div><div class="label">Estimate #</div><div class="field">${formatDocRefDisplay(resolved.estimate_number || resolved.number || "")}</div></div>
            <div><div class="label">Status</div><div class="field">${escapeHtml(resolved.status || "")}</div></div>
            <div><div class="label">Address</div><div class="field">${escapeHtml(resolved.street_address || resolved.address || "")}</div></div>
            <div><div class="label">Date</div><div class="field">${escapeHtml(formatDisplayDate(resolved.date || ""))}</div></div>
          </div>`;
        drawerBody.appendChild(card);
      });
    }
 
    async function renderDashboardTab() {
      body.innerHTML = "";
      const { month, monthJobs, monthTimecards, monthDocs } = await loadData();
      monthText.textContent = monthPretty(currentMonth);
      nextBtn.disabled = month >= monthKey(new Date());
      const forms = monthJobs.flatMap(j => formsOf(j).map(f => ({ ...f, __job: j })));
      const leads = monthJobs.filter(j => j.kind === "sales_lead");
      const completed = monthJobs.filter(j => ["Complete", "Complete/Quote", "Done"].includes(j.status));
      const dispatch = monthJobs.filter(j => j.status === "Dispatch");
      const estimates = monthDocs.filter(d => d.type === "estimate");
      const invoices = monthDocs.filter(d => d.type === "invoice");
      const onsiteHours = forms.reduce((sum, f) => sum + Number(f.time_onsite_hours || 0), 0);
      const tcHours = monthTimecards.reduce((sum, t) => sum + calcTimeHours(t.start_time, t.end_time, !!t.lunch_taken, t.lunch_start, t.lunch_end), 0);
      const techMap = {};
      forms.forEach(f => { const tech = f.technician_name || "Unassigned"; techMap[tech] = (techMap[tech] || 0) + Number(f.time_onsite_hours || 0); });
      monthTimecards.forEach(t => { const tech = t.technician_name || t.employee_name || t.employee || "Unassigned"; techMap[tech] = (techMap[tech] || 0) + calcTimeHours(t.start_time, t.end_time, !!t.lunch_taken, t.lunch_start, t.lunch_end); });
      const statGrid = document.createElement("div");
      statGrid.style.display = "grid"; statGrid.style.gridTemplateColumns = "repeat(auto-fit, minmax(180px, 1fr))"; statGrid.style.gap = "12px";
      [["Jobs Created", monthJobs.length],["Sales Leads", leads.length],["Dispatch", dispatch.length],["Quote Sent", estimates.length],["Completed", completed.length],["Estimates", estimates.length],["Invoices", invoices.length],["Onsite Hours", onsiteHours.toFixed(2)],["Timecard Hours", tcHours.toFixed(2)]].forEach(([label,val]) => {
        const c = document.createElement("div"); c.className = "card"; c.innerHTML = `<div class="label">${label}</div><div style="font-size:28px; font-weight:1000; margin-top:6px;">${val}</div><div class="hint" style="margin-top:6px;">${monthPretty(currentMonth)}</div>`; statGrid.appendChild(c);
      });
      body.appendChild(statGrid);

      const approved = monthJobs.filter(j => isApprovedEstimateJob(j, month));
      const findLinkedJob = (doc) => monthJobs.find(j => {
        const docEstimate = cleanDocRef(doc.number || doc.estimate_number || "");
        const jobEstimate = cleanDocRef(j.estimate_number || "");
        return (docEstimate && jobEstimate === docEstimate)
          || (String(doc.job_id || "").trim() && String(j.id || "").trim() === String(doc.job_id || "").trim())
          || (String(doc.job_number || "").trim() && String(j.job_number || "").trim() === String(doc.job_number || "").trim());
      }) || null;
      const sentQuotes = [];
      const seenQuoteKeys = new Set();
      estimates
        .slice()
        .sort((a,b) => String(b.date || b.created_at || "").localeCompare(String(a.date || a.created_at || "")))
        .forEach(d => {
          const estimateNo = cleanDocRef(d.number || d.estimate_number || "");
          const key = [estimateNo, String(d.job_id || "").trim(), String(d.job_number || "").trim()].join("|");
          if (seenQuoteKeys.has(key)) return;
          seenQuoteKeys.add(key);
          sentQuotes.push({ doc: d, job: findLinkedJob(d) });
        });

      const makeDataCenterRow = ({ title, statusLabel, statusKind, subtitle, address, clickItem, fallbackJob }) => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(title || "Job")}</div>${statusKind === "approved" ? statusPill("Approved").outerHTML : statusPill(statusLabel || "Quote Sent").outerHTML}</div><div class="jobrow-addr">${escapeHtml(subtitle || "")}</div><div class="hint">${escapeHtml(address || "")}</div>`;
        row.addEventListener("click", () => { openDataCenterJob(clickItem || fallbackJob || {}); });
        return row;
      };

      const approvalLayout=document.createElement("div"); approvalLayout.style.display="grid"; approvalLayout.style.gridTemplateColumns="1fr 1fr"; approvalLayout.style.gap="14px"; approvalLayout.style.marginTop="14px";
      const leftCard=document.createElement("div"); leftCard.className="card"; leftCard.innerHTML=`<h3>Quote Sent</h3><div class="hint">All estimates sent this month, even if later approved or denied.</div>`;
      const leftList=document.createElement("div"); leftList.style.marginTop="12px";
      if (!sentQuotes.length) leftList.innerHTML=`<div class="hint">No estimates were sent this month.</div>`;
      else sentQuotes.forEach(({doc, job})=>{
        const title = job?.customer || doc.customer || doc.customer_name || doc.job_number || cleanDocRef(doc.number || doc.estimate_number || "") || "Estimate";
        const subtitle = `${job?.job_number ? `Job #${job.job_number}` : (doc.job_number ? `Job #${doc.job_number}` : "")}${cleanDocRef(doc.number || doc.estimate_number || "") ? `${(job?.job_number || doc.job_number) ? ' - ' : ''}Est ${cleanDocRef(doc.number || doc.estimate_number || '')}` : ""}${job?.status ? ` - ${job.status}` : ""}`;
        const address = job?.street_address || job?.address || doc.address || "";
        leftList.appendChild(makeDataCenterRow({ title, statusLabel: job?.status || "Quote Sent", subtitle, address, clickItem: job || { id: doc.job_id, job_number: doc.job_number, customer: doc.customer || doc.customer_name || "", address: doc.address || "", estimate_number: cleanDocRef(doc.number || doc.estimate_number || ""), status: job?.status || "Quote Sent" }, fallbackJob: job }));
      });
      leftCard.appendChild(leftList);
      const rightCard=document.createElement("div"); rightCard.className="card"; rightCard.innerHTML=`<h3>Approved Jobs</h3><div class="hint">Customer - Job # - Estimate #</div>`;
      const rightList=document.createElement("div"); rightList.style.marginTop="12px";
      if (!approved.length) rightList.innerHTML=`<div class="hint">No approved jobs yet.</div>`;
      else approved.forEach(j=>{
        const subtitle = `${j.job_number ? `Job #${j.job_number}` : ""}${j.estimate_number ? `${j.job_number ? ' - ' : ''}Est ${j.estimate_number}` : ""}`;
        rightList.appendChild(makeDataCenterRow({ title: j.customer||j.job_number, statusKind: "approved", subtitle, address: j.street_address || j.address || "", clickItem: j, fallbackJob: j }));
      });
      rightCard.appendChild(rightList);
      approvalLayout.append(leftCard,rightCard);
      body.appendChild(approvalLayout);
    }
 


    async function renderRollUpTab() {
      body.innerHTML = "";
      const { month, monthJobs, monthTimecards } = await loadData();
      monthText.textContent = monthPretty(currentMonth);
      nextBtn.disabled = month >= monthKey(new Date());

      const formsForJob = (j) => formsOf(j).filter(f => {
        const isRollup = String(f.door_type || "").toLowerCase() === "roll up";
        const formDate = String(f.date || f.form_date || f.created_at || j.date || j.created_at || "");
        return isRollup && formDate.startsWith(month);
      });
      const allJobsForRollups = await apiListJobs({ limit: 5000, _ts: Date.now() }).catch(() => []);
      const rollUps = allJobsForRollups.filter(j => formsForJob(j).length > 0);

      const timecardRollups = monthTimecards.filter(t => {
        const note = `${t.customer || ""} ${t.job_number || ""} ${t.notes || t.description || ""}`.toLowerCase();
        return note.includes("roll up") || note.includes("rollup");
      });

      const techTotals = {};
      const detailRows = [];
      let totalFormHours = 0;
      let totalTimecardRollupHours = 0;

      rollUps.forEach(j => {
        const forms = formsForJob(j);
        forms.forEach(f => {
          const tech = String(f.technician_name || "Unassigned").trim() || "Unassigned";
          const hrs = Number(f.rollup_adjusted_hours ?? f.time_onsite_hours ?? 0);
          totalFormHours += hrs;
          techTotals[tech] = techTotals[tech] || { total: 0, jobs: 0 };
          techTotals[tech].total += hrs;
          techTotals[tech].jobs += 1;
          detailRows.push({
            date: f.date || f.form_date || j.date || j.created_at || "",
            customer: j.customer || j.customer_name || "",
            address: j.street_address || j.address || "",
            technician: tech,
            hours: hrs,
            status: j.status || "",
            job_number: j.job_number || "",
            door_location: f.door_location || "",
            source: "Completion Form",
            jobRef: j,
          });
        });
      });

      timecardRollups.forEach(t => {
        const tech = String(t.technician_name || t.employee_name || t.employee || "Unassigned").trim() || "Unassigned";
        const hrs = calcTimeHours(t.start_time, t.end_time, !!t.lunch_taken, t.lunch_start, t.lunch_end);
        totalTimecardRollupHours += hrs;
        techTotals[tech] = techTotals[tech] || { total: 0, jobs: 0 };
        techTotals[tech].total += hrs;
        detailRows.push({
          date: t.date || t.created_at || "",
          customer: t.customer || "",
          address: t.address || "",
          technician: tech,
          hours: hrs,
          status: "Timecard",
          job_number: t.job_number || "",
          door_location: "",
          source: "Timecard",
          jobRef: null,
        });
      });

      const totalHours = totalFormHours + totalTimecardRollupHours;
      const totalJobs = rollUps.length;
      const uniqueTechs = Object.keys(techTotals).length;
      const totalCost = detailRows.reduce((sum, r) => {
        const prof = getRollupProfile(r.technician, r.date);
        return sum + (Number(r.hours || 0) * Number(prof.wage || 0));
      }, 0);

      const exportBtn = document.createElement("button");
      exportBtn.className = "btn btn-orange";
      exportBtn.textContent = "Export Roll Up Report";
      exportBtn.addEventListener("click", () => {
        let csv = "Date,Customer,Address,Technician,Hours,Job Status,Job Number,Door Location,Source,Wage,Total Cost\n";
        detailRows.slice().sort((a,b)=>String(a.date).localeCompare(String(b.date))).forEach(r => {
          const prof = getRollupProfile(r.technician, r.date);
          const cost = Number(r.hours || 0) * Number(prof.wage || 0);
          const esc = (v) => `"${String(v || "").replace(/"/g, '""')}"`;
          csv += [esc(r.date), esc(r.customer), esc(r.address), esc(r.technician), Number(r.hours || 0).toFixed(2), esc(r.status), esc(r.job_number), esc(r.door_location), esc(r.source), Number(prof.wage || 0).toFixed(2), cost.toFixed(2)].join(",") + "\n";
        });
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "rollup_report.csv";
        a.click();
        URL.revokeObjectURL(url);
      });
      body.appendChild(exportBtn);

      const summaryWrap = document.createElement("div");
      summaryWrap.style.display = "grid";
      summaryWrap.style.gridTemplateColumns = "repeat(auto-fit, minmax(180px, 1fr))";
      summaryWrap.style.gap = "12px";
      summaryWrap.style.margin = "14px 0";

      const metricCard = (label, value, hint = "") => {
        const card = document.createElement("div");
        card.className = "card";
        card.style.padding = "14px";
        card.innerHTML = `
          <div style="font-size:12px;font-weight:800;opacity: ""}</div>
          <div style="font-size:30px;font-weight:900;line-height:1;">${escapeHtml(value)}</div>
          <div class="hint" style="margin-top:6px;">${escapeHtml(hint)}</div>
        `;
        return card;
      };

      [
        metricCard("Roll Up Jobs", String(totalJobs), monthPretty(currentMonth)),
        metricCard("Entries", String(detailRows.length), "Logged roll up entries"),
        metricCard("Total Hours", totalHours.toFixed(2), "All technicians"),
        metricCard("Technicians", String(uniqueTechs), "With roll up hours"),
        metricCard("Total Cost", totalCost.toFixed(2), "Hours × wage"),
      ].forEach(c => summaryWrap.appendChild(c));
      body.appendChild(summaryWrap);

      const layout = document.createElement("div");
      layout.style.display = "grid";
      layout.style.gridTemplateColumns = "1.35fr 1fr";
      layout.style.gap = "14px";

      const leftCard = document.createElement("div");
      leftCard.className = "card";
      leftCard.innerHTML = `<h3>Roll Up Log</h3><div class="hint">${totalJobs} jobs | ${detailRows.length} entries | ${totalHours.toFixed(2)} hrs</div>`;

      const leftList = document.createElement("div");
      leftList.style.marginTop = "12px";
      if (!detailRows.length) {
        leftList.innerHTML = `<div class="hint">No matching roll up jobs for this month.</div>`;
      } else {
        detailRows
          .slice()
          .sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")))
          .forEach(r => {
            const prof = getRollupProfile(r.technician, r.date);
            const cost = Number(r.hours || 0) * Number(prof.wage || 0);
            const row = document.createElement("div");
            row.className = "jobrow";
            row.style.cursor = r.jobRef ? "pointer" : "default";
            row.innerHTML = `
              <div class="jobrow-top">
                <div class="jobrow-name">${escapeHtml(formatDisplayDate(r.date) || r.customer || r.job_number || "Roll Up Entry")}</div>
                <div class="hint">${Number(r.hours || 0).toFixed(2)} hrs</div>
              </div>
              <div class="jobrow-addr">${escapeHtml(r.customer || "")}${r.job_number ? ` - Job #${escapeHtml(r.job_number)}` : ""}${r.door_location ? ` - ${escapeHtml(r.door_location)}` : ""}</div>
              <div class="hint" style="margin-top:6px;">${escapeHtml(r.address || "")}</div>
              <div class="hint" style="margin-top:6px;">${escapeHtml(r.technician)} - ${escapeHtml(r.status || "")} - Wage ${Number(prof.wage || 0).toFixed(2)} - Cost ${cost.toFixed(2)}</div>
            `;
            if (r.jobRef) row.addEventListener("click", () => openDataCenterJob(r.jobRef));
            leftList.appendChild(row);
          });
      }
      leftCard.appendChild(leftList);

      const rightCard = document.createElement("div");
      rightCard.className = "card";
      rightCard.innerHTML = `<h3>Technician Roll Up Report</h3><div class="hint">${monthPretty(currentMonth)}</div>`;

      const rightList = document.createElement("div");
      rightList.style.marginTop = "12px";
      const techRows = Object.entries(techTotals)
        .map(([tech, data]) => {
          const total = Number(data.total || 0);
          return [tech, { ...data, total }];
        })
        .sort((a, b) => b[1].total - a[1].total);

      if (!techRows.length) {
        rightList.innerHTML = `<div class="hint">No technician hours logged yet.</div>`;
      } else {
        techRows.forEach(([tech, data]) => {
          const prof = getRollupProfile(tech, month);
          const totalCostTech = detailRows
            .filter(r => r.technician === tech)
            .reduce((sum, r) => {
              const rowProf = getRollupProfile(tech, r.date);
              return sum + (Number(r.hours || 0) * Number(rowProf.wage || 0));
            }, 0);

          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `
            <div class="jobrow-top">
              <div class="jobrow-name">${escapeHtml(tech)}</div>
              <div class="hint">${Number(data.total).toFixed(2)} hrs</div>
            </div>
            <div class="jobrow-addr">Total Hours ${Number(data.total).toFixed(2)} | Jobs ${data.jobs || 0}</div>
            <div class="hint" style="margin-top:6px;">Wage ${Number(prof.wage || 0).toFixed(2)} | Total Cost ${totalCostTech.toFixed(2)}</div>
          `;

          const actions = document.createElement("div");
          actions.style.display = "flex";
          actions.style.gap = "8px";
          actions.style.marginTop = "8px";

          const editBtn = document.createElement("button");
          editBtn.className = "btn";
          editBtn.textContent = "Edit Wage";
          editBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const effectiveMonth = monthKey(currentMonth);
            const wage = prompt(`Hourly wage for ${tech} effective ${monthPretty(currentMonth)} and forward:`, String(Number(prof.wage || 0).toFixed(2)));
            if (wage === null) return;
            const wageNum = Number(wage || 0);
            if (Number.isNaN(wageNum)) return alert("Enter a valid wage.");
            setRollupProfile(tech, wageNum, 1, effectiveMonth);
            renderActiveTab();
          });

          const exportTechBtn = document.createElement("button");
          exportTechBtn.className = "btn btn-orange";
          exportTechBtn.textContent = "Export";
          exportTechBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            let csv = "Date,Customer,Address,Technician,Hours,Job Status,Job Number,Door Location,Source,Wage,Total Cost\n";
            detailRows.filter(r => r.technician === tech).forEach(r => {
              const p = getRollupProfile(tech, r.date);
              const cost = Number(r.hours || 0) * Number(p.wage || 0);
              const esc = (v) => `"${String(v || "").replace(/"/g, '""')}"`;
              csv += [esc(r.date), esc(r.customer), esc(r.address), esc(r.technician), Number(r.hours || 0).toFixed(2), esc(r.status), esc(r.job_number), esc(r.door_location), esc(r.source), Number(p.wage || 0).toFixed(2), cost.toFixed(2)].join(",") + "\n";
            });
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${tech.replace(/\s+/g, "_").toLowerCase()}_rollup_report.csv`;
            a.click();
            URL.revokeObjectURL(url);
          });

          actions.appendChild(editBtn);
          actions.appendChild(exportTechBtn);
          row.appendChild(actions);
          rightList.appendChild(row);
        });
      }
      rightCard.appendChild(rightList);

      layout.append(leftCard, rightCard);
      body.appendChild(layout);
    }

    async function renderApprovalTab() {
      body.innerHTML="";
      const { month, monthJobs } = await loadData();
      monthText.textContent = monthPretty(currentMonth); nextBtn.disabled = month >= monthKey(new Date());
      const quoteSent = monthJobs.filter(j => j.status === "Quote Sent");
      const approved = monthJobs.filter(j => isApprovedEstimateJob(j, month));
      const layout=document.createElement("div"); layout.style.display="grid"; layout.style.gridTemplateColumns="1fr 1fr"; layout.style.gap="14px";
      const leftCard=document.createElement("div"); leftCard.className="card"; leftCard.innerHTML=`<h3>Quote Sent</h3><div class="hint">Waiting on approval</div>`;
      const leftList=document.createElement("div"); leftList.style.marginTop="12px";
      if (!quoteSent.length) leftList.innerHTML=`<div class="hint">No records currently in Quote Sent.</div>`;
      else quoteSent.forEach(j=>{ const row=document.createElement("div"); row.className="jobrow"; row.innerHTML=`<div class="jobrow-top"><div class="jobrow-name">${j.customer||j.job_number}</div>${statusPill(j.status).outerHTML}</div><div class="jobrow-addr">${j.customer||""}${j.job_number?` - Job #${j.job_number}`:""}${j.estimate_number?` - Est ${j.estimate_number}`:""}</div><div class="hint">${j.street_address || j.address || ""}</div>`; leftList.appendChild(row);});
      leftCard.appendChild(leftList);
      const rightCard=document.createElement("div"); rightCard.className="card"; rightCard.innerHTML=`<h3>Approved Jobs</h3><div class="hint">Customer - Job # - Estimate #</div>`;
      const rightList=document.createElement("div"); rightList.style.marginTop="12px";
      if (!approved.length) rightList.innerHTML=`<div class="hint">No approved jobs yet.</div>`;
      else approved.forEach(j=>{ const row=document.createElement("div"); row.className="jobrow"; row.innerHTML=`<div class="jobrow-top"><div class="jobrow-name">${j.customer||j.job_number}</div><div class="hint">Approved</div></div><div class="jobrow-addr">${j.customer||""}${j.job_number?` - Job #${j.job_number}`:""}${j.estimate_number?` - Est ${j.estimate_number}`:""}</div><div class="hint">${j.street_address || j.address || ""}</div>`; rightList.appendChild(row);});
      rightCard.appendChild(rightList); layout.append(leftCard,rightCard); body.appendChild(layout);
    }
 
    async function renderEstimatorTab() {
      body.innerHTML = "";
      const { month, monthJobs, monthDocs, documentApprovals } = await loadData();
      monthText.textContent = monthPretty(currentMonth);
      nextBtn.disabled = month >= monthKey(new Date());

      const approvedJobs = monthJobs.filter(j => isApprovedEstimateJob(j, month));
      const approvedEstimateNumbers = new Set(
        approvedJobs.map(j => cleanDocRef(j.estimate_number || j.estimate_no || "")).filter(Boolean)
      );
      const approvedJobIds = new Set(approvedJobs.map(j => String(j.id || "").trim()).filter(Boolean));
      const approvedJobNumbers = new Set(approvedJobs.map(j => String(j.job_number || "").trim()).filter(Boolean));

      const estimateDetailsByEmployee = {};
      monthDocs.filter(d => d.type === "estimate").forEach(d => {
        const who = String(d.completed_by || d.created_by || "Unassigned").trim() || "Unassigned";
        if (!estimateDetailsByEmployee[who]) estimateDetailsByEmployee[who] = [];
        const estimateNo = cleanDocRef(d.number || d.estimate_number || d.estimate_no || "");
        const docJobId = String(d.job_id || "").trim();
        const docJobNumber = String(d.job_number || "").trim();
        const linkedJob = monthJobs.find(j => {
          const jobEstimate = cleanDocRef(j.estimate_number || j.estimate_no || "");
          return (estimateNo && jobEstimate === estimateNo)
            || (docJobId && String(j.id || "").trim() === docJobId)
            || (docJobNumber && String(j.job_number || "").trim() === docJobNumber);
        }) || null;

        const approvalKey = documentApprovalKey(d);
        const approvalOverride = (documentApprovals && documentApprovals[approvalKey]) || null;
        const isApprovedFromJob = !!(
          (estimateNo && approvedEstimateNumbers.has(estimateNo)) ||
          (docJobId && approvedJobIds.has(docJobId)) ||
          (docJobNumber && approvedJobNumbers.has(docJobNumber)) ||
          (linkedJob && isApprovedEstimateJob(linkedJob, month))
        );
        const hasStandaloneOverride = approvalOverride && Object.prototype.hasOwnProperty.call(approvalOverride, "approved");
        const isApproved = hasStandaloneOverride ? !!approvalOverride.approved : isApprovedFromJob;

        estimateDetailsByEmployee[who].push({
          ...d,
          __estimateNo: estimateNo,
          __approved: isApproved,
          __approvalKey: approvalKey,
          __approvalOverride: approvalOverride,
          __linkedJob: linkedJob
        });
      });

      const leaderboard = Object.entries(estimateDetailsByEmployee).map(([name, docs]) => {
        const sent = docs.length;
        const approved = docs.filter(d => d.__approved).length;
        return {
          name,
          sent,
          approved,
          docs: docs.slice().sort((a,b) => String(b.date || b.created_at || "").localeCompare(String(a.date || a.created_at || "")))
        };
      }).sort((a,b) => (b.sent - a.sent) || (b.approved - a.approved) || a.name.localeCompare(b.name));

      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `<h3>Employee Estimate Activity</h3><div class="hint">${monthPretty(currentMonth)} - ranked by estimates sent</div>`;

      const list = document.createElement("div");
      list.style.marginTop = "12px";

      if (!leaderboard.length) {
        list.innerHTML = `<div class="hint">No employee estimates found for this month.</div>`;
      } else {
        leaderboard.forEach((entry) => {
          const rowWrap = document.createElement("div");
          rowWrap.style.marginBottom = "10px";

          const row = document.createElement("div");
          row.className = "jobrow estimator-parent-row";
          row.style.cursor = "pointer";
          row.innerHTML = `
            <div class="jobrow-top">
              <div class="jobrow-name">${escapeHtml(entry.name)}</div>
              <div class="hint">${entry.sent} sent • ${entry.approved} approved</div>
            </div>
            <div class="hint" style="margin-top:6px;">Click to view estimate numbers</div>
          `;

          const inline = document.createElement("div");
          inline.className = "estimator-inline-list";
          inline.style.display = "none";
          inline.style.margin = "8px 0 0 14px";

          const renderInline = () => {
            inline.innerHTML = "";
            if (!entry.docs.length) {
              inline.innerHTML = `<div class="hint" style="padding:6px 0 2px 0;">No estimates found for ${escapeHtml(entry.name)}.</div>`;
              return;
            }
            entry.docs.forEach((d) => {
              const estimateNo = d.__estimateNo || cleanDocRef(d.number || d.estimate_number || d.estimate_no || "") || "Estimate";
              const linkedJob = d.__linkedJob;
              const customer = (linkedJob && linkedJob.customer) || d.customer || d.customer_name || "";
              const jobNo = (linkedJob && linkedJob.job_number) || d.job_number || "";
              const docDate = formatDisplayDate(d.date || d.created_at || "");
              const item = document.createElement("div");
              item.className = "jobrow";
              item.style.cursor = linkedJob ? "pointer" : "default";
              item.style.marginBottom = "8px";
              item.innerHTML = `
                <div class="jobrow-top">
                  <div class="jobrow-name">${escapeHtml(estimateNo)}</div>
                  <div class="hint">${d.__approved ? "Approved" : "Sent"}</div>
                </div>
                <div class="jobrow-addr">${escapeHtml(customer || "")}${jobNo ? ` - Job #${escapeHtml(jobNo)}` : ""}</div>
                <div class="hint" style="margin-top:6px;">${escapeHtml(docDate || "")}</div>
              `;
              const actions = document.createElement("div");
              actions.style.display = "flex";
              actions.style.gap = "8px";
              actions.style.flexWrap = "wrap";
              actions.style.marginTop = "8px";

              if (linkedJob) {
                const openBtn = document.createElement("button");
                openBtn.className = "btn";
                openBtn.textContent = "Open Job";
                openBtn.addEventListener("click", (ev) => { ev.stopPropagation(); openDataCenterJob(linkedJob); });
                actions.appendChild(openBtn);
                item.addEventListener("click", (ev) => { ev.stopPropagation(); openDataCenterJob(linkedJob); });
              }

              const approvalBtn = document.createElement("button");
              approvalBtn.className = d.__approved ? "btn" : "btn btn-orange";
              approvalBtn.textContent = d.__approved ? "Mark Not Approved" : "Mark Approved";
              approvalBtn.addEventListener("click", async (ev) => {
                ev.stopPropagation();
                try {
                  const nextApproved = !d.__approved;
                  const approvedAt = nextApproved ? new Date().toISOString() : "";
                  if (linkedJob && linkedJob.id) {
                    const savedJob = await apiUpdateJob(linkedJob.id, {
                      approved: nextApproved,
                      approved_at: approvedAt
                    });
                    d.__linkedJob = savedJob || linkedJob;
                  }
                  await apiSetDocumentApproval(d.__approvalKey || documentApprovalKey(d), {
                    approved: nextApproved,
                    approved_at: approvedAt,
                    estimate_number: d.__estimateNo || cleanDocRef(d.number || d.estimate_number || d.estimate_no || ""),
                    filename: d.filename || "",
                    customer: customer || "",
                  });
                  d.__approved = nextApproved;
                  await renderEstimatorTab();
                } catch (e) {
                  alert(e.message || String(e));
                }
              });

              actions.appendChild(approvalBtn);
              item.appendChild(actions);
              inline.appendChild(item);
            });
          };

          row.addEventListener("click", () => {
            const willOpen = inline.style.display === "none";
            list.querySelectorAll(".estimator-inline-list").forEach(el => { el.style.display = "none"; });
            list.querySelectorAll(".estimator-parent-row").forEach(el => { el.classList.remove("navbtn-active"); });
            if (willOpen) {
              renderInline();
              inline.style.display = "block";
              row.classList.add("navbtn-active");
            } else {
              inline.style.display = "none";
              row.classList.remove("navbtn-active");
            }
          });

          rowWrap.appendChild(row);
          rowWrap.appendChild(inline);
          list.appendChild(rowWrap);
        });
      }

      card.appendChild(list);
      body.appendChild(card);
    }

    async function renderActiveTab() { setTab(); if (activeTab==="rollup") return renderRollUpTab(); if (activeTab==="estimator") return renderEstimatorTab(); return renderDashboardTab(); }
    if (!leadEstimatorOnly) btnDashboard.addEventListener("click",()=>{activeTab="dashboard";renderActiveTab();});
    if (!leadEstimatorOnly) btnRollUp.addEventListener("click",()=>{activeTab="rollup";renderActiveTab();});
    btnEstimator.addEventListener("click",()=>{activeTab="estimator";renderActiveTab();});
    prevBtn.addEventListener("click",()=>{currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth()-1, 1); renderActiveTab();});
    nextBtn.addEventListener("click",()=>{currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth()+1, 1); renderActiveTab();});
    workspaceBody.innerHTML=""; workspaceBody.appendChild(root); currentView={ refresh: renderActiveTab }; renderActiveTab();
  }
 
function renderCustomersView() {
    setNavActive(navCustomers);
    setActiveChip("Work Flow");
    setWorkspace("Customers");
    clearWorkspaceActions();

    const root = document.createElement("div");
    const header = document.createElement("div");
    header.className = "card";
    header.innerHTML = `<h3>Customers</h3><div class="hint">Manage customers, contacts, and saved addresses.</div>`;

    const tabs = document.createElement("div");
    tabs.style.display = "flex";
    tabs.style.gap = "8px";
    tabs.style.marginTop = "12px";
    tabs.style.flexWrap = "wrap";

    const btnCustomers = document.createElement("button");
    btnCustomers.className = "btn btn-orange";
    btnCustomers.textContent = "Customers";
    const btnContacts = document.createElement("button");
    btnContacts.className = "btn";
    btnContacts.textContent = "Contacts";
    const btnAddresses = document.createElement("button");
    btnAddresses.className = "btn";
    btnAddresses.textContent = "Addresses";
    tabs.append(btnCustomers, btnContacts, btnAddresses);

    const body = document.createElement("div");
    body.style.marginTop = "14px";

    let activeTab = "customers";

    function setTab(tab) {
      activeTab = tab;
      btnCustomers.className = tab === "customers" ? "btn btn-orange" : "btn";
      btnContacts.className = tab === "contacts" ? "btn btn-orange" : "btn";
      btnAddresses.className = tab === "addresses" ? "btn btn-orange" : "btn";
    }

    function itemMatches(item, q, keys) {
      if (!q) return true;
      const hay = keys.map(k => String(item?.[k] || "")).join(" ").toLowerCase();
      return hay.includes(String(q || "").toLowerCase());
    }

    async function editCustomer(item) {
      const company_name = (prompt("Customer name:", item.company_name || "") || "").trim();
      if (!company_name) return;
      const address = (prompt("Street Address:", item.address || "") || "").trim();
      const phone_number = (prompt("Phone:", item.phone_number || "") || "").trim();
      const email = (prompt("Email:", item.email || "") || "").trim();
      const notes = (prompt("Notes:", item.notes || "") || "").trim();
      await apiUpdateCustomer(item.id, {
        company_name,
        address,
        city: item.city || "",
        state: item.state || "",
        zip_code: item.zip_code || "",
        phone_number,
        email,
        notes,
      });
      await renderCustomersTab();
    }

    async function editContact(item, customers) {
      const name = (prompt("Contact name:", item.name || "") || "").trim();
      if (!name) return;
      const company_name = (prompt("Company:", item.company_name || "") || "").trim();
      const phone_number = (prompt("Phone:", item.phone_number || "") || "").trim();
      const cell_phone = (prompt("Cell phone:", item.cell_phone || "") || "").trim();
      const email = (prompt("Email:", item.email || "") || "").trim();
      const title = (prompt("Title:", item.title || "") || "").trim();
      const notes = (prompt("Notes:", item.notes || "") || "").trim();
      const matched = (customers || []).find(c => normalizeText(c.company_name) === normalizeText(company_name));
      await apiUpdateContact(item.id, {
        name,
        company_name,
        customer_id: matched ? matched.id || "" : item.customer_id || "",
        phone_number,
        cell_phone,
        email,
        title,
        notes,
      });
      await renderContactsTab();
    }

    async function editAddress(item) {
      if (item.readonly || String(item.source || "") !== "saved") {
        alert("Legacy CSV addresses are read-only. Add this as a saved address if you need to edit it.");
        return;
      }
      const customer = (prompt("Customer:", item.customer || item.company_name || "") || "").trim();
      const address = (prompt("Street Address:", item.address || "") || "").trim();
      if (!address) return;
      const label = (prompt("Label / Location:", item.label || "") || "").trim();
      const notes = (prompt("Notes:", item.notes || "") || "").trim();
      await apiUpdateAddress(item.id, { customer, company_name: customer, address, label, notes });
      await renderAddressesTab();
    }

    async function renderCustomersTab() {
      setTab("customers");
      const items = await apiListCustomers().catch(() => []);
      body.innerHTML = "";
      const panel = document.createElement("div");
      panel.className = "card";
      panel.innerHTML = `
        <h3>Customers</h3>
        <div class="hint">Search, add, and edit customers.</div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:10px;">
          <input class="input" id="cust_search" placeholder="Search customers, address, phone, email..." style="flex:1; min-width:220px;" />
          <button class="btn btn-orange" id="cust_add">Add Customer</button>
        </div>
        <div id="cust_list" style="display:grid; gap:8px; margin-top:12px;"></div>
      `;
      body.appendChild(panel);
      const list = panel.querySelector("#cust_list");
      const search = panel.querySelector("#cust_search");

      function renderList() {
        const q = search.value.trim();
        const filtered = items.filter(c => itemMatches(c, q, ["company_name", "address", "phone_number", "email", "notes"]));
        list.innerHTML = "";
        if (!filtered.length) { list.innerHTML = `<div class="hint">No customers found.</div>`; return; }
        filtered.forEach(c => {
          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `
            <div class="jobrow-top">
              <div>
                <div class="jobrow-name">${escapeHtml(c.company_name || "")}</div>
                <div class="jobrow-addr">${escapeHtml(c.address || "")}</div>
                <div class="hint">${escapeHtml(c.phone_number || "")}${c.email ? ` - ${escapeHtml(c.email)}` : ""}</div>
              </div>
              <button class="btn" data-edit> Edit </button>
            </div>
          `;
          row.querySelector("[data-edit]").addEventListener("click", () => editCustomer(c));
          list.appendChild(row);
        });
      }

      panel.querySelector("#cust_add").addEventListener("click", async () => {
        const name = (prompt("Customer name:") || "").trim();
        if (!name) return;
        const address = (prompt("Street address (optional):") || "").trim();
        const phone = (prompt("Phone (optional):") || "").trim();
        const email = (prompt("Email (optional):") || "").trim();
        const created = await apiCreateCustomer({ company_name: name, address, phone_number: phone, email });
        await renderCustomersTab();
      });

      search.addEventListener("input", renderList);
      renderList();
    }

    async function renderContactsTab() {
      setTab("contacts");
      const [items, customers] = await Promise.all([apiListContacts().catch(() => []), apiListCustomers().catch(() => [])]);
      body.innerHTML = "";
      const companyListId = `contact-company-${Math.random().toString(36).slice(2)}`;
      const panel = document.createElement("div");
      panel.className = "card";
      panel.innerHTML = `
        <h3>Contacts</h3>
        <div class="grid2">
          <div><div class="label">Name</div><input class="input" id="cont_name" /></div>
          <div><div class="label">Company</div><input class="input" id="cont_company" list="${companyListId}" placeholder="Link to existing customer" /></div>
          <div><div class="label">Phone</div><input class="input" id="cont_phone" /></div>
          <div><div class="label">Email</div><input class="input" id="cont_email" /></div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:10px;">
          <button class="btn btn-orange" id="cont_add">Add Contact</button>
        </div>
        <div style="margin-top:12px;"><input class="input" id="cont_search" placeholder="Search contacts, company, phone, email..." /></div>
        <div id="cont_list" style="display:grid; gap:8px; margin-top:12px;"></div>
      `;
      panel.appendChild(buildCustomerDatalist(companyListId, customers));
      body.appendChild(panel);
      const list = panel.querySelector("#cont_list");
      const search = panel.querySelector("#cont_search");

      function renderList() {
        const q = search.value.trim();
        const filtered = items.filter(c => itemMatches(c, q, ["name", "company_name", "phone_number", "cell_phone", "email", "title", "notes"]));
        list.innerHTML = "";
        if (!filtered.length) { list.innerHTML = `<div class="hint">No contacts found.</div>`; return; }
        filtered.forEach(c => {
          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `
            <div class="jobrow-top">
              <div>
                <div class="jobrow-name">${escapeHtml(c.name || "")}</div>
                <div class="hint">${escapeHtml(c.company_name || "")}</div>
                <div class="jobrow-addr">${escapeHtml(c.phone_number || "")}${c.cell_phone ? ` / ${escapeHtml(c.cell_phone)}` : ""}${c.email ? ` - ${escapeHtml(c.email)}` : ""}</div>
              </div>
              <button class="btn" data-edit> Edit </button>
            </div>
          `;
          row.querySelector("[data-edit]").addEventListener("click", () => editContact(c, customers));
          list.appendChild(row);
        });
      }

      panel.querySelector("#cont_add").addEventListener("click", async () => {
        const company = panel.querySelector("#cont_company").value.trim();
        const matched = customers.find(c => normalizeText(c.company_name) === normalizeText(company));
        await apiCreateContact({
          name: panel.querySelector("#cont_name").value.trim(),
          company_name: company,
          customer_id: matched ? matched.id || "" : "",
          phone_number: panel.querySelector("#cont_phone").value.trim(),
          email: panel.querySelector("#cont_email").value.trim(),
        });
        await renderContactsTab();
      });

      search.addEventListener("input", renderList);
      renderList();
    }

    async function renderAddressesTab() {
      setTab("addresses");
      let [items, customers] = await Promise.all([
        apiListAddresses({ limit: 1500, include_legacy: true }).catch(() => []),
        apiListCustomers().catch(() => [])
      ]);
      body.innerHTML = "";
      const customerListId = `addr-company-${Math.random().toString(36).slice(2)}`;
      const panel = document.createElement("div");
      panel.className = "card";
      panel.innerHTML = `
        <h3>Addresses</h3>
        <div class="hint">Saved addresses behave like CRM records. Legacy CSV addresses are shown as read-only suggestions.</div>
        <div class="grid2" style="margin-top:12px;">
          <div><div class="label">Customer</div><input class="input" id="addr_customer" list="${customerListId}" placeholder="Link to existing customer" /></div>
          <div><div class="label">Street Address</div><input class="input" id="addr_address" placeholder="Job-site address" /></div>
          <div><div class="label">Label / Location</div><input class="input" id="addr_label" placeholder="Optional, e.g. North Building" /></div>
          <div><div class="label">Notes</div><input class="input" id="addr_notes" placeholder="Optional notes" /></div>
        </div>
        <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn btn-orange" id="addr_add">Add Address</button>
          <button class="btn" id="addr_refresh">Refresh</button>
        </div>
        <div style="margin-top:12px;"><input class="input" id="addr_search" placeholder="Search addresses, customers, job numbers..." /></div>
        <div id="addr_list" style="display:grid; gap:8px; margin-top:12px;"></div>
      `;
      panel.appendChild(buildCustomerDatalist(customerListId, customers));
      body.appendChild(panel);

      const list = panel.querySelector("#addr_list");
      const search = panel.querySelector("#addr_search");

      function renderList() {
        const q = search.value.trim().toLowerCase();
        const filtered = items.filter(a => !q || [a.address, a.customer, a.company_name, a.label, a.notes, a.job_number, a.source].join(" ").toLowerCase().includes(q));
        list.innerHTML = "";
        if (!filtered.length) { list.innerHTML = `<div class="hint">No addresses found.</div>`; return; }
        filtered.slice(0, 500).forEach(a => {
          const isSaved = String(a.source || "") === "saved";
          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `
            <div class="jobrow-top">
              <div>
                <div class="jobrow-name">${escapeHtml(a.address || "")}</div>
                <div class="jobrow-addr">${escapeHtml(a.customer || a.company_name || "")}${a.job_number ? ` - Job #${escapeHtml(a.job_number)}` : ""}</div>
                <div class="hint">${escapeHtml(a.label || a.notes || "")}</div>
              </div>
              <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                <div class="badge">${escapeHtml(a.source || "saved")}</div>
                ${isSaved ? `<button class="btn" data-edit> Edit </button><button class="btn" data-delete> Delete </button>` : ""}
              </div>
            </div>
          `;
          const edit = row.querySelector("[data-edit]");
          if (edit) edit.addEventListener("click", () => editAddress(a));
          const del = row.querySelector("[data-delete]");
          if (del) del.addEventListener("click", async () => {
            if (!confirm("Delete this saved address?")) return;
            await apiDeleteAddress(a.id);
            await renderAddressesTab();
          });
          list.appendChild(row);
        });
      }

      panel.querySelector("#addr_add").addEventListener("click", async () => {
        const address = panel.querySelector("#addr_address").value.trim();
        if (!address) return alert("Address is required.");
        const customer = panel.querySelector("#addr_customer").value.trim();
        const matched = customers.find(c => normalizeText(c.company_name) === normalizeText(customer));
        await apiCreateAddress({
          customer,
          company_name: customer,
          customer_id: matched ? matched.id || "" : "",
          address,
          label: panel.querySelector("#addr_label").value.trim(),
          notes: panel.querySelector("#addr_notes").value.trim(),
        });
        items = await apiListAddresses({ limit: 1500, include_legacy: true }).catch(() => []);
        panel.querySelector("#addr_address").value = "";
        panel.querySelector("#addr_label").value = "";
        panel.querySelector("#addr_notes").value = "";
        renderList();
      });

      panel.querySelector("#addr_refresh").addEventListener("click", renderAddressesTab);
      search.addEventListener("input", renderList);
      renderList();
    }

    btnCustomers.addEventListener("click", () => renderCustomersTab());
    btnContacts.addEventListener("click", () => renderContactsTab());
    btnAddresses.addEventListener("click", () => renderAddressesTab());

    root.appendChild(header);
    root.appendChild(tabs);
    root.appendChild(body);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);

    currentView = {
      refresh: () => activeTab === "customers" ? renderCustomersTab() : activeTab === "contacts" ? renderContactsTab() : renderAddressesTab()
    };
    renderCustomersTab();
  }
  function renderContactsView() {
    renderCustomersView();
  }

function renderEmployeesView() {
    setNavActive(navEmployees);
    setActiveChip("Office Flow");
    setWorkspace("Employees / Users");
    clearWorkspaceActions();

    const root = document.createElement("div");

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>Employees / Users</h3><div class="hint">Create employee records for forms and matching login users for Doorks access. Leads can create/edit dispatches and sales leads. Office Admin can manage user credentials.</div>`;

    const form = document.createElement("div");
    form.className = "grid2";
    form.style.marginTop = "10px";
    form.innerHTML = `
      <div><div class="label">Full Name</div><input class="input" id="e_name" /></div>
      <div><div class="label">Username</div><input class="input" id="e_username" placeholder="Defaults to full name" /></div>
      <div><div class="label">Role</div>
        <select class="input" id="e_role">
          <option value="tech">tech</option>
          <option value="lead">lead</option>
          <option value="office">office</option>
          <option value="office_admin">office_admin</option>
        </select>
      </div>
      <div><div class="label">Phone</div><input class="input" id="e_phone" placeholder="Used for default PIN if left blank" /></div>
      <div><div class="label">Email</div><input class="input" id="e_email" /></div>
      <div><div class="label">Address</div><input class="input" id="e_address" /></div>
      <div><div class="label">Password</div><input type="password" class="input" id="e_pw" placeholder="Required for login" /></div>
      <div><div class="label">PIN</div><input class="input" id="e_pin" maxlength="4" inputmode="numeric" placeholder="Defaults to last 4 of phone" /></div>
    `;

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "8px";
    actions.style.marginTop = "10px";

    const btnAdd = document.createElement("button");
    btnAdd.className = "btn btn-orange";
    btnAdd.textContent = "Add Employee / User";

    const btnRefresh = document.createElement("button");
    btnRefresh.className = "btn";
    btnRefresh.textContent = "Refresh";

    actions.appendChild(btnAdd);
    actions.appendChild(btnRefresh);

    const userList = document.createElement("div");
    userList.style.marginTop = "12px";

    const employeeList = document.createElement("div");
    employeeList.style.marginTop = "16px";

    function normalizePin(pinRaw, phoneRaw) {
      const pin = String(pinRaw || "").replace(/\D/g, "").slice(-4);
      if (pin.length === 4) return pin;
      const phone = String(phoneRaw || "").replace(/\D/g, "").slice(-4);
      return phone;
    }

    async function refresh() {
      const [users, employees] = await Promise.all([
        apiListAuthUsers().catch(() => []),
        apiListEmployees().catch(() => []),
      ]);

      userList.innerHTML = `<div class="card"><h3 style="margin:0 0 10px 0;">Doorks Login Users</h3></div>`;
      const userWrap = document.createElement("div");
      userWrap.style.display = "grid";
      userWrap.style.gap = "8px";
      if (!users.length) {
        userWrap.innerHTML = `<div class="hint">No login users yet.</div>`;
      } else {
        users.forEach(u => {
          const row = document.createElement("div");
          row.className = "jobrow";
          const top = document.createElement("div");
          top.className = "jobrow-top";
          const name = document.createElement("div");
          name.className = "jobrow-name";
          name.textContent = `${u.name || u.username || "User"} (${u.role})`;
          top.appendChild(name);
          const pill = document.createElement("span");
          pill.className = "pill";
          pill.textContent = u.active === false ? "disabled" : u.role;
          pill.style.background = u.role === "office_admin" ? "#111827" : (u.role === "office" ? "#2563eb" : (u.role === "lead" ? "#b45309" : "#7c3aed"));
          top.appendChild(pill);
          const meta = document.createElement("div");
          meta.className = "jobrow-addr";
          meta.textContent = `${u.username || ""}${u.email ? ` - ${u.email}` : ""}`;

          const btnRow = document.createElement("div");
          btnRow.style.display = "flex";
          btnRow.style.gap = "8px";
          btnRow.style.marginTop = "8px";
          btnRow.style.flexWrap = "wrap";

          const roleSel = document.createElement("select");
          roleSel.className = "input";
          roleSel.style.maxWidth = "180px";
          roleSel.innerHTML = `
            <option value="tech">tech</option>
            <option value="lead">lead</option>
            <option value="office">office</option>
            <option value="office_admin">office_admin</option>
          `;
          roleSel.value = u.role || "tech";

          const saveRole = document.createElement("button");
          saveRole.className = "btn";
          saveRole.textContent = "Save Role";
          saveRole.addEventListener("click", async () => {
            try {
              await apiUpdateAuthUser(u.id, { role: roleSel.value, active: u.active !== false });
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });

          const editUser = document.createElement("button");
          editUser.className = "btn";
          editUser.textContent = "Edit User";
          editUser.addEventListener("click", async () => {
            const nextName = prompt(`Full name for ${u.username || u.name}:`, u.name || "");
            if (nextName === null) return;
            const nextUsername = prompt(`Username for ${u.name || u.username}:`, u.username || "");
            if (nextUsername === null) return;
            const nextEmail = prompt(`Email for ${u.name || u.username}:`, u.email || "");
            if (nextEmail === null) return;
            try {
              await apiUpdateAuthUser(u.id, {
                name: String(nextName || "").trim(),
                username: String(nextUsername || "").trim(),
                email: String(nextEmail || "").trim(),
                role: roleSel.value,
                active: u.active !== false,
              });
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });

          const resetPw = document.createElement("button");
          resetPw.className = "btn";
          resetPw.textContent = "Reset Password";
          resetPw.addEventListener("click", async () => {
            const next = prompt(`New password for ${u.username || u.name}:`);
            if (!next) return;
            try {
              await apiSetAuthUserPassword(u.id, next);
              alert("Password updated.");
            } catch (err) { alert(err.message || String(err)); }
          });

          const resetPin = document.createElement("button");
          resetPin.className = "btn";
          resetPin.textContent = "Reset PIN";
          resetPin.addEventListener("click", async () => {
            const next = prompt(`New 4-digit PIN for ${u.username || u.name}:`);
            if (!next) return;
            try {
              await apiSetAuthUserPin(u.id, next);
              alert("PIN updated.");
            } catch (err) { alert(err.message || String(err)); }
          });

          const toggle = document.createElement("button");
          toggle.className = "btn";
          toggle.textContent = u.active === false ? "Enable" : "Disable";
          toggle.addEventListener("click", async () => {
            try {
              await apiSetAuthUserActive(u.id, u.active === false);
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });

          const del = document.createElement("button");
          del.className = "btn";
          del.style.borderColor = "#fecaca";
          del.style.color = "#b91c1c";
          del.textContent = "Delete User";
          del.addEventListener("click", async () => {
            if (!confirm(`Delete login for ${u.username || u.name}?`)) return;
            try {
              await apiDeleteAuthUser(u.id);
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });

          btnRow.appendChild(roleSel);
          btnRow.appendChild(saveRole);
          btnRow.appendChild(editUser);
          btnRow.appendChild(resetPw);
          btnRow.appendChild(resetPin);
          btnRow.appendChild(toggle);
          if (!(u.role === "office_admin" && String(u.username || "").toLowerCase() === "jason brewster")) btnRow.appendChild(del);

          row.appendChild(top);
          row.appendChild(meta);
          row.appendChild(btnRow);
          userWrap.appendChild(row);
        });
      }
      userList.appendChild(userWrap);

      employeeList.innerHTML = `<div class="card"><h3 style="margin:0 0 10px 0;">Employee Records</h3><div class="hint">These are used in technician dropdowns, forms, payroll, and time cards.</div></div>`;
      const empWrap = document.createElement("div");
      empWrap.style.display = "grid";
      empWrap.style.gap = "8px";
      if (!employees.length) {
        empWrap.innerHTML = `<div class="hint">No employees yet.</div>`;
      } else {
        employees.forEach(e => {
          const row = document.createElement("div");
          row.className = "jobrow";
          const top = document.createElement("div");
          top.className = "jobrow-top";
          const name = document.createElement("div");
          name.className = "jobrow-name";
          name.textContent = `${e.name} (${e.role})`;
          top.appendChild(name);
          const pill = document.createElement("span");
          pill.className = "pill";
          pill.style.background = e.role === "office_admin" ? "#111827" : (e.role === "office" ? "#2563eb" : (e.role === "lead" ? "#b45309" : "#7c3aed"));
          pill.textContent = e.role;
          top.appendChild(pill);
          const meta = document.createElement("div");
          meta.className = "jobrow-addr";
          meta.textContent = `${e.phone || ""}${e.email ? ` - ${e.email}` : ""}${e.name ? ` - PTO Accrual: ${getPtoAccrualRate(e.name).toFixed(2)} hrs/pay period` : ""}`;
          const a = document.createElement("div");
          a.style.display = "flex";
          a.style.gap = "8px";
          a.style.marginTop = "8px";
          a.style.flexWrap = "wrap";

          const edit = document.createElement("button");
          edit.className = "btn";
          edit.textContent = "Edit Employee";
          edit.addEventListener("click", async () => {
            const nextName = prompt("Employee name:", e.name || "");
            if (nextName === null) return;
            const nextRole = prompt("Employee role (tech, lead, office, office_admin):", e.role || "tech");
            if (nextRole === null) return;
            const nextPhone = prompt("Employee phone:", e.phone || "");
            if (nextPhone === null) return;
            const nextEmail = prompt("Employee email:", e.email || "");
            if (nextEmail === null) return;
            const nextAddress = prompt("Employee address:", e.address || "");
            if (nextAddress === null) return;
            try {
              await apiUpdateEmployee(e.id, {
                name: String(nextName || "").trim(),
                role: String(nextRole || "tech").trim() || "tech",
                phone: String(nextPhone || "").trim(),
                email: String(nextEmail || "").trim(),
                address: String(nextAddress || "").trim(),
              });
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });

          const ptoAccrual = document.createElement("button");
          ptoAccrual.className = "btn";
          ptoAccrual.textContent = "PTO Accrual";
          ptoAccrual.addEventListener("click", async () => {
            const current = getPtoAccrualRate(e.name);
            const next = prompt(`PTO accrual hours per pay period for ${e.name}:`, String(current.toFixed(2)));
            if (next === null) return;
            const val = Number(next || 0);
            if (Number.isNaN(val)) return alert("Enter a valid PTO accrual rate.");
            setPtoAccrualRate(e.name, val);
            await refresh();
          });

          const del = document.createElement("button");
          del.className = "btn";
          del.textContent = "Delete Employee";
          del.style.borderColor = "#fecaca";
          del.style.color = "#b91c1c";
          del.addEventListener("click", async () => {
            if (!confirm("Delete employee record?")) return;
            try {
              await apiDeleteEmployee(e.id);
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });
          a.appendChild(edit);
          a.appendChild(ptoAccrual);
          a.appendChild(del);
          row.appendChild(top);
          row.appendChild(meta);
          row.appendChild(a);
          empWrap.appendChild(row);
        });
      }
      employeeList.appendChild(empWrap);
    }

    btnAdd.addEventListener("click", async () => {
      try {
        const name = form.querySelector("#e_name").value.trim();
        const username = (form.querySelector("#e_username").value.trim() || name).trim();
        const role = form.querySelector("#e_role").value;
        const phone = form.querySelector("#e_phone").value.trim();
        const email = form.querySelector("#e_email").value.trim();
        const address = form.querySelector("#e_address").value.trim();
        const password = form.querySelector("#e_pw").value.trim();
        const pin = normalizePin(form.querySelector("#e_pin").value.trim(), phone);
        if (!name) throw new Error("Full name is required.");
        if (!username) throw new Error("Username is required.");
        if (!password) throw new Error("Password is required.");
        if (!pin || pin.length !== 4) throw new Error("PIN must be 4 digits or derive from phone.");

        await apiCreateEmployee({ name, role, phone, email, address, password }).catch(() => null);
        await apiCreateAuthUser({ username, name, email, role, password, pin, active: true });

        ["#e_name", "#e_username", "#e_phone", "#e_email", "#e_address", "#e_pw", "#e_pin"].forEach(sel => {
          const el = form.querySelector(sel);
          if (el) el.value = "";
        });
        form.querySelector("#e_role").value = "tech";
        await refresh();
      } catch (e) {
        alert(e.message || String(e));
      }
    });

    btnRefresh.addEventListener("click", refresh);

    root.appendChild(card);
    root.appendChild(form);
    root.appendChild(actions);
    root.appendChild(userList);
    root.appendChild(employeeList);

    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);

    currentView = { refresh };
    refresh();
  }
 
  function money(v) {
    const n = Number(v || 0);
    return Number.isFinite(n) ? n.toFixed(2) : "0.00";
  }
 
  function createDocLineItem(item = {}) {
    const kind = item.kind || "part";
    return {
      code: item.code || "",
      description: item.description || "",
      qty: Number(item.qty ?? 1),
      rate: Number(item.rate || 0),
      kind,
      taxable: typeof item.taxable === "boolean" ? item.taxable : !(kind === "labor" || kind === "fee"),
    };
  }
 
  function defaultDocItems() {
    return [
      createDocLineItem({ code: "TRIP", description: "Trip Charge", qty: 1, rate: 175, kind: "fee", taxable: false }),
      createDocLineItem({ code: "FUEL", description: "Fuel Surcharge", qty: 1, rate: 20, kind: "fee", taxable: false }),
    ];
  }
 
  
  
  function openEstimateInvoiceEmail(doc, docType = "invoice") {
    const typeLabel = docType === "estimate" ? "Estimate" : "Invoice";
    const number = doc.number || doc.invoice_number || doc.estimate_number || "";
    const customer = doc.customer || "Customer";
    const address = doc.address || "";
    const email = prompt("Customer email address:", doc.email || "");
    if (email === null) return;

    const subject = `${typeLabel} ${number ? `#${number}` : ""} - ${customer}`.trim();
    const estimateBody = `Hello,\n\nAttached is estimate ${number || ""} for the recommended work${address ? ` at ${address}` : ""}.\n\nPlease review and let us know if you would like us to proceed. Scheduling will be coordinated upon approval.\n\n***PLEASE NOTE: Invoices 10 days past due will automatically incur a Late Charge of $35 and after 15 days there will be a 22% APR interest charge applied. Estimates are valid for 30 days unless otherwise noted.***\n\nThank you,\nPriority Door Systems\n\n(760) 233-5037\nwww.prioritydoors.com`;
    const invoiceBody = `Hello,\n\nAttached is invoice ${number || ""} for the completed work${address ? ` at ${address}` : ""}.\n\nPlease remit payment at your earliest convenience. Thank you for your business.\n\nThank you,\nPriority Door Systems\n\nAccounting Department\n(760) 233-5037\nwww.prioritydoors.com`;
    const body = docType === "estimate" ? estimateBody : invoiceBody;

    // Browser mailto links cannot attach files automatically. Open/download the PDF first,
    // then open the email draft with the standard response so the user can attach it.
    if (doc.download_url) {
      try { window.open(doc.download_url, "_blank", "noopener,noreferrer"); } catch {}
    }
    const mailto = `mailto:${encodeURIComponent((email || "").trim())}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    setTimeout(() => { window.location.href = mailto; }, 300);
  }

function exportEstimateInvoiceToQuickBooksCSV(payload, docType = "invoice") {
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const cleanDate = (value) => {
      const s = String(value || "").slice(0, 10);
      const p = s.split("-");
      if (p.length === 3) return `${p[1]}/${p[2]}/${p[0]}`;
      return s;
    };
    const number = payload.number || payload.invoice_number || payload.estimate_number || payload.job_number || "";
    const header = ["Customer","Email","Document Type","Document No","Date","PO Number","Job Number","Item","Description","Qty","Rate","Amount","Taxable"];
    const rows = [];

    (payload.items || []).forEach((item) => {
      const qty = Number(item.qty || 0);
      const rate = Number(item.rate || 0);
      const amount = qty * rate;
      if (!qty && !rate && !String(item.description || "").trim()) return;
      rows.push([
        payload.customer || "",
        payload.email || "",
        docType === "estimate" ? "Estimate" : "Invoice",
        number,
        cleanDate(payload.date || ""),
        payload.po_number || "",
        payload.job_number || "",
        item.code || item.kind || "Service",
        item.description || "",
        qty,
        rate.toFixed(2),
        amount.toFixed(2),
        item.taxable === false ? "No" : "Yes",
      ]);
    });

    if (!rows.length) {
      alert("No line items found to export.");
      return;
    }

    const csv = [header, ...rows].map(row => row.map(esc).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const safeNumber = String(number || "quickbooks_export").replace(/[^a-z0-9_-]+/gi, "_");
    const a = document.createElement("a");
    a.href = url;
    a.download = `${safeNumber}_quickbooks.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

function serializeDocItems(items, laborOnly) {
    return items
      .filter(it => laborOnly ? it.kind === "labor" : it.kind !== "labor")
      .map(it => `${it.code || "ITEM"} - ${it.description} | Qty ${Number(it.qty || 0)} @ $${money(it.rate)} = $${money(Number(it.qty) * Number(it.rate))}${it.taxable === false ? " | Non-Taxable" : ""}`)
      .join("\n");
  }
 
  function openEstimateInvoiceDrawer(job = null, initialType = "estimate", container = null, ctx = null) {
    openDrawer("Estimate / Invoice", async (drawerBody, overlay) => {
      const editDoc = job && job.__docEdit ? job.__docEdit : null;
      const [customers, employees, pricing, knownAddresses] = await Promise.all([apiListCustomers().catch(() => []), apiListEmployees().catch(() => []), apiGetPricing().catch(() => ({ trip:175, fuel:20, labor:175, crew_labor:235, tax:7.75 })), apiListAddresses({ limit: 1500 }).catch(() => [])]);
      let docType = editDoc ? (editDoc.type || initialType) : initialType;
      let items = Array.isArray(editDoc?.items) && editDoc.items.length ? editDoc.items.map(createDocLineItem) : defaultDocItems().map(it => ({ ...it, kind: it.code === "TRIP" ? "trip" : (it.code === "FUEL" ? "fuel" : (it.kind || "other")) }));
      let currentPartResults = [];
      drawerBody.innerHTML = "";
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; align-items:flex-start;">
          <div>
            <div style="font-size:28px; font-weight:1000; letter-spacing:.04em;">PRIORITY DOOR SYSTEMS</div>
            <div class="hint">836 W. Washington Ave. - Escondido, CA 92025 - 760-233-5037 - www.prioritydoors.com</div>
          </div>
          <div class="card" style="min-width:260px; padding:12px;">
            <div class="label">Document Type</div>
            <select class="input" id="doc_type"><option value="estimate">Estimate</option><option value="invoice">Invoice</option></select>
            <div class="label" style="margin-top:8px;">Date</div>
            <input class="input" id="doc_date" type="date" />
            <div class="label" style="margin-top:8px;">Sales Tax % <span style="color:#b91c1c;">*</span></div>
            <select class="input" id="doc_tax_rate_select">
              <option value="">-- Select city / rate --</option>
            </select>
            <input class="input" id="doc_tax_rate_custom" type="number" min="0" step="0.01" placeholder="Enter custom tax %" style="margin-top:8px; display:none;" />
            <div class="hint" id="doc_tax_rate_hint" style="margin-top:6px;">Required: choose a city tax rate, No Sales Tax, or Custom.</div>
            <div class="label" style="margin-top:8px;">Terms <span style="color:#b91c1c;">*</span></div>
            <select class="input" id="doc_terms"></select>
            <div class="label" style="margin-top:8px;">Prepared By</div>
            <select class="input" id="doc_completed_by"><option value="">-- Select employee --</option></select>
          </div>
        </div>
        <div class="grid2" style="margin-top:12px; align-items:start;">
          <div class="card" style="padding:12px;">
            <div class="label">Name / Address</div>
            <input class="input" id="doc_customer" list="doc_customer_list" placeholder="Customer" style="margin-top:6px;" />
            <input class="input" id="doc_address" name="doc_address" placeholder="Address" autocomplete="off" autocapitalize="off" spellcheck="false" data-lpignore="true" data-1p-ignore="true" style="margin-top:8px;" />
          </div>
          <div class="card" style="padding:12px;">
            <div class="label">Ship To / Bill To</div>
            <input class="input" id="doc_ship" placeholder="Ship To / Bill To" style="margin-top:6px;" />
            <div class="grid2" style="margin-top:8px;">
              <div><div class="label">PO #</div><input class="input" id="doc_po" /></div>
              <div><div class="label">Work Order / Job #</div><input class="input" id="doc_job" /></div>
            </div>
            <div style="margin-top:8px;"><div class="label" id="doc_number_label">Estimate #</div><input class="input" id="doc_number" /></div>
          </div>
        </div>
        <div style="margin-top:12px;"><div class="label">Proposal / Invoice Body</div><textarea id="doc_work" placeholder="Proposal Includes / Invoice Includes..." style="min-height:140px;"></textarea></div>
        <div class="card" id="doc_source_wrap" style="padding:12px; margin-top:12px;">
          <div class="label">Description Source</div>
          <select class="input" id="doc_source_form"></select>
          <div class="hint" style="margin-top:6px;">Choose which saved Completion/Recommendation Form should drive Auto Fill Description.</div>
          <div id="doc_scope_wrap" style="margin-top:10px;">
            <div class="label">Proposed Scope</div>
            <select class="input" id="doc_scope_intent">
              <option value="">-- Select proposed work --</option>
              <option value="Furnish and install">Furnish &amp; Install</option>
              <option value="Repair">Repair</option>
              <option value="Adjust">Adjust</option>
              <option value="Replace">Replace</option>
              <option value="New installation">New Installation</option>
              <option value="Other">Other</option>
            </select>
            <div class="hint" style="margin-top:6px;">Tells Auto Fill what you are proposing. The generated description remains editable.</div>
          </div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; align-items:center;">
          <button class="btn" id="doc_auto_fill">Auto Fill Description</button>
          <button class="btn" id="add_trip">Trip Charge</button>
          <button class="btn" id="add_fuel">Fuel Surcharge</button>
          <button class="btn" id="add_freight">Freight Surcharge</button>
          <button class="btn" id="add_single">Single Tech Labor</button>
          <button class="btn" id="add_crew">Crew Tech Labor</button>
          <button class="btn" id="add_blank">Add Blank Line</button>
        </div>
        <div class="card" style="padding:12px; margin-top:12px;">
          <div class="label">Find Existing Parts</div>
          <input class="input" id="part_lookup" placeholder="Type item number or description" autocomplete="off" />
          <div class="hint" id="part_lookup_hint" style="margin-top:6px;">Start typing to search your saved parts list.</div>
          <div id="part_lookup_results" style="display:grid; gap:8px; margin-top:8px;"></div>
        </div>
        <div style="margin-top:12px; overflow:auto;"><table style="width:100%; border-collapse:collapse; min-width:920px;"><thead><tr>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; min-width:130px;">Item</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; min-width:320px;">Description</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:90px;">Qty</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:110px;">Price</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:90px;">Taxable</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:110px;">Total</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:60px;"></th>
        </tr></thead><tbody id="doc_items"></tbody></table></div>
        <div style="display:grid; grid-template-columns:1fr 320px; gap:12px; margin-top:12px;">
          <div class="card" style="padding:12px;"><div class="jobrow-top"><div class="jobrow-name">Cost Breakdown</div></div>
            <div class="jobrow-top" style="margin-top:8px;"><div>Trip Charges</div><div id="doc_trip_total">$0.00</div></div>
            <div class="jobrow-top"><div>Fuel Surcharges</div><div id="doc_fuel_total">$0.00</div></div>
            <div class="jobrow-top"><div>Labor</div><div id="doc_labor_total">$0.00</div></div>
            <div class="jobrow-top"><div>Parts</div><div id="doc_parts_total">$0.00</div></div>
            <div class="jobrow-top"><div>Other</div><div id="doc_other_total">$0.00</div></div>
          </div>
          <div class="card" style="padding:12px;"><div class="jobrow-top"><div class="jobrow-name">Totals</div></div>
            <div class="jobrow-top" style="margin-top:8px;"><div>Subtotal</div><div id="doc_subtotal">$0.00</div></div>
            <div class="jobrow-top"><div>Taxable Subtotal</div><div id="doc_taxable">$0.00</div></div>
            <div class="jobrow-top"><div>Sales Tax</div><div id="doc_tax">$0.00</div></div>
            <div class="jobrow-top" style="font-weight:1000; margin-top:6px;"><div>Total</div><div id="doc_total">$0.00</div></div>
          </div>
        </div>
        <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;"><button class="btn btn-orange" id="doc_generate">Generate PDF</button><button class="btn" id="doc_cancel">Cancel</button></div>`;
      drawerBody.appendChild(card);
      card.appendChild(buildCustomerDatalist("doc_customer_list", customers));
      const completedSel = card.querySelector("#doc_completed_by");
      employees.forEach(e => { const opt=document.createElement("option"); opt.value=e.name||""; opt.textContent=e.name||""; completedSel.appendChild(opt); });
      const dom = { type:card.querySelector("#doc_type"), date:card.querySelector("#doc_date"), customer:card.querySelector("#doc_customer"), address:card.querySelector("#doc_address"), ship:card.querySelector("#doc_ship"), po:card.querySelector("#doc_po"), job:card.querySelector("#doc_job"), number:card.querySelector("#doc_number"), numberLabel:card.querySelector("#doc_number_label"), work:card.querySelector("#doc_work"), tbody:card.querySelector("#doc_items"), subtotal:card.querySelector("#doc_subtotal"), taxable:card.querySelector("#doc_taxable"), tax:card.querySelector("#doc_tax"), total:card.querySelector("#doc_total"), taxRateSelect:card.querySelector("#doc_tax_rate_select"), taxRateCustom:card.querySelector("#doc_tax_rate_custom"), taxRateHint:card.querySelector("#doc_tax_rate_hint"), partLookup:card.querySelector("#part_lookup"), partLookupHint:card.querySelector("#part_lookup_hint"), partResults:card.querySelector("#part_lookup_results"), tripTotal:card.querySelector("#doc_trip_total"), fuelTotal:card.querySelector("#doc_fuel_total"), laborTotal:card.querySelector("#doc_labor_total"), partsTotal:card.querySelector("#doc_parts_total"), otherTotal:card.querySelector("#doc_other_total"), completedBy:completedSel, terms:card.querySelector("#doc_terms"), sourceWrap:card.querySelector("#doc_source_wrap"), sourceForm:card.querySelector("#doc_source_form"), scopeWrap:card.querySelector("#doc_scope_wrap"), scopeIntent:card.querySelector("#doc_scope_intent") };
      SALES_TAX_OPTIONS.forEach(opt => { const o=document.createElement("option"); o.value=String(opt.rate); o.textContent=`${opt.city} — ${Number(opt.rate).toFixed(2)}%`; o.dataset.city=opt.city; dom.taxRateSelect.appendChild(o); });
      const jobFormsForDescriptions = Array.isArray(job && job.completion_forms) ? job.completion_forms : [];
      function isRecommendationLikeForm(f) {
        if (!f) return false;
        return !!(f.ready_to_quote || String(f.recommendations || "").trim() || String(f.parts_required || "").trim() || String(f.time_required || "").trim());
      }
      function formDateLabel(f) {
        const raw = String((f && (f.date || f.form_date || f.created_at)) || "").slice(0, 10);
        if (!raw) return "No date";
        const parts = raw.split("-");
        return parts.length === 3 ? `${parts[1]}/${parts[2]}/${parts[0]}` : raw;
      }
      function formSourceLabel(f, idx) {
        const type = isRecommendationLikeForm(f) ? "Recommendation" : "Completion";
        const details = [formDateLabel(f), f.technician_name || "", f.door_location || "", f.door_type || ""].filter(Boolean).join(" • ");
        return `${type} Form ${idx + 1}${details ? ` — ${details}` : ""}`;
      }
      function selectedDescriptionForms() {
        const selected = dom.sourceForm ? dom.sourceForm.value : "";
        if (selected && selected.startsWith("idx:")) {
          const idx = Number(selected.slice(4));
          const chosen = jobFormsForDescriptions[idx];
          return chosen ? [chosen] : [];
        }
        return jobFormsForDescriptions;
      }
      if (dom.sourceForm) {
        dom.sourceForm.innerHTML = jobFormsForDescriptions.length
          ? `<option value="">Auto-select best saved form</option>` + jobFormsForDescriptions.map((f, idx) => `<option value="idx:${idx}">${escapeHtml(formSourceLabel(f, idx))}</option>`).join("")
          : `<option value="">No saved Completion/Recommendation Forms</option>`;
        dom.sourceForm.value = jobFormsForDescriptions.length === 1 ? "idx:0" : "";
        dom.sourceForm.disabled = !jobFormsForDescriptions.length;
      }
      function syncDescriptionControls() {
        if (dom.scopeWrap) dom.scopeWrap.style.display = dom.type.value === "estimate" ? "block" : "none";
      }
      syncDescriptionControls();
      const customOpt=document.createElement("option"); customOpt.value="__custom__"; customOpt.textContent="Custom"; dom.taxRateSelect.appendChild(customOpt);
      if (dom.terms) {
        const blankTerm = document.createElement("option");
        blankTerm.value = "";
        blankTerm.textContent = "-- Select terms --";
        dom.terms.appendChild(blankTerm);
      }
      BILLING_TERMS_OPTIONS.forEach(term => { const o=document.createElement("option"); o.value=term; o.textContent=term; dom.terms.appendChild(o); });
      if (!String(editDoc?.tax_rate || "").trim() && pricing && pricing.tax != null) {
        const taxDefault = Number(pricing.tax || 0);
        if (taxDefault) {
          const matched = SALES_TAX_OPTIONS.find(opt => Number(opt.rate) === taxDefault);
          if (matched) {
            /* value set below via setTaxRateValue */
          }
        }
      }
      function setTaxRateValue(rate, city="") { const normalized = String(rate == null ? "" : rate).trim(); const known = normalized && SALES_TAX_OPTIONS.some(opt => String(opt.rate) === normalized);
        if (known) { dom.taxRateSelect.value = normalized; dom.taxRateCustom.value = normalized; dom.taxRateCustom.style.display = "none"; dom.taxRateHint.textContent = city ? `${city} selected.` : "City tax rate selected."; return; }
        if (normalized) { dom.taxRateSelect.value = "__custom__"; dom.taxRateCustom.value = normalized; dom.taxRateCustom.style.display = "block"; dom.taxRateHint.textContent = "Custom sales tax entered."; return; }
        dom.taxRateSelect.value = ""; dom.taxRateCustom.value = ""; dom.taxRateCustom.style.display = "none"; dom.taxRateHint.textContent = "Choose a city tax rate or select Custom."; }
      function getCurrentTaxRateValue() { return dom.taxRateSelect.value === "__custom__" ? String(dom.taxRateCustom.value || "").trim() : String(dom.taxRateSelect.value || "").trim(); }
      dom.type.value = docType; dom.date.value = (editDoc && editDoc.date) || yyyyMmDd(new Date()); wireKnownAddressAutofill({ input: dom.address, customerInput: dom.customer, knownAddresses, extraAddresses: customers.map(c => c.address).filter(Boolean) }); if (editDoc && editDoc.tax_rate != null) setTaxRateValue(editDoc.tax_rate); else setTaxRateValue("");
      if (dom.terms) dom.terms.value = (editDoc && editDoc.terms) || "";
      if (job) { dom.customer.value = (editDoc && editDoc.customer) || job.customer || ""; dom.address.value = (editDoc && editDoc.address) || job.address || ""; dom.ship.value = (editDoc && editDoc.ship_to) || job.address || job.customer || ""; dom.po.value = (editDoc && editDoc.po_number) || job.po_number || ""; dom.job.value = (editDoc && editDoc.job_number) || job.job_number || ""; }
      if (editDoc) { dom.work.value = editDoc.work || ""; setTaxRateValue(editDoc.tax_rate ?? 7.75); dom.completedBy.value = editDoc.completed_by || ""; dom.number.value = editDoc.number || ""; }
      function applyDocTypeMeta(){ docType=dom.type.value; const defaultNumber=nextDocNumberFromStorage(docType); dom.numberLabel.textContent = docType === "estimate" ? "Estimate #" : "Invoice #"; if (editDoc) return; if (!String(dom.number.value||"").trim() || (docType==="estimate" && String(dom.number.value||"").startsWith("JS")) || (docType==="invoice" && String(dom.number.value||"").startsWith("RE"))) dom.number.value = docType === "estimate" ? defaultNumber : (job?.invoice_number || defaultNumber); }
      function categoryTotals(){ const sums={trip:0,fuel:0,labor:0,parts:0,other:0}; items.forEach(it=>{ const total=Number(it.qty||0)*Number(it.rate||0); const kind=String(it.kind||"other").toLowerCase(); if (kind==="trip") sums.trip+=total; else if (kind==="fuel") sums.fuel+=total; else if (kind==="labor") sums.labor+=total; else if (kind==="part") sums.parts+=total; else sums.other+=total;}); return sums; }
      function updateTotals(){ const subtotal=items.reduce((s,it)=>s+(Number(it.qty||0)*Number(it.rate||0)),0); const taxableSubtotal=getTaxableSubtotal(items); const taxRate=Number(getCurrentTaxRateValue()||0)/100; const tax=taxableSubtotal*taxRate; const sums=categoryTotals(); dom.subtotal.textContent=`$${money(subtotal)}`; dom.taxable.textContent=`$${money(taxableSubtotal)}`; dom.tax.textContent=`$${money(tax)}`; dom.total.textContent=`$${money(subtotal+tax)}`; dom.tripTotal.textContent=`$${money(sums.trip)}`; dom.fuelTotal.textContent=`$${money(sums.fuel)}`; dom.laborTotal.textContent=`$${money(sums.labor)}`; dom.partsTotal.textContent=`$${money(sums.parts)}`; dom.otherTotal.textContent=`$${money(sums.other)}`; }
      function renderPartLookupResults(results){ currentPartResults=Array.isArray(results)?results:[]; dom.partResults.innerHTML=""; dom.partLookupHint.textContent=currentPartResults.length?`${currentPartResults.length} matching part${currentPartResults.length===1?"":"s"}`:"No matching parts found yet."; currentPartResults.slice(0,10).forEach(p=>{ const row=document.createElement("button"); row.className="btn"; row.style.textAlign="left"; row.innerHTML=`<strong>${escapeHtml(p.Item||"")}</strong><br><span class="hint">${escapeHtml(p.Description||"")}${p.Price?` - $${money(p.Price)}`:""}</span>`; row.addEventListener("click",()=>addPartToItems(p)); dom.partResults.appendChild(row); }); }
      let searchTimer=null; async function searchParts(q){ try{ renderPartLookupResults(await apiListParts({ q, limit:25 })); } catch { renderPartLookupResults([]); } }
      function addPartToItems(part){ if(!part) return; items.push(createDocLineItem({ code:part.Item||"", description:part.Description||"", qty:1, rate:Number(part.Price||0), kind:"part", taxable:true })); dom.partLookup.value=""; renderPartLookupResults([]); renderItems(); }
      function findPartMatch(q){ const n=String(q||"").trim().toLowerCase(); if(!n) return null; return currentPartResults.find(p=>String(p.Item||"").trim().toLowerCase()===n) || currentPartResults.find(p=>String(p.Description||"").trim().toLowerCase()===n) || currentPartResults.find(p=>`${p.Item||""} ${p.Description||""}`.toLowerCase().includes(n)) || null; }
      function makeRow(item,idx){ const tr=document.createElement("tr"); const total=Number(item.qty||0)*Number(item.rate||0); tr.innerHTML=`<td style="padding:8px; border-bottom:1px solid #f3f4f6;"><input class="input" data-k="code" value="${item.code||""}" /></td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><input class="input" data-k="description" value="${item.description||""}" /></td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><input class="input" style="min-width:72px;" data-k="qty" type="number" min="0" step="0.25" value="${Number(item.qty||0)}" /></td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><input class="input" style="min-width:96px;" data-k="rate" type="number" min="0" step="0.01" value="${Number(item.rate||0)}" /></td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><label style="display:flex; align-items:center; gap:6px;"><input type="checkbox" data-k="taxable" ${item.taxable===false?"":"checked"}/> <span class="hint">Tax</span></label></td><td style="padding:8px; border-bottom:1px solid #f3f4f6; white-space:nowrap;" data-k="line_total">$${money(total)}</td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><button class="btn" data-k="del">&times;</button></td>`; const updateLine=()=>{ tr.querySelector('[data-k="line_total"]').textContent=`$${money(Number(item.qty||0)*Number(item.rate||0))}`; updateTotals(); }; tr.querySelector('[data-k="code"]').addEventListener("change", async e => { item.code=e.target.value; const hit=await apiListParts({ q:item.code, limit:10 }).catch(()=>[]); const part=hit.find(p=>String(p.Item||"").trim().toLowerCase()===String(item.code||"").trim().toLowerCase())||hit[0]; if(part){ item.code=part.Item||item.code; item.description=part.Description||item.description; item.rate=Number(part.Price||item.rate||0); item.kind="part"; item.taxable=true; renderItems(); return; } updateLine(); }); tr.querySelector('[data-k="description"]').addEventListener("input", e => { item.description=e.target.value; }); tr.querySelector('[data-k="qty"]').addEventListener("input", e => { item.qty=Number(e.target.value||0); updateLine(); }); tr.querySelector('[data-k="rate"]').addEventListener("input", e => { item.rate=Number(e.target.value||0); updateLine(); }); tr.querySelector('[data-k="taxable"]').addEventListener("change", e => { item.taxable=!!e.target.checked; updateLine(); }); tr.querySelector('[data-k="del"]').addEventListener("click", ()=>{ items.splice(idx,1); renderItems(); }); return tr; }
      function renderItems(){ applyDocTypeMeta(); dom.tbody.innerHTML=""; items.forEach((item,idx)=>dom.tbody.appendChild(makeRow(item,idx))); updateTotals(); }
      dom.partLookup.addEventListener("input", ()=>{ clearTimeout(searchTimer); const q=dom.partLookup.value.trim(); if(!q){ renderPartLookupResults([]); return; } searchTimer=setTimeout(()=>searchParts(q), 180); });
      dom.partLookup.addEventListener("keydown", e=>{ if(e.key==="Enter"){ e.preventDefault(); addPartToItems(findPartMatch(dom.partLookup.value)||currentPartResults[0]); }});
      card.querySelector("#add_trip").addEventListener("click", ()=>{ items.push(createDocLineItem({ code:"TRIP", description:"Trip Charge", qty:1, rate:Number(pricing.trip || 175), kind:"trip", taxable:false })); renderItems(); });
      card.querySelector("#add_fuel").addEventListener("click", ()=>{ items.push(createDocLineItem({ code:"FUEL", description:"Fuel Surcharge", qty:1, rate:Number(pricing.fuel || 20), kind:"fuel", taxable:false })); renderItems(); });
      const freightBtn = card.querySelector("#add_freight"); if (freightBtn) freightBtn.addEventListener("click", ()=>{ const amt = prompt("Freight surcharge amount:", ""); if (amt === null) return; const n = Number(String(amt).replace(/[$,]/g, "") || 0); if (!Number.isFinite(n) || n < 0) return alert("Enter a valid freight amount."); items.push(createDocLineItem({ code:"FREIGHT", description:"Freight Surcharge", qty:1, rate:n, kind:"fee", taxable:false })); renderItems(); });
      card.querySelector("#add_single").addEventListener("click", ()=>{ items.push(createDocLineItem({ code:"LABOR", description:"Single Tech Labor", qty:1, rate:Number(pricing.labor || 175), kind:"labor", taxable:false })); renderItems(); });
      card.querySelector("#add_crew").addEventListener("click", ()=>{ items.push(createDocLineItem({ code:"CREW", description:"Crew Tech Labor", qty:1, rate:Number(pricing.crew_labor || 235), kind:"labor", taxable:false })); renderItems(); });
      card.querySelector("#add_blank").addEventListener("click", ()=>{ items.push(createDocLineItem({ kind:"other" })); renderItems(); });
      card.querySelector("#doc_cancel").addEventListener("click", ()=> overlay.remove());
      dom.type.addEventListener("change", ()=>{ renderItems(); syncDescriptionControls(); });
      dom.taxRateSelect.addEventListener("change", ()=>{
        if (dom.taxRateSelect.value === "__custom__") {
          dom.taxRateCustom.style.display = "block";
          dom.taxRateHint.textContent = "Enter a custom sales tax %.";
          if (!String(dom.taxRateCustom.value || "").trim()) dom.taxRateCustom.value = "7.75";
          dom.taxRateCustom.focus();
        } else {
          dom.taxRateCustom.style.display = "none";
          const selected = dom.taxRateSelect.options[dom.taxRateSelect.selectedIndex];
          dom.taxRateHint.textContent = selected && selected.dataset && selected.dataset.city ? `${selected.dataset.city} selected.` : "Choose a city tax rate or select Custom.";
        }
        updateTotals();
      });
      dom.taxRateCustom.addEventListener("input", updateTotals);
      dom.address.addEventListener("blur", ()=>{
        if (getCurrentTaxRateValue()) return;
        const inferred = inferTaxCityFromAddress(dom.address.value);
        dom.taxRateHint.textContent = inferred
          ? `${inferred.city} may apply. Please select the sales tax rate before saving.`
          : "Please select the correct sales tax rate before saving.";
      });
      const _docOpenPricingBtn = card.querySelector("#doc_open_pricing"); if (_docOpenPricingBtn) _docOpenPricingBtn.addEventListener("click", ()=> renderPricingSettingsView());
      const _docPromptBtn = card.querySelector("#doc_prompt_builder"); if (_docPromptBtn) _docPromptBtn.addEventListener("click", ()=> {
        const extra = prompt("Add extra wording or scope to the document description:", "");
        if (extra === null) return;
        const clean = String(extra || "").trim();
        if (!clean) return;
        dom.work.value = [String(dom.work.value || "").trim(), clean].filter(Boolean).join("\n\n");
      });
      card.querySelector("#doc_auto_fill").addEventListener("click", async ()=> {
        try {
          if (dom.type.value === "estimate" && !String(dom.scopeIntent?.value || "").trim()) {
            return alert("Select the Proposed Scope before using Auto Fill Description.");
          }
          const completionForms = selectedDescriptionForms();
          const crew = completionForms.length > 1 || /crew/i.test(JSON.stringify(completionForms || []));
          const resp = await apiAutoFillDescription({
            job_id: job ? (job.id || "") : "",
            customer: dom.customer.value.trim() || (job && job.customer) || "",
            address: dom.address.value.trim() || (job && job.address) || "",
            door_location: (job && (job.door_location || job.location_on_site)) || "",
            door_id: (job && (job.door_id || job.opening_id)) || "",
            office_notes: (job && job.office_notes) || "",
            job_notes: (job && job.job_notes) || "",
            completion_forms: completionForms,
            recommendation_forms: completionForms.filter(f => f && (f.ready_to_quote || f.parts_required || f.time_required)),
            scope_intent: String(dom.scopeIntent?.value || "").trim(),
            crew: !!crew,
            trips: 1,
            type: docType,
            doc_type: docType,
            kind: docType,
            dates: [dom.date.value || ""],
          });
          dom.work.value = String((resp && resp.description) || "");
          if (!items.some(it => it.kind === "trip")) items.push(createDocLineItem({ code:"TRIP", description:"Trip Charge", qty:1, rate:Number(pricing.trip || 175), kind:"trip", taxable:false }));
          if (!items.some(it => it.kind === "fuel")) items.push(createDocLineItem({ code:"FUEL", description:"Fuel Surcharge", qty:1, rate:Number(pricing.fuel || 20), kind:"fuel", taxable:false }));
          renderItems();
        } catch (e) { alert(e.message || String(e)); }
      });
      async function applyHelperPrefill() {
        const helper = ctx && ctx.helperPrefill ? ctx.helperPrefill : null;
        if (!helper || editDoc) return;

        const trip = items.find(it => it.code === "TRIP" || it.kind === "trip" || it.description === "Trip Charge");
        if (trip) {
          trip.code = "TRIP";
          trip.description = "Trip Charge";
          trip.kind = "trip";
          trip.taxable = false;
          trip.qty = Number(helper.tripQty || 0);
          trip.rate = Number(pricing.trip || trip.rate || 175);
        }

        const fuel = items.find(it => it.code === "FUEL" || it.kind === "fuel" || it.description === "Fuel Surcharge");
        if (fuel) {
          fuel.code = "FUEL";
          fuel.description = "Fuel Surcharge";
          fuel.kind = "fuel";
          fuel.taxable = false;
          fuel.qty = Number(helper.fuelQty || 0);
          fuel.rate = Number(pricing.fuel || fuel.rate || 20);
        }

        const hours = Number(helper.hours || 0);
        if (hours > 0) {
          let desc = "Single Tech Labor";
          let qty = hours;
          let rate = Number(pricing.labor || 175);
          if (helper.laborType === "crew") {
            desc = "Crew Tech Labor";
            rate = Number(pricing.crew_labor || 235);
          } else if (helper.laborType === "other") {
            const count = Math.max(1, Number(helper.techCount || 1));
            desc = `${count} Tech Labor`;
            qty = hours;
            rate = Number(helper.customRate || pricing.labor || 175);
          }
          items.push(createDocLineItem({ code: "LABOR", description: desc, qty, rate, kind: "labor", taxable: false }));
        }

        const freightAmount = Number(helper.freightAmount || 0);
        if (freightAmount > 0) {
          items.push(createDocLineItem({ code: "FREIGHT", description: "Freight Surcharge", qty: 1, rate: freightAmount, kind: "fee", taxable: false }));
        }

        const helperParts = Array.isArray(helper.parts) ? helper.parts : [];
        helperParts.forEach(part => {
          items.push(createDocLineItem({ code: part.Item || "PART", description: part.Description || "", qty: 1, rate: Number(part.Price || 0), kind: "part", taxable: true }));
        });

        const partsText = String(helper.partsText || "").trim();
        if (partsText) {
          partsText.split(/\n+/).map(s => s.trim()).filter(Boolean).forEach(line => {
            items.push(createDocLineItem({ code: "PART", description: line, qty: 1, rate: 0, kind: "part", taxable: true }));
          });
        }

        if (helper.autoFill) {
          try {
            const completionForms = helper.sourceIndex != null && jobFormsForDescriptions[helper.sourceIndex] ? [jobFormsForDescriptions[helper.sourceIndex]] : selectedDescriptionForms();
            const crew = helper.laborType === "crew" || helper.laborType === "other" || completionForms.length > 1;
            const resp = await apiAutoFillDescription({
              job_id: job ? (job.id || "") : "",
              customer: dom.customer.value.trim() || (job && job.customer) || "",
              address: dom.address.value.trim() || (job && job.address) || "",
              door_location: (job && (job.door_location || job.location_on_site)) || "",
              door_id: (job && (job.door_id || job.opening_id)) || "",
              office_notes: (job && job.office_notes) || "",
              job_notes: (job && job.job_notes) || "",
              completion_forms: completionForms,
              recommendation_forms: completionForms.filter(f => f && (f.ready_to_quote || f.parts_required || f.time_required)),
              scope_intent: String(dom.scopeIntent?.value || "").trim(),
              selected_parts: Array.isArray(helper.parts) ? helper.parts : [],
              custom_parts_text: String(helper.partsText || "").trim(),
              crew: !!crew,
              trips: Number(helper.tripQty || 1),
              type: docType,
              doc_type: docType,
              kind: docType,
              dates: [dom.date.value || ""],
            });
            dom.work.value = String((resp && resp.description) || "");
          } catch (e) {
            console.warn("helper autofill failed", e);
          }
        }
      }

      await applyHelperPrefill();
      if (!editDoc) setTaxRateValue("");
      renderItems();
      
      function buildCurrentDocPayloadForExport() {
        return {
          job_id: job ? job.id : ((editDoc && editDoc.job_id) || ""),
          customer: dom.customer.value.trim(),
          email: job ? (job.email || "") : "",
          address: dom.address.value.trim(),
          work: dom.work.value.trim(),
          labor: serializeDocItems(items, true),
          parts: serializeDocItems(items, false),
          number: dom.number.value.trim(),
          po_number: dom.po.value.trim(),
          invoice_number: docType === "invoice" ? dom.number.value.trim() : "",
          estimate_number: docType === "estimate" ? dom.number.value.trim() : "",
          job_number: dom.job.value.trim(),
          tax_rate: Number(getCurrentTaxRateValue() || 0),
          terms: dom.terms ? dom.terms.value : "",
          completed_by: dom.completedBy.value || "",
          items: items,
          date: dom.date.value || "",
          ship_to: dom.ship.value.trim()
        };
      }
card.querySelector("#doc_generate").addEventListener("click", async ()=>{ try { if (!String(dom.completedBy.value || "").trim()) { alert("Please select who prepared this document before saving."); dom.completedBy.focus(); return; } if (!String(getCurrentTaxRateValue() || "").trim()) { alert("Please select the correct sales tax before saving."); if (dom.taxRateSelect.value === "__custom__") dom.taxRateCustom.focus(); else dom.taxRateSelect.focus(); return; } if (dom.terms && !String(dom.terms.value || "").trim()) { alert("Please select payment terms before saving."); dom.terms.focus(); return; } const payload = buildCurrentDocPayloadForExport(); const resp = editDoc ? await apiUpdateDocument(editDoc.filename, { ...payload, type: docType }) : (docType === "invoice" ? await apiCreateInvoice(payload) : await apiCreateEstimate(payload)); if (job && !editDoc) { const newDocNumber = (resp.doc && resp.doc.number) || dom.number.value.trim();
const updated = await apiUpdateJob(job.id, {
  po_number: dom.po.value.trim(),
  // Estimate/follow-up quote creation should populate Sent Estimate # only.
  // Never overwrite the job's actual Estimate # and never auto-move the dispatch to Quote Sent.
  estimate_number: job.estimate_number || "",
  invoice_number: docType === "invoice" ? newDocNumber : (job.invoice_number || ""),
  status: docType === "invoice" ? "Done" : (job.status || "Dispatch"),
  quote_assigned_to: dom.completedBy.value || (job.quote_assigned_to || ""),
  sent_quote_number: docType === "estimate" ? newDocNumber : (job.sent_quote_number || "")
}); if (overlay) overlay.remove(); if (ctx && ctx.afterSave) await ctx.afterSave(); if (container) renderJobDetails(container, updated, ctx); refreshBadges(); return; } if (overlay) overlay.remove(); if (ctx && ctx.refreshDocs) await ctx.refreshDocs(); if (currentView && currentView.refresh) currentView.refresh(); } catch(e){ alert(e.message || String(e)); } });
    });
  }
 

  function openEstimateInvoiceHelper(job = null, initialType = "estimate", container = null, ctx = null) {
    // Keep edits to existing saved docs direct; helper is only for new job estimate/invoice.
    if ((job && job.__docEdit) || (ctx && ctx.skipHelper)) {
      return openEstimateInvoiceDrawer(job, initialType, container, ctx);
    }

    openDrawer(initialType === "invoice" ? "Invoice Helper" : "Estimate Helper", async (drawerBody, overlay) => {
      const pricing = await apiGetPricing().catch(() => ({ trip:175, fuel:20, labor:175, crew_labor:235, tax:7.75 }));
      const forms = Array.isArray(job && job.completion_forms) ? job.completion_forms : [];

      function helperFormDate(value) {
        if (!value) return "";
        const s = String(value || "").slice(0, 10);
        const parts = s.split("-");
        if (parts.length === 3) return `${parts[1]}/${parts[2]}/${parts[0]}`;
        return s;
      }

      function isRecommendationForm(form) {
        return !!(form && (
          form.ready_to_quote ||
          form.parts_required ||
          form.time_required ||
          form.recommendations
        ));
      }

      function helperSourceLabel(form, idx) {
        const type = isRecommendationForm(form) ? "Recommendation" : "Completion";
        const details = [helperFormDate(form.date || form.form_date || form.created_at), form.technician_name || "", form.door_location || "", form.door_type || ""].filter(Boolean).join(" • ");
        return `${type} Form ${idx + 1}${details ? ` — ${details}` : ""}`;
      }

      function formSummaryHtml(form, typeLabel) {
        const rows = [];
        const addRow = (label, value) => {
          const clean = String(value || "").trim();
          if (clean) rows.push(`<div style="margin-top:8px;"><div class="label">${label}</div><div style="white-space:pre-wrap; font-weight:800;">${escapeHtml(clean)}</div></div>`);
        };

        addRow("Date", helperFormDate(form.date || form.form_date || form.created_at));
        addRow("Tech", form.technician_name);
        addRow("Door Type", form.door_type);
        addRow("Door Location", form.door_location);
        addRow("Time In", formatTime12(form.time_in));
        addRow("Time Out", formatTime12(form.time_out));

        if (typeLabel === "Recommendation") {
          addRow("Recommendations", form.recommendations || form.additional_recommendations || form.tech_notes);
          addRow("Parts Required", form.parts_required);
          addRow("Time Required", form.time_required);
          addRow("Ready to Quote", form.ready_to_quote ? "Yes" : "");
        } else {
          addRow("Time Onsite", form.time_onsite_hours ? `${form.time_onsite_hours} hour(s)` : "");
          addRow("Tech Notes", form.tech_notes);
          addRow("Parts Used", form.parts_used);
          addRow("Additional Recommendations", form.additional_recommendations || form.recommendations);
        }

        return `
          <div class="jobrow" style="align-items:stretch;">
            <div class="jobrow-top">
              <div>
                <div class="jobrow-name">${typeLabel} Form${form.date ? ` — ${escapeHtml(helperFormDate(form.date))}` : ""}</div>
                <div class="hint">${escapeHtml([form.door_location, form.door_type].filter(Boolean).join(" • ") || "No door/location entered")}</div>
              </div>
              ${form.ready_to_quote ? `<div class="badge">Ready to Quote</div>` : ""}
            </div>
            <div style="margin-top:8px;">${rows.join("") || `<div class="hint">No details saved on this form.</div>`}</div>
          </div>
        `;
      }

      function renderReferencePanel(kind) {
        const panel = card.querySelector("#helper_reference_panel");
        if (!panel) return;
        const wanted = kind === "recommendation" ? forms.filter(isRecommendationForm) : forms.filter(f => !isRecommendationForm(f));
        const label = kind === "recommendation" ? "Recommendation" : "Completion";
        panel.style.display = "block";
        panel.innerHTML = `
          <div class="card" style="padding:12px; margin-top:12px; background:#f9fafb;">
            <div class="jobrow-top">
              <div>
                <div class="jobrow-name">${label} Forms</div>
                <div class="hint">Reference only — this helps you see what the tech entered before building the ${initialType === "invoice" ? "invoice" : "estimate"}.</div>
              </div>
              <button class="btn" id="helper_reference_close">Hide</button>
            </div>
            <div style="display:grid; gap:10px; margin-top:10px;">
              ${wanted.length ? wanted.map(f => formSummaryHtml(f, label)).join("") : `<div class="hint">No ${label.toLowerCase()} forms found for this job.</div>`}
            </div>
          </div>
        `;
        const close = panel.querySelector("#helper_reference_close");
        if (close) close.addEventListener("click", () => { panel.style.display = "none"; panel.innerHTML = ""; });
      }

      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h3>${initialType === "invoice" ? "Invoice Helper" : "Estimate Helper"}</h3>
        <div class="hint">Answer a few quick questions to prefill the editable ${initialType === "invoice" ? "invoice" : "estimate"}. You can still edit everything before saving.</div>

        <div class="card" style="padding:12px; margin-top:12px;">
          <div class="jobrow-top">
            <div>
              <div class="jobrow-name">Want Help?</div>
              <div class="hint">Choose No to skip this helper and open the normal editable page.</div>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-orange" id="help_yes">Yes</button>
              <button class="btn" id="help_no">No</button>
            </div>
          </div>
        </div>

        <div id="helper_questions" style="display:none; margin-top:12px;">
          <div class="card" style="padding:12px; margin-bottom:12px;">
            <div class="jobrow-top">
              <div>
                <div class="jobrow-name">Job Reference</div>
                <div class="hint">${escapeHtml(job ? `${job.customer || ""}${job.job_number ? ` • Job #${job.job_number}` : ""}` : "No job selected")}</div>
              </div>
              <div style="display:flex; gap:8px; flex-wrap:wrap;">
                <button class="btn" id="helper_view_completion">Completion Form</button>
                <button class="btn" id="helper_view_recommendation">Recommendation Form</button>
              </div>
            </div>
            <div id="helper_reference_panel" style="display:none;"></div>
          </div>

          <div class="card" id="helper_source_wrap" style="padding:12px; margin-bottom:12px; ${forms.length ? "" : "display:none;"}">
            <div class="label">Description Source</div>
            <select class="input" id="helper_source_form">
              <option value="">Auto-select best saved form</option>
              ${forms.map((f, idx) => `<option value="${idx}">${escapeHtml(helperSourceLabel(f, idx))}</option>`).join("")}
            </select>
            <div class="hint" style="margin-top:6px;">Choose which Completion/Recommendation Form should drive the auto-filled description.</div>
          </div>

          <div class="grid2">
            <div>
              <div class="label">Trip Charge Quantity</div>
              <input class="input" id="helper_trip_qty" type="number" min="0" step="1" value="1" />
            </div>
            <div>
              <div class="label">Fuel Surcharge Quantity</div>
              <input class="input" id="helper_fuel_qty" type="number" min="0" step="1" value="1" />
            </div>
          </div>
          <div style="margin-top:12px;">
            <div class="label">Freight Surcharge (Untaxed)</div>
            <input class="input" id="helper_freight" type="number" min="0" step="0.01" placeholder="Optional freight amount" />
          </div>

          <div class="card" style="padding:12px; margin-top:12px;">
            <div class="label">Labor Type</div>
            <select class="input" id="helper_labor_type">
              <option value="tech">Tech</option>
              <option value="crew">Crew</option>
              <option value="other">Other</option>
            </select>
            <div id="helper_other_wrap" class="grid2" style="display:none; margin-top:10px;">
              <div>
                <div class="label">Total Techs</div>
                <input class="input" id="helper_tech_count" type="number" min="1" step="1" value="1" />
              </div>
              <div>
                <div class="label">Custom Labor Rate</div>
                <input class="input" id="helper_custom_rate" type="number" min="0" step="0.01" value="${Number(pricing.labor || 175)}" />
              </div>
            </div>
          </div>

          <div class="grid2" style="margin-top:12px;">
            <div>
              <div class="label">Time Onsite / Labor Hours</div>
              <input class="input" id="helper_hours" type="number" min="0" step="0.25" placeholder="e.g., 2.5" />
            </div>
            <div>
              <div class="label">Auto Fill Description?</div>
              <select class="input" id="helper_auto_fill">
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
          </div>

          <div style="margin-top:12px;">
            <div class="label">Parts / Materials</div>
            <input class="input" id="helper_part_search" placeholder="Search saved parts list by item number or description" autocomplete="off" />
            <div class="hint" id="helper_part_hint" style="margin-top:6px;">Search and click a part to add it. You can still add blank/special items in the editable estimate.</div>
            <div id="helper_part_results" style="display:grid; gap:8px; margin-top:8px;"></div>
            <div class="label" style="margin-top:10px;">Special / Blank Line Items</div>
            <textarea id="helper_parts" placeholder="Optional: enter custom parts/materials, one per line. These will be added as editable blank lines." style="min-height:90px;"></textarea>
            <div id="helper_selected_parts" style="display:grid; gap:8px; margin-top:8px;"></div>
          </div>

          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:12px;">
            <button class="btn btn-orange" id="helper_continue">Continue to Editable ${initialType === "invoice" ? "Invoice" : "Estimate"}</button>
            <button class="btn" id="helper_cancel">Cancel</button>
          </div>
        </div>
      `;
      drawerBody.appendChild(card);

      const questions = card.querySelector("#helper_questions");
      const laborType = card.querySelector("#helper_labor_type");
      const otherWrap = card.querySelector("#helper_other_wrap");

      function updateLaborMode() {
        otherWrap.style.display = laborType.value === "other" ? "grid" : "none";
      }
      laborType.addEventListener("change", updateLaborMode);
      updateLaborMode();

      const completionBtn = card.querySelector("#helper_view_completion");
      const recommendationBtn = card.querySelector("#helper_view_recommendation");
      if (completionBtn) completionBtn.addEventListener("click", () => renderReferencePanel("completion"));
      if (recommendationBtn) recommendationBtn.addEventListener("click", () => renderReferencePanel("recommendation"));

      card.querySelector("#help_no").addEventListener("click", () => {
        if (overlay) overlay.remove();
        openEstimateInvoiceDrawer(job, initialType, container, { ...(ctx || {}), skipHelper: true });
      });

      card.querySelector("#help_yes").addEventListener("click", () => {
        questions.style.display = "block";
        card.querySelector("#help_yes").disabled = true;
      });

      const helperSelectedParts = [];
      const helperPartSearch = card.querySelector("#helper_part_search");
      const helperPartResults = card.querySelector("#helper_part_results");
      const helperPartHint = card.querySelector("#helper_part_hint");
      const helperSelectedPartsBox = card.querySelector("#helper_selected_parts");
      function renderHelperSelectedParts() {
        if (!helperSelectedPartsBox) return;
        helperSelectedPartsBox.innerHTML = "";
        if (!helperSelectedParts.length) return;
        helperSelectedParts.forEach((part, idx) => {
          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `<div class="jobrow-top"><div><div class="jobrow-name">${escapeHtml(part.Item || part.item || "PART")}</div><div class="hint">${escapeHtml(part.Description || part.description || "")}${part.Price ? ` - $${money(part.Price)}` : ""}</div></div><button class="btn" type="button">Remove</button></div>`;
          row.querySelector("button").addEventListener("click", () => { helperSelectedParts.splice(idx, 1); renderHelperSelectedParts(); });
          helperSelectedPartsBox.appendChild(row);
        });
      }
      function renderHelperPartResults(results) {
        if (!helperPartResults) return;
        helperPartResults.innerHTML = "";
        const arr = Array.isArray(results) ? results : [];
        if (helperPartHint) helperPartHint.textContent = arr.length ? `${arr.length} matching part${arr.length === 1 ? "" : "s"}` : "No matching parts found.";
        arr.slice(0, 8).forEach(part => {
          const btn = document.createElement("button");
          btn.className = "btn";
          btn.type = "button";
          btn.style.textAlign = "left";
          btn.innerHTML = `<strong>${escapeHtml(part.Item || "")}</strong><br><span class="hint">${escapeHtml(part.Description || "")}${part.Price ? ` - $${money(part.Price)}` : ""}</span>`;
          btn.addEventListener("click", () => {
            helperSelectedParts.push(part);
            if (helperPartSearch) helperPartSearch.value = "";
            renderHelperPartResults([]);
            renderHelperSelectedParts();
          });
          helperPartResults.appendChild(btn);
        });
      }
      let helperPartTimer = null;
      if (helperPartSearch) helperPartSearch.addEventListener("input", () => {
        clearTimeout(helperPartTimer);
        const q = helperPartSearch.value.trim();
        if (!q) { renderHelperPartResults([]); return; }
        helperPartTimer = setTimeout(async () => {
          try { renderHelperPartResults(await apiListParts({ q, limit: 20 })); }
          catch { renderHelperPartResults([]); }
        }, 180);
      });

      card.querySelector("#helper_cancel").addEventListener("click", () => {
        if (overlay) overlay.remove();
      });

      card.querySelector("#helper_continue").addEventListener("click", () => {
        const helperPrefill = {
          tripQty: Number(card.querySelector("#helper_trip_qty").value || 0),
          fuelQty: Number(card.querySelector("#helper_fuel_qty").value || 0),
          freightAmount: Number(card.querySelector("#helper_freight")?.value || 0),
          laborType: laborType.value,
          techCount: Number(card.querySelector("#helper_tech_count").value || 1),
          customRate: Number(card.querySelector("#helper_custom_rate").value || pricing.labor || 175),
          hours: Number(card.querySelector("#helper_hours").value || 0),
          partsText: String(card.querySelector("#helper_parts").value || "").trim(),
          parts: helperSelectedParts.map(p => ({ Item: p.Item || "", Description: p.Description || "", Price: Number(p.Price || 0) })),
          autoFill: card.querySelector("#helper_auto_fill").value === "yes",
          sourceIndex: card.querySelector("#helper_source_form") && card.querySelector("#helper_source_form").value !== "" ? Number(card.querySelector("#helper_source_form").value) : null,
        };
        if (overlay) overlay.remove();
        openEstimateInvoiceDrawer(job, initialType, container, { ...(ctx || {}), skipHelper: true, helperPrefill });
      });
    });
  }


function openEstimateDrawer(job, container = null, ctx = null) {
    return openEstimateInvoiceHelper(job, "estimate", container, ctx);
  }
 
  function openInvoiceDrawer(job, container = null, ctx = null) {
    return openEstimateInvoiceHelper(job, "invoice", container, ctx);
  }
 
  function renderEstimatePage() {
    setNavActive(primaryEstimateNav);
    setActiveChip("Office Flow");
    setWorkspace("Estimate/Invoice");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const tabs = document.createElement("div");
    tabs.style.display = "flex";
    tabs.style.gap = "8px";
    tabs.style.flexWrap = "wrap";
    tabs.style.marginBottom = "12px";
 
    const btnGen = document.createElement("button");
    btnGen.className = "navbtn navbtn-active";
    btnGen.style.width = "auto";
    btnGen.innerHTML = `<span>Generator</span>`;
    const btnEst = document.createElement("button");
    btnEst.className = "navbtn";
    btnEst.style.width = "auto";
    btnEst.innerHTML = `<span>Estimates</span>`;
    const btnInv = document.createElement("button");
    btnInv.className = "navbtn";
    btnInv.style.width = "auto";
    btnInv.innerHTML = `<span>Invoices</span>`;
    tabs.append(btnGen, btnEst, btnInv);
 
    const body = document.createElement("div");
    root.append(tabs, body);
 
    let activeTab = "generator";
    function syncTabs() {
      btnGen.classList.toggle("navbtn-active", activeTab === "generator");
      btnEst.classList.toggle("navbtn-active", activeTab === "estimates");
      btnInv.classList.toggle("navbtn-active", activeTab === "invoices");
    }
 
    async function renderDocList(type) {
      body.innerHTML = "";
      const docs = await apiListDocuments({ type }).catch(() => []);
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `<h3>${type === "estimate" ? "Saved Estimates" : "Saved Invoices"}</h3><div class="hint">View, edit, or delete saved documents.</div><input class="input" id="doc_list_search" placeholder="Search ${type === "estimate" ? "estimates" : "invoices"} by #, customer, address, job #, PO #, prepared by..." style="margin-top:12px;" />`;
      const list = document.createElement("div");
      list.style.display = "grid";
      list.style.gap = "8px";
      list.style.marginTop = "12px";

      const renderRows = (query = "") => {
        const q = String(query || "").trim().toLowerCase();
        const filtered = docs.filter(doc => {
          if (!q) return true;
          const hay = [doc.number, doc.filename, doc.customer, doc.address, doc.job_number, doc.po_number, doc.completed_by, doc.type]
            .map(v => String(v || "").toLowerCase()).join(" ");
          return hay.includes(q);
        });
        list.innerHTML = "";
        if (!filtered.length) {
          list.innerHTML = `<div class="hint">No matching ${type}s found.</div>`;
          return;
        }
        filtered.forEach(doc => {
          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${type === "invoice" ? "Invoice" : "Estimate"} ${escapeHtml(doc.number || "")}</div>${statusPill(type === "invoice" ? "Done" : "Quote Sent").outerHTML}</div><div class="jobrow-addr">${escapeHtml(doc.customer || "")}${doc.job_number ? ` - Job #${escapeHtml(doc.job_number)}` : ""}</div><div class="hint">${escapeHtml(doc.address || "")}</div><div class="hint">Prepared By: ${escapeHtml(doc.completed_by || "")}</div>`;
          const actions = document.createElement("div");
          actions.style.display = "flex";
          actions.style.gap = "8px";
          actions.style.marginTop = "8px";
          const open = document.createElement("a");
          open.href = doc.open_url || doc.download_url || "#";
          open.target = "_blank";
          open.rel = "noopener noreferrer";
          open.textContent = "Open";
          styleActionButton(open, "blue", true);
          const emailBtn = document.createElement("button");
          emailBtn.type = "button";
          emailBtn.textContent = "Email";
          styleActionButton(emailBtn, "green", true);
          emailBtn.addEventListener("click", () => openEstimateInvoiceEmail(doc, doc.type || type));
          const edit = document.createElement("button");
          edit.type = "button";
          edit.textContent = "Edit";
          styleActionButton(edit, "ghost", true);
          edit.addEventListener("click", () => {
            const fakeJob = { id: doc.job_id || "", customer: doc.customer || "", address: doc.address || "", po_number: doc.po_number || "", job_number: doc.job_number || "", __docEdit: doc };
            openEstimateInvoiceDrawer(fakeJob, doc.type || type, null, { refreshDocs: () => renderDocList(type) });
          });
          const del = document.createElement("button");
          del.type = "button";
          del.textContent = "Delete";
          styleActionButton(del, "danger", true);
          del.addEventListener("click", async () => {
            if (!confirm(`Delete ${doc.number || doc.filename || "this document"}?`)) return;
            await apiDeleteDocument(doc.filename);
            renderDocList(type);
          });
          actions.append(open, emailBtn, edit, del);
          row.appendChild(actions);
          list.appendChild(row);
        });
      };

      renderRows("");
      const searchInput = card.querySelector("#doc_list_search");
      if (searchInput) searchInput.addEventListener("input", () => renderRows(searchInput.value));
      card.appendChild(list);
      body.appendChild(card);
    }
 
    function renderGeneratorTab() {
      body.innerHTML = `<div class="card"><h3>Estimate / Invoice</h3><div class="hint">Open a blank document and choose estimate or invoice inside the builder.</div><div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;"><button class="btn btn-orange" id="openDocBuilder">Open Builder</button><button class="btn" id="openPricingSettings">Billing Settings</button></div></div>`;
      const btn = document.getElementById("openDocBuilder");
      if (btn) btn.addEventListener("click", () => openEstimateInvoiceDrawer(null, "estimate", null, { refreshDocs: renderActiveTab }));
      const ps = document.getElementById("openPricingSettings");
      if (ps) ps.addEventListener("click", renderPricingSettingsView);
    }
 
    async function renderActiveTab() {
      syncTabs();
      if (activeTab === "estimates") return renderDocList("estimate");
      if (activeTab === "invoices") return renderDocList("invoice");
      renderGeneratorTab();
    }
 
    btnGen.addEventListener("click", () => { activeTab = "generator"; renderActiveTab(); });
    btnEst.addEventListener("click", () => { activeTab = "estimates"; renderActiveTab(); });
    btnInv.addEventListener("click", () => { activeTab = "invoices"; renderActiveTab(); });
 
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    currentView = { refresh: renderActiveTab };
    renderActiveTab();
  }
 
  function renderInvoicePage() {
    renderEstimatePage();
  }
 


  function renderPricingSettingsView() {
    setNavActive(navPricingSettings);
    setActiveChip("Office Flow");
    setWorkspace("Billing Settings");
    clearWorkspaceActions();
    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3>Billing Settings</h3>
      <div class="hint">Update default charges, billing terms, and city sales tax rates used by the estimate/invoice builder.</div>
      <div class="grid2" style="margin-top:12px;">
        <div><div class="label">Trip Charge</div><input class="input" id="ps_trip" type="number" step="0.01" /></div>
        <div><div class="label">Fuel Surcharge</div><input class="input" id="ps_fuel" type="number" step="0.01" /></div>
        <div><div class="label">Single Tech Labor</div><input class="input" id="ps_labor" type="number" step="0.01" /></div>
        <div><div class="label">Crew Tech Labor</div><input class="input" id="ps_crew" type="number" step="0.01" /></div>
        <div><div class="label">Default Sales Tax %</div><input class="input" id="ps_tax" type="number" step="0.01" /></div>
        <div><div class="label">Default Terms</div><select class="input" id="ps_default_terms"></select></div>
      </div>
      <div style="margin-top:12px;">
        <div class="label">Sales Tax Cities / Rates</div>
        <div class="hint">One per line: City | Rate. Example: Escondido | 8.75</div>
        <textarea id="ps_tax_cities" style="min-height:180px;"></textarea>
      </div>
      <div style="margin-top:12px;">
        <div class="label">Billing Terms</div>
        <div class="hint">One term per line.</div>
        <textarea id="ps_terms" style="min-height:120px;"></textarea>
      </div>
      <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
        <button class="btn btn-orange" id="ps_save">Save Billing Settings</button>
        <button class="btn" id="ps_reset">Reset City/Terms Defaults</button>
      </div>
      <div class="hint" id="ps_status" style="margin-top:8px;"></div>
    `;
    root.appendChild(card);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    currentView = { refresh: renderPricingSettingsView };
    (async () => {
      const pricing = await apiGetPricing().catch(() => ({ trip:175, fuel:20, labor:175, crew_labor:235, tax:7.75 }));
      applyPricingBillingSettings(pricing);
      const termSel = card.querySelector("#ps_default_terms");
      function renderTermsSelect() {
        termSel.innerHTML = "";
        BILLING_TERMS_OPTIONS.forEach(term => { const o=document.createElement("option"); o.value=term; o.textContent=term; termSel.appendChild(o); });
      }
      function fillTextareas() {
        card.querySelector("#ps_tax_cities").value = SALES_TAX_OPTIONS.map(x => `${x.city} | ${Number(x.rate || 0).toFixed(2)}`).join("\n");
        card.querySelector("#ps_terms").value = BILLING_TERMS_OPTIONS.join("\n");
        renderTermsSelect();
      }
      card.querySelector("#ps_trip").value = pricing.trip ?? 175;
      card.querySelector("#ps_fuel").value = pricing.fuel ?? 20;
      card.querySelector("#ps_labor").value = pricing.labor ?? 175;
      card.querySelector("#ps_crew").value = pricing.crew_labor ?? 235;
      card.querySelector("#ps_tax").value = pricing.tax ?? 7.75;
      fillTextareas();
      termSel.value = pricing.default_terms || "Due on Receipt";
      card.querySelector("#ps_reset").addEventListener("click", () => { saveBillingTaxOptions(DEFAULT_SALES_TAX_OPTIONS); saveBillingTermsOptions(DEFAULT_BILLING_TERMS); fillTextareas(); termSel.value = "Due on Receipt"; });
      card.querySelector("#ps_save").addEventListener("click", async () => {
        try {
          const taxCities = String(card.querySelector("#ps_tax_cities").value || "").split(/\n+/).map(line => {
            const [city, rate] = line.split("|");
            return { city: String(city || "").trim(), rate: Number(String(rate || "0").trim()) };
          }).filter(x => x.city);
          const terms = String(card.querySelector("#ps_terms").value || "").split(/\n+/).map(x => x.trim()).filter(Boolean);
          saveBillingTaxOptions(taxCities);
          saveBillingTermsOptions(terms);
          await apiSavePricing({
            trip: Number(card.querySelector("#ps_trip").value || 0),
            fuel: Number(card.querySelector("#ps_fuel").value || 0),
            labor: Number(card.querySelector("#ps_labor").value || 0),
            crew_labor: Number(card.querySelector("#ps_crew").value || 0),
            tax: Number(card.querySelector("#ps_tax").value || 0),
            default_terms: termSel.value || "Due on Receipt",
            tax_cities: taxCities,
            billing_terms: terms,
          });
          card.querySelector("#ps_status").textContent = "Billing settings saved.";
        } catch (e) { card.querySelector("#ps_status").textContent = e.message || String(e); }
      });
    })();
  }

  function renderDoorLogsView() {
    setNavActive(navDoorLogs);
    setActiveChip("Job Flow");
    setWorkspace("Door Records");
    clearWorkspaceActions();
    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3>Door Records</h3>
      <div class="hint">Track specific openings by customer, address, project, and job number.</div>
      <div class="grid2" style="margin-top:12px;">
        <div style="position:relative;"><div class="label">Customer</div><input class="input" id="dl_customer" list="dl_customer_list" autocomplete="off" /><datalist id="dl_customer_list"></datalist><div id="dl_customer_results" style="display:none; position:absolute; left:0; right:0; top:100%; z-index:20; background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:6px;"></div></div>
        <div><div class="label">Address</div><input class="input" id="dl_address" /></div>
        <div><div class="label">Project</div><input class="input" id="dl_project" /></div>
        <div><div class="label">Job #</div><input class="input" id="dl_job_number" /></div>
        <div><div class="label">Door Location</div><input class="input" id="dl_location" /></div>
        <div><div class="label">Door ID</div><input class="input" id="dl_door_id" placeholder="Required searchable door identifier" /></div>
        <div><div class="label">Door Type</div><select class="input" id="dl_door_type"><option value="">Select Door Type --</option><option>Automatic Door</option><option>Man Door</option><option>Storefront Door</option><option>Herculite Door</option><option>Roll Up</option><option>Glass</option><option>Roll/Swing Gate</option><option>Other</option></select></div>
        
        <div><div class="label">Manufacturer</div><input class="input" id="dl_manufacturer" /></div>
        <div><div class="label">Model</div><input class="input" id="dl_model" /></div>
        <div><div class="label">Serial Number</div><input class="input" id="dl_serial" /></div>
      </div>
      <div style="margin-top:10px;"><div class="label">Notes</div><textarea id="dl_notes"></textarea></div>
      <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
        <button class="btn btn-orange" id="dl_save">Save Door Log</button>
        <button class="btn" id="dl_clear">Clear</button>
        <button class="btn" id="dl_print">Print Results</button>
      </div>
      <div style="margin-top:12px;"><input class="input" id="dl_search" placeholder="Search customer, address, door location, door ID, notes..." /></div>
      <div id="dl_list" style="display:grid; gap:8px; margin-top:12px;"></div>
    `;
    root.appendChild(card);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    currentView = { refresh: renderDoorLogsView };

    let editId = "";
    let allLogs = [];
    let knownAddresses = [];
    const list = card.querySelector("#dl_list");
    function readForm() {
      return {
        customer: card.querySelector("#dl_customer").value.trim(),
        address: card.querySelector("#dl_address").value.trim(),
        project: card.querySelector("#dl_project").value.trim(),
        job_number: card.querySelector("#dl_job_number").value.trim(),
        door_location: card.querySelector("#dl_location").value.trim(),
        door_id: card.querySelector("#dl_door_id").value.trim(),
        door_type: card.querySelector("#dl_door_type").value.trim(),
        manufacturer: card.querySelector("#dl_manufacturer").value.trim(),
        model: card.querySelector("#dl_model").value.trim(),
        serial_number: card.querySelector("#dl_serial").value.trim(),
        notes: card.querySelector("#dl_notes").value.trim(),
      };
    }
    function fillForm(item) {
      editId = item && item.id ? item.id : "";
      card.querySelector("#dl_customer").value = item?.customer || "";
      card.querySelector("#dl_address").value = item?.address || "";
      card.querySelector("#dl_project").value = item?.project || "";
      card.querySelector("#dl_job_number").value = item?.job_number || "";
      card.querySelector("#dl_location").value = item?.door_location || "";
      card.querySelector("#dl_door_id").value = item?.door_id || "";
      card.querySelector("#dl_door_type").value = item?.door_type || "";
      card.querySelector("#dl_manufacturer").value = item?.manufacturer || "";
      card.querySelector("#dl_model").value = item?.model || "";
      card.querySelector("#dl_serial").value = item?.serial_number || "";
      card.querySelector("#dl_notes").value = item?.notes || "";
    }
    function clearForm() { fillForm(null); }
    function matches(item, q) {
      const history = Array.isArray(item.history) ? item.history : [];
      const historyText = history.map(entry => [entry.job_number, entry.technician, entry.date, entry.summary, entry.parts_used, entry.recommendations, entry.door_location, entry.door_type].join(" ")).join(" ");
      const hay = [item.customer, item.address, item.project, item.job_number, item.door_location, item.door_id, item.door_type, item.manufacturer, item.model, item.serial_number, item.notes, historyText].join(" ").toLowerCase();
      return !q || hay.includes(q);
    }
    async function openDoorHistoryJob(entry) {
      if (!entry || !entry.job_id) return;
      try {
        const sourceJob = await apiGetJob(entry.job_id);
        openDrawer(`Door History — ${sourceJob.job_number || "Job"}`, async (drawerBody) => {
          renderJobDetails(drawerBody, sourceJob, { afterSave: async () => {}, afterDelete: async () => {} });
        });
      } catch (e) {
        alert(e.message || String(e));
      }
    }
    function renderList() {
      const q = String(card.querySelector("#dl_search").value || "").trim().toLowerCase();
      list.innerHTML = "";
      const filtered = allLogs.filter(item => matches(item, q));
      if (!filtered.length) { list.innerHTML = `<div class="hint">No door records found.</div>`; return; }
      filtered.forEach(item => {
        const row = document.createElement("div");
        row.className = "jobrow";
        const history = (Array.isArray(item.history) ? item.history.slice() : []).sort((a, b) => String(b.date || b.created_at || "").localeCompare(String(a.date || a.created_at || "")));
        const historyHtml = history.length ? history.map((entry, index) => `
          <div style="border-top:1px solid #e5e7eb; padding:10px 0; margin-top:${index ? 0 : 8}px;">
            <div style="display:flex; justify-content:space-between; gap:8px; flex-wrap:wrap;">
              <strong>${escapeHtml(entry.date || "Service Visit")}</strong>
              <span class="badge">${escapeHtml(entry.job_number || "No Job #")}</span>
            </div>
            <div class="hint">Technician: ${escapeHtml(entry.technician || "—")}</div>
            ${entry.summary ? `<div style="margin-top:5px;">${escapeHtml(entry.summary)}</div>` : ""}
            ${entry.parts_used ? `<div class="hint" style="margin-top:4px;"><strong>Parts:</strong> ${escapeHtml(entry.parts_used)}</div>` : ""}
            ${entry.recommendations ? `<div class="hint" style="margin-top:4px;"><strong>Recommendations:</strong> ${escapeHtml(entry.recommendations)}</div>` : ""}
            ${entry.job_id ? `<button class="btn" data-door-history-index="${index}" style="margin-top:7px;">Open Job / Completion Form</button>` : ""}
          </div>`).join("") : `<div class="hint" style="margin-top:8px;">No linked completion-form history yet.</div>`;
        row.innerHTML = `
          <div class="jobrow-top"><div class="jobrow-name">${escapeHtml(item.customer || "Door Record")}</div><div class="badge">Active</div></div>
          <div class="jobrow-addr">${escapeHtml(item.address || "")}</div>
          <div class="hint">Door: ${escapeHtml(item.door_id || "—")} | ${escapeHtml(item.door_location || "—")} | ${escapeHtml(item.door_type || "—")}</div>
          <div class="hint">Manufacturer: ${escapeHtml(item.manufacturer || "—")} | Model: ${escapeHtml(item.model || "—")} | Serial: ${escapeHtml(item.serial_number || "—")}</div>
          <div class="hint">Latest Job #: ${escapeHtml(item.job_number || "—")} | History Entries: ${history.length}</div>
          <details style="margin-top:8px;"><summary style="cursor:pointer; font-weight:800;">Service History (${history.length})</summary>${historyHtml}</details>`;
        row.querySelectorAll("button[data-door-history-index]").forEach(btn => {
          btn.addEventListener("click", () => openDoorHistoryJob(history[Number(btn.dataset.doorHistoryIndex)]));
        });
        const actions = document.createElement("div");
        actions.style.display = "flex"; actions.style.gap = "8px"; actions.style.marginTop = "8px";
        const edit = document.createElement("button"); edit.className = "btn"; edit.textContent = "Edit"; edit.addEventListener("click", ()=> fillForm(item));
        const del = document.createElement("button"); del.className = "btn"; del.textContent = "Delete"; del.addEventListener("click", async ()=> { if (!confirm("Delete this door record and its linked history?")) return; await apiDeleteDoorLog(item.id); await load(); });
        actions.append(edit, del); row.appendChild(actions); list.appendChild(row);
      });
    }
    let customers = [];
    function hideCustomerResults() {
      const box = card.querySelector("#dl_customer_results");
      if (box) { box.innerHTML = ""; box.style.display = "none"; }
    }
    function renderCustomerResults(q) {
      const box = card.querySelector("#dl_customer_results");
      if (!box) return;
      const query = String(q || "").trim().toLowerCase();
      if (!query || !Array.isArray(customers) || !customers.length) { hideCustomerResults(); return; }
      const matches = customers.filter(c => {
        const hay = [c.company_name, c.name, c.customer_name, c.company, c.address, c.site_address, c.job_address, c.street, c.city, c.state, c.zip].join(" ").toLowerCase();
        return hay.includes(query);
      }).slice(0, 8);
      if (!matches.length) { hideCustomerResults(); return; }
      box.innerHTML = matches.map(c => {
        const name = escapeHtml(c.company_name || c.name || c.customer_name || c.company || "");
        const addr = escapeHtml((c.address || c.site_address || c.job_address || [c.street || "", c.city || "", c.state || "", c.zip || ""].filter(Boolean).join(", ")) || "");
        return `<button type="button" class="btn" data-customer-name="${name.replace(/"/g,'&quot;')}" data-customer-address="${addr.replace(/"/g,'&quot;')}" style="width:100%; text-align:left; display:block; margin-top:4px;">${name}<div class="hint">${addr}</div></button>`;
      }).join("");
      box.style.display = "block";
      box.querySelectorAll("button[data-customer-name]").forEach(btn => {
        btn.addEventListener("click", () => {
          card.querySelector("#dl_customer").value = btn.getAttribute("data-customer-name") || "";
          const addr = btn.getAttribute("data-customer-address") || "";
          if (addr && !card.querySelector("#dl_address").value.trim()) card.querySelector("#dl_address").value = addr;
          hideCustomerResults();
        });
      });
    }
    function renderCustomerDatalist() {
      const dl = card.querySelector("#dl_customer_list");
      if (!dl) return;
      dl.innerHTML = (Array.isArray(customers) ? customers : []).map(c => {
        const val = c.company_name || c.name || c.customer_name || c.company || "";
        return val ? `<option value="${escapeHtml(val)}"></option>` : "";
      }).join("");
    }
    function autofillCustomerAddress() {
      const typed = normalizeText(card.querySelector("#dl_customer").value);
      if (!typed) return;
      const match = (Array.isArray(customers) ? customers : []).find(c => {
        const names = [c.company_name, c.name, c.customer_name, c.company].map(normalizeText).filter(Boolean);
        return names.some(n => n === typed || n.includes(typed) || typed.includes(n));
      });
      if (!match) return;
      const display = match.company_name || match.name || match.customer_name || match.company || card.querySelector("#dl_customer").value;
      const addr = match.address || match.site_address || match.job_address || [match.street || "", match.city || "", match.state || "", match.zip || ""].filter(Boolean).join(", ");
      card.querySelector("#dl_customer").value = display;
      if (addr && !card.querySelector("#dl_address").value.trim()) card.querySelector("#dl_address").value = addr;
    }
    async function load() {
      const data = await apiListDoorLogs().catch(() => []);
      allLogs = Array.isArray(data) ? data : [];
      customers = await apiListCustomers().catch(() => []);
      knownAddresses = await apiListAddresses({ limit: 1500 }).catch(() => []);
      wireKnownAddressAutofill({ input: card.querySelector("#dl_address"), customerInput: card.querySelector("#dl_customer"), knownAddresses, extraAddresses: customers.map(c => c.address || c.site_address || c.job_address || "").filter(Boolean) });
      renderCustomerDatalist();
      renderList();
    }
    card.querySelector("#dl_customer").addEventListener("input", (e)=> renderCustomerResults(e.target.value));
    card.querySelector("#dl_customer").addEventListener("change", autofillCustomerAddress);
    card.querySelector("#dl_customer").addEventListener("blur", ()=> setTimeout(() => { autofillCustomerAddress(); hideCustomerResults(); }, 150));
    card.querySelector("#dl_save").addEventListener("click", async ()=> {
      const payload = readForm();
      if (!payload.door_id) { alert("Door ID is required so each individual door can be tracked and searched."); return; }
      if (!payload.customer && !payload.address && !payload.project && !payload.job_number && !payload.door_location) { alert("Enter at least customer, address, project, job number, or door location."); return; }
      if (editId) await apiUpdateDoorLog(editId, payload); else await apiCreateDoorLog(payload);
      clearForm();
      await load();
    });
    card.querySelector("#dl_clear").addEventListener("click", clearForm);
    card.querySelector("#dl_search").addEventListener("input", renderList);
    card.querySelector("#dl_print").addEventListener("click", ()=> window.print());
    load();
  }

  function renderTimeOffView() {
    setNavActive(navFormsTimeOff);
    setActiveChip("Forms");
    setWorkspace("Time Off Request");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    root.style.display = "grid";
    root.style.gridTemplateColumns = "1.1fr 1fr";
    root.style.gap = "14px";
 
    const formCard = document.createElement("div");
    formCard.className = "card";
    formCard.innerHTML = `
      <h3>Request Time Off</h3>
      <div class="hint">Submit a request for approval.</div>
      <div style="margin-top:12px;">
        <div class="label">Employee</div>
        <select class="input" id="tor_employee"></select>
      </div>
      <div class="grid2" style="margin-top:10px;">
        <div><div class="label">Start Date</div><input class="input" id="tor_start" type="date" /></div>
        <div><div class="label">End Date</div><input class="input" id="tor_end" type="date" /></div>
      </div>
      <div style="margin-top:10px;">
        <label style="display:flex; align-items:center; gap:8px; font-weight:700;">
          <input type="checkbox" id="tor_emergency" />
          <span>Emergency</span>
        </label>
        <div class="hint" style="margin-top:4px;">Use for same-day call-outs, illness, or immediate emergencies.</div>
      </div>
      <div class="grid2" style="margin-top:10px;">
        <div>
          <label style="display:flex; align-items:center; gap:8px; font-weight:700;">
            <input type="checkbox" id="tor_use_pto" />
            <span>Use PTO</span>
          </label>
        </div>
        <div><div class="label">PTO Hours</div><input class="input" id="tor_pto_hours" type="number" step="0.25" placeholder="0.00" /></div>
      </div>
      <div style="margin-top:10px;">
        <div class="label">Notes</div>
        <textarea id="tor_notes" placeholder="Reason / notes" style="min-height:100px;"></textarea>
      </div>
      <div style="display:flex; gap:8px; margin-top:12px;">
        <button class="btn btn-orange" id="tor_submit">Submit Request</button>
      </div>
    `;
 
    const listCard = document.createElement("div");
    listCard.className = "card";
    listCard.innerHTML = `<h3>Requests</h3><div class="hint">Pending, approved, and declined time off.</div>`;
    const list = document.createElement("div");
    list.style.display = "grid";
    list.style.gap = "8px";
    list.style.marginTop = "12px";
    listCard.appendChild(list);
 
    root.append(formCard, listCard);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    async function refresh() {
      const selfOnly = currentUser && ["tech", "lead"].includes(String(currentUser.role || ""));
      const selfName = (currentUser && (currentUser.name || currentUser.username)) ? String(currentUser.name || currentUser.username) : "";
      const [employees, requestsRaw] = await Promise.all([apiListEmployees().catch(() => []), apiListTimeOff({ limit: 500, ...(selfOnly && selfName ? { employee_name: selfName } : {}) }).catch(() => [])]);
      const requests = [...requestsRaw].sort((a, b) => {
        const ap = a && a.emergency ? 1 : 0;
        const bp = b && b.emergency ? 1 : 0;
        if (bp !== ap) return bp - ap;
        return String(b.created_at || "").localeCompare(String(a.created_at || ""));
      });
      const sel = formCard.querySelector("#tor_employee");
      const prevVal = sel.value;
      if (selfOnly) {
        sel.innerHTML = selfName ? `<option value="${escapeHtml(selfName)}">${escapeHtml(selfName)}</option>` : `<option value="">-- Select employee --</option>`;
        sel.value = selfName;
        sel.disabled = true;
      } else {
        sel.disabled = false;
        sel.innerHTML = `<option value="">-- Select employee --</option>` + employees.map(e => `<option value="${escapeHtml(e.name || "")}">${escapeHtml(e.name || "")}</option>`).join("");
        if (prevVal) sel.value = prevVal;
      }
 
      const pendingCount = requests.filter(item => isActionableTimeOffRequest(item)).length;
      const timeOffBadge = el('badgeTimeOff');
      if (timeOffBadge) {
        timeOffBadge.textContent = String(pendingCount);
        timeOffBadge.style.display = pendingCount ? 'inline-flex' : 'none';
      }
      list.innerHTML = "";
      if (!requests.length) {
        list.innerHTML = `<div class="hint">No time off requests yet.</div>`;
        return;
      }
      requests.forEach(item => {
        const pillStatus = item.status === "approved" ? "Approved" : item.status === "declined" ? "Denied" : "Pending";
        const row = document.createElement("div");
        row.className = "jobrow";
        row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(item.employee_name || "")}${item.emergency ? ` <span style="margin-left:8px; font-size:12px; color:#b91c1c;">EMERGENCY</span>` : ""}</div>${statusPill(pillStatus).outerHTML}</div><div class="jobrow-addr">${escapeHtml(formatDisplayDate(item.start_date || ""))}${item.end_date && item.end_date !== item.start_date ? ` - ${escapeHtml(formatDisplayDate(item.end_date))}` : ""}${item.use_pto ? ` - PTO ${escapeHtml(String(item.pto_hours || 0))} hrs` : ""}</div><div class="hint">${escapeHtml(item.notes || "")}</div>`;
        const actions = document.createElement("div");
        actions.style.display = "flex"; actions.style.gap = "8px"; actions.style.marginTop = "8px";
        if (!selfOnly && item.status === "pending") {
          const approve = document.createElement("button"); approve.type = "button"; approve.textContent = "Approve"; styleActionButton(approve, "green", true);
          approve.addEventListener("click", async () => { await apiUpdateTimeOff(item.id, { status: "approved" }); refresh(); });
          const decline = document.createElement("button"); decline.type = "button"; decline.textContent = "Decline"; styleActionButton(decline, "ghost", true);
          decline.addEventListener("click", async () => { await apiUpdateTimeOff(item.id, { status: "declined" }); refresh(); });
          actions.append(approve, decline);
        }
        if (!selfOnly || String(item.status || "").toLowerCase() === "pending") {
          const del = document.createElement("button"); del.type = "button"; del.textContent = "Delete"; styleActionButton(del, "danger", true);
          del.addEventListener("click", async () => { if (!confirm("Delete this time off request?")) return; await apiDeleteTimeOff(item.id); refresh(); });
          actions.appendChild(del);
        }
        row.appendChild(actions);
        list.appendChild(row);
      });
    }
 
    formCard.querySelector("#tor_submit").addEventListener("click", async () => {
      const employee = ((currentUser && ["tech", "lead"].includes(String(currentUser.role || ""))) ? String(currentUser.name || currentUser.username || "") : formCard.querySelector("#tor_employee").value.trim());
      const start = formCard.querySelector("#tor_start").value;
      const end = formCard.querySelector("#tor_end").value || start;
      const notes = formCard.querySelector("#tor_notes").value.trim();
      if (!employee) return alert("Please select an employee.");
      if (!start) return alert("Please choose a start date.");
      await apiCreateTimeOff({ employee_name: employee, start_date: start, end_date: end, notes, emergency: !!formCard.querySelector("#tor_emergency").checked, use_pto: !!formCard.querySelector("#tor_use_pto").checked, pto_hours: Number(formCard.querySelector("#tor_pto_hours").value || 0), status: "pending" });
      formCard.querySelector("#tor_start").value = "";
      formCard.querySelector("#tor_end").value = "";
      formCard.querySelector("#tor_notes").value = "";
      formCard.querySelector("#tor_emergency").checked = false;
      formCard.querySelector("#tor_use_pto").checked = false;
      formCard.querySelector("#tor_pto_hours").value = "";
      refresh();
    });
 
    currentView = { refresh };
    refresh();
  }
 
  function renderNotificationsView() {
    setNavActive(navNotifications);
    setActiveChip("Notifications");
    setWorkspace("Team Messages");
    clearWorkspaceActions();

    const root = document.createElement("div");
    root.style.display = "grid";
    root.style.gridTemplateColumns = "320px 1fr";
    root.style.gap = "14px";

    const left = document.createElement("div");
    left.className = "card";
    left.innerHTML = `
      <h3>Messages</h3>
      <div class="hint">All Hands and direct messages.</div>
      <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
        <button class="btn btn-orange" id="msg_filter_inbox">Inbox</button>
        <button class="btn" id="msg_filter_direct">Direct</button>
        <button class="btn" id="msg_filter_all">All</button>
      </div>
      <div style="margin-top:10px;"><input class="input" id="msg_search" placeholder="Search messages..." /></div>
      <div id="msg_threads" style="display:grid; gap:8px; margin-top:12px;"></div>
    `;

    const right = document.createElement("div");
    right.className = "card";
    right.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
        <div>
          <h3 id="msg_title" style="margin:0;">All Hands</h3>
          <div class="hint" id="msg_subtitle">Team-wide messages</div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn" id="msg_mark_read">Mark Read</button>
          <button class="btn" id="msg_refresh">Refresh</button>
        </div>
      </div>
      <div id="msg_feed" style="display:grid; gap:10px; margin-top:14px; min-height:260px;"></div>
      <div style="border-top:1px solid var(--line); margin-top:14px; padding-top:14px; display:grid; gap:10px;">
        <div>
          <div class="label">Send To</div>
          <select class="input" id="msg_to"><option value="__ALL__">All Hands</option></select>
        </div>
        <div>
          <div class="label">Message</div>
          <textarea id="msg_body" placeholder="Type a message..." style="min-height:110px;"></textarea>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end;">
          <button class="btn" id="msg_clear">Clear</button>
          <button class="btn btn-orange" id="msg_send">Send Message</button>
        </div>
      </div>
    `;

    root.append(left, right);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);

    const threadsEl = left.querySelector("#msg_threads");
    const feedEl = right.querySelector("#msg_feed");
    const titleEl = right.querySelector("#msg_title");
    const subtitleEl = right.querySelector("#msg_subtitle");
    const toSel = right.querySelector("#msg_to");
    const bodyInput = right.querySelector("#msg_body");
    const searchInput = left.querySelector("#msg_search");
    const filterInbox = left.querySelector("#msg_filter_inbox");
    const filterDirect = left.querySelector("#msg_filter_direct");
    const filterAll = left.querySelector("#msg_filter_all");

    let filterMode = "inbox";
    let threadMode = "allhands";
    let threadPeer = "";
    let threadCache = [];

    function setFilterUi() {
      [filterInbox, filterDirect, filterAll].forEach(btn => {
        btn.classList.remove("btn-orange");
        btn.classList.add("btn");
      });
      const active = filterMode === "inbox" ? filterInbox : filterMode === "direct" ? filterDirect : filterAll;
      active.classList.add("btn-orange");
    }

    function initials(name) {
      const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
      return (parts.slice(0,2).map(p => p[0] || "").join("") || "?").toUpperCase();
    }

    async function refreshRecipients() {
      const prev = toSel.value;
      const items = await apiNotificationRecipients().catch(() => []);
      toSel.innerHTML = `<option value="__ALL__">All Hands</option>`;
      items.filter(u => String(u.username || "").toLowerCase() !== String((currentUser && currentUser.username) || "").toLowerCase()).forEach(u => {
        const opt = document.createElement("option");
        opt.value = u.username || u.id || "";
        opt.textContent = u.name || u.username || "User";
        toSel.appendChild(opt);
      });
      if ([...toSel.options].some(o => o.value === prev)) toSel.value = prev;
    }

    function buildThreads(items) {
      const me = String((currentUser && currentUser.username) || "").toLowerCase();
      const q = String(searchInput.value || "").trim().toLowerCase();
      const threads = [];
      const allhands = items.filter(item => item.kind !== "direct");
      const allhandsUnread = allhands.filter(item => !item.is_mine && !item.read).length;
      const allhandsLast = allhands[0];
      if (filterMode !== "direct") {
        threads.push({
          key: "allhands",
          mode: "allhands",
          title: "All Hands",
          subtitle: allhandsLast ? (allhandsLast.message || "") : "No team messages yet.",
          unread: allhandsUnread,
          stamp: allhandsLast ? String(allhandsLast.created_at || "").replace("T", " ").slice(0,16) : "",
          avatar: "AH"
        });
      }
      const peerMap = new Map();
      items.filter(item => item.kind === "direct").forEach(item => {
        const from = String(item.from || "");
        const to = String(item.to || "");
        const peer = String(from).toLowerCase() === me ? to : from;
        if (!peer) return;
        if (!peerMap.has(peer)) peerMap.set(peer, []);
        peerMap.get(peer).push(item);
      });
      [...peerMap.entries()].forEach(([peer, msgs]) => {
        const last = msgs[0];
        const unread = msgs.filter(item => !item.is_mine && !item.read).length;
        const peerName = last.is_mine ? (last.to_name || peer) : (last.from_name || peer);
        threads.push({
          key: `direct:${peer}`,
          mode: "direct",
          peer,
          title: peerName,
          subtitle: last.message || "",
          unread,
          stamp: String(last.created_at || "").replace("T", " ").slice(0,16),
          avatar: initials(peerName)
        });
      });
      let filtered = threads;
      if (q) {
        filtered = threads.filter(t => [t.title, t.subtitle, t.peer || ""].join(" ").toLowerCase().includes(q));
      }
      return filtered;
    }

    function renderThreads(items) {
      threadsEl.innerHTML = "";
      const threads = buildThreads(items);
      if (!threads.length) {
        threadsEl.innerHTML = `<div class="hint">No messages found.</div>`;
        return;
      }
      threads.forEach(thread => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        row.style.border = (thread.mode === threadMode && (thread.mode !== "direct" || thread.peer === threadPeer)) ? "1px solid #f97316" : "1px solid var(--line)";
        row.innerHTML = `
          <div style="display:flex; gap:10px; align-items:flex-start;">
            <div style="width:42px; height:42px; border-radius:999px; background:linear-gradient(135deg,#3b82f6,#60a5fa); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:900; flex:0 0 42px;">${escapeHtml(thread.avatar)}</div>
            <div style="min-width:0; flex:1;">
              <div class="jobrow-top">
                <div class="jobrow-name">${escapeHtml(thread.title)}</div>
                <div style="display:flex; gap:8px; align-items:center;">${thread.unread ? `<span class="badge" style="background:#f97316;color:#fff;">${thread.unread}</span>` : ""}</div>
              </div>
              <div class="hint" style="margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(thread.subtitle)}</div>
              <div class="hint" style="margin-top:4px;">${escapeHtml(thread.stamp)}</div>
            </div>
          </div>
        `;
        row.addEventListener("click", () => {
          threadMode = thread.mode;
          threadPeer = thread.peer || "";
          if (thread.mode === "direct" && thread.peer) toSel.value = thread.peer;
          if (thread.mode === "allhands") toSel.value = "__ALL__";
          renderThreads(threadCache);
          renderFeed(threadCache);
        });
        threadsEl.appendChild(row);
      });
    }

    function renderFeed(items) {
      const visible = items.filter(item => {
        if (threadMode === "allhands") return item.kind !== "direct";
        const me = String((currentUser && currentUser.username) || "").toLowerCase();
        const from = String(item.from || "").toLowerCase();
        const to = String(item.to || "").toLowerCase();
        return item.kind === "direct" && ((from === me && to === String(threadPeer || "").toLowerCase()) || (to === me && from === String(threadPeer || "").toLowerCase()));
      });
      titleEl.textContent = threadMode === "allhands" ? "All Hands" : (buildThreads(items).find(t => t.mode === "direct" && t.peer === threadPeer)?.title || "Direct Message");
      subtitleEl.textContent = threadMode === "allhands" ? "Team-wide messages" : "Private conversation";
      feedEl.innerHTML = "";
      if (!visible.length) {
        feedEl.innerHTML = `<div class="hint">No messages in this conversation yet.</div>`;
        return;
      }
      visible.slice().reverse().forEach(item => {
        const mine = !!item.is_mine;
        const wrap = document.createElement("div");
        wrap.style.display = "flex";
        wrap.style.justifyContent = mine ? "flex-end" : "flex-start";
        const bubble = document.createElement("div");
        bubble.style.maxWidth = "78%";
        bubble.style.border = "1px solid var(--line)";
        bubble.style.borderRadius = "14px";
        bubble.style.padding = "12px 14px";
        bubble.style.background = mine ? "#fff7ed" : "#fff";
        bubble.innerHTML = `
          <div class="label" style="margin-bottom:6px;">${escapeHtml(mine ? "You" : (item.from_name || item.from || "User"))}</div>
          <div style="white-space:pre-wrap; font-weight:800;">${escapeHtml(item.message || "")}</div>
          <div class="hint" style="margin-top:8px; display:flex; justify-content:space-between; gap:12px; align-items:center;">
            <span>${escapeHtml(String(item.created_at || "").replace("T"," ").slice(0,16))}</span>
            <span>${!mine && !item.read ? `<span class="badge" style="background:#f97316;color:#fff;">New</span>` : ""}</span>
          </div>
        `;
        if (!mine && !item.read) {
          bubble.addEventListener("click", async () => {
            try { await apiMarkNotificationRead(item.id, true); } catch {}
            await refreshAll();
          });
          bubble.style.cursor = "pointer";
        }
        if (mine) {
          const actions = document.createElement("div");
          actions.style.display = "flex";
          actions.style.justifyContent = "flex-end";
          actions.style.marginTop = "8px";
          const del = document.createElement("button");
          del.type = "button";
          del.textContent = "Delete";
          styleActionButton(del, "danger", true);
          del.addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!confirm("Delete this message?")) return;
            await apiDeleteNotification(item.id);
            await refreshAll();
          });
          actions.appendChild(del);
          bubble.appendChild(actions);
        }
        wrap.appendChild(bubble);
        feedEl.appendChild(wrap);
      });
    }

    async function refreshAll() {
      setFilterUi();
      const items = await apiListNotifications({ limit: 300 }).catch(() => []);
      threadCache = items.filter(item => {
        if (filterMode === "direct") return item.kind === "direct";
        if (filterMode === "inbox") return !item.is_mine;
        return true;
      });
      renderThreads(threadCache);
      renderFeed(threadCache);
      refreshBadges();
    }

    filterInbox.addEventListener("click", () => { filterMode = "inbox"; if (threadMode !== "allhands" && filterMode === "inbox") threadMode = "allhands"; refreshAll(); });
    filterDirect.addEventListener("click", () => { filterMode = "direct"; if (threadMode === "allhands") threadPeer = ""; refreshAll(); });
    filterAll.addEventListener("click", () => { filterMode = "all"; refreshAll(); });
    searchInput.addEventListener("input", () => renderThreads(threadCache));
    right.querySelector("#msg_refresh").addEventListener("click", refreshAll);
    right.querySelector("#msg_clear").addEventListener("click", () => { bodyInput.value = ""; });
    right.querySelector("#msg_mark_read").addEventListener("click", async () => {
      const target = threadCache.filter(item => {
        if (item.is_mine || item.read) return false;
        if (threadMode === "allhands") return item.kind !== "direct";
        const me = String((currentUser && currentUser.username) || "").toLowerCase();
        const from = String(item.from || "").toLowerCase();
        const to = String(item.to || "").toLowerCase();
        return item.kind === "direct" && to === me && from === String(threadPeer || "").toLowerCase();
      });
      for (const item of target) {
        try { await apiMarkNotificationRead(item.id, true); } catch {}
      }
      await refreshAll();
    });
    right.querySelector("#msg_send").addEventListener("click", async () => {
      const to = toSel.value;
      const message = bodyInput.value.trim();
      if (!message) return alert("Please enter a message.");
      await apiCreateNotification({ to, message });
      bodyInput.value = "";
      threadMode = to === "__ALL__" ? "allhands" : "direct";
      threadPeer = to === "__ALL__" ? "" : to;
      await refreshAll();
    });

    currentView = { refresh: async () => { await refreshRecipients(); await refreshAll(); } };
    refreshRecipients();
    refreshAll();
  }

  function renderChatView(mode) {
    setNavActive(mode === "tech" ? navAtlas : navMoses);
    setActiveChip(mode === "tech" ? "Atlas" : "Moses");
    setWorkspace(mode === "tech" ? "Atlas" : "Moses");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    root.className = "card";
 
    const title = document.createElement("h3");
    title.textContent = mode === "tech" ? "Atlas" : "Moses";
 
    const sub = document.createElement("div");
    sub.className = "hint";
    sub.textContent = mode === "tech" ? "Tech Support" : "Office Support";
 
    const msgs = document.createElement("div");
    msgs.style.marginTop = "10px";
    msgs.style.border = "1px solid var(--line)";
    msgs.style.borderRadius = "12px";
    msgs.style.padding = "10px";
    msgs.style.height = "360px";
    msgs.style.overflow = "auto";
    msgs.style.background = "#fff";
 
    const row = document.createElement("div");
    row.style.display = "flex";
    row.style.gap = "8px";
    row.style.marginTop = "10px";
 
    const input = document.createElement("input");
    input.className = "input";
    input.placeholder = mode === "tech" ? "Ask a tech question..." : "Ask an office question...";
 
    const btn = document.createElement("button");
    btn.className = "btn btn-orange";
    btn.textContent = "Send";
 
    row.appendChild(input);
    row.appendChild(btn);
 
    function addMsg(who, text) {
      const wrap = document.createElement("div");
      wrap.style.marginBottom = "10px";
 
      const meta = document.createElement("div");
      meta.className = "label";
      meta.style.marginBottom = "4px";
      meta.textContent = who;
 
      const body = document.createElement("div");
      body.style.whiteSpace = "pre-wrap";
      body.style.fontWeight = "900";
      body.textContent = text;
 
      wrap.appendChild(meta);
      wrap.appendChild(body);
      msgs.appendChild(wrap);
      msgs.scrollTop = msgs.scrollHeight;
    }
 
    let conversationId = "";
 
    function openAnyJobCard(job) {
      if (!job) return;
      const sourceLabel = String(job.source || "").toUpperCase();
      if (sourceLabel.startsWith("LEGACY") || !job.id) {
        openDrawer(`Legacy Job ${job.job_number || "Details"}`, async (drawerBody) => {
          const card = document.createElement("div");
          card.className = "card";
          card.innerHTML = `
            <h3 style="margin:0;">${escapeHtml(job.customer || job.customer_name || "Legacy Job")}</h3>
            <div class="hint" style="margin-top:6px;">${escapeHtml(job.job_number || "")}${job.date ? ` - ${escapeHtml(job.date)}` : ""}${job.source ? ` - ${escapeHtml(String(job.source).toUpperCase())}` : ""}</div>
            <div class="grid2" style="margin-top:12px;">
              <div><div class="label">Customer</div><div class="field">${escapeHtml(job.customer || job.customer_name || "")}</div></div>
              <div><div class="label">Job #</div><div class="field">${escapeHtml(job.job_number || "")}</div></div>
              <div><div class="label">Estimate #</div><div class="field">${formatDocRefDisplay(job.estimate_number || job.estimate_no || "")}</div></div>
              <div><div class="label">Invoice #</div><div class="field">${formatDocRefDisplay(job.invoice_number || job.invoice_no || "")}</div></div>
              <div><div class="label">PO #</div><div class="field">${formatDocRefDisplay(job.po_number || job.po_no || "")}</div></div>
              <div><div class="label">Address</div><div class="field">${escapeHtml(job.address || "")}</div></div>
              <div><div class="label">Date</div><div class="field">${escapeHtml(job.date || "")}</div></div>
              <div><div class="label">Status</div><div class="field">${escapeHtml(job.status || "")}</div></div>
              <div><div class="label">Contact</div><div class="field">${escapeHtml(job.contact || job.contact_name || "")}</div></div>
            </div>
            <div style="margin-top:10px;"><div class="label">Job Notes</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.job_notes || job.tech_notes || job.description || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Work Performed</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.work_performed || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Additional Recommendations</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.additional_recommendations || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Parts Used</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.parts_used || "")}</div></div>
          `;
          drawerBody.appendChild(card);
        });
        return;
      }
      apiGetJob(job.id).then(full => {
        openDrawer(`Job ${full.job_number || "Details"}`, async (bd) => renderJobDetails(bd, full, { afterSave: async () => {}, afterDelete: async () => {} }));
      }).catch(e => alert(e.message || String(e)));
    }
 
    function openJobResultsPanel(items) {
      const panel = document.createElement("div");
      panel.style.position = "fixed";
      panel.style.top = "0";
      panel.style.right = "0";
      panel.style.width = "420px";
      panel.style.maxWidth = "92vw";
      panel.style.height = "100vh";
      panel.style.background = "#0f172a";
      panel.style.borderLeft = "1px solid rgba(255,255,255,.15)";
      panel.style.zIndex = "9999";
      panel.style.overflowY = "auto";
      panel.style.padding = "16px";
      const inner = document.createElement("div");
      inner.style.display = "grid";
      inner.style.gap = "8px";
      const close = document.createElement("button");
      close.className = "btn";
      close.textContent = "Close";
      close.addEventListener("click", () => panel.remove());
      panel.appendChild(close);
      panel.appendChild(inner);
      const sorted = [...items].sort((a,b)=>String(b.date||"").localeCompare(String(a.date||"")));
      sorted.forEach(j => {
        const card = document.createElement("div");
        card.className = "jobrow";
        card.style.cursor = "pointer";
        const customer = j.customer || j.customer_name || "Job";
        const estimate = j.estimate_number || j.estimate_no || "";
        const invoice = j.invoice_number || j.invoice_no || "";
        const address = j.address || "";
        const date = j.date || j.date_display || "";
        const sourceLabel = j.source ? String(j.source).toUpperCase() : "CURRENT";
        card.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(customer)}</div>
            <div style="display:flex; gap:8px; align-items:center;">${statusPill(j.status || "Dispatch").outerHTML}<span class="badge">${escapeHtml(sourceLabel)}</span></div>
          </div>
          <div class="jobrow-addr">Job #: ${escapeHtml(j.job_number || "")}${date ? ` - ${escapeHtml(date)}` : ""}</div>
          <div class="hint" style="margin-top:6px; font-weight:900;">Estimate: ${formatDocRefDisplay(estimate)} | Invoice: ${formatDocRefDisplay(invoice)} | PO: ${formatDocRefDisplay(j.po_number || j.po_no || "")}</div>
          <div class="hint" style="margin-top:4px;">${escapeHtml(address || "")}</div>
        `;
        card.addEventListener("click", () => openAnyJobCard(j));
        inner.appendChild(card);
      });
      document.body.appendChild(panel);
    }

    function addJobCards(items) {
      if (!Array.isArray(items) || !items.length) return;
      const wrap = document.createElement("div");
      wrap.style.display = "grid";
      wrap.style.gap = "8px";
      wrap.style.marginBottom = "10px";
      if (items.length > 5) {
        const more = document.createElement("div");
        more.className = "jobrow";
        more.style.cursor = "pointer";
        more.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">View All Results</div></div><div class="jobrow-addr">${items.length} matching jobs</div><div class="hint" style="margin-top:4px;">Open full results newest to oldest</div>`;
        more.addEventListener("click", () => openJobResultsPanel(items));
        wrap.appendChild(more);
      }
      items.slice(0, 5).forEach(j => {
        const card = document.createElement("div");
        card.className = "jobrow";
        card.style.cursor = "pointer";
        const customer = j.customer || j.customer_name || "Job";
        const estimate = j.estimate_number || j.estimate_no || "";
        const invoice = j.invoice_number || j.invoice_no || "";
        const address = j.address || "";
        const date = j.date || j.date_display || "";
        const sourceLabel = j.source ? String(j.source).toUpperCase() : "CURRENT";
        card.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(customer)}</div>
            <div style="display:flex; gap:8px; align-items:center;">${statusPill(j.status || "Dispatch").outerHTML}<span class="badge">${escapeHtml(sourceLabel)}</span></div>
          </div>
          <div class="jobrow-addr">Job #: ${escapeHtml(j.job_number || "")}${date ? ` - ${escapeHtml(date)}` : ""}</div>
          <div class="hint" style="margin-top:6px; font-weight:900;">Estimate: ${formatDocRefDisplay(estimate || "")} | Invoice: ${formatDocRefDisplay(invoice || "")} | PO: ${formatDocRefDisplay(j.po_number || j.po_no || "")}</div>
          <div class="hint" style="margin-top:4px;">${escapeHtml(address || "")}</div>
        `;
        card.addEventListener("click", () => openAnyJobCard(j));
        wrap.appendChild(card);
      });
      msgs.appendChild(wrap);
      msgs.scrollTop = msgs.scrollHeight;
    }
 
    async function send() {
 
      const q = input.value.trim();
      if (!q) return;
      addMsg("You", q);
      input.value = "";
      try {
        const data = await fetchJSON("/atlas/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ q, mode: mode === "tech" ? "tech" : "office", conversation_id: conversationId || "" }),
        });
        conversationId = data.conversation_id || conversationId || "";
        addMsg(mode === "tech" ? "Atlas" : "Moses", data.answer_md || (data.moses && data.moses.jobs && data.moses.jobs.length ? "Found matching jobs." : "No matching jobs found."));
        if (mode === "office") {
          if (data.moses && data.moses.job) addJobCards([data.moses.job]);
          if (data.moses && Array.isArray(data.moses.jobs) && data.moses.jobs.length) addJobCards(data.moses.jobs);
        }
      } catch (e) {
        addMsg(mode === "tech" ? "Atlas" : "Moses", `Error: ${e.message || e}`);
      }
    }
 
    btn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") send();
    });
 
    root.appendChild(title);
    root.appendChild(sub);
    root.appendChild(msgs);
    root.appendChild(row);
 
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    currentView = { refresh: async () => {} };
  }
 
  if (loginBtn) loginBtn.addEventListener("click", handleLogin);
  if (pinBtn) pinBtn.addEventListener("click", handlePinLogin);
  if (logoutBtn) logoutBtn.addEventListener("click", handleLogout);
  if (passwordInput) passwordInput.addEventListener("keydown", (e) => { if (e.key === "Enter") handleLogin(); });
  if (usernameInput) usernameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") handleLogin(); });
  if (pinInput) pinInput.addEventListener("keydown", (e) => { if (e.key === "Enter") handlePinLogin(); });

  if (headerCalendarBtn) headerCalendarBtn.addEventListener("click", renderCalendarView);
 
  if (navFormsTimeCard) navFormsTimeCard.addEventListener("click", renderTimeCardView);
  if (navFormsTimeOff) navFormsTimeOff.addEventListener("click", renderTimeOffView);
  if (navTakeoffs) navTakeoffs.addEventListener("click", renderTakeoffsView);
  if (navFormsSignOff) navFormsSignOff.addEventListener("click", renderSignOffLibraryView);
 
  if (navDataCenter) {
    const small = navDataCenter.querySelector("small");
    if (small) small.textContent = "Monthly Dashboard";
  }
 
  if (navJobFlow) navJobFlow.addEventListener("click", () => renderJobFlowView("Dispatch"));
  if (navToDoList) navToDoList.addEventListener("click", renderToDoListView);
  if (navAllJobs) navAllJobs.addEventListener("click", renderAllJobsView);
  if (navEstimateInvoice) navEstimateInvoice.addEventListener("click", renderEstimatePage);
  if (navEstimatePage && !navEstimateInvoice) navEstimatePage.addEventListener("click", renderEstimatePage);
  if (navInvoicePage && !navEstimateInvoice) navInvoicePage.addEventListener("click", renderInvoicePage);
  if (navCustomers) navCustomers.addEventListener("click", renderCustomersView);
  if (navContacts) navContacts.addEventListener("click", renderContactsView);
  if (navPartsList) navPartsList.addEventListener("click", renderPartsListView);
  if (navDoorLogs) navDoorLogs.addEventListener("click", renderDoorLogsView);
  
 

function renderDataUploadView() {
    setNavActive(navDataUpload);
    setActiveChip("Office Flow");
    setWorkspace("Data Upload");
    clearWorkspaceActions();

    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3>Admin Data Upload</h3>
      <div class="hint">Upload only billable_time.csv or tech_notes.csv to the live Render disk.</div>
      <div class="grid2" style="margin-top:12px;">
        <div>
          <div class="label">billable_time.csv</div>
          <input class="input" id="upload_billable" type="file" accept=".csv" />
          <button class="btn btn-orange" id="upload_billable_btn" style="margin-top:10px;">Upload billable_time.csv</button>
          <div class="hint" id="upload_billable_status" style="margin-top:8px;"></div>
        </div>
        <div>
          <div class="label">tech_notes.csv</div>
          <input class="input" id="upload_notes" type="file" accept=".csv" />
          <button class="btn btn-orange" id="upload_notes_btn" style="margin-top:10px;">Upload tech_notes.csv</button>
          <div class="hint" id="upload_notes_status" style="margin-top:8px;"></div>
        </div>
        <div>
          <div class="label">customers.csv</div>
          <input class="input" id="upload_customers" type="file" accept=".csv" />
          <button class="btn btn-orange" id="upload_customers_btn" style="margin-top:10px;">Upload customers.csv</button>
          <div class="hint" id="upload_customers_status" style="margin-top:8px;"></div>
        </div>
        <div>
          <div class="label">contacts.csv</div>
          <input class="input" id="upload_contacts" type="file" accept=".csv" />
          <button class="btn btn-orange" id="upload_contacts_btn" style="margin-top:10px;">Upload contacts.csv</button>
          <div class="hint" id="upload_contacts_status" style="margin-top:8px;"></div>
        </div>
      </div>
      <div class="card" style="margin-top:14px; padding:14px;">
        <div style="font-weight:900; margin-bottom:6px;">How to use</div>
        <div class="hint">billable_time.csv and tech_notes.csv overwrite those live files directly. customers.csv and contacts.csv are converted into customers_db.json and contacts_db.json on the live Render disk. Restart the Render service once after upload to refresh references.</div>
      </div>
    `;

    const wireUploader = (inputId, buttonId, statusId, expectedName) => {
      const input = card.querySelector(inputId);
      const button = card.querySelector(buttonId);
      const status = card.querySelector(statusId);
      button.addEventListener("click", async () => {
        try {
          const file = input.files && input.files[0];
          if (!file) {
            status.textContent = "Choose a CSV first.";
            return;
          }
          if (file.name !== expectedName) {
            status.textContent = `Please choose ${expectedName}.`;
            return;
          }
          status.textContent = "Uploading...";
          const result = await uploadAdminDataFile(file);
          status.textContent = `Uploaded ${result.filename} successfully. Restart Render once to refresh references.`;
          input.value = "";
        } catch (e) {
          status.textContent = e.message || String(e);
        }
      });
    };

    wireUploader("#upload_billable", "#upload_billable_btn", "#upload_billable_status", "billable_time.csv");
    wireUploader("#upload_notes", "#upload_notes_btn", "#upload_notes_status", "tech_notes.csv");
    wireUploader("#upload_customers", "#upload_customers_btn", "#upload_customers_status", "customers.csv");
    wireUploader("#upload_contacts", "#upload_contacts_btn", "#upload_contacts_status", "contacts.csv");

    root.appendChild(card);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
  }


function renderSaddlebackView() {
    setNavActive(navSaddleback);
    setActiveChip("Office Flow");
    setWorkspace("Saddleback Design Co.");
    clearWorkspaceActions();

    let state = { orders: [], expenses: [], purchases: [] };
    let sdcLoaded = false;

    const normalizeSdcState = (data) => ({
      orders: Array.isArray(data && data.orders) ? data.orders : [],
      expenses: Array.isArray(data && data.expenses) ? data.expenses : [],
      purchases: Array.isArray(data && data.purchases) ? data.purchases : [],
    });

    const money = (n) => `$${(Number(n || 0)).toFixed(2)}`;
    const monthKey = (iso) => String(iso || "").slice(0, 7);
    const makeId = () => `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const sdcExpenseCategories = [
      "Advertising / Marketing",
      "Bank / Processing Fees",
      "Business / Licensing Fees",
      "Etsy / Marketplace Fees",
      "Fuel / Mileage",
      "Insurance",
      "Meals",
      "Office Supplies",
      "Postage / Shipping",
      "Rent / Workspace",
      "Repairs / Maintenance",
      "Software / Subscriptions",
      "Tools / Equipment",
      "Utilities",
      "Vehicle",
      "Other Expense"
    ];
    const sdcPurchaseCategories = [
      "Wood / Lumber",
      "Rattan / Cane Webbing",
      "Hardware",
      "Finish / Stain / Paint",
      "Glue / Adhesives",
      "Sanding / Abrasives",
      "Packaging Materials",
      "Shipping Materials",
      "Outsourced Labor",
      "Tools / Equipment",
      "Other Material"
    ];
    function sdcOptions(options, selected) {
      return options.map(opt => `<option value="${escapeHtml(opt)}" ${String(selected || "") === opt ? "selected" : ""}>${escapeHtml(opt)}</option>`).join("");
    }
    function addToBucketTotals(target, key, amount) {
      const label = String(key || "Uncategorized").trim() || "Uncategorized";
      target[label] = (target[label] || 0) + Number(amount || 0);
    }

    async function persist() {
      try {
        state = normalizeSdcState(await apiSaveSaddlebackData(state));
        sdcLoaded = true;
      } catch (e) {
        console.warn("Saddleback save failed", e);
        alert(e.message || "Unable to save Saddleback data.");
      }
    }

    function upsert(bucket, row) {
      const items = Array.isArray(state[bucket]) ? state[bucket].slice() : [];
      const idx = items.findIndex(x => String(x.id || "") === String(row.id || ""));
      if (idx >= 0) items[idx] = row;
      else items.unshift(row);
      state[bucket] = items;
      persist().then(renderCurrent);
    }

    function removeItem(bucket, id) {
      state[bucket] = (state[bucket] || []).filter(x => String(x.id || "") !== String(id || ""));
      persist().then(renderCurrent);
    }

    function summaryCard(title, value, hint = "") {
      const card = document.createElement("div");
      card.className = "metric";
      card.innerHTML = `<div class="metric-label">${title}</div><div class="metric-value">${value}</div><div class="metric-sub">${hint}</div>`;
      return card;
    }

    function exportSdcRows(filename, headers, rows) {
      const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
      const csv = [headers, ...(Array.isArray(rows) ? rows : [])].map(row => row.map(esc).join(",")).join("\r\n");
      const safeName = filename || "saddleback_export.csv";
      try {
        const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = safeName;
        a.style.display = "none";
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
          try { document.body.removeChild(a); } catch (e) {}
          try { URL.revokeObjectURL(url); } catch (e) {}
        }, 1000);
      } catch (err) {
        console.warn("Saddleback CSV export fallback", err);
        const encoded = encodeURIComponent("\ufeff" + csv);
        const a = document.createElement("a");
        a.href = "data:text/csv;charset=utf-8," + encoded;
        a.download = safeName;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    }

    function recordCard(title, subtitle, meta = "", onOpen = null, onDelete = null, badgeText = "") {
      const row = document.createElement("div");
      row.className = "jobrow";
      row.style.cursor = onOpen ? "pointer" : "default";
      row.innerHTML = `
        <div class="jobrow-top">
          <div class="jobrow-name">${escapeHtml(title || "Record")}</div>
          <div style="display:flex; gap:8px; align-items:center;">${badgeText ? statusPill(badgeText).outerHTML : ""}</div>
        </div>
        <div class="jobrow-addr">${escapeHtml(subtitle || "")}</div>
        ${meta ? `<div class="hint" style="margin-top:6px; font-weight:900;">${escapeHtml(meta)}</div>` : ""}
      `;
      if (onOpen) row.addEventListener("click", onOpen);
      if (onDelete) {
        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "8px";
        const del = document.createElement("button");
        del.className = "btn";
        del.textContent = "Delete";
        del.addEventListener("click", (e) => {
          e.stopPropagation();
          onDelete();
        });
        actions.appendChild(del);
        row.appendChild(actions);
      }
      return row;
    }

    function openOrderEditor(item = null) {
      const row = item ? { ...item } : {
        id: makeId(),
        bucket: "orders",
        date: "",
        channel: "",
        customer: "",
        address: "",
        item: "",
        ref: "",
        total: 0,
        shipping: 0,
        tax: 0,
        channel_fee: 0,
        profit: 0,
        status: "Open",
        notes: "",
      };

      openDrawer(item ? "Edit Order" : "Add Order", (drawerBody, overlay) => {
        const wrap = document.createElement("div");
        wrap.className = "card";
        wrap.innerHTML = `
          <div class="grid2">
            <div><div class="label">Date</div><input class="input" id="sdc_order_date" type="date" value="${escapeHtml(row.date || "")}" /></div>
            <div><div class="label">Channel</div><input class="input" id="sdc_order_channel" value="${escapeHtml(row.channel || "")}" placeholder="Etsy / In Person" /></div>
            <div><div class="label">Customer</div><input class="input" id="sdc_order_customer" value="${escapeHtml(row.customer || "")}" placeholder="Customer name" /></div>
            <div><div class="label">Address</div><input class="input" id="sdc_order_address" value="${escapeHtml(row.address || "")}" placeholder="Customer address" /></div>
            <div><div class="label">Item</div><input class="input" id="sdc_order_item" value="${escapeHtml(row.item || "")}" placeholder="Door / style / finish" /></div>
            <div><div class="label">Order ID</div><input class="input" id="sdc_order_ref" value="${escapeHtml(row.ref || "")}" placeholder="Etsy order / invoice #" /></div>
            <div><div class="label">Total Amount</div><input class="input" id="sdc_order_total" type="number" step="0.01" value="${escapeHtml(String(row.total || 0))}" /></div>
            <div><div class="label">Shipping Cost</div><input class="input" id="sdc_order_shipping" type="number" step="0.01" value="${escapeHtml(String(row.shipping || 0))}" /></div>
            <div><div class="label">Sales Tax</div><input class="input" id="sdc_order_tax" type="number" step="0.01" value="${escapeHtml(String(row.tax || 0))}" /></div>
            <div><div class="label">Channel Fee</div><input class="input" id="sdc_order_channel_fee" type="number" step="0.01" value="${escapeHtml(String(row.channel_fee || 0))}" /></div>
            <div><div class="label">Status</div>
              <select class="input" id="sdc_order_status">
                <option value="Open">Open</option>
                <option value="In Production">In Production</option>
                <option value="Shipped">Shipped</option>
                <option value="Delivered">Delivered</option>
              </select>
            </div>
            <div style="grid-column:1 / -1;"><div class="label">Notes</div><textarea id="sdc_order_notes">${escapeHtml(row.notes || "")}</textarea></div>
          </div>
        `;
        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "12px";
        const saveBtn = document.createElement("button");
        saveBtn.className = "btn btn-orange";
        saveBtn.textContent = "Save";
        const cancelBtn = document.createElement("button");
        cancelBtn.className = "btn";
        cancelBtn.textContent = "Cancel";
        actions.append(saveBtn, cancelBtn);
        if (item) {
          const delBtn = document.createElement("button");
          delBtn.className = "btn";
          delBtn.textContent = "Delete";
          delBtn.addEventListener("click", () => {
            removeItem("orders", row.id);
            overlay.remove();
          });
          actions.appendChild(delBtn);
        }
        wrap.appendChild(actions);
        drawerBody.appendChild(wrap);
        wrap.querySelector("#sdc_order_status").value = row.status || "Open";
        cancelBtn.addEventListener("click", () => overlay.remove());
        saveBtn.addEventListener("click", () => {
          const next = {
            ...row,
            bucket: "orders",
            date: wrap.querySelector("#sdc_order_date").value,
            channel: wrap.querySelector("#sdc_order_channel").value.trim(),
            customer: wrap.querySelector("#sdc_order_customer").value.trim(),
            address: wrap.querySelector("#sdc_order_address").value.trim(),
            item: wrap.querySelector("#sdc_order_item").value.trim(),
            ref: wrap.querySelector("#sdc_order_ref").value.trim(),
            total: Number(wrap.querySelector("#sdc_order_total").value || 0),
            shipping: Number(wrap.querySelector("#sdc_order_shipping").value || 0),
            tax: Number(wrap.querySelector("#sdc_order_tax").value || 0),
            channel_fee: Number(wrap.querySelector("#sdc_order_channel_fee").value || 0),
            status: wrap.querySelector("#sdc_order_status").value,
            notes: wrap.querySelector("#sdc_order_notes").value.trim(),
          };
          if (!next.date || !next.customer || !next.item) return alert("Date, customer, and item are required.");
          next.profit = Number(next.total || 0) - Number(next.shipping || 0) - Number(next.tax || 0) - Number(next.channel_fee || 0);
          upsert("orders", next);
          overlay.remove();
        });
      });
    }

    function openExpenseEditor(item = null) {
      const row = item ? { ...item } : {
        id: makeId(),
        bucket: "expenses",
        date: "",
        category: "",
        vendor: "",
        amount: 0,
        payment_method: "",
        reference: "",
        notes: "",
      };
      openDrawer(item ? "Edit Expense" : "Add Expense", (drawerBody, overlay) => {
        const wrap = document.createElement("div");
        wrap.className = "card";
        wrap.innerHTML = `
          <div class="grid2">
            <div><div class="label">Date</div><input class="input" id="sdc_exp_date" type="date" value="${escapeHtml(row.date || "")}" /></div>
            <div><div class="label">Category</div><select class="input" id="sdc_exp_cat">${sdcOptions(sdcExpenseCategories, row.category)}</select></div>
            <div><div class="label">Vendor</div><input class="input" id="sdc_exp_vendor" value="${escapeHtml(row.vendor || "")}" placeholder="Vendor" /></div>
            <div><div class="label">Amount</div><input class="input" id="sdc_exp_amt" type="number" step="0.01" value="${escapeHtml(String(row.amount || 0))}" /></div>
            <div><div class="label">Payment Method</div><input class="input" id="sdc_exp_method" value="${escapeHtml(row.payment_method || "")}" placeholder="Business card / cash / bank" /></div>
            <div><div class="label">Receipt / Reference #</div><input class="input" id="sdc_exp_ref" value="${escapeHtml(row.reference || "")}" placeholder="Receipt, order, or transaction #" /></div>
            <div style="grid-column:1 / -1;"><div class="label">Notes</div><textarea id="sdc_exp_notes">${escapeHtml(row.notes || "")}</textarea></div>
          </div>
        `;
        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "12px";
        const saveBtn = document.createElement("button");
        saveBtn.className = "btn btn-orange";
        saveBtn.textContent = "Save";
        const cancelBtn = document.createElement("button");
        cancelBtn.className = "btn";
        cancelBtn.textContent = "Cancel";
        actions.append(saveBtn, cancelBtn);
        if (item) {
          const delBtn = document.createElement("button");
          delBtn.className = "btn";
          delBtn.textContent = "Delete";
          delBtn.addEventListener("click", () => {
            removeItem("expenses", row.id);
            overlay.remove();
          });
          actions.appendChild(delBtn);
        }
        wrap.appendChild(actions);
        drawerBody.appendChild(wrap);
        cancelBtn.addEventListener("click", () => overlay.remove());
        saveBtn.addEventListener("click", () => {
          const next = {
            ...row,
            bucket: "expenses",
            date: wrap.querySelector("#sdc_exp_date").value,
            category: wrap.querySelector("#sdc_exp_cat").value.trim(),
            vendor: wrap.querySelector("#sdc_exp_vendor").value.trim(),
            amount: Number(wrap.querySelector("#sdc_exp_amt").value || 0),
            payment_method: wrap.querySelector("#sdc_exp_method").value.trim(),
            reference: wrap.querySelector("#sdc_exp_ref").value.trim(),
            notes: wrap.querySelector("#sdc_exp_notes").value.trim(),
          };
          if (!next.date || !next.category) return alert("Date and category are required.");
          upsert("expenses", next);
          overlay.remove();
        });
      });
    }

    function openPurchaseEditor(item = null) {
      const row = item ? { ...item } : {
        id: makeId(),
        bucket: "purchases",
        date: "",
        vendor: "",
        category: "",
        item: "",
        order_ref: "",
        amount: 0,
        tax_paid: 0,
        payment_method: "",
        reference: "",
        notes: "",
      };
      openDrawer(item ? "Edit Purchase" : "Add Purchase", (drawerBody, overlay) => {
        const wrap = document.createElement("div");
        wrap.className = "card";
        wrap.innerHTML = `
          <div class="grid2">
            <div><div class="label">Date</div><input class="input" id="sdc_pur_date" type="date" value="${escapeHtml(row.date || "")}" /></div>
            <div><div class="label">Vendor</div><input class="input" id="sdc_pur_vendor" value="${escapeHtml(row.vendor || "")}" placeholder="Vendor" /></div>
            <div><div class="label">Category</div><select class="input" id="sdc_pur_cat">${sdcOptions(sdcPurchaseCategories, row.category)}</select></div>
            <div><div class="label">Material / Item</div><input class="input" id="sdc_pur_item" value="${escapeHtml(row.item || "")}" placeholder="Oak slab / rails / hinges / stain" /></div>
            <div><div class="label">Linked Order</div><input class="input" id="sdc_pur_order" value="${escapeHtml(row.order_ref || "")}" placeholder="Customer / order #" /></div>
            <div><div class="label">Amount</div><input class="input" id="sdc_pur_amt" type="number" step="0.01" value="${escapeHtml(String(row.amount || 0))}" /></div>
            <div><div class="label">Tax Paid</div><input class="input" id="sdc_pur_tax" type="number" step="0.01" value="${escapeHtml(String(row.tax_paid || 0))}" /></div>
            <div><div class="label">Payment Method</div><input class="input" id="sdc_pur_method" value="${escapeHtml(row.payment_method || "")}" placeholder="Business card / cash / bank" /></div>
            <div><div class="label">Receipt / Reference #</div><input class="input" id="sdc_pur_ref" value="${escapeHtml(row.reference || "")}" placeholder="Receipt, order, or transaction #" /></div>
            <div style="grid-column:1 / -1;"><div class="label">Notes</div><textarea id="sdc_pur_notes">${escapeHtml(row.notes || "")}</textarea></div>
          </div>
        `;
        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "12px";
        const saveBtn = document.createElement("button");
        saveBtn.className = "btn btn-orange";
        saveBtn.textContent = "Save";
        const cancelBtn = document.createElement("button");
        cancelBtn.className = "btn";
        cancelBtn.textContent = "Cancel";
        actions.append(saveBtn, cancelBtn);
        if (item) {
          const delBtn = document.createElement("button");
          delBtn.className = "btn";
          delBtn.textContent = "Delete";
          delBtn.addEventListener("click", () => {
            removeItem("purchases", row.id);
            overlay.remove();
          });
          actions.appendChild(delBtn);
        }
        wrap.appendChild(actions);
        drawerBody.appendChild(wrap);
        cancelBtn.addEventListener("click", () => overlay.remove());
        saveBtn.addEventListener("click", () => {
          const next = {
            ...row,
            bucket: "purchases",
            date: wrap.querySelector("#sdc_pur_date").value,
            vendor: wrap.querySelector("#sdc_pur_vendor").value.trim(),
            category: wrap.querySelector("#sdc_pur_cat").value.trim(),
            item: wrap.querySelector("#sdc_pur_item").value.trim(),
            order_ref: wrap.querySelector("#sdc_pur_order").value.trim(),
            amount: Number(wrap.querySelector("#sdc_pur_amt").value || 0),
            tax_paid: Number(wrap.querySelector("#sdc_pur_tax").value || 0),
            payment_method: wrap.querySelector("#sdc_pur_method").value.trim(),
            reference: wrap.querySelector("#sdc_pur_ref").value.trim(),
            notes: wrap.querySelector("#sdc_pur_notes").value.trim(),
          };
          if (!next.date || !next.item) return alert("Date and item are required.");
          upsert("purchases", next);
          overlay.remove();
        });
      });
    }

    const root = document.createElement("div");
    const tabs = document.createElement("div");
    tabs.style.display = "flex";
    tabs.style.gap = "8px";
    tabs.style.flexWrap = "wrap";
    tabs.style.marginBottom = "12px";

    const btnOrders = document.createElement("button");
    btnOrders.className = "btn btn-orange";
    btnOrders.textContent = "Orders";
    const btnExpenses = document.createElement("button");
    btnExpenses.className = "btn";
    btnExpenses.textContent = "Expenses";
    const btnPurchases = document.createElement("button");
    btnPurchases.className = "btn";
    btnPurchases.textContent = "Purchases";
    const btnTaxes = document.createElement("button");
    btnTaxes.className = "btn";
    btnTaxes.textContent = "Tax Snapshot";
    [btnOrders, btnExpenses, btnPurchases, btnTaxes].forEach(b => tabs.appendChild(b));
    root.appendChild(tabs);

    const host = document.createElement("div");
    root.appendChild(host);

    function renderOrders() {
      host.innerHTML = "";
      btnOrders.className = "btn btn-orange";
      btnExpenses.className = btnPurchases.className = btnTaxes.className = "btn";

      const toolbar = document.createElement("div");
      toolbar.className = "card";
      toolbar.innerHTML = `<h3>Orders</h3><div class="hint">Track Etsy or in-person orders, shipping, production status, delivery, and fees.</div>`;
      const toolbarActions = document.createElement("div");
      toolbarActions.style.display = "flex";
      toolbarActions.style.gap = "8px";
      toolbarActions.style.flexWrap = "wrap";
      toolbarActions.style.marginTop = "12px";
      const addBtn = document.createElement("button");
      addBtn.className = "btn btn-orange";
      addBtn.textContent = "Add Order";
      addBtn.addEventListener("click", () => openOrderEditor());
      const exportBtn = document.createElement("button");
      exportBtn.type = "button";
      exportBtn.className = "btn";
      exportBtn.textContent = "Export Orders CSV";
      exportBtn.addEventListener("click", () => {
        const rows = state.orders.slice().sort((a,b) => String(b.date||"").localeCompare(String(a.date||""))).map(x => [x.date, x.channel, x.customer, x.address, x.ref, x.item, x.status, x.notes, x.total, x.shipping, x.tax, x.channel_fee, x.profit]);
        exportSdcRows("saddleback_orders.csv", ["Date","Channel","Customer","Address","Order ID","Item","Status","Notes","Total Amount","Shipping Cost","Sales Tax","Channel Fee","Profit"], rows);
      });
      toolbarActions.append(addBtn, exportBtn);
      toolbar.appendChild(toolbarActions);
      host.appendChild(toolbar);

      const filters = document.createElement("div");
      filters.className = "card";
      filters.style.marginTop = "12px";
      filters.innerHTML = `
        <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
          <button class="btn btn-orange" data-status="All">All</button>
          <button class="btn" data-status="Open">Open</button>
          <button class="btn" data-status="In Production">In Production</button>
          <button class="btn" data-status="Shipped">Shipped</button>
          <button class="btn" data-status="Delivered">Delivered</button>
          <input class="input" id="sdc_order_search" placeholder="Search customer, address, order id, item, notes" style="max-width:360px; margin-left:auto;" />
        </div>
      `;
      host.appendChild(filters);

      let activeStatus = "All";
      const searchInput = filters.querySelector("#sdc_order_search");

      const renderOrderList = () => {
        let rows = state.orders.slice();
        if (activeStatus !== "All") rows = rows.filter(x => String(x.status || "") === activeStatus);
        const q = String(searchInput.value || "").trim().toLowerCase();
        if (q) rows = rows.filter(x => [x.customer, x.address, x.ref, x.item, x.notes].some(v => String(v || "").toLowerCase().includes(q)));
        rows.sort((a,b) => String(b.date || "").localeCompare(String(a.date || "")));

        const existing = host.querySelector(".sdc-order-list-wrap");
        if (existing) existing.remove();

        const wrap = document.createElement("div");
        wrap.className = "sdc-order-list-wrap";
        wrap.style.marginTop = "12px";
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `<h3>Order Records</h3><div class="hint">${rows.length} saved order${rows.length === 1 ? "" : "s"}</div>`;
        const list = document.createElement("div");
        list.style.display = "grid";
        list.style.gap = "8px";
        if (!rows.length) {
          const empty = document.createElement("div");
          empty.className = "hint";
          empty.textContent = "No orders found.";
          list.appendChild(empty);
        } else {
          rows.forEach(item => {
            const subtitle = [item.date || "", item.channel || "", item.address || ""].filter(Boolean).join(" - ");
            const meta = `Order ID: ${item.ref || ""} | ${item.item || ""} | Total: ${money(item.total)} | Shipping: ${money(item.shipping)} | Tax: ${money(item.tax)} | Fee: ${money(item.channel_fee)}`;
            list.appendChild(recordCard(item.customer || item.ref || "Order", subtitle, meta, () => openOrderEditor(item), () => removeItem("orders", item.id), item.status || "Open"));
          });
        }
        card.appendChild(list);
        wrap.appendChild(card);
        host.appendChild(wrap);
      };

      filters.querySelectorAll("button[data-status]").forEach(btn => {
        btn.addEventListener("click", () => {
          activeStatus = btn.getAttribute("data-status");
          filters.querySelectorAll("button[data-status]").forEach(b => b.className = b === btn ? "btn btn-orange" : "btn");
          renderOrderList();
        });
      });
      searchInput.addEventListener("input", renderOrderList);
      renderOrderList();
    }

    function renderExpenses() {
      host.innerHTML = "";
      btnExpenses.className = "btn btn-orange";
      btnOrders.className = btnPurchases.className = btnTaxes.className = "btn";

      const toolbar = document.createElement("div");
      toolbar.className = "card";
      toolbar.innerHTML = `<h3>Expenses</h3><div class="hint">Track recurring business costs like Etsy fees, mileage, tools, software, fuel, marketing, and home office items.</div>`;
      const toolbarActions = document.createElement("div");
      toolbarActions.style.display = "flex";
      toolbarActions.style.gap = "8px";
      toolbarActions.style.flexWrap = "wrap";
      toolbarActions.style.marginTop = "12px";
      const addBtn = document.createElement("button");
      addBtn.className = "btn btn-orange";
      addBtn.textContent = "Add Expense";
      addBtn.addEventListener("click", () => openExpenseEditor());
      const exportBtn = document.createElement("button");
      exportBtn.type = "button";
      exportBtn.className = "btn";
      exportBtn.textContent = "Export Expenses CSV";
      exportBtn.addEventListener("click", () => {
        const rows = state.expenses.slice().sort((a,b) => String(b.date||"").localeCompare(String(a.date||""))).map(x => [x.date, x.category, x.vendor, x.amount, x.payment_method, x.reference, x.notes]);
        exportSdcRows("saddleback_expenses.csv", ["Date","Category","Vendor","Amount","Payment Method","Receipt / Reference #","Notes"], rows);
      });
      toolbarActions.append(addBtn, exportBtn);
      toolbar.appendChild(toolbarActions);
      host.appendChild(toolbar);

      const rows = state.expenses.slice().sort((a,b) => String(b.date || "").localeCompare(String(a.date || "")));
      const card = document.createElement("div");
      card.className = "card";
      card.style.marginTop = "12px";
      card.innerHTML = `<h3>Expense Records</h3><div class="hint">${rows.length} saved expense${rows.length === 1 ? "" : "s"}</div>`;
      const list = document.createElement("div");
      list.style.display = "grid";
      list.style.gap = "8px";
      if (!rows.length) {
        const empty = document.createElement("div");
        empty.className = "hint";
        empty.textContent = "No expenses yet.";
        list.appendChild(empty);
      } else {
        rows.forEach(item => {
          const subtitle = [item.date || "", item.category || "", item.vendor || ""].filter(Boolean).join(" - ");
          const meta = `${item.notes || ""}${item.notes ? " | " : ""}Amount: ${money(item.amount)}${item.reference ? " | Ref: " + item.reference : ""}`;
          list.appendChild(recordCard(item.category || "Expense", subtitle, meta, () => openExpenseEditor(item), () => removeItem("expenses", item.id)));
        });
      }
      card.appendChild(list);
      host.appendChild(card);
    }

    function renderPurchases() {
      host.innerHTML = "";
      btnPurchases.className = "btn btn-orange";
      btnOrders.className = btnExpenses.className = btnTaxes.className = "btn";

      const toolbar = document.createElement("div");
      toolbar.className = "card";
      toolbar.innerHTML = `<h3>Material Purchases</h3><div class="hint">Track wood, hardware, finish, shipping materials, and outsourced labor tied to orders.</div>`;
      const toolbarActions = document.createElement("div");
      toolbarActions.style.display = "flex";
      toolbarActions.style.gap = "8px";
      toolbarActions.style.flexWrap = "wrap";
      toolbarActions.style.marginTop = "12px";
      const addBtn = document.createElement("button");
      addBtn.className = "btn btn-orange";
      addBtn.textContent = "Add Purchase";
      addBtn.addEventListener("click", () => openPurchaseEditor());
      const exportBtn = document.createElement("button");
      exportBtn.type = "button";
      exportBtn.className = "btn";
      exportBtn.textContent = "Export Purchases CSV";
      exportBtn.addEventListener("click", () => {
        const rows = state.purchases.slice().sort((a,b) => String(b.date||"").localeCompare(String(a.date||""))).map(x => [x.date, x.vendor, x.category, x.item, x.order_ref, x.amount, x.tax_paid, x.payment_method, x.reference, x.notes]);
        exportSdcRows("saddleback_purchases.csv", ["Date","Vendor","Category","Material / Item","Linked Order","Amount","Tax Paid","Payment Method","Receipt / Reference #","Notes"], rows);
      });
      toolbarActions.append(addBtn, exportBtn);
      toolbar.appendChild(toolbarActions);
      host.appendChild(toolbar);

      const rows = state.purchases.slice().sort((a,b) => String(b.date || "").localeCompare(String(a.date || "")));
      const card = document.createElement("div");
      card.className = "card";
      card.style.marginTop = "12px";
      card.innerHTML = `<h3>Purchase Records</h3><div class="hint">${rows.length} saved purchase${rows.length === 1 ? "" : "s"}</div>`;
      const list = document.createElement("div");
      list.style.display = "grid";
      list.style.gap = "8px";
      if (!rows.length) {
        const empty = document.createElement("div");
        empty.className = "hint";
        empty.textContent = "No purchases yet.";
        list.appendChild(empty);
      } else {
        rows.forEach(item => {
          const subtitle = [item.date || "", item.vendor || "", item.category || "", item.order_ref || ""].filter(Boolean).join(" - ");
          const meta = `${item.item || ""} | Amount: ${money(item.amount)} | Tax Paid: ${money(item.tax_paid)}${item.reference ? " | Ref: " + item.reference : ""}`;
          list.appendChild(recordCard(item.item || "Purchase", subtitle, meta, () => openPurchaseEditor(item), () => removeItem("purchases", item.id)));
        });
      }
      card.appendChild(list);
      host.appendChild(card);
    }

    function renderTaxes() {
      host.innerHTML = "";
      btnTaxes.className = "btn btn-orange";
      btnOrders.className = btnExpenses.className = btnPurchases.className = "btn";

      const exportRow = document.createElement("div");
      exportRow.style.display = "flex";
      exportRow.style.gap = "8px";
      exportRow.style.marginBottom = "12px";
      const exportBtn = document.createElement("button");
      exportBtn.type = "button";
      exportBtn.className = "btn";
      exportBtn.textContent = "Export Tax Snapshot CSV";
      exportRow.appendChild(exportBtn);
      host.appendChild(exportRow);

      const wrap = document.createElement("div");
      wrap.style.display = "grid";
      wrap.style.gridTemplateColumns = "repeat(auto-fit, minmax(220px, 1fr))";
      wrap.style.gap = "12px";

      const grossRevenue = state.orders.reduce((sum, x) => sum + Number(x.total || 0), 0);
      const shipping = state.orders.reduce((sum, x) => sum + Number(x.shipping || 0), 0);
      const salesTax = state.orders.reduce((sum, x) => sum + Number(x.tax || 0), 0);
      const netRevenue = grossRevenue - salesTax;
      const expenses = state.expenses.reduce((sum, x) => sum + Number(x.amount || 0), 0);
      const purchases = state.purchases.reduce((sum, x) => sum + Number(x.amount || 0), 0);
      const purchaseTax = state.purchases.reduce((sum, x) => sum + Number(x.tax_paid || 0), 0);
      const estProfit = netRevenue - expenses - purchases;

      [
        summaryCard("Gross Revenue", money(grossRevenue), "All saved orders"),
        summaryCard("Sales Tax Collected", money(salesTax), "Collected and remitted"),
        summaryCard("Net Revenue", money(netRevenue), "Gross revenue less sales tax"),
        summaryCard("Shipping", money(shipping), "Shipping charged on saved orders"),
        summaryCard("Expenses", money(expenses), "Recurring business costs"),
        summaryCard("Material Purchases", money(purchases), "Order-related material spend"),
        summaryCard("Tax Paid on Purchases", money(purchaseTax), "Helpful for bookkeeping"),
        summaryCard("Est. Profit", money(estProfit), "Net revenue - expenses - purchases"),
      ].forEach(card => wrap.appendChild(card));
      host.appendChild(wrap);

      const expenseCategoryTotals = {};
      const purchaseCategoryTotals = {};
      state.expenses.forEach(x => addToBucketTotals(expenseCategoryTotals, x.category, x.amount));
      state.purchases.forEach(x => addToBucketTotals(purchaseCategoryTotals, x.category, x.amount));
      const catCard = document.createElement("div");
      catCard.className = "card";
      catCard.style.marginTop = "12px";
      const renderCatLines = (obj) => Object.keys(obj).sort().map(k => `<div class="hint"><strong>${escapeHtml(k)}:</strong> ${money(obj[k])}</div>`).join("") || `<div class="hint">No category totals yet.</div>`;
      catCard.innerHTML = `<h3>Itemized Tax Categories</h3><div class="grid2"><div><h4>Expenses</h4>${renderCatLines(expenseCategoryTotals)}</div><div><h4>Purchases</h4>${renderCatLines(purchaseCategoryTotals)}</div></div>`;
      host.appendChild(catCard);

      const months = {};
      [...state.orders, ...state.expenses, ...state.purchases].forEach(item => {
        const key = monthKey(item.date) || "No Date";
        months[key] = months[key] || { gross_revenue: 0, sales_tax: 0, net_revenue: 0, expenses: 0, purchases: 0, expense_categories: {}, purchase_categories: {} };
        if (item.bucket === "orders") {
          months[key].gross_revenue += Number(item.total || 0);
          months[key].sales_tax += Number(item.tax || 0);
          months[key].net_revenue += (Number(item.total || 0) - Number(item.tax || 0));
        }
        if (item.bucket === "expenses") {
          months[key].expenses += Number(item.amount || 0);
          addToBucketTotals(months[key].expense_categories, item.category, item.amount);
        }
        if (item.bucket === "purchases") {
          months[key].purchases += Number(item.amount || 0);
          addToBucketTotals(months[key].purchase_categories, item.category, item.amount);
        }
      });

      const monthly = Object.keys(months).sort().reverse().map(key => ({
        month: key,
        gross_revenue: months[key].gross_revenue,
        sales_tax: months[key].sales_tax,
        net_revenue: months[key].net_revenue,
        expenses: months[key].expenses,
        purchases: months[key].purchases,
        net: months[key].net_revenue - months[key].expenses - months[key].purchases,
        expense_categories: months[key].expense_categories,
        purchase_categories: months[key].purchase_categories,
      }));

      exportBtn.addEventListener("click", () => {
        const rows = monthly.map(x => [
          x.month,
          x.gross_revenue,
          x.sales_tax,
          x.net_revenue,
          x.expenses,
          Object.entries(x.expense_categories || {}).map(([k,v]) => `${k}: ${money(v)}`).join("; "),
          x.purchases,
          Object.entries(x.purchase_categories || {}).map(([k,v]) => `${k}: ${money(v)}`).join("; "),
          x.net
        ]);
        exportSdcRows("saddleback_tax_snapshot.csv", ["Month","Gross Revenue","Sales Tax Collected","Net Revenue","Expenses","Expense Category Breakdown","Purchases","Purchase Category Breakdown","Net"], rows);
      });

      const card = document.createElement("div");
      card.className = "card";
      card.style.marginTop = "12px";
      card.innerHTML = `<h3>Monthly Snapshot</h3><div class="hint">Month-by-month tax and profitability view.</div>`;
      const list = document.createElement("div");
      list.style.display = "grid";
      list.style.gap = "8px";
      if (!monthly.length) {
        const empty = document.createElement("div");
        empty.className = "hint";
        empty.textContent = "No tax snapshot data yet.";
        list.appendChild(empty);
      } else {
        monthly.forEach(item => {
          const subtitle = `${item.month} - Gross: ${money(item.gross_revenue)} - Tax: ${money(item.sales_tax)} - Net Revenue: ${money(item.net_revenue)}`;
          const expenseBreakdown = Object.entries(item.expense_categories || {}).map(([k,v]) => `${k}: ${money(v)}`).join("; ");
          const purchaseBreakdown = Object.entries(item.purchase_categories || {}).map(([k,v]) => `${k}: ${money(v)}`).join("; ");
          const meta = `Expenses: ${money(item.expenses)}${expenseBreakdown ? " (" + expenseBreakdown + ")" : ""} | Purchases: ${money(item.purchases)}${purchaseBreakdown ? " (" + purchaseBreakdown + ")" : ""} | Net: ${money(item.net)}`;
          list.appendChild(recordCard(item.month, subtitle, meta));
        });
      }
      card.appendChild(list);
      host.appendChild(card);
    }

    function renderCurrent() {
      if (btnOrders.className.includes("btn-orange")) return renderOrders();
      if (btnExpenses.className.includes("btn-orange")) return renderExpenses();
      if (btnPurchases.className.includes("btn-orange")) return renderPurchases();
      return renderTaxes();
    }

    btnOrders.addEventListener("click", renderOrders);
    btnExpenses.addEventListener("click", renderExpenses);
    btnPurchases.addEventListener("click", renderPurchases);
    btnTaxes.addEventListener("click", renderTaxes);

    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    host.innerHTML = `<div class="card"><div class="hint">Loading Saddleback data...</div></div>`;
    apiGetSaddlebackData()
      .then(data => {
        state = normalizeSdcState(data);
        sdcLoaded = true;
        renderOrders();
      })
      .catch(e => {
        host.innerHTML = `<div class="card"><div class="hint">${escapeHtml(e.message || "Unable to load Saddleback data.")}</div></div>`;
      });
  }


  if (navDataCenter)
  if (navDataCenter) navDataCenter.addEventListener("click", renderDataCenterView);
  if (navAccounting) navAccounting.addEventListener("click", async () => { try { await fetchJSON("/accounting/lock", {method:"POST"}); } catch (e) { console.warn("Accounting lock",e); } await renderAccountingView(); });
  if (navPayroll) navPayroll.addEventListener("click", renderPayrollView);
  if (navEmployees) navEmployees.addEventListener("click", renderEmployeesView);
  if (navDataUpload) navDataUpload.addEventListener("click", renderDataUploadView);
  if (navSaddleback) navSaddleback.addEventListener("click", renderSaddlebackView);
 
  if (navAtlas) navAtlas.addEventListener("click", () => renderChatView("tech"));
  // Emergency is a priority flag, not an ongoing notification after resolution.
  // Retain old requests in history without showing an endless badge.
  function isActionableTimeOffRequest(item) {
    if (!item || String(item.status || '').trim().toLowerCase() !== 'pending') return false;
    const end = String(item.end_date || item.start_date || '').slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(end)) return true;
    const today = new Date();
    const localToday = [today.getFullYear(), String(today.getMonth() + 1).padStart(2, '0'), String(today.getDate()).padStart(2, '0')].join('-');
    return end >= localToday;
  }

  if (navMoses) navMoses.addEventListener("click", () => renderChatView("office"));
 
  if (navNotifications) {
    navNotifications.addEventListener("click", renderNotificationsView);
  }
 
  (async () => {
    if (loginBody) loginBody.style.display = "none";
    if (formsBody) formsBody.style.display = "block";
    if (loginChev) loginChev.innerHTML = "&#9656;";

    const me = await apiAuthMe().catch(() => ({ logged_in: false, user: null }));
    currentUser = me && me.logged_in ? me.user : null;
    pendingPinUser = null;
    applyRoleAccess(currentUser ? currentUser.role : null);
    updateLoginUi();
    if (!currentUser) {
      showLoggedOutSplash();
      return;
    }
    renderCalendarView();
    await initializePlatform();
    apiListTimeOff({ limit: 500 }).then(items => {
      const pendingCount = (items || []).filter(item => isActionableTimeOffRequest(item)).length;
      const timeOffBadge = el('badgeTimeOff');
      if (timeOffBadge) {
        timeOffBadge.textContent = String(pendingCount);
        timeOffBadge.style.display = pendingCount ? 'inline-flex' : 'none';
      }
    }).catch(() => {});
    refreshBadges();
  })();
})();
