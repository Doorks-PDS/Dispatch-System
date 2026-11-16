/* Public, privacy-safe Atlas product Q&A preview. No API requests or business access. */
(()=>{'use strict';
  const root=document.getElementById('atlas-moses-demo');
  if(!root)return;
  const feed=root.querySelector('#amd-conversation');
  const form=root.querySelector('#amd-form');
  const question=root.querySelector('#amd-question');
  const topics=[
    {name:'overview',pattern:/\b(atlas|software|platform|do|feature|capabilit|business|help|what is)\b/i,
     answer:'Atlas brings scheduling, customer information, work orders, estimates, invoices, purchasing and business reporting into a connected workspace. Moses is the assistant designed to help you find information and prepare next steps.'},
    {name:'work-orders',pattern:/\b(work.?orders?|jobs?|dispatch|schedule|calendar|field|technician|service|visit)\b/i,
     answer:'Example workflow (sample only): A customer submits a service request. The office reviews it, opens a work order, schedules a visit, and the field team adds notes and photos. Moses can help locate the record, prepare a change, and request approval before an authorized action.'},
    {name:'quotes',pattern:/\b(estimat|quot|bid|pricing|repair|recommend)\b/i,
     answer:'Example (sample only): “Prepare an estimate for the recommended repairs.” Moses would locate the exact job, review the saved technician recommendations, and prepare an estimate scope. A person confirms parts, labor, pricing and approval before an official document is issued.'},
    {name:'ai',pattern:/\b(moses|assistant|ai|automat|autonom|butler|chat|agent)\b/i,
     answer:'Moses is Atlas’ built-in business assistant. In an authorized workspace, it is designed to search records, summarize priorities and prepare actions using existing tools. It does not get unlimited access or silently send, charge or change records. Actions that require approval are reviewed first.'},
    {name:'approvals',pattern:/\b(approv|permission|safe|secur|role|access|audit|confirm|change|delete)\b/i,
     answer:'Moses follows workspace and user permissions. For supported changes, it prepares a proposal, asks an authorized person to approve or reject it, then uses the existing workflow. An execution receipt should distinguish pending, approved, completed and “needs review.” This public demo cannot access your company.'},
    {name:'invoices',pattern:/\b(invoice|bill|account|pay|stripe|money|receiv|checkout|financial)\b/i,
     answer:'Atlas includes connected invoicing and accounting workflows. Moses can help prepare document and payment steps for review. Stripe support is being validated in sandbox mode; this public demo never creates an invoice, checkout, charge or payment.'},
    {name:'purchasing',pattern:/\b(purchas|supplier|vendor|parts|inventory|receiv|purchase order|po\b)/i,
     answer:'For purchasing, an example flow is: review a supplier and parts list, prepare a draft purchase order, confirm receiving against a packing slip, and review a supplier bill. Moses helps organize the steps, with approval and verification at the points that update records.'},
    {name:'teams',pattern:/\b(team|employee|timecard|payroll|hours|pto|overtime|mobile|tablet)\b/i,
     answer:'Atlas supports office and field teams, including work-order access, completion information, time reporting and administrative workflows. The exact modules and permissions depend on the configured package.'},
    {name:'plans',pattern:/\b(plan|package|basic|platinum|premium|personaliz|tier|cost|price|pricing)\b/i,
     answer:'Atlas offers Basic, Platinum, Premium and Personalized setups. Basic focuses on core operations; expanded tiers add portals, documents, purchasing and connected workflows. See the Plans section for displayed starting prices, then request a demo to scope your business.'},
    {name:'smallbiz',pattern:/\b(small|solo|single|llc|contractor|startup|company|business size)\b/i,
     answer:'Atlas is aimed at small and growing businesses, including solo operators and service teams. The best setup depends on what you need to schedule, track, quote, invoice and report.'},
    {name:'email',pattern:/\b(email|resend|send|notification|customer message|contact)\b/i,
     answer:'Moses can help prepare customer updates and document-delivery proposals inside an authorized workspace. Real messages require verified sender configuration and the applicable approval step. This public preview sends no email.'},
    {name:'demo',pattern:/\b(demo|trial|try|see|test|show|example|walkthrough|start)\b/i,
     answer:'Try a sample request: “Prepare a quote from technician notes.” In a real account Moses first checks your role and workspace, finds a unique saved job, drafts the scope, requests approval where needed, and checks the saved execution receipt. To see your own workflow, use Request a demo below.'}
  ];
  const prompts=[
    'What does Atlas do?',
    'Show me a work-order example',
    'How does Moses prepare an estimate?',
    'How do approvals work?',
    'Can Moses handle invoices?',
    'What plans are available?'
  ];
  function addMessage(who,content){
    const el=document.createElement('div');el.className='amd-message';el.dataset.from=who;
    const by=document.createElement('div');by.className='amd-meta';by.textContent=who==='moses'?'MOSES · PRODUCT PREVIEW':'YOU';
    const p=document.createElement('p');p.textContent=content;
    el.append(by,p);feed.appendChild(el);
    while(feed.children.length>16)feed.removeChild(feed.firstElementChild);
    feed.scrollTop=feed.scrollHeight;
  }
  function reply(raw){
    const input=String(raw||'').trim().slice(0,240);if(!input)return;
    addMessage('visitor',input);
    const normalized=input.toLowerCase();
    // Match more specific business intents before broad words like “Atlas” or “software”.
    const order=['approvals','quotes','work-orders','invoices','purchasing','teams','plans','smallbiz','email','ai','demo','overview'];
    let found=order.map(name=>topics.find(t=>t.name===name)).find(t=>t.pattern.test(normalized));
    if(!found)found={answer:'I can walk you through Atlas features, work orders, estimating, invoices, AI assistance, permissions, packages and how to request a demo. Try one of the sample questions below. This is a guided preview—not a live AI connection.'};
    addMessage('moses',found.answer);
  }
  const quick=root.querySelector('#amd-quick');
  prompts.forEach(prompt=>{const button=document.createElement('button');button.type='button';button.className='amd-prompt';button.textContent=prompt;button.addEventListener('click',()=>reply(prompt));quick.appendChild(button)});
  form.addEventListener('submit',event=>{event.preventDefault();const value=question.value;question.value='';reply(value);question.focus()});
  addMessage('moses','Hi! I’m Moses. This is an interactive preview of how I can help with Atlas. Ask about scheduling, estimates, invoicing, approval workflows or plans—or select an example below.');
})();
