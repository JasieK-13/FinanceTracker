from pathlib import Path

p = Path('index.html')
s = p.read_text()
if 'V5.5 Account & Wallet Reconciliation' in s:
    print('already patched')
    raise SystemExit(0)

# 1 config default
old = 'forecastFutureExpenses: [], forecastCustomEnd: "", calendarNotes: {} }'
new = 'forecastFutureExpenses: [], forecastCustomEnd: "", calendarNotes: {}, accounts: [] }'
if old not in s: raise SystemExit('config anchor missing')
s = s.replace(old, new, 1)

css = '''\n  /* V5.5 Account & Wallet Reconciliation */\n  .account-card { margin-bottom: 10px; }\n  .account-card .stats-grid .card { margin: 0; }\n  .account-owner-pill { font-size: 10px; }\n  @media (max-width: 640px) { .account-card .stats-grid { grid-template-columns: 1fr 1fr; } }\n'''
if '</style>' not in s: raise SystemExit('style anchor missing')
s = s.replace('</style>', css + '\n</style>', 1)
s = s.replace('<title>Household Ledger</title>', '<title>Household Ledger</title>\n<!-- V5.5 Account & Wallet Reconciliation -->', 1)

# 2 More nav add Accounts
old = '["settings", "planning", "calculator", "backup"].map'
new = '["settings", "accounts", "planning", "calculator", "backup"].map'
if old not in s: raise SystemExit('more nav anchor missing')
s = s.replace(old, new, 1)

# 3 renderMore Accounts branch
old = 'if (sec === "settings") html += renderSettingsSection();\n    else if (sec === "planning") html += renderPlanningSection(t);'
new = 'if (sec === "settings") html += renderSettingsSection();\n    else if (sec === "accounts") html += renderAccountsSection(t);\n    else if (sec === "planning") html += renderPlanningSection(t);'
if old not in s: raise SystemExit('renderMore branch missing')
s = s.replace(old, new, 1)

# 4 Account helpers/render before planning
anchor = '  function renderPlanningSection(t) {'
if anchor not in s: raise SystemExit('planning anchor missing')
insert = r'''  // ---------- ACCOUNTS / WALLET RECONCILIATION ----------
  function getAccounts() {
    return Array.isArray(data.config.accounts) ? data.config.accounts : [];
  }
  function accountOwnerLabel(a) { return a.owner || "Joint"; }
  function accountTypeLabel(a) { return a.type || "Current"; }
  function accountTrackedBalance(a) {
    const id = String(a.id || "");
    const opening = Number(a.openingBalance) || 0;
    const openingDate = String(a.openingDate || "");
    return opening + data.transactions.filter(tx => {
      if (String(tx.accountId || "") !== id) return false;
      if (openingDate && String(tx.date || "") < openingDate) return false;
      if (tx.type === "income") return Number(tx.amount) || 0;
      if (tx.type === "expense") return -(Number(tx.amount) || 0);
      return 0;
    }).reduce((s,x)=>s+x,0);
  }
  function accountDiff(a) {
    if (a.currentBalance == null || a.currentBalance === "") return null;
    return (Number(a.currentBalance)||0) - accountTrackedBalance(a);
  }
  function walletTotals() {
    const out = {};
    getAccounts().forEach(a => {
      const owner = accountOwnerLabel(a);
      out[owner] = (out[owner] || 0) + (Number(a.currentBalance) || 0);
    });
    return out;
  }
  function accountReconciliation() {
    const accounts = getAccounts();
    let actual=0, tracked=0, difference=0, needs=0;
    accounts.forEach(a=>{
      if(a.currentBalance!=null && a.currentBalance!=="") actual += Number(a.currentBalance)||0;
      tracked += accountTrackedBalance(a);
      const d=accountDiff(a); if(d!=null){ difference += d; if(Math.abs(d)>0.009) needs++; }
    });
    return {accounts,actual,tracked,difference,needs};
  }
  function renderAccountsSection(t) {
    const rec=accountReconciliation(), accounts=rec.accounts;
    const owners=[data0("personA"),data0("personB"),"Joint"];
    let html='<div class="section-title first"><span>Accounts & wallets</span><span class="note">Separate wallets, one household total</span></div>';
    html+='<div class="grid3">';
    html+='<div class="hero-card cash"><div class="hc-label">Total across accounts</div><div class="hc-value">'+fmt(rec.actual)+'</div><div class="hc-sub">Current balances across every wallet</div></div>';
    html+='<div class="hero-card committed"><div class="hc-label">Tracked in Ledger</div><div class="hc-value">'+fmt(rec.tracked)+'</div><div class="hc-sub">Opening balances + account-tagged transactions</div></div>';
    const diffClass=Math.abs(rec.difference)<0.01?'good':'bad';
    html+='<div class="hero-card safe"><div class="hc-label">Reconciliation</div><div class="hc-value" style="color:var(--'+diffClass+');">'+fmt(rec.difference)+'</div><div class="hc-sub">'+(rec.needs?rec.needs+' account'+(rec.needs===1?'':'s')+' need attention':'All accounts balance')+'</div></div>';
    html+='</div>';
    html+='<div class="section-title">Wallet split</div><div class="list-grid">';
    const wt=walletTotals();
    owners.forEach(o=>{ html+='<div class="card"><div class="card-label">'+esc(o)+'</div><div class="card-value">'+fmt(wt[o]||0)+'</div><div class="card-sub">All accounts assigned to '+esc(o)+'</div></div>'; });
    html+='</div>';
    html+='<div class="section-title">Add bank account</div><form class="entry" id="account-form"><div class="field-row"><div class="field"><label>Account name</label><input id="acc-name" required placeholder="e.g. HSBC Current"></div><div class="field"><label>Owner / wallet</label><select id="acc-owner"><option>'+esc(data0("personA"))+'</option><option>'+esc(data0("personB"))+'</option><option selected>Joint</option></select></div></div>';
    html+='<div class="field-row"><div class="field"><label>Account type</label><select id="acc-type"><option>Current</option><option>Savings</option><option>Credit card</option><option>Other</option></select></div><div class="field"><label>Current bank balance (£)</label><input id="acc-balance" type="number" step="0.01" required placeholder="0.00"></div></div>';
    html+='<div class="field-row"><div class="field"><label>Balance date</label><input id="acc-date" type="date" value="'+todayStr()+'"></div><div class="field"><label>Opening balance for tracking (£)</label><input id="acc-opening" type="number" step="0.01" placeholder="Usually same as current balance"></div></div>';
    html+='<div class="note">The bank balance is what you say the account currently contains. The opening balance is the starting point for account reconciliation. Neither changes household Cash Now by itself.</div><div class="row-actions"><button type="submit" class="btn primary">Add account</button></div></form>';
    html+='<div class="section-title">Your accounts</div>';
    if(!accounts.length) html+='<div class="card"><div class="empty">No accounts added yet. Add HSBC, Santander and any joint/savings accounts here.</div></div>';
    else accounts.forEach(a=>{
      const tb=accountTrackedBalance(a), d=accountDiff(a), bad=d!=null && Math.abs(d)>0.009;
      const status=d==null?'<span class="tag">balance not set</span>':(bad?'<span class="tag overdue">needs attention</span>':'<span class="tag good">reconciled</span>');
      html+='<div class="card account-card"><div class="pot-row-top"><div><div class="li-title">'+esc(a.name)+' '+status+'</div><div class="li-sub">'+esc(accountOwnerLabel(a))+' · '+esc(accountTypeLabel(a))+(a.balanceDate?' · checked '+esc(a.balanceDate):'')+'</div></div><div style="text-align:right"><div class="li-amt">'+fmt(a.currentBalance)+'</div><div class="note">bank balance</div></div></div>';
      html+='<div class="stats-grid" style="margin-top:8px"><div class="card"><div class="card-label">Tracked</div><div class="card-value">'+fmt(tb)+'</div></div><div class="card"><div class="card-label">Difference</div><div class="card-value" style="color:'+(bad?'var(--bad)':'var(--good)')+';">'+(d==null?'—':fmt(d))+'</div></div></div>';
      if(bad) html+='<div class="banner warn" style="margin-top:8px;margin-bottom:0"><span><strong>Not fully tracked.</strong> The bank is '+fmt(Math.abs(d))+(d>0?' higher':' lower')+' than the Ledger. Check for missing, duplicate or personal transactions.</span></div>';
      html+='<div class="row-actions"><button class="btn small" data-action="update-account-balance" data-id="'+esc(a.id)+'">Update bank balance</button><button class="btn small" data-action="edit-account" data-id="'+esc(a.id)+'">Edit</button><button class="btn small danger" data-action="delete-account" data-id="'+esc(a.id)+'">Delete</button></div></div>';
    });
    html+='<div class="section-title">What needs attention?</div><div class="card"><div class="card-sub">This compares each bank balance with transactions assigned to that account. A difference means something has not been logged, is duplicated, or is classified differently. Automatic Open Banking can use the same account IDs later.</div>';
    if(rec.needs===0) html+='<div class="note" style="margin-top:8px;color:var(--good);font-weight:800">✓ No account differences detected.</div>';
    else accounts.filter(a=>{const d=accountDiff(a);return d!=null&&Math.abs(d)>0.009;}).forEach(a=>{const d=accountDiff(a);html+='<div class="list-item"><div class="li-main"><div class="li-title">'+esc(a.name)+'</div><div class="li-sub">'+(d>0?'More money at bank than tracked':'Less money at bank than tracked')+'</div></div><div class="li-amt" style="color:var(--bad)">'+fmt(Math.abs(d))+'</div></div>';});
    html+='</div>';
    return html;
  }

'''
s=s.replace(anchor,insert+anchor,1)

# 5 settings note
old='<div class="card-sub" style="margin-top:8px;">BNU Bursary payments go straight to the Aviation pot when marked received.</div>'
new='<div class="card-sub" style="margin-top:8px;">BNU Bursary payments go straight to the Aviation pot when marked received.</div><div class="card-sub" style="margin-top:8px;">Bank accounts are separate wallets. Splitting money between Jasiek, Partner and Joint does not create or remove money from the household total.</div>'
if old not in s: raise SystemExit('settings note anchor missing')
s=s.replace(old,new,1)

# 6 transaction edit account selector
old='''      '<div class="field-row single"><div class="field"><label>Person</label><select id="tx-person"><option' + (d.person === data0("personA") ? " selected" : "") + '>' + esc(data0("personA")) + '</option><option' + (d.person === data0("personB") ? " selected" : "") + '>' + esc(data0("personB")) + '</option><option' + (d.person === "Joint" || !d.person ? " selected" : '') + '>Joint</option></select></div></div>' '''
new='''      '<div class="field-row"><div class="field"><label>Person</label><select id="tx-person"><option' + (d.person === data0("personA") ? " selected" : "") + '>' + esc(data0("personA")) + '</option><option' + (d.person === data0("personB") ? " selected" : "") + '>' + esc(data0("personB")) + '</option><option' + (d.person === "Joint" || !d.person ? " selected" : '') + '>Joint</option></select></div><div class="field"><label>Account / wallet</label><select id="tx-account"><option value="">Unassigned</option>' + getAccounts().map(a=>'<option value="' + esc(a.id) + '"' + (d.accountId===a.id ? " selected" : "") + '>' + esc(a.name) + ' · ' + esc(accountOwnerLabel(a)) + '</option>').join("") + '</select></div></div>' '''
if old not in s: raise SystemExit('edit tx anchor missing')
s=s.replace(old,new,1)

# 7 edit tx patch account
old='const patch = { date: document.getElementById("tx-date").value, amount: Math.abs(parseFloat(document.getElementById("tx-amount").value) || 0), person: document.getElementById("tx-person").value, description:'
new='const patch = { date: document.getElementById("tx-date").value, amount: Math.abs(parseFloat(document.getElementById("tx-amount").value) || 0), person: document.getElementById("tx-person").value, accountId: (document.getElementById("tx-account") ? document.getElementById("tx-account").value : "") || null, description:'
if old not in s: raise SystemExit('patch tx anchor missing')
s=s.replace(old,new,1)

# 8 account handlers
anchor='    // More\n'
if anchor not in s: raise SystemExit('more handlers anchor missing')
handlers=r'''    // Accounts / wallet reconciliation
    const accountForm = document.getElementById("account-form");
    if (accountForm) accountForm.onsubmit = async (e) => {
      e.preventDefault();
      const name=String(document.getElementById("acc-name").value||"").trim();
      const owner=document.getElementById("acc-owner").value;
      const type=document.getElementById("acc-type").value;
      const balance=Number(document.getElementById("acc-balance").value)||0;
      const date=document.getElementById("acc-date").value||todayStr();
      const openingRaw=document.getElementById("acc-opening").value;
      const opening=openingRaw===""?balance:(Number(openingRaw)||0);
      if(!name) return;
      const accounts=getAccounts().concat([{id:"acc-"+Date.now().toString(36),name,owner,type,currentBalance:balance,balanceDate:date,openingBalance:opening,openingDate:date,createdAt:Date.now()}]);
      const ok=await safeWrite(()=>db.doc("settings/config").update({accounts})); if(ok) render();
    };
    document.querySelectorAll('[data-action="update-account-balance"]').forEach(b=>{b.onclick=async()=>{const a=getAccounts().find(x=>x.id===b.dataset.id);if(!a)return;const raw=prompt("Current bank balance for "+a.name+":",Number(a.currentBalance||0).toFixed(2));if(raw===null)return;const n=Number(raw);if(!Number.isFinite(n))return alert("Enter a valid balance.");const accounts=getAccounts().map(x=>x.id===a.id?Object.assign({},x,{currentBalance:n,balanceDate:todayStr()}):x);const ok=await safeWrite(()=>db.doc("settings/config").update({accounts}));if(ok)render();};});
    document.querySelectorAll('[data-action="edit-account"]').forEach(b=>{b.onclick=async()=>{const a=getAccounts().find(x=>x.id===b.dataset.id);if(!a)return;const name=prompt("Account name:",a.name);if(name===null)return;const balance=prompt("Current bank balance:",Number(a.currentBalance||0).toFixed(2));if(balance===null)return;const accounts=getAccounts().map(x=>x.id===a.id?Object.assign({},x,{name:String(name).trim()||x.name,currentBalance:Number(balance)||0,balanceDate:todayStr()}):x);const ok=await safeWrite(()=>db.doc("settings/config").update({accounts}));if(ok)render();};});
    document.querySelectorAll('[data-action="delete-account"]').forEach(b=>{b.onclick=async()=>{const a=getAccounts().find(x=>x.id===b.dataset.id);if(!a)return;if(!confirm("Delete the account "+a.name+"? Transactions already logged will not be deleted, but they will become unassigned."))return;const accounts=getAccounts().filter(x=>x.id!==a.id);const ops=[db.doc("settings/config").update({accounts})].concat(data.transactions.filter(tx=>tx.accountId===a.id).map(tx=>db.doc("transactions/"+tx.id).update({accountId:null})));const ok=await safeWrite(()=>Promise.all(ops));if(ok)render();};});

'''
s=s.replace(anchor,handlers+anchor,1)

# 9 export accounts
old='config: data.config, transactions: data.transactions, commitments: data.commitments, scheduled_income: data.scheduled, aviation: data.aviation'
new='config: data.config, accounts: getAccounts(), transactions: data.transactions, commitments: data.commitments, scheduled_income: data.scheduled, aviation: data.aviation'
if old not in s: raise SystemExit('export anchor missing')
s=s.replace(old,new,1)

p.write_text(s)
print('patched',len(s))
