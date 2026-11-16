(()=>{'use strict';
 const root=document.getElementById('atlas-moses-chat-widget');if(!root)return;
 const openBtn=root.querySelector('[data-moses-open]'),panel=root.querySelector('[data-moses-panel]');
 const closeBtn=root.querySelector('[data-moses-close]'),log=root.querySelector('[data-moses-log]');
 const form=root.querySelector('form'),input=form.querySelector('input'),send=form.querySelector('button');
 const note=root.querySelector('[data-moses-status]');let history=[],busy=false;
 const examples={
 'What can Atlas do?':'Atlas connects dispatching, work orders, customers, field forms, estimates, invoices, purchasing, accounting and team workflows. Features vary by package.',
 'How does Moses help?':'Moses helps authorized users search records, prepare drafts and proposed actions, and route actions for human approval. It does not bypass workspace permissions.',
 'What are the packages?':'Basic starts at $3,000, Platinum at $5,000, Premium at $7,500, and Personalized is quoted. Pricing and scope are shown on this page.',
 'Can I request a demo?':'Yes. Use the Request a Demo form below and describe your business and the workflows you want connected.'
 };
 const add=(who,body)=>{const div=document.createElement('div');div.className='atlas-moses-bubble '+(who==='You'?'user':'assistant');const strong=document.createElement('strong');strong.textContent=who;const content=document.createElement('span');content.textContent=body;div.append(strong,content);log.append(div);log.scrollTop=log.scrollHeight;};
 const toggle=(show)=>{panel.hidden=!show;openBtn.setAttribute('aria-expanded',String(show));if(show){input.focus();}else{openBtn.focus();}};
 openBtn.addEventListener('click',()=>toggle(panel.hidden));closeBtn.addEventListener('click',()=>toggle(false));
 document.getElementById('atlas-chat-nav')?.addEventListener('click',e=>{e.preventDefault();toggle(true);});
 const prompts=root.querySelector('[data-moses-prompts]');Object.keys(examples).forEach(q=>{const b=document.createElement('button');b.type='button';b.textContent=q;b.onclick=()=>{toggle(true);input.value=q;form.requestSubmit();};prompts.append(b);});
 add('Moses','Hi! I can answer questions about Atlas software, how Moses works, and our packages. This public demo cannot access private business records or execute actions.');
 form.addEventListener('submit',async(e)=>{e.preventDefault();if(busy)return;const question=input.value.trim().slice(0,320);if(!question)return;input.value='';add('You',question);busy=true;send.disabled=true;note.textContent='Moses is answering…';
  try{
   const response=await fetch('/doorks-assistant/public/atlas-chat',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({message:question,history:history.slice(-4)})});
   const data=await response.json();if(!response.ok)throw Error(data.detail||'Live chat not available');
   const answer=String(data.answer||'').trim();if(!answer)throw Error('Empty response');add('Moses',answer);history.push({role:'user',content:question},{role:'assistant',content:answer});note.textContent='Live public product assistant · no account records';
  }catch(err){const answer=examples[question]||'Live product chat is temporarily unavailable. You can review the package details below or request a personal demonstration.';add('Moses',answer);history=[];note.textContent='Offline product guidance · no live AI connection';}
  finally{busy=false;send.disabled=false;input.focus();}
 });
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden)toggle(false)});
})();
