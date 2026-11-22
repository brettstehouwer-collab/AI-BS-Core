/** @param {{width?:number,height?:number,visualHeight?:number|null,offsetTop?:number}} [size] */
export function studioViewport({width=1440,height=900,visualHeight,offsetTop=0}={}) {
  return {
    compact: width <= 900 || (width <= 1100 && height <= 600),
    height: Math.round(typeof visualHeight === 'number' && Number.isFinite(visualHeight) && visualHeight > 0 ? visualHeight : height),
    top: Math.max(0,Math.round(offsetTop || 0)),
  };
}

/** @param {Window} target @param {(value:ReturnType<typeof studioViewport>)=>void} onChange */
export function watchStudioViewport(target,onChange) {
  const read=()=>onChange(studioViewport({width:target.innerWidth,height:target.innerHeight,visualHeight:target.visualViewport?.height,offsetTop:target.visualViewport?.offsetTop}));
  /** @type {Array<[EventTarget,string]>} */
  const listeners=[[target,'resize'],[target,'orientationchange']];
  if(target.visualViewport)listeners.push([target.visualViewport,'resize'],[target.visualViewport,'scroll']);
  for(const [node,event] of listeners)node.addEventListener(event,read);
  read();
  return ()=>{for(const [node,event] of listeners)node.removeEventListener(event,read);};
}
