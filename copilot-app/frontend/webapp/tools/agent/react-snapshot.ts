import { chromium } from 'playwright'

// Loader au cas où __DUMP_REACT_TREE__ n'est pas attaché par le bundle
function dumperPolyfill() {
  // Copie minimaliste : même logique que dumpReactTree ci-dessus, raccourcie pour inline.
  return `
  (function(){
    if (window.__DUMP_REACT_TREE__) return;
    function safeClone(v,d){if(d>3)return'[DepthLimit]';if(v===null||typeof v!=='object'){if(typeof v==='function')return'[Function]';if(typeof v==='symbol')return'[Symbol]';return v}if(Array.isArray(v))return v.slice(0,20).map(x=>safeClone(x,d+1));const o={};let c=0;for(const k in v){if(c++>50){o['[Truncated]']=true;break}try{const val=v[k];o[k]=typeof val==='function'?'[Function]':safeClone(val,d+1)}catch{o[k]='[Unserializable]'}}return o}
    function ser(f){const n=(f.elementType&& (f.elementType.displayName||f.elementType.name))||(f.type&&(f.type.displayName||f.type.name))||('tag:'+f.tag);const node={name:n,key:f.key??null,props:safeClone(f.memoizedProps,0),state:safeClone(f.memoizedState,0),children:[]};let ch=f.child;while(ch){node.children.push(ser(ch));ch=ch.sibling}return node}
    window.__DUMP_REACT_TREE__ = function(){
      const hook = (window as any).__REACT_DEVTOOLS_GLOBAL_HOOK__
      if(!hook || !hook.renderers || hook.renderers.size===0) return {ok:false,error:'DevTools hook not available'}
      const [rid] = Array.from(hook.renderers.keys())
      const roots = hook.getFiberRoots(rid)
      const out=[]; for(const r of Array.from(roots)){ out.push(ser((r as any).current||r)) }
      return {ok:true, trees: out}
    }
  })();`
}

async function main() {
  const url = process.env.APP_URL ?? 'http://localhost:5173'
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  await page.goto(url, { waitUntil: 'networkidle' })

  // Si le bundle n'a pas exposé __DUMP_REACT_TREE__, on injecte le polyfill
  await page.addScriptTag({ content: dumperPolyfill() })

  const result = await page.evaluate(() => {
    // @ts-ignore
    const fn = (window as any).__DUMP_REACT_TREE__
    return fn ? fn() : { ok: false, error: 'no dumper available' }
  })

  console.log(JSON.stringify(result, null, 2))
  await browser.close()

  if (!result.ok) process.exit(2)
}

main().catch(e => { console.error(e); process.exit(1) })