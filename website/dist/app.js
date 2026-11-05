'use strict';
(() => {
  const course = window.COURSE_DATA;
  const main = document.getElementById('main');
  if (!course?.lessons?.length) {
    main.textContent = '课程数据未能加载。请刷新，或打开 GitHub 中的 START_HERE.md。';
    return;
  }
  const REPO = 'https://github.com/HeHaodong2004/Genesis_learning';
  const STORAGE = 'genesis-workshop-progress-v1';
  const labels = {read:'阅读与定位',predict:'写下预测',run:'动手运行',implement:'亲手实现',verify:'检查证据',reflect:'解释与反思'};
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const prose = value => String(value ?? '').split(/\n\s*\n/).map(p => `<p>${escape(p).replace(/`([^`]+)`/g,'<code>$1</code>')}</p>`).join('');
  const displayTitle = lesson => lesson.title.replace(/^\d+\s*[·.\-]\s*/, '');
  const sourceURL = path => `${REPO}/blob/main/${path.split('/').map(encodeURIComponent).join('/')}`;
  const key = (lesson, step) => `${lesson.id}:${step.id}`;
  const stepKeys = new Set(course.lessons.flatMap(l => l.steps.map(s => key(l,s))));
  const emptyState = () => ({version:1,completed:{},notes:{},errors:{},gates:{},last:''});
  let state = emptyState(), storageAvailable = true, selectedFile = '', toastTimer;
  function cleanState(input) {
    if (!input || input.version !== 1 || typeof input !== 'object') throw new Error('unsupported progress');
    const result = emptyState();
    for (const k of stepKeys) {
      if (input.completed?.[k] === true) result.completed[k] = true;
      if (typeof input.notes?.[k] === 'string') result.notes[k] = input.notes[k].slice(0,20000);
      if (typeof input.errors?.[k] === 'string') result.errors[k] = input.errors[k].slice(0,20000);
    }
    for (const l of course.lessons) (l.gates || []).forEach((_,i) => {
      if (input.gates?.[`${l.id}:${i}`] === true) result.gates[`${l.id}:${i}`] = true;
    });
    if (typeof input.last === 'string' && /^#\/lesson\/[a-z0-9-]+\/\d+$/.test(input.last)) result.last = input.last;
    return result;
  }
  try { const old = localStorage.getItem(STORAGE); if (old) state = cleanState(JSON.parse(old)); }
  catch (_) { storageAvailable = false; }
  function save() {
    try { localStorage.setItem(STORAGE,JSON.stringify(state)); }
    catch (_) { storageAvailable = false; document.querySelector('.local-label').textContent = '本浏览器无法保存，请导出进度'; }
  }
  function toast(text) {
    const box = document.getElementById('toast'); box.textContent=text; box.classList.add('visible');
    clearTimeout(toastTimer); toastTimer=setTimeout(()=>box.classList.remove('visible'),2800);
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast('已复制，可以粘贴使用'); }
    catch (_) {
      const area=document.createElement('textarea'); area.value=text; area.style.position='fixed'; area.style.opacity='0';
      document.body.append(area); area.select(); const ok=document.execCommand('copy'); area.remove();
      toast(ok ? '已复制，可以粘贴使用' : '浏览器不支持自动复制，请选中文本后复制');
    }
  }
  const completed = () => [...stepKeys].filter(k=>state.completed[k]).length;
  const lessonCount = lesson => lesson.steps.filter(s=>state.completed[key(lesson,s)]).length;
  const lessonLink = (lesson,index=0) => `#/lesson/${lesson.id}/${index}`;
  const nextIncomplete = lesson => Math.max(0,lesson.steps.findIndex(s=>!state.completed[key(lesson,s)]));
  function currentRoute() {
    const parts=location.hash.split('/');
    if(parts[1]==='roadmap') return {type:'roadmap'};
    const lesson=course.lessons.find(l=>l.id===parts[2]);
    if(parts[1]==='lesson' && lesson) return {type:'lesson',lesson,index:Math.max(0,Math.min(lesson.steps.length-1,Number.parseInt(parts[3],10)||0))};
    return {type:'overview'};
  }
  function footer() { return `<footer class="site-footer"><span>Genesis 研究者工坊 · 先预测，再运行，再解释。</span><a href="${REPO}/blob/main/docs/developer/VALIDATION.md" target="_blank" rel="noopener">训练包验证记录 ↗</a></footer>`; }
  function renderSidebar(route) {
    document.getElementById('sidebar').innerHTML=`
      <div class="nav-label">你的学习工作台</div>
      <a class="nav-item ${route.type==='overview'?'active':''}" href="#/overview"><span class="nav-num">⌂</span><span>课程总览<small>从这里开始 / 继续学习</small></span></a>
      <div class="rail-divider"></div><div class="nav-label">实战主线 · 按顺序完成</div>
      ${course.lessons.map((l,i)=>`<a href="${lessonLink(l,nextIncomplete(l))}" class="nav-item ${route.lesson?.id===l.id?'active':''}" ${route.lesson?.id===l.id?'aria-current="page"':''}><span class="nav-num">${String(i+1).padStart(2,'0')}</span><span>${escape(displayTitle(l))}<small>${lessonCount(l)} / ${l.steps.length} 步 · ${escape(l.minutes)} 分钟</small></span>${lessonCount(l)===l.steps.length?'<span class="nav-check">✓</span>':''}</a>`).join('')}
      <div class="rail-divider"></div><a class="nav-item ${route.type==='roadmap'?'active':''}" href="#/roadmap"><span class="nav-num">↗</span><span>接下来 12 周<small>把练习连接成研究系统</small></span></a>
      <div class="rail-bottom"><div class="progress-title"><span>自评学习进度</span><strong>${completed()} / ${stepKeys.size}</strong></div><div class="progress-track"><span style="width:${100*completed()/stepKeys.size}%"></span></div><div class="rail-tools"><button id="export">导出进度与笔记</button><button id="import">导入</button></div><p class="rail-note">${storageAvailable?'保存在当前浏览器，可导出后换设备。':'浏览器存储不可用，请在离开前导出。'}<br>网站不上传你的笔记，也不会自动调用 AI。</p></div>`;
    document.getElementById('export').onclick=exportProgress;
    document.getElementById('import').onclick=()=>document.getElementById('import-file').click();
  }
  function instrument() { return `<div class="instrument" aria-label="研究流程示意图"><div class="instrument-top"><span>EXPERIMENT LOOP / 001</span><span>从假设到证据</span></div><svg viewBox="0 0 370 155" aria-hidden="true"><defs><pattern id="grid" width="15" height="15" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".7" fill="#c4d2be"/></pattern></defs><rect width="370" height="155" fill="url(#grid)"/><path d="M50 100 C100 100 100 45 160 45 S230 110 310 70" fill="none" stroke="#9ab394" stroke-width="1.5" stroke-dasharray="5 5"/><path d="M50 105 C100 105 100 55 160 55 S230 120 310 80" fill="none" stroke="#176856" stroke-width="3"/><circle cx="50" cy="105" r="7" fill="#176856"/><circle cx="160" cy="55" r="7" fill="#f6d474" stroke="#bd9837"/><circle cx="310" cy="80" r="7" fill="#176856"/><g fill="#526e5c" font-size="11" text-anchor="middle"><text x="50" y="137">提出预测</text><text x="160" y="29">实现与运行</text><text x="310" y="113">对照验证</text></g></svg><div class="instrument-note">每一章，都留下代码、证据和你自己的解释。</div></div>`; }
  function renderOverview() {
    const resume=state.last || lessonLink(course.lessons[0]);
    main.innerHTML=`<div class="eyebrow">为研究能力，而动手构建</div><section class="hero"><div><h1>把每一次运行，<br>变成一次理解。</h1><p>从熟悉的数学与机器人问题出发，练习现代开发、Genesis 验证与学习算法。你负责预测、实现和解释；这里提供脚手架、测试与参考答案。</p><div class="hero-actions"><a class="button primary" href="${resume}">${state.last?'继续上次学习':'开始第一章'} <span>→</span></a><small>按自己的节奏，约两周完成首轮</small></div></div>${instrument()}</section>
      <div class="stats-strip"><div class="stat"><strong>${course.lessons.length}<small> 章</small></strong><span>从环境到研究交付</span></div><div class="stat"><strong>${stepKeys.size}<small> 步</small></strong><span>运行 · 实现 · 验收</span></div><div class="stat"><strong>100<small> 项</small></strong><span>训练包参考测试已通过</span></div><div class="stat"><strong>${Math.round(100*completed()/stepKeys.size)}<small> %</small></strong><span>你的自评完成度</span></div></div>
      <div class="section-heading"><h2>你的实战路径</h2><small>先尝试，再对照参考实现</small></div>
      <div class="lesson-grid">${course.lessons.map((l,i)=>`<a href="${lessonLink(l,nextIncomplete(l))}" class="lesson-card"><div class="card-top"><span class="chapter-label">CHAPTER ${String(i+1).padStart(2,'0')}</span><span class="pill">${escape(l.minutes)} 分钟</span></div><h3>${escape(displayTitle(l))}</h3><p>${escape(l.subtitle)}</p><div class="card-bottom"><span>${lessonCount(l)} / ${l.steps.length} 步已自评完成</span><b>${lessonCount(l)?'继续':'进入章节'} →</b></div></a>`).join('')}</div>
      <div class="method-strip"><div><h3>一轮有效的学习，不止于运行成功</h3><p>先写下会发生什么，再用一个新输入检验自己的解释。</p></div><div class="method-flow">预测<span>→</span>运行<span>→</span>实现<span>→</span>验证<span>→</span>解释</div></div>${footer()}`;
  }
  function sandbox() {
    return `<div class="sandbox"><h3>一分钟边界实验：这一步还要 bootstrap 吗？</h3><p>固定 r = 1，γ = 0.9，V(s) = 0，V(真正下一观测) = 10。点击边界类型，观察 δ 和 trace。</p><div class="sandbox-switches"><button class="selected" data-boundary="ongoing">正常继续</button><button data-boundary="terminated">真正终止</button><button data-boundary="truncated">时间截断</button></div><div class="sandbox-result" id="sandbox-result">δ = 1 + 0.9 × 10 − 0 = 10<br><small>允许 bootstrap；trace 可以延续。</small></div><p>这是单步定义的交互演示；完整批量实现仍需在本机通过测试。</p></div>`;
  }
  function renderLesson(lesson,index) {
    const step=lesson.steps[index], k=key(lesson,step), chapter=course.lessons.indexOf(lesson);
    state.last=lessonLink(lesson,index); save();
    selectedFile=step.file && course.files[step.file] ? step.file : '';
    main.innerHTML=`<div class="breadcrumb"><a href="#/overview">学习工作台</a><span>/</span><span>第 ${String(chapter+1).padStart(2,'0')} 章</span></div><div class="lesson-heading"><div><div class="eyebrow">${escape(lesson.subtitle)}</div><h1>${escape(displayTitle(lesson))}</h1><p>${escape(lesson.question)}</p></div><div class="heading-actions"><a class="button subtle small" href="${sourceURL(lesson.docPath)}" target="_blank" rel="noopener">完整讲义 ↗</a><span class="pill">${escape(lesson.minutes)} 分钟 · ${index+1}/${lesson.steps.length} 步</span></div></div>
      <nav class="step-nav" aria-label="本章步骤">${lesson.steps.map((s,i)=>`<button data-step="${i}" class="${i===index?'active':''} ${state.completed[key(lesson,s)]?'completed':''}" ${i===index?'aria-current="step"':''}><span class="step-dot">${state.completed[key(lesson,s)]?'✓':i+1}</span>${escape(labels[s.kind]||s.kind)}</button>`).join('')}</nav>
      <div class="workspace-grid"><div><article class="panel"><div class="step-content"><div class="step-kicker">STEP ${String(index+1).padStart(2,'0')} / ${escape(labels[step.kind]||'实战')}</div><h2>${escape(step.title)}</h2><div class="prose">${prose(step.body)}</div>
      ${step.command?`<div class="terminal"><div class="terminal-head"><span><i></i>在你的工作站终端运行</span><button class="copy-dark" id="copy-command">复制命令</button></div><pre id="command-text">${escape(step.command)}</pre></div><p class="terminal-note">每条命令从克隆的 Genesis_learning 根目录运行；网站不会执行本机代码。</p>`:''}
      ${lesson.id==='gae'?sandbox():''}
      <div class="expected"><h3>◇ 这一步怎样算完成</h3><p>${escape(step.expected)}</p></div></div><div class="step-footer"><button class="button small" id="previous" ${chapter===0&&index===0?'disabled':''}>← 上一步</button><small>${state.completed[k]?'已自评完成；可以取消后重做':'运行后，再用自己的话解释结果'}</small><div class="footer-right"><button id="complete" class="button small ${state.completed[k]?'done':''}">${state.completed[k]?'✓ 已完成':'标记完成'}</button><button id="next" class="button primary small">${index===lesson.steps.length-1?'下一章':'下一步'} →</button></div></div></article>
      <section class="panel source-panel" aria-label="本步源码"><div class="source-head"><h3>源码阅读台</h3><a id="source-link" target="_blank" rel="noopener">在 GitHub 查看 ↗</a></div><div class="source-selector"><label for="source-select" class="muted" style="font-size:10px">选择需要理解的文件（参考答案标注为 solution）</label><select id="source-select"><option value="">选择源码文件…</option>${Object.keys(course.files).map(path=>`<option value="${escape(path)}" ${path===selectedFile?'selected':''}>${escape(path)}</option>`).join('')}</select></div><pre class="source-code" id="source-code"></pre><div class="source-tip">先读 starter 中的关键函数。选中一段代码，再点右侧“复制问题与代码”，可以只询问这一段。</div></section>
      <section class="panel notes"><h3>我的预测与解释</h3><textarea id="notes" aria-label="我的预测与解释" placeholder="运行前：我预计会……，因为……\n运行后：实际结果是……，我的解释需要修正为……">${escape(state.notes[k]||'')}</textarea><small>输入即保存在本浏览器；可以在左下角导出。给 AI 的问题不会自动包含这份笔记。</small></section></div>
      <aside class="workspace-side" aria-label="学习辅助"><section class="side-card tint"><h3>卡住时，把问题问具体</h3><p>把目标、相关代码和实际输出一起交给其他 AI，请它先解释机制或给一个提示。</p><label for="error-notes">你的问题 / 终端报错（可选）</label><textarea id="error-notes" placeholder="粘贴报错，或写下具体哪一行不理解……">${escape(state.errors[k]||'')}</textarea><button class="button primary" id="copy-prompt">复制问题与代码 ↗</button><p class="small-note">复制后手动粘贴给你选择的 AI。这里不调用模型、不发送代码。</p></section>
      <section class="side-card"><h3>本章理解检查</h3><ul class="gates">${(lesson.gates||[]).map((g,i)=>`<li><input type="checkbox" id="gate-${i}" data-gate="${i}" ${state.gates[`${lesson.id}:${i}`]?'checked':''}><label for="gate-${i}">${escape(g)}</label></li>`).join('')}</ul><p class="small-note">勾选代表你的自评，不代表自动通过算法验收。</p></section><section class="side-card"><h3>开始前需要</h3><p>${(lesson.prerequisites||[]).map(escape).join('<br>')}</p><a href="${sourceURL(lesson.docPath)}" target="_blank" rel="noopener" style="font-size:11px">打开对应完整中文教程 →</a></section></aside></div>${footer()}`;
    main.querySelectorAll('[data-step]').forEach(button=>button.onclick=()=>{location.hash=lessonLink(lesson,Number(button.dataset.step));});
    if(step.command) document.getElementById('copy-command').onclick=()=>copy(step.command);
    document.getElementById('previous').onclick=()=>{location.hash=index>0?lessonLink(lesson,index-1):lessonLink(course.lessons[chapter-1],course.lessons[chapter-1].steps.length-1);};
    document.getElementById('next').onclick=()=>{location.hash=index<lesson.steps.length-1?lessonLink(lesson,index+1):chapter<course.lessons.length-1?lessonLink(course.lessons[chapter+1]):'#/roadmap';};
    document.getElementById('complete').onclick=()=>{state.completed[k]=!state.completed[k];save();render(false);toast(state.completed[k]?'本步自评进度已记录':'已取消完成标记');};
    document.getElementById('notes').oninput=e=>{state.notes[k]=e.target.value;save();};
    document.getElementById('error-notes').oninput=e=>{state.errors[k]=e.target.value;save();};
    main.querySelectorAll('[data-gate]').forEach(box=>box.onchange=()=>{state.gates[`${lesson.id}:${box.dataset.gate}`]=box.checked;save();});
    document.getElementById('source-select').onchange=e=>{selectedFile=e.target.value;renderSource();};
    document.getElementById('copy-prompt').onclick=()=>{
      const selection=window.getSelection();
      const codeElement=document.getElementById('source-code');
      const selected=selection && codeElement.contains(selection.anchorNode) && codeElement.contains(selection.focusNode)?selection.toString():'';
      const code=selected || (course.files[selectedFile]||'');
      const text=`我正在学习 Genesis 现代机器人研究训练包。\n章节：${lesson.title}\n当前步骤：${step.title}\n目标：${step.body}\n验收：${step.expected}\n\n${step.prompt||'请解释这一部分的机制，并给我一个能检验理解的小问题。'}\n\n相关文件：${selectedFile||'本步没有指定源码'}\n仓库：${REPO}\n${step.command?'运行命令：\n'+step.command+'\n':''}\n我的问题或实际输出：\n${state.errors[k]||'请先问我对代码的预测，再逐步引导。'}\n\n${code?'相关代码'+(selected?'（我选中的片段）':'')+'：\n```python\n'+code.slice(0,18000)+(code.length>18000?'\n# 片段过长已截断，完整代码见仓库。':'')+'\n```\n':''}\n请用中文解释，把数学假设、张量/数据形状和可观察结果联系起来。先给一个提示，不要直接替我完成整个 starter，不要编造已运行的结果。`;
      copy(text);
    };
    main.querySelectorAll('[data-boundary]').forEach(button=>button.onclick=()=>{
      main.querySelectorAll('[data-boundary]').forEach(b=>b.classList.toggle('selected',b===button));
      const mode=button.dataset.boundary;
      document.getElementById('sandbox-result').innerHTML=mode==='terminated'?'δ = 1 + 0 − 0 = 1<br><small>不做 bootstrap；trace 在此结束。</small>':mode==='truncated'?'δ = 1 + 0.9 × 10 − 0 = 10<br><small>保留 bootstrap；trace 在此结束，不能串入 reset 后的新回合。</small>':'δ = 1 + 0.9 × 10 − 0 = 10<br><small>允许 bootstrap；trace 可以延续。</small>';
    });
    renderSource();
  }
  function renderSource() {
    const pre=document.getElementById('source-code'), link=document.getElementById('source-link');
    pre.textContent=course.files[selectedFile] || '本步先完成思考或运行任务；你也可以从上方选择一个文件阅读。';
    if(selectedFile){link.href=sourceURL(selectedFile);link.hidden=false;}else{link.removeAttribute('href');link.hidden=true;}
  }
  function renderRoadmap() {
    main.innerHTML=`<div class="eyebrow">从练习到独立研究</div><h1>接下来，把能力接起来。</h1><p class="muted" style="margin-top:14px;max-width:720px;font-size:14px">首轮练习建立定义、边界与验证习惯。下面是后续 12 周的项目路线：保留数学参考，逐步加入真实仿真、学习和闭环评价。</p><div class="callout">这里是后续项目任务，不是已实现的完整 PPO、world model 或真机系统。每阶段都要产出能被别人复现的证据。</div><div class="roadmap-list">${(course.roadmap||[]).map((r,i)=>`<article class="roadmap-card"><span class="number">${i+1}</span><div><h3>${escape(r.title)}</h3><p>${escape(r.body)}</p><div class="deliverable">交付物 · ${escape(r.deliverable)}</div></div></article>`).join('')}</div><div class="hero-actions"><a class="button primary" href="${sourceURL('docs/developer/learning-path.md')}" target="_blank" rel="noopener">阅读完整 12 周与三年路线 ↗</a><a class="button" href="${sourceURL('docs/developer/templates/experiment.md')}" target="_blank" rel="noopener">使用实验卡模板 ↗</a></div>${footer()}`;
  }
  function render(scroll=true) {
    const route=currentRoute(); renderSidebar(route);
    if(route.type==='lesson') renderLesson(route.lesson,route.index);
    else if(route.type==='roadmap') renderRoadmap(); else renderOverview();
    document.title=route.lesson?`${route.lesson.title} · Genesis 研究者工坊`:'Genesis 研究者工坊 · 逐步实战';
    document.body.classList.remove('menu-open');document.getElementById('menu').setAttribute('aria-expanded','false');
    if(scroll) window.scrollTo({top:0,behavior:'instant'});
  }
  function exportProgress() {
    const data={...state,exportedAt:new Date().toISOString(),course:'genesis-research-workshop'};
    const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='genesis-learning-progress.json';link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);toast('进度和笔记已导出');
  }
  document.getElementById('import-file').onchange=async event=>{
    const file=event.target.files[0]; if(!file) return;
    try {
      if(file.size>2000000) throw new Error('too large');
      const incoming=cleanState(JSON.parse(await file.text()));
      // Merge known step records, retaining this browser's unrelated notes.
      state={...state,completed:{...state.completed,...incoming.completed},notes:{...state.notes,...incoming.notes},errors:{...state.errors,...incoming.errors},gates:{...state.gates,...incoming.gates},last:incoming.last||state.last};
      save();render(false);toast('进度已合并，原有笔记保留；同一步以导入内容为准');
    } catch (_) {toast('无法导入：请选择本工坊导出的有效进度 JSON（不超过 2 MB）');}
    event.target.value='';
  };
  document.getElementById('menu').onclick=()=>{
    const open=document.body.classList.toggle('menu-open');document.getElementById('menu').setAttribute('aria-expanded',String(open));
  };
  window.addEventListener('hashchange',()=>render());
  render(false);
})();
