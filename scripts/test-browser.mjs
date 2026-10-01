// Optional real Chromium verification. Set CHROME_PATH or install Chromium via playwright-core.
import assert from 'node:assert/strict';
import {mkdtemp,rm,mkdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawn,spawnSync} from 'node:child_process';
import {chromium} from 'playwright-core';
const temp=await mkdtemp(path.join(tmpdir(),'plateful-browser-'));
const python=process.env.PYTHON||'python';
const env={...process.env,DATABASE_URL:`sqlite:///${path.join(temp,'test.db').replaceAll('\\','/')}`,
  JWT_SECRET:'test-browser-secret-32-characters-long',ENVIRONMENT:'test',GEMINI_API_KEY:'',RATE_LIMIT_PER_MINUTE:'1000'};
for(const args of [['-m','alembic','upgrade','head'],['-m','app.db.seed']]){
 const r=spawnSync(python,args,{cwd:'backend',env,encoding:'utf8'});assert.equal(r.status,0,r.stderr);
}
const api=spawn(python,['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--no-access-log'],{cwd:'backend',env,stdio:'ignore'});
const web=spawn(python,['-m','http.server','5500','--bind','127.0.0.1','--directory','frontend'],{stdio:'ignore'});
let browser;
try{
 for(const url of ['http://127.0.0.1:8000/health','http://127.0.0.1:5500']){
  let ok=false;for(let i=0;i<100;i++){try{ok=(await fetch(url)).ok}catch{}if(ok)break;await new Promise(r=>setTimeout(r,50))}assert.ok(ok,'server ready');
 }
 browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',msg=>{if(msg.type()==='error')errors.push(msg.text())});
 await page.goto('http://localhost:5500');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByLabel('Email',{exact:true}).fill('browser@example.com');
 await page.getByLabel('Password (12–128 characters)').fill('browser-test-password');
 await page.getByRole('button',{name:'Create account',exact:true}).click();
 await page.waitForFunction(()=>!document.getElementById('authDialog').open);
 for(let i=0;i<5;i++)await page.getByRole('button',{name:'Continue →',exact:true}).click();
 await page.getByLabel('Ingredients you already have').fill('rice: 500 g\nonion: 3 count');
 await page.getByRole('button',{name:'Generate my plan →',exact:true}).click();
 await page.locator('.meal-card').first().waitFor();
 assert.equal(await page.locator('.meal-card').count(),7);
 const before=await page.locator('.meal-card h3').first().textContent();
 await page.getByRole('button',{name:'Swap meal ↻'}).first().click();
 await page.waitForFunction(old=>document.querySelector('.meal-card h3').textContent!==old,before);
 await page.getByRole('button',{name:'Save plan',exact:true}).click();
 await page.getByRole('button',{name:'Saved ✓'}).waitFor();
 await page.getByRole('button',{name:'History',exact:true}).click();
 await page.getByRole('button',{name:'Open',exact:true}).click();
 await page.waitForFunction(()=>!document.getElementById('historyDialog').open);
 await mkdir('test-results',{recursive:true});
 await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0));
 await page.screenshot({path:'test-results/desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'test-results/mobile.png',fullPage:true});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'No mobile horizontal overflow');
 await page.getByRole('button',{name:'Grocery list',exact:true}).click();
 await page.locator('[data-grocery]').first().check();
 await page.getByRole('button',{name:'Account',exact:true}).click();
 await page.getByRole('button',{name:'Sign out on all devices'}).click();
 await page.waitForFunction(()=>document.getElementById('accountButton').textContent==='Sign in');
 assert.deepEqual(errors,[]);
 console.log('Chromium: registration, generation, swap, save, history, groceries, logout, desktop/mobile, no JS page errors: passed');
}finally{
 await browser?.close();api.kill();web.kill();await new Promise(r=>setTimeout(r,100));await rm(temp,{recursive:true,force:true});
}
