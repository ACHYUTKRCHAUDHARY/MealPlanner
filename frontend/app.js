const DAYS=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
const steps=[
 {title:'Which days will you cook?',sub:'Pick the days you want meals planned for.',type:'days'},
 {title:"What's your weekly budget?",sub:'Set what you’re happy to spend on those days.',type:'budget'},
 {title:'What are you in the mood for?',sub:'Pick up to 3 goals.',type:'goals'},
 {title:'Any dietary needs?',sub:'Choose one diet and any ingredient allergies.',type:'diet'},
 {title:'What appliances do you have?',sub:'Select everything we can plan with.',type:'appliances'},
 {title:'One last detail',sub:'Tell us what is already in your kitchen.',type:'pantry'}
];
const defaults={step:0,days:[...DAYS],budget:1800,people:2,goals:['protein'],diet:['vegetarian'],appliances:['stove','pressure-cooker'],pantry:'',allergies:[],exclusions:'',meal_types:['dinner']};
let state={...defaults};
try { state={...defaults,...JSON.parse(localStorage.getItem('plateful-state')||'{}')}; } catch { /* Corrupt draft: use defaults. */ }
state.step=Math.max(0,Math.min(5,Number(state.step)||0));
const escapeHtml=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let currentPlan=null;
const $=id=>document.getElementById(id); const el=$('stepContent');
function save(){try{localStorage.setItem('plateful-state',JSON.stringify(state))}catch{};$('savedStatus').textContent='Draft saved on this device'}
function option(label,value,group,emoji,selected){return `<button class="option ${selected?'selected':''}" data-group="${group}" aria-pressed="${!!selected}" data-value="${value}"><span class="emoji">${emoji}</span><span>${label}</span></button>`}
function render(){const s=steps[state.step];$('progressBar').style.width=`${((state.step+1)/steps.length)*100}%`;$('stepCount').textContent=`${state.step+1} / ${steps.length}`;$('backButton').style.visibility=state.step?'visible':'hidden';let body='';
 if(s.type==='days') body=`<div class="option-grid">${DAYS.map(d=>option(d,d,'days','',state.days.includes(d))).join('')}</div>`;
 if(s.type==='budget') body=`<div class="budget-value">₹<span id="budgetNumber">${state.budget}</span></div><div class="budget-caption">for ${state.days.length} cooking days</div><input class="range" id="budgetRange" aria-label="Meal budget in rupees" type="range" min="500" max="5000" step="100" value="${state.budget}"><div class="range-labels"><span>₹500</span><span>₹5,000</span></div><div class="people-box"><div><strong>How many people?</strong><div class="budget-caption" style="text-align:left;margin:5px 0 0">We’ll scale every recipe.</div></div><div class="counter"><button id="minusPeople" aria-label="Fewer people">−</button><strong id="peopleNumber">${state.people}</strong><button id="plusPeople" aria-label="More people">+</button></div></div>`;
 const goals=[['Speedy meals','speedy','⚡'],['Low calorie','low-calorie','⚖️'],['Family favourites','family','👨‍👩‍👧‍👦'],['Healthy comfort','healthy-comfort','🥗'],['Fakeaway','fakeaway','🥡'],['Gut friendly','gut-friendly','🌱'],['Protein packed','protein','💪']];
 if(s.type==='goals') body=`<div class="option-grid">${goals.map(x=>option(x[0],x[1],'goals',x[2],state.goals.includes(x[1]))).join('')}</div>`;
 const diets=[['No preference','none','◯'],['Vegetarian','vegetarian','🥕'],['Vegan','vegan','🌱'],['Egg-friendly','eggetarian','🥚']];
 if(s.type==='diet') body=`<div class="option-grid">${diets.map(x=>option(x[0],x[1],'diet',x[2],state.diet.includes(x[1]))).join('')}</div>`;
 const appliances=[['Gas / induction stove','stove','🔥'],['Pressure cooker','pressure-cooker','♨️'],['Air fryer','air-fryer','🍟'],['Oven','oven','▣'],['Microwave','microwave','〽️'],['Blender','blender','🥤']];
 if(s.type==='appliances') body=`<div class="option-grid">${appliances.map(x=>option(x[0],x[1],'appliances',x[2],state.appliances.includes(x[1]))).join('')}</div>`;
 if(s.type==='pantry') body=`<label for="pantry"><strong>Ingredients you already have</strong></label><textarea class="text-input" id="pantry" rows="6" placeholder="Rice, onion, tomato — or one quantity per line: rice: 500 g">${escapeHtml(state.pantry)}</textarea><p style="margin-top:12px">We’ll prioritise meals that use these ingredients and reduce waste.</p>`;
 if(s.type==='days') body+=`<h2>Meal types</h2><div class="option-grid">${['breakfast','lunch','dinner','snack'].map(v=>option(v[0].toUpperCase()+v.slice(1),v,'meal_types','',state.meal_types.includes(v))).join('')}</div>`;
 if(s.type==='diet') body+=`<h2>Allergies</h2><div class="option-grid">${['dairy','peanuts','tree nuts','gluten','soy','egg'].map(v=>option(v,v,'allergies','',state.allergies.includes(v))).join('')}</div><label for="exclusions">Other excluded ingredients (comma-separated)</label><input class="text-input" id="exclusions" value="${escapeHtml(state.exclusions)}">`;
 el.innerHTML=`<h1>${s.title}</h1><p>${s.sub}</p>${body}`; bind();$('continueButton').textContent=state.step===steps.length-1?'Generate my plan →':'Continue →';save();}
function bind(){if($('exclusions')) $('exclusions').oninput=e=>{state.exclusions=e.target.value;save()};document.querySelectorAll('.option').forEach(b=>b.onclick=()=>{const g=b.dataset.group,v=b.dataset.value;if(g==='goals'){state[g].includes(v)?state[g]=state[g].filter(x=>x!==v):state[g].length<3&&state[g].push(v)}else if(g==='diet'){state[g]=v==='none'?['none']:[v]}else{state[g].includes(v)?state[g]=state[g].filter(x=>x!==v):state[g].push(v)}render()});
 if($('budgetRange')) $('budgetRange').oninput=e=>{state.budget=+e.target.value;$('budgetNumber').textContent=state.budget;save()};
 if($('minusPeople')){$('minusPeople').onclick=()=>{state.people=Math.max(1,state.people-1);render()};$('plusPeople').onclick=()=>{state.people=Math.min(8,state.people+1);render()}}
 if($('pantry')) $('pantry').oninput=e=>{state.pantry=e.target.value;save()};}
function validate(){const t=steps[state.step].type;if(t==='days'&&!state.meal_types.length)return 'Select at least one meal type';if(t==='days'&&!state.days.length)return 'Select at least one cooking day';if(t==='goals'&&!state.goals.length)return 'Choose at least one meal goal';if(t==='diet'&&!state.diet.length)return 'Choose a dietary preference';if(t==='appliances'&&!state.appliances.length)return 'Choose at least one appliance';return ''}
function toast(msg){$('toast').textContent=msg;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),2200)}
$('continueButton').onclick=()=>{const error=validate();if(error)return toast(error);if(state.step<steps.length-1){state.step++;render()}else generate()};$('backButton').onclick=()=>{if(state.step){state.step--;render()}};$('newPlanButton').onclick=()=>{state.step=0;$('dashboard').classList.add('hidden');$('wizard').classList.remove('hidden');render()};$('brandButton').onclick=()=>{$('dashboard').classList.add('hidden');$('loadingScreen').classList.add('hidden');$('wizard').classList.remove('hidden');render()};$('printButton').onclick=()=>window.print();$('themeButton').onclick=()=>document.body.classList.toggle('dark');document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));t.classList.add('active');$('mealsPanel').classList.toggle('hidden',t.dataset.tab!=='meals');$('groceriesPanel').classList.toggle('hidden',t.dataset.tab!=='groceries')});render();

function pantryItems(){
  return state.pantry.split(/[,\n]/).map(s=>s.trim()).filter(Boolean).map(s=>{
    const match=s.match(/^(.+?):\s*(\d+(?:\.\d+)?)\s*(g|kg|ml|L|piece|count|bunch|bulb)$/);
    if(s.includes(':')&&!match) throw new Error('Use pantry quantities like rice: 500 g, one per line.');
    return match?{name:match[1].trim(),quantity:Number(match[2]),unit:match[3]}:{name:s,quantity:null,unit:'g'};
  });
}
function requestBody(){
  const pantry=pantryItems();
  return {days:state.days,budget:state.budget,people:state.people,goals:state.goals,
    diet:state.diet[0],appliances:state.appliances,pantry:pantry.map(i=>i.name),pantry_quantities:pantry,
    allergies:state.allergies,exclusions:state.exclusions.split(',').map(s=>s.trim()).filter(Boolean),meal_types:state.meal_types};
}
function showError(error,retry){
  $('errorText').textContent=error.message;
  $('errorBanner').classList.remove('hidden');
  $('retryButton').classList.toggle('hidden',!retry);
  $('retryButton').onclick=()=>{clearError();retry?.()};
  if(error.status===401){$('accountButton').textContent='Sign in';$('authDialog').showModal()}
}
function clearError(){$('errorBanner').classList.add('hidden')}
async function busy(button,action){
  if(button.disabled)return;
  button.disabled=true;
  const original=button.textContent;
  button.textContent='Please wait…';
  try{clearError();await action()}catch(error){showError(error,()=>busy(button,action))}
  finally{button.disabled=false;button.textContent=original}
}
async function generate(){
  if(!API.signedIn()){$('authDialog').showModal();return}
  let body;try{body=requestBody()}catch(error){showError(error);return}
  clearError();$('wizard').classList.add('hidden');$('loadingScreen').classList.remove('hidden');
  $('brandButton').disabled=true;
  try{
    await API.request('/users/me/preferences',{method:'PUT',body});
    await API.request('/users/me/pantry',{method:'PUT',body:{items:body.pantry_quantities}});
    currentPlan=await API.request('/plans/generate',{method:'POST',body});
    await showDashboard();
  }catch(error){$('wizard').classList.remove('hidden');showError(error,generate)}
  finally{$('loadingScreen').classList.add('hidden');$('brandButton').disabled=false}
}
async function showDashboard(){
  const p=currentPlan,meals=p.meals;
  $('wizard').classList.add('hidden');$('dashboard').classList.remove('hidden');
  $('planSummary').textContent=`${meals.length} planned meals. ${p.explanation}`;
  $('savePlanButton').textContent=p.saved?'Saved ✓':'Save plan';
  $('savePlanButton').disabled=p.saved;
  const average=key=>meals.every(m=>m[key]!=null)?Math.round(meals.reduce((s,m)=>s+m[key],0)/meals.length):'Unknown';
  $('metricRow').innerHTML=[['₹'+p.estimated_total,'Estimated spend'],['₹'+p.budget_remaining,'Budget remaining'],[average('protein_grams')+' g','Avg. protein / person / meal'],[average('calories'),'Avg. calories / person / meal']].map(x=>`<div class="metric"><strong>${escapeHtml(x[0])}</strong><span>${x[1]}</span></div>`).join('');
  $('planWarnings').replaceChildren(...p.warnings.map(w=>{const li=document.createElement('li');li.textContent=w;return li}));
  $('retrievalStatus').textContent=`Selection: ${p.retrieval_mode}. Explanation: ${p.ai_mode}.`;
  $('nutritionTotals').innerHTML=`<h2>Nutrition for all people and selected meals</h2><div class="table-scroll"><table><thead><tr><th>Day</th><th>Calories</th><th>Protein (g)</th><th>Carbs (g)</th><th>Fat (g)</th><th>Fiber (g)</th></tr></thead><tbody>${Object.entries({...p.nutrition_totals.daily,Total:p.nutrition_totals.weekly}).map(([day,n])=>`<tr><th>${escapeHtml(day)}</th>${['calories','protein_grams','carbohydrates','fat','fiber'].map(k=>`<td>${n[k]??'Unknown'}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  $('mealsPanel').innerHTML=`<div class="meal-grid">${meals.map(m=>`<article class="meal-card"><span class="day">${escapeHtml(m.day)} · ${escapeHtml(m.meal_type)}</span><h3>${escapeHtml(m.name)}</h3><div class="meal-meta"><span>${m.time_minutes} min</span><span>${m.protein_grams??'Unknown'}g protein / person</span><span>₹${m.estimated_cost}</span></div><details><summary>Ingredients & preparation</summary><ul>${Object.entries(m.ingredients).map(([k,v])=>`<li>${escapeHtml(k)}: ${escapeHtml(v)}</li>`).join('')}</ul>${m.instructions.length?`<ol>${m.instructions.map(i=>`<li>${escapeHtml(i)}</li>`).join('')}</ol>`:'<p>Preparation instructions are not available for this legacy recipe.</p>'}</details><button data-swap="${m.id}">Swap meal ↻</button></article>`).join('')}</div>`;
  document.querySelectorAll('[data-swap]').forEach(button=>button.onclick=()=>busy(button,async()=>{
    currentPlan=await API.request(`/plans/${p.id}/items/${button.dataset.swap}/swap`,{method:'POST'});
    await showDashboard();toast('Meal and groceries updated');
  }));
  await loadGroceries();
}
async function loadGroceries(){
  try{
    const groceries=await API.request(`/plans/${currentPlan.id}/groceries`);
    $('groceriesPanel').innerHTML=groceries.length?`<div class="grocery-grid"><section class="grocery-section"><h3>Shopping list</h3>${groceries.map(i=>`<label class="grocery-item"><input type="checkbox" data-grocery="${i.id}" ${i.checked?'checked':''}><span>${escapeHtml(i.name)}</span><span>${i.quantity} ${escapeHtml(i.unit)}</span></label>`).join('')}</section></div>`:'<p>Your measured pantry covers this plan’s ingredients.</p>';
    document.querySelectorAll('[data-grocery]').forEach(input=>input.onchange=async()=>{
      input.disabled=true;try{await API.request(`/plans/${currentPlan.id}/groceries/${input.dataset.grocery}`,{method:'PATCH',body:{checked:input.checked}})}
      catch(error){input.checked=!input.checked;showError(error)}finally{input.disabled=false}
    });
  }catch(error){$('groceriesPanel').textContent='Unable to load groceries.';showError(error,loadGroceries)}
}
$('savePlanButton').onclick=()=>busy($('savePlanButton'),async()=>{
  currentPlan=await API.request('/plans',{method:'POST',body:{plan_id:currentPlan.id}});toast('Plan saved');
  // busy restores text after its promise; update label on the next event-loop turn.
  setTimeout(()=>{$('savePlanButton').textContent='Saved ✓';$('savePlanButton').disabled=true},0);
});
$('accountButton').onclick=()=>{$('authDialog').showModal()};
$('closeAuth').onclick=()=>{$('authDialog').close()};
$('authForm').onsubmit=event=>{
  event.preventDefault();
  const mode=event.submitter.dataset.mode;
  busy(event.submitter,async()=>{
    $('authError').textContent='';
    let data;
    try{data=await API.request('/auth/'+mode,{method:'POST',body:{email:$('email').value,password:$('password').value}})}
    catch(error){$('authError').textContent=error.message;throw error}
    API.setToken(data.access_token);$('password').value='';$('accountButton').textContent='Account';
    $('logoutButton').classList.remove('hidden');$('authDialog').close();
    const [preferences,pantry]=await Promise.all([API.request('/users/me/preferences'),API.request('/users/me/pantry')]);
    if(preferences){state={...state,...preferences,diet:[preferences.diet],exclusions:preferences.exclusions.join(',')};
      state.pantry=pantry.items.map(i=>i.quantity==null?i.name:`${i.name}: ${i.quantity} ${i.unit}`).join('\n');render()}
    toast('Signed in. Your saved preferences are ready.');
  });
};
$('logoutButton').onclick=()=>busy($('logoutButton'),async()=>{
  await API.request('/auth/logout',{method:'POST'});API.setToken(null);currentPlan=null;
  state={...defaults,days:[...DAYS]};localStorage.removeItem('plateful-state');render();
  $('accountButton').textContent='Sign in';$('logoutButton').classList.add('hidden');
  $('authDialog').close();$('historyDialog').close();$('dashboard').classList.add('hidden');$('wizard').classList.remove('hidden');
});
let historyOffset=0;
async function loadHistory(){
  if(!API.signedIn()){$('authDialog').showModal();return}
  const plans=await API.request(`/plans?limit=20&offset=${historyOffset}`);
  $('historyItems').innerHTML=plans.length?plans.map(p=>`<article class="history-row"><div><strong>${new Date(p.created_at).toLocaleDateString()}</strong><p>${p.meal_count} meals · ₹${p.estimated_total}</p></div><button class="secondary-button" data-open="${p.id}">Open</button><button class="secondary-button" data-delete="${p.id}">Delete</button></article>`).join(''):'<p>No saved plans yet. Generate a plan and select Save plan.</p>';
  $('historyPrevious').disabled=historyOffset===0;$('historyNext').disabled=plans.length<20;
  if(!$('historyDialog').open)$('historyDialog').showModal();
  document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>busy(b,async()=>{currentPlan=await API.request('/plans/'+b.dataset.open);$('historyDialog').close();await showDashboard()}));
  document.querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>busy(b,async()=>{
    if(!confirm('Delete this saved plan?'))return;
    await API.request('/plans/'+b.dataset.delete,{method:'DELETE'});
    if(currentPlan?.id===b.dataset.delete){currentPlan=null;$('dashboard').classList.add('hidden');$('wizard').classList.remove('hidden')}
    await loadHistory();
  }));
}
$('historyButton').onclick=()=>busy($('historyButton'),async()=>{historyOffset=0;await loadHistory()});
$('historyPrevious').onclick=()=>busy($('historyPrevious'),async()=>{historyOffset=Math.max(0,historyOffset-20);await loadHistory()});
$('historyNext').onclick=()=>busy($('historyNext'),async()=>{historyOffset+=20;await loadHistory()});
$('closeHistory').onclick=()=>$('historyDialog').close();
$('dismissError').onclick=clearError;
