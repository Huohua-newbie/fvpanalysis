#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 dependency.json 打包为自包含的交互式 HTML 依赖图浏览器。

特性：
- 中心节点 + 可调 BFS 展开深度（callers / callees / both）
- 分层环形（radial）布局，层内垂直居中，避免节点重叠
- pan / zoom，刻度自适应
- 下拉搜索（全部 5456 函数 + 130 syscall）
- 节点/边视觉分层、状态与动效
"""
import json

d = json.load(open('dependency.json', encoding='utf-8'))
nodes_funcs = d['nodes']['functions']
nodes_sys = d['nodes']['syscalls']
leaf_sel = set(d['nodes']['leaf_functions'])
edges = d['edges']
stats = d['stats']

out_map = {}
in_map = {}
for e in edges:
    s, t = e['src'], e['dst']
    out_map.setdefault(s, []).append(t)
    in_map.setdefault(t, []).append(s)

# 按入/出度排序，方便"热门"列表
deg = {}
for e in edges:
    deg[e['src']] = deg.get(e['src'], 0) + 1
    deg[e['dst']] = deg.get(e['dst'], 0) + 1

DATA = {
    'funcs': nodes_funcs,
    'sys': nodes_sys,
    'leaf': list(leaf_sel),
    'out': out_map,
    'in': in_map,
    'deg': deg,
    'stats': stats,
}

html = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FVP Sakura.lua · 函数依赖图</title>
<style>
  :root{
    --bg:#0b0f17; --bg-e:#0e1420; --panel:#111826; --panel-2:#162032;
    --line:#1f2a3d; --line-2:#2a3850; --fg:#dfe7f4; --dim:#7f8ea8;
    --accent:#6ea8ff; --accent-2:#88b6ff; --sys:#ffab5e; --leaf:#7ee0a0;
    --link:#6b7fae; --link-sys:#c98a45;
    --r:10px; --r-sm:6px;
    --shadow-1:0 1px 2px rgba(0,0,0,.35), 0 1px 1px rgba(0,0,0,.25);
    --shadow-2:0 8px 24px rgba(0,0,0,.35), 0 2px 6px rgba(0,0,0,.30);
    --shadow-pop:0 16px 40px rgba(0,0,0,.5), 0 4px 12px rgba(0,0,0,.35);
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{margin:0;background:var(--bg);color:var(--fg);
    font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
    font-size:14px;height:100vh;overflow:hidden;-webkit-font-smoothing:antialiased}
  .app{display:flex;flex-direction:column;height:100vh}

  /* ---------- Header ---------- */
  header{display:flex;align-items:center;gap:18px;padding:0 20px;height:56px;
    background:linear-gradient(180deg,#101724,#0e151f);border-bottom:1px solid var(--line);flex-shrink:0}
  .brand{display:flex;flex-direction:column;line-height:1.15;min-width:230px}
  .brand h1{font-size:14px;font-weight:600;letter-spacing:.2px;margin:0;color:#fff}
  .brand .sub{font-size:11px;color:var(--dim);font-family:'SFMono-Regular',Consolas,monospace;letter-spacing:.3px}
  .stats{display:flex;gap:22px;flex-wrap:wrap}
  .stat{display:flex;flex-direction:column;line-height:1.1;padding-left:16px;border-left:1px solid var(--line)}
  .stat .k{font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:.6px}
  .stat .v{font-size:15px;font-weight:600;color:#fff;font-family:Consolas,monospace}
  .stat .v small{font-size:11px;color:var(--dim);font-weight:400;margin-left:2px}
  .legend{margin-left:auto;display:flex;gap:16px;align-items:center}
  .lg{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--dim)}
  .dotp{width:12px;height:12px;border-radius:3px;flex-shrink:0}
  .dotp.func{background:#223054;border:1px solid #3a4d75}
  .dotp.leaf{background:#173624;border:1px solid #2f7d4d}
  .dotp.sys{background:#3a2a1a;border:1px solid #c98a45}

  /* ---------- Toolbar ---------- */
  .toolbar{display:flex;align-items:center;gap:10px;padding:9px 20px;
    background:var(--panel);border-bottom:1px solid var(--line);flex-shrink:0;flex-wrap:wrap}
  .search{position:relative;flex:1;min-width:220px;max-width:460px}
  .search .icn{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--dim);pointer-events:none}
  .search input{width:100%;padding:8px 12px 8px 36px;border-radius:var(--r-sm);border:1px solid var(--line);
    background:var(--panel-2);color:var(--fg);font-size:13px;outline:none;transition:border-color .15s, box-shadow .15s}
  .search input::placeholder{color:#5c6b87}
  .search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(110,168,255,.14)}
  .ctrl{display:flex;align-items:center;gap:7px;padding:8px 12px;border-radius:var(--r-sm);
    border:1px solid var(--line);background:var(--panel-2);color:var(--dim);font-size:13px}
  .ctrl label{color:var(--dim);font-size:12px}
  .ctrl select{border:none;background:transparent;color:var(--fg);font-size:13px;outline:none;cursor:pointer}
  .ctrl select option{background:var(--panel-2);color:var(--fg)}
  .seg{display:flex;border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
  .seg button{border:none;background:var(--panel-2);color:var(--dim);padding:8px 12px;font-size:12px;cursor:pointer;
    border-right:1px solid var(--line);transition:background .15s,color .15s}
  .seg button:last-child{border-right:none}
  .seg button.on{background:#1d2b45;color:#cfe0ff;font-weight:500}
  .seg button:hover:not(.on){color:var(--fg)}
  .range{width:110px;accent-color:var(--accent);cursor:pointer}
  .dlabel{font-size:12px;color:var(--dim);min-width:34px;text-align:center;font-family:Consolas,monospace}
  .btn{display:inline-flex;align-items:center;gap:6px;padding:8px 13px;border-radius:var(--r-sm);
    border:1px solid var(--line);background:var(--panel-2);color:var(--fg);cursor:pointer;font-size:12.5px;
    transition:border-color .15s,background .15s}
  .btn:hover{border-color:var(--accent)}
  .btn.primary{border-color:var(--accent);background:#1d2b45;color:#cfe0ff}

  /* ---------- Main ---------- */
  main{flex:1;display:grid;grid-template-columns:250px 1fr;min-height:0}
  aside{background:var(--panel);border-right:1px solid var(--line);overflow-y:auto;padding:14px 12px}
  aside h3{font-size:10.5px;color:var(--dim);text-transform:uppercase;letter-spacing:.7px;margin:18px 6px 8px;font-weight:600}
  aside h3:first-child{margin-top:0}
  .node-list{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:2px}
  .node-list li{display:flex;align-items:center;gap:7px;padding:5px 8px;border-radius:var(--r-sm);cursor:pointer;
    font-family:Consolas,monospace;font-size:12px;transition:background .12s}
  .node-list li:hover{background:var(--panel-2)}
  .node-list li.sel{background:#1d2b45;color:#cfe0ff}
  .node-list li .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .node-list li .ct{color:var(--dim);font-size:10.5px}
  .node-list li .tag{width:6px;height:6px;border-radius:50%;flex-shrink:0}
  .tag.func{background:#3a4d75}.tag.leaf{background:#2f7d4d}.tag.sys{background:#c98a45}
  .aside-hint{font-size:11px;color:#5c6b87;line-height:1.45;margin:6px;padding:0 4px}

  /* ---------- Canvas ---------- */
  .canvas-wrap{position:relative;overflow:hidden;background:
    radial-gradient(1200px 600px at 30% 20%, #101b2e, transparent 60%),
    radial-gradient(900px 500px at 80% 90%, #0f1a29, transparent 60%),
    var(--bg)}
  #svg{width:100%;height:100%;display:block;cursor:grab}
  #svg:active{cursor:grabbing}
  .graph-layer{will-change:transform}
  canvas{position:absolute;inset:0;width:100%;height:100%}

  svg .edge{fill:none;stroke:var(--link);stroke-width:1.3;opacity:.5;
    transition:opacity .15s,stroke .15s}
  svg .edge.sys{stroke:var(--link-sys)}
  svg .edge.hot{stroke:var(--accent);opacity:.9;stroke-width:1.8}
  svg .node{cursor:pointer}
  svg .n.func rect{fill:#223054;stroke:#3a4d75}
  svg .n.leaf rect,svg .n.leaf ellipse{fill:#173624;stroke:#2f7d4d}
  svg .n.sys ellipse{fill:#3a2a1a;stroke:#c98a45}
  svg .n.center rect,svg .n.center rect,svg .n.center ellipse{
    stroke:var(--accent);stroke-width:2;filter:drop-shadow(0 0 6px rgba(110,168,255,.45))}
  svg .n text{fill:var(--fg);font-family:Consolas,monospace;font-size:11px;pointer-events:none}
  svg .n.sys text{fill:#ffd2a3}
  svg .n.leaf text{fill:#b8ecc8}
  svg .n:hover rect,svg .n:hover ellipse{stroke:var(--accent)}
  .zoombar{position:absolute;left:14px;bottom:14px;display:flex;flex-direction:column;gap:6px;
    background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:6px;box-shadow:var(--shadow-2)}
  .zoombar button{width:34px;height:34px;border:none;background:transparent;color:var(--dim);cursor:pointer;
    border-radius:var(--r-sm);font-size:16px;line-height:1;transition:background .15s,color .15s}
  .zoombar button:hover{background:var(--panel-2);color:var(--fg)}
  .cursor-hint{position:absolute;left:14px;top:14px;font-size:11px;color:#6c7d99;background:var(--panel);
    border:1px solid var(--line);border-radius:var(--r-sm);padding:5px 9px;box-shadow:var(--shadow-1);opacity:.85}
  .cursor-hint b{color:var(--fg);font-weight:500}

  /* ---------- Detail panel ---------- */
  #detail{position:absolute;right:16px;top:16px;width:300px;max-height:78vh;overflow-y:auto;
    background:var(--panel);border:1px solid var(--line-2);border-radius:var(--r);
    box-shadow:var(--shadow-pop);padding:15px 16px;display:none;backdrop-filter:blur(8px)}
  #detail h2{font-size:13px;margin:0 0 3px;color:#fff;font-family:Consolas,monospace;display:flex;align-items:center;gap:8px}
  #detail .sub{font-size:11px;color:var(--dim);margin-bottom:11px}
  #detail .rows{display:flex;flex-direction:column;gap:5px;margin-bottom:10px}
  #detail .row{display:flex;justify-content:space-between;font-size:12px}
  #detail .row .k{color:var(--dim)}
  #detail .row .v{color:var(--fg);font-family:Consolas,monospace}
  #detail .sec{margin-top:12px;padding-top:10px;border-top:1px solid var(--line)}
  #detail .sec .t{font-size:10.5px;color:var(--dim);text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}
  #detail .set-center{width:100%;margin-top:10px}
  .chip{display:inline-block;padding:2px 8px;border-radius:99px;border:1px solid var(--line);
    border-radius:6px;margin:2px 3px 2px 0;font-family:Consolas,monospace;font-size:11px;cursor:pointer;
    transition:border-color .12s,color .12s}
  .chip:hover{border-color:var(--accent)}
  .chip.sys{border-color:#513b25;color:#ffab5e}
  .chip.func{border-color:#34456a;color:#9db8e8}
  .chip.leaf{border-color:#2f7d4d;color:#7ee0a0}
  .chip.more{border-style:dashed;color:var(--dim)}
  .empty-hint{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:#6c7d99}
  .empty-hint .big{font-size:34px;margin-bottom:10px}
  .empty-hint p{font-size:13px;max-width:420px;line-height:1.6;color:#7f8ea8}
  .empty-hint .keys{font-family:Consolas,monospace;font-size:12px;color:#a9b8d4;background:var(--panel);
    border:1px solid var(--line);border-radius:var(--r-sm);padding:10px 14px;display:inline-block;margin-top:8px;text-align:left}

  footer{flex-shrink:0;display:flex;justify-content:space-between;align-items:center;padding:5px 20px;
    border-top:1px solid var(--line);background:var(--panel);font-size:11px;color:#5c6b87}
  footer .kbd{background:var(--panel-2);border:1px solid var(--line);border-radius:4px;padding:1px 5px;font-family:Consolas,monospace;color:var(--dim)}
  footer a{color:#6c7d99;text-decoration:none}
  footer a:hover{color:var(--fg)}

  @media(max-width:860px){
    .stats{display:none}
    .legend{margin-left:0}
    main{grid-template-columns:1fr}
    aside{display:none}
  }
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand">
      <h1>FVP 函数依赖图</h1>
      <span class="sub">Sakura_hcb_ir / Sakura.lua</span>
    </div>
    <div class="stats" id="stats"></div>
    <div class="legend">
      <span class="lg"><span class="dotp func"></span>函数</span>
      <span class="lg"><span class="dotp leaf"></span>叶子函数</span>
      <span class="lg"><span class="dotp sys"></span>syscall</span>
    </div>
  </header>

  <div class="toolbar">
    <div class="search">
      <span class="icn">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
      </span>
      <input id="search" placeholder="搜索函数 / syscall，回车定位…" autocomplete="off" list="sug">
      <datalist id="sug"></datalist>
    </div>

    <div class="seg" id="dirSeg">
      <button data-dir="both" class="on">双向</button>
      <button data-dir="out">被调用</button>
      <button data-dir="in">调用者</button>
    </div>

    <div class="ctrl">
      <label>深度</label>
      <input type="range" id="depth" class="range" min="1" max="5" value="2">
      <span class="dlabel" id="depthVal">2</span>
    </div>

    <button class="btn" id="btn-reset">重置视图</button>
  </div>

  <main>
    <aside>
      <h3>Top 交点</h3>
      <ul class="node-list" id="hot"></ul>
      <h3>Top Syscall</h3>
      <ul class="node-list" id="top-sys"></ul>
      <div class="aside-hint">点击任一项改为图中心；拖动深度滑块或切换方向可扩展层级。</div>
    </aside>

    <div class="canvas-wrap" id="wrap">
      <div class="cursor-hint" id="cursorHint"></div>
      <div class="empty-hint" id="empty">
        <div class="big">☘️</div>
        <p>点击左侧列表、在搜索框输入函数名，或任选一个节点开始浏览依赖图。</p>
        <div class="keys">滚轮 缩放 · 拖拽 平移<br>点击节点 设为新中心 · 深度滑块 多层展开</div>
      </div>
      <svg id="svg"></svg>
      <div id="detail"></div>
      <div class="zoombar">
        <button id="z-in" title="放大">＋</button>
        <button id="z-out" title="缩小">−</button>
        <button id="z-fit" title="适配">⌖</button>
      </div>
    </div>
  </main>

  <footer>
    <span>syscall 为叶子节点，不展开脚本侧依赖。节点边表示调用关系，箭头指向被调用方。</span>
    <span><span class="kbd">0/⌘0</span> 适配 · <span class="kbd">+/-</span> 缩放 · <span class="kbd">拖拽</span> 平移</span>
  </footer>
</div>

<script>
const DATA = __DATA__;
const $ = s => document.querySelector(s);
const isSys = n => n.startsWith('syscall:');
const label = n => isSys(n) ? n.slice(8) : n;
const out = DATA.out, inp = DATA.in, deg = DATA.deg;
const funcs = DATA.funcs, sysL = DATA.sys, leafSet = new Set(DATA.leaf);

/* ---------- 状态 ---------- */
let center = null;
let dir = 'both';           // both | out(被调用) | in(调用者)
let depth = 2;
let scale = 1, tx = 0, ty = 0;
let nodeset = new Set();    // 当前展示的节点
let edgeset = [];           // [[src,dst,isSysEdge]]

/* ---------- 热门列表 ---------- */
function nodeClass(n){ return isSys(n) ? 'sys' : (leafSet.has(n) ? 'leaf' : 'func'); }
const hot = Object.entries(deg).filter(([k])=>!isSys(k)).sort((a,b)=>b[1]-a[1]).slice(0,15);
const topSys = Object.entries(deg).filter(([k])=>isSys(k)).sort((a,b)=>b[1]-a[1]).slice(0,12);
function renderList(sel, arr){
  const el = $(sel);
  el.innerHTML = arr.map(([n,v])=>`<li data-n="${n}"><span class="tag ${nodeClass(n)}"></span><span class="nm">${label(n)}</span><span class="ct">${v}</span></li>`).join('');
}
renderList('#hot', hot);
renderList('#top-sys', topSys);

/* ---------- BFS 抽取子图 ---------- */
function bfsSub(start, dir, depth){
  const vset = new Set([start]);
  if(dir==='in'||dir==='both'){
    let level=[start], d=0;
    while(d<depth && level.length){
      d++; const next=[];
      for(const n of level) for(const t of (inp[n]||[])){
        if(!vset.has(t)){ vset.add(t); next.push(t); }
      }
      level=next;
    }
  }
  if(dir==='out'||dir==='both'){
    let level=[start], d=0;
    while(d<depth && level.length){
      d++; const next=[];
      for(const n of level) for(const t of (out[n]||[])){
        if(!vset.has(t)){ vset.add(t); next.push(t); }
      }
      level=next;
    }
  }
  // 边：两端都在 vset 内的调用边（caller -> callee），用于显示调用关系
  const es=[];
  for(const s of vset){
    for(const t of (out[s]||[])) if(vset.has(t)) es.push([s,t,isSys(t)]);
  }
  return {vset, es};
}

/* ---------- 分层布局 ---------- */
function fullLayout(start, vset, es){
  // 计算左右各层节点（只取 vset 内的）
  const layers={out:{}, in:{}};
  // out 层
  let level=[start], seed=new Set([start]), d=0;
  while(d<depth){ d++; const nxt=[], arr=[];
    for(const n of level){
      for(const tmp of (out[n]||[])){
        if(vset.has(tmp) && !seed.has(tmp)){ seed.add(tmp); arr.push(tmp); nxt.push(tmp); }
      }
    }
    if(arr.length) layers.out[d]=arr;
    level=nxt;
  }
  // in 层
  level=[start]; seed=new Set([start]); d=0;
  while(d<depth){ d++; const nxt=[], arr=[];
    for(const n of level){
      for(const tmp of (inp[n]||[])){
        if(vset.has(tmp) && !seed.has(tmp)){ seed.add(tmp); arr.push(tmp); nxt.push(tmp); }
      }
    }
    if(arr.length) layers.in[d]=arr;
    level=nxt;
  }
  return layers;
}

/* ---------- SVG 渲染 ---------- */
const SVGNS='http://www.w3.org/2000/svg';
let W=0,H=0;
function nodeDim(n){
  const l=label(n).length;
  const w=Math.min(170, Math.max(52, l*6.6+24));
  return {w, h:24};
}
function draw(){
  const svg=$('#svg');
  const wrap=$('#wrap');
  W=wrap.clientWidth; H=wrap.clientHeight;
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  if(!center){
    $('#empty').style.display='block'; svg.innerHTML=''; $('#cursorHint').innerHTML=''; return;
  }
  $('#empty').style.display='none';

  const {vset,es}=bfsSub(center,dir,depth);
  nodeset=vset; edgeset=es;
  const layers=fullLayout(center,vset,es);

  // 布局坐标
  const pos={};
  const cx=W/2, cy=H/2;
  const colW=185;
  const nodeGapX = colW;
  // 每侧各层垂直居中排布
  function placeSide(side, sign){
    const Ls=layers[side];
    Object.keys(Ls).forEach(k=>{
      const d=parseInt(k), list=Ls[k];
      const colCount=Math.max(1,list.length);
      const rowGap=Math.max(16, Math.min(30, Math.round(520/colCount)));
      const startY=cy-((list.length-1)*rowGap)/2;
      const x=cx + sign*d*nodeGapX;
      list.forEach((n,i)=>{ pos[n]={x, y:startY+i*rowGap, depth:d, side}; });
    });
  }
  placeSide('out', 1);
  placeSide('in', -1);
  pos[center]={x:cx,y:cy,depth:0,side:'center'};

  // 渲染边
  let edgeB='';
  es.forEach(([s,t,isS])=>{
    if(!pos[s]||!pos[t]) return;
    const a=pos[s], b=pos[t];
    const x1=a.x,y1=a.y,x2=b.x,y2=b.y;
    const dx=(x2-x1), dy=(y2-y1);
    const mx=(x1+x2)/2, my=(y1+y2)/2;
    // 贝塞尔
    const curve=`M ${x1} ${y1} C ${x1+ (x2>x1?60:-60)} ${y1}, ${x2- (x2>x1?60:-60)} ${y2}, ${x2} ${y2}`;
    const hot=(s===center||t===center);
    edgeB+=`<path class="edge ${isS?'sys':''} ${hot?'hot':''}" d="${curve}"/>`;
  });

  // 渲染节点
  let nodeB='';
  const inNew=(n)=>pos[n];
  Object.keys(pos).forEach(n=>{
    const p=pos[n]; if(!p) return;
    const {w,h}=nodeDim(n);
    const cls=nodeClass(n);
    const isCenter=(n===center);
    const cx2=p.x, cy2=p.y;
    if(cls==='sys'){
      nodeB+=`<g class="node n sys ${isCenter?'center':''}" transform="translate(${cx2},${cy2})" data-n="${n}">
        <ellipse rx="${w/2}" ry="14" class="body"><title>${label(n)}</title></ellipse>
        <text text-anchor="middle" y="4">${label(n)}</text></g>`;
    } else if(cls==='leaf'){
      nodeB+=`<g class="node n leaf ${isCenter?'center':''}" transform="translate(${cx2},${cy2})" data-n="${n}">
        <ellipse rx="${w/2}" ry="14" class="body"><title>${label(n)}</title></ellipse>
        <text text-anchor="middle" y="4">${label(n)}</text></g>`;
    } else {
      nodeB+=`<g class="node n func ${isCenter?'center':''}" transform="translate(${cx2},${cy2})" data-n="${n}">
        <rect x="${-w/2}" y="-13" width="${w}" height="26" rx="7" class="body"><title>${label(n)}</title></rect>
        <text text-anchor="middle" y="4">${label(n)}</text></g>`;
    }
  });

  svg.innerHTML=`
    <defs>
      <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" fill="#7d92be"/>
      </marker>
    </defs>
    <g class="graph-layer" transform="translate(${tx},${ty}) scale(${scale})">
      ${edgeB}
      ${nodeB}
    </g>`;
  // 绑定 marker 到边
  svg.querySelectorAll('.edge').forEach(e=>e.setAttribute('marker-end','url(#arrow)'));
  // 自动适配：让子图尽量完整进入视口
  autoFit(pos, center);
  applyTransform();
  showDetail(center);
  $('#cursorHint').innerHTML=`中心 <b>${label(center)}</b> · 深度 ${depth} · ${vset.size} 节点 / ${es.length} 边`;
  hlList(center);
}

/* ---------- 自动适配视口 ---------- */
function autoFit(pos, centerNode){
  if(!pos || Object.keys(pos).length===0) return;
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for(const k in pos){ const p=pos[k]; if(!p||k.indexOf('root_')===0) continue;
    if(p.x<minX)minX=p.x; if(p.x>maxX)maxX=p.x; if(p.y<minY)minY=p.y; if(p.y>maxY)maxY=p.y; }
  if(minX===Infinity) return;
  const pad=60;
  const cw=(maxX-minX)+pad*2, ch=(maxY-minY)+pad*2;
  if(cw<=0||ch<=0) return;
  const s=Math.min(W/cw, H/ch, 1.15);
  scale=s;
  // 把内容中心移动到视口中心
  const contentCX=(minX+maxX)/2, contentCY=(minY+maxY)/2;
  tx=W/2 - contentCX*s;
  ty=H/2 - contentCY*s;
}

/* ---------- transforms ---------- */
function applyTransform(){
  const g=$('#svg .graph-layer');
  if(g) g.setAttribute('transform',`translate(${tx},${ty}) scale(${scale})`);
}
function zoom(f, px, py){
  const nx=px? px : W/2, ny=py? py: H/2;
  const ns=Math.min(3.2,Math.max(0.2, scale*f));
  // 以 (nx,ny) 为中心缩放
  const k=ns/scale; tx=nx-(nx-tx)*k; ty=ny-(ny-ty)*k; scale=ns;
  applyTransform();
}
function fit(){
  if(!center){ scale=1;tx=0;ty=0;applyTransform();draw();return; }
  scale=1; tx=0; ty=0; applyTransform();
}

/* ---------- 交互：平移/缩放 ---------- */
let drag=null;
$('#svg').addEventListener('mousedown',e=>{
  const target=e.target.closest('[data-n]');
  if(target) return; // 交给节点点击
  drag={x:e.clientX,y:e.clientY,tx,ty};
});
window.addEventListener('mousemove',e=>{
  if(!drag) return;
  tx=drag.tx+(e.clientX-drag.x); ty=drag.ty+(e.clientY-drag.y);
  applyTransform();
});
window.addEventListener('mouseup',()=>drag=null);
$('#svg').addEventListener('wheel',e=>{
  e.preventDefault();
  const box=$('#svg').getBoundingClientRect();
  const px=e.clientX-box.left, py=e.clientY-box.top;
  zoom(e.deltaY<0?1.12:0.89, px, py);
},{passive:false});
$('#z-in').onclick=()=>zoom(1.2);
$('#z-out').onclick=()=>zoom(0.8);
$('#z-fit').onclick=()=>{ scale=1;tx=0;ty=0;applyTransform(); };
window.addEventListener('keydown',e=>{
  if(e.key==='+'||e.key==='='){zoom(1.15);}
  else if(e.key==='-'){zoom(0.85);}
  else if(e.key==='0'){scale=1;tx=0;ty=0;applyTransform();}
});

/* ---------- 点击节点：设为中心 ---------- */
document.addEventListener('click',e=>{
  const el=e.target.closest('[data-n]');
  if(el){ let n=el.dataset.n; pick(n); e.preventDefault(); }
});
function pick(n){
  center=n;
  // 若该节点从未展示过，重置视图
  scale=1;tx=0;ty=0;
  draw();
}
function hlList(n){
  document.querySelectorAll('#hot li,#top-sys li').forEach(li=>li.classList.toggle('sel',li.dataset.n===n));
}

/* ---------- 详情面板 ---------- */
function showDetail(n){
  const d=$('#detail');
  if(!n){ d.style.display='none'; return; }
  const co=(inp[n]||[]), ce=(out[n]||[]);
  d.style.display='block';
  const cls=isSys(n)?'sys':(leafSet.has(n)?'leaf':'func');
  d.innerHTML=`
    <h2>${label(n)} ${leafSet.has(n)?'<span style="color:#7ee0a0;font-size:10px">●LEAF</span>':''}</h2>
    <div class="sub">${isSys(n)?'syscall · 宿主函数（叶子）':'脚本函数'}</div>
    <div class="rows">
      <div class="row"><span class="k">调用者</span><span class="v">${co.length}</span></div>
      <div class="row"><span class="k">被调用</span><span class="v">${ce.length}</span></div>
      <div class="row"><span class="k">交点度</span><span class="v">${deg[n]||0}</span></div>
    </div>
    <div class="sec"><div class="t">调用者 (${co.length})</div>${chipList(co)}
      ${co.length>12?`<span class="chip more">+${co.length-12}</span>`:''}
    </div>
    <div class="sec"><div class="t">被调用 (${ce.length})</div>${chipList(ce)}
      ${ce.length>14?`<span class="chip more">+${ce.length-14}</span>`:''}
    </div>
    <button class="btn primary set-center" data-makecenter="${n}">设为中心展开</button>`;
  d.querySelectorAll('.chip[data-n]').forEach(ch=>{
    ch.onclick=()=>pick(ch.dataset.n);
  });
  const mc=d.querySelector('[data-makecenter]');
  if(mc) mc.onclick=()=>pick(mc.dataset.makecenter);
}
function chipList(arr){
  return arr.slice(0,12).map(t=>`<span class="chip ${isSys(t)?'sys':(leafSet.has(t)?'leaf':'func')}" data-n="${t}">${label(t)}</span>`).join('') || '<span style="color:#5c6b87;font-size:11px">无</span>';
}

/* ---------- 方向 & 深度控制 ---------- */
$('#dirSeg').addEventListener('click',e=>{
  const b=e.target.closest('button'); if(!b) return;
  dir=b.dataset.dir; $('#dirSeg').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));
  draw();
});
$('#depth').addEventListener('input',e=>{
  depth=parseInt(e.target.value); $('#depthVal').textContent=depth; draw();
});
$('#btn-reset').onclick=()=>{ center=null; scale=1;tx=0;ty=0; draw(); };

/* ---------- 搜索 ---------- */
const sug=$('#sug');
const allNodes=[...funcs.map(x=>x), ...sysL.map(x=>'syscall:'+x)];
sug.innerHTML=allNodes.slice(0,4000).map(n=>`<option value="${label(n)}">`).join('');
$('#search').addEventListener('keydown',e=>{
  if(e.key!=='Enter') return;
  const q=e.target.value.trim().toLowerCase();
  if(!q) return;
  const found=allNodes.filter(n=>label(n).toLowerCase()===q);
  const f=found.length?found[0] : allNodes.filter(n=>label(n).toLowerCase().includes(q))[0];
  if(f) pick(f);
});
$('#search').addEventListener('input',()=>{
  // datalist 由浏览器接管
});

/* ---------- 初始 ---------- */
(function(){
  const s=DATA.stats;
  $('#stats').innerHTML=`
    <div class="stat"><span class="k">函数</span><span class="v">${s.functions_defined.toLocaleString()}</span></div>
    <div class="stat"><span class="k">syscall</span><span class="v">${s.unique_syscalls}</span></div>
    <div class="stat"><span class="k">调用边</span><span class="v">${s.unique_dep_edges.toLocaleString()}</span></div>
    <div class="stat"><span class="k">调用点</span><span class="v">${s.total_call_sites.toLocaleString()}</span></div>`;
})();
draw();
</script>
</body>
</html>
"""

html = html.replace('__DATA__', json.dumps(DATA, ensure_ascii=False))
with open('dependency.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("已写入 dependency.html")
