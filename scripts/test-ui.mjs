// DOM integration test: real frontend JS + real HTTP API; not a visual browser test.
import assert from 'node:assert/strict';
import {readFile, mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawn, spawnSync} from 'node:child_process';
import {JSDOM, VirtualConsole} from 'jsdom';

const temp=await mkdtemp(path.join(tmpdir(),'plateful-ui-'));
const port=18765;
const env={...process.env,DATABASE_URL:`sqlite:///${path.join(temp,'test.db').replaceAll('\\','/')}`,
  JWT_SECRET:'test-ui-only-secret-at-least-32-characters',ENVIRONMENT:'test',GEMINI_API_KEY:'',RATE_LIMIT_PER_MINUTE:'1000'};
const python=process.env.PYTHON||'python';
for(const args of [['-m','alembic','upgrade','head'],['-m','app.db.seed']]){
  const result=spawnSync(python,args,{cwd:'backend',env,encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
}
const api=spawn(python,['-m','uvicorn','app.main:app','--host','127.0.0.1','--port',String(port),'--no-access-log'],{cwd:'backend',env,stdio:'ignore'});
async function until(predicate,message){
  const deadline=Date.now()+15000;
  while(Date.now()<deadline){if(await predicate())return;await new Promise(r=>setTimeout(r,40))}
  throw new Error('Timeout: '+message);
}
let dom;
try{
  await until(async()=>{try{return(await fetch(`http://127.0.0.1:${port}/health`)).ok}catch{return false}},'API health');
  const errors=[];
  const vc=new VirtualConsole();vc.on('jsdomError',error=>errors.push(error.message));
  dom=new JSDOM(await readFile('frontend/index.html','utf8'),{url:'http://localhost:5500',runScripts:'outside-only',virtualConsole:vc});
  const w=dom.window,d=w.document;
  w.fetch=fetch;w.AbortController=AbortController;w.confirm=()=>true;w.print=()=>{};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true};
  w.HTMLDialogElement.prototype.close=function(){this.open=false};
  w.PLATEFUL_CONFIG={apiUrl:`http://127.0.0.1:${port}`};
  // One evaluation shares the scripts' lexical environment, as classic browser scripts do.
  w.eval((await readFile('frontend/api.js','utf8'))+'\n'+(await readFile('frontend/app.js','utf8')));
  const click=id=>d.getElementById(id).click();
  click('accountButton');
  d.getElementById('email').value='ui@example.com';d.getElementById('password').value='safe-ui-test-password';
  const register=d.querySelector('[data-mode="register"]');
  d.getElementById('authForm').dispatchEvent(new w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:register}));
  await until(()=>d.getElementById('accountButton').textContent==='Account','registration');
  await until(()=>!register.disabled,'preferences loaded');
  for(let i=0;i<5;i++)click('continueButton');
  const pantry=d.getElementById('pantry');pantry.value='rice: 500 g\nonion: 3 count';pantry.dispatchEvent(new w.Event('input'));
  click('continueButton');
  await until(()=>d.querySelectorAll('[data-swap]').length===7,'generation');
  await until(()=>d.querySelector('[data-grocery]'),'grocery load');
  assert.equal(d.getElementById('errorBanner').classList.contains('hidden'),true,d.getElementById('errorText').textContent);
  const before=d.querySelector('.meal-card h3').textContent;
  d.querySelector('[data-swap]').click();
  await until(()=>d.querySelector('.meal-card h3').textContent!==before,'swap');
  click('savePlanButton');
  await until(()=>d.getElementById('savePlanButton').textContent==='Saved ✓','save');
  click('historyButton');
  await until(()=>d.querySelector('[data-open]'),'history');
  d.querySelector('[data-open]').click();
  await until(()=>!d.getElementById('historyDialog').open,'open saved plan');
  const grocery=d.querySelector('[data-grocery]');grocery.checked=true;grocery.dispatchEvent(new w.Event('change'));
  await until(()=>!grocery.disabled,'grocery persistence');
  click('newPlanButton');
  for(let i=0;i<5;i++)click('continueButton');
  w.fetch=async()=>{throw new w.TypeError('offline')};
  click('continueButton');
  await until(()=>!d.getElementById('errorBanner').classList.contains('hidden'),'network error');
  assert.equal(d.getElementById('dashboard').classList.contains('hidden'),true,'No fake dashboard on API failure');
  assert.match(d.getElementById('errorText').textContent,/Cannot reach/);
  assert.deepEqual(errors,[]);
  console.log('UI DOM integration passed: register → preferences → generate → swap → save → history → groceries; network failure stays explicit.');
}finally{
  dom?.window.close();api.kill();await new Promise(r=>api.once('exit',r));await rm(temp,{recursive:true,force:true});
}
