/* XUNIA CL1 Physarum model — dimensionless, Tero-inspired flow simulation.
 * No living organism, laboratory equipment, neurons, or physical devices.
 * Q = D/L * (p_i - p_j); conductance reinforced by |Q| and eroded by decay.
 * This is a qualitative teaching model, not a validated biological solver.
 */
(function (root, make) {
  "use strict";
  const api=make();
  if(typeof module==="object"&&module.exports)module.exports=api;
  else root.PhysarumModel=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
  "use strict";
  const clamp=(x,min,max)=>Math.max(min,Math.min(max,x));
  const SCHEMA="xunia.cl1.physarum-simulation.v1";
  const COLS=18,ROWS=12;
  function index(x,y,s){return y*s.cols+x;}
  function create(cols=COLS,rows=ROWS){
    if(!Number.isInteger(cols)||!Number.isInteger(rows)||cols<8||cols>30||rows<6||rows>22)throw Error("Grid bounds must be 8–30 columns and 6–22 rows");
    const nodes=Array.from({length:cols*rows},(_,id)=>({
      id,x:id%cols,y:Math.floor(id/cols),blocked:false,trail:0,pressure:0
    }));
    const edges=[],around=Array.from({length:nodes.length},()=>[]);
    function edge(a,b){
      const e={a,b,length:1,d:0.105+((a*29+b*17)%11)*.004,q:0};
      edges.push(e);around[a].push(edges.length-1);around[b].push(edges.length-1);
    }
    for(let y=0;y<rows;y++)for(let x=0;x<cols;x++){
      const a=index(x,y,{cols});
      if(x<cols-1)edge(a,index(x+1,y,{cols}));
      if(y<rows-1)edge(a,index(x,y+1,{cols}));
    }
    const origin=index(2,Math.floor(rows/2),{cols});
    const food=[index(cols-3,2,{cols}),index(cols-4,rows-3,{cols})];
    return {schema:SCHEMA,cols,rows,nodes,edges,around,origin,food,
      tick:0,params:{growth:1.15,decay:.78,saturation:.055},lastFlow:0,flowEnergy:0};
  }
  function canUse(s,id){
    return Number.isInteger(id)&&id>=0&&id<s.nodes.length&&!s.nodes[id].blocked;
  }
  function nearest(s,x,y){
    return index(clamp(Math.round(x),0,s.cols-1),clamp(Math.round(y),0,s.rows-1),s);
  }
  function addFood(s,id){
    if(!canUse(s,id)||id===s.origin)return false;
    if(s.food.includes(id)){if(s.food.length<=1)return false;s.food=s.food.filter(v=>v!==id);return true;}
    if(s.food.length>=8)return false;
    s.food.push(id);return true;
  }
  function setOrigin(s,id){
    if(!canUse(s,id))return false;
    s.origin=id;s.food=s.food.filter(v=>v!==id);
    if(!s.food.length){
      const candidate=s.nodes.find(n=>!n.blocked&&n.id!==id);
      if(!candidate)return false;
      s.food=[candidate.id];
    }
    return true;
  }
  function barrier(s,id,value){
    if(!Number.isInteger(id)||id<0||id>=s.nodes.length||id===s.origin||s.food.includes(id))return false;
    s.nodes[id].blocked=!!value;
    if(value){s.nodes[id].trail=0;s.nodes[id].pressure=0;}
    return true;
  }
  function resetConductance(s){
    for(let i=0;i<s.edges.length;i++){const e=s.edges[i];
      e.d=.105+((e.a*29+e.b*17)%11)*.004;e.q=0;
    }
    for(const n of s.nodes){n.trail=0;n.pressure=0;}
    s.tick=0;s.lastFlow=0;s.flowEnergy=0;
  }
  function tick(s,opts={}){
    const growth=clamp(Number(opts.growth??s.params.growth),0,3);
    const decay=clamp(Number(opts.decay??s.params.decay),.05,2.5);
    const saturation=clamp(Number(opts.saturation??s.params.saturation),.012,.25);
    const food=s.food.filter(id=>canUse(s,id)&&id!==s.origin);
    if(!food.length||!canUse(s,s.origin))return false;
    // Fix origin at p=0, set the food nodes to equal sink loads.
    // This solves a regularized graph Laplacian for a source-to-food transport field.
    const loads=new Float64Array(s.nodes.length);
    const sink=-1/food.length;for(const id of food)loads[id]+=sink;
    const p=new Float64Array(s.nodes.map(n=>n.pressure));
    p[s.origin]=0;
    for(let k=0;k<95;k++){
      for(let i=0;i<s.nodes.length;i++){
        if(i===s.origin||s.nodes[i].blocked)continue;
        let sum=0,diag=.001;
        for(const ei of s.around[i]){
          const e=s.edges[ei],j=e.a===i?e.b:e.a;
          if(s.nodes[j].blocked)continue;
          const w=e.d/e.length;
          sum+=w*p[j];diag+=w;
        }
        const target=(sum+loads[i])/diag;
        p[i]=clamp(p[i]+.84*(target-p[i]),-100,100);
      }
    }
    p[s.origin]=0;
    let flow=0,energy=0;
    for(const e of s.edges){
      if(s.nodes[e.a].blocked||s.nodes[e.b].blocked){
        e.q=0;e.d=Math.max(.015,e.d*(1-.12*decay));continue;
      }
      const q=(e.d/e.length)*(p[e.a]-p[e.b]);
      e.q=Number.isFinite(q)?clamp(q,-8,8):0;
      const abs=Math.abs(e.q);
      flow+=abs;energy+=abs*abs;
      const gain=growth*(abs/(saturation+abs));
      e.d=clamp(e.d+.082*(gain-decay*e.d),.015,3.5);
    }
    for(let i=0;i<s.nodes.length;i++){
      const n=s.nodes[i];
      n.pressure=n.blocked?0:p[i];
      if(!n.blocked){
        let t=0;for(const ei of s.around[i])t+=Math.abs(s.edges[ei].q);
        n.trail=clamp(n.trail*.996+Math.min(.008,t*.001),0,1);
      }
    }
    s.tick++;s.lastFlow=flow;s.flowEnergy=energy;
    return true;
  }
  function step(s,n=1,opts={}){
    if(!Number.isInteger(n)||n<1||n>2000)throw Error("Step count 1–2000");
    for(let i=0;i<n;i++)tick(s,opts);
    return stats(s);
  }
  function stats(s){
    let tubes=0,length=0,maxFlux=0;
    const threshold=.26;
    for(const e of s.edges){
      if(s.nodes[e.a].blocked||s.nodes[e.b].blocked)continue;
      if(e.d>=threshold){tubes++;length+=e.length;}
      maxFlux=Math.max(maxFlux,Math.abs(e.q));
    }
    const seen=new Set([s.origin]),queue=[s.origin];
    while(queue.length){
      const id=queue.shift();
      for(const ei of s.around[id]){
        const e=s.edges[ei],j=e.a===id?e.b:e.a;
        if(s.nodes[j].blocked||e.d<.055||seen.has(j))continue;
        seen.add(j);queue.push(j);
      }
    }
    const foodReached=s.food.filter(id=>seen.has(id)).length;
    const blocked=s.nodes.filter(n=>n.blocked).length;
    return {ticks:s.tick,active_tubes:tubes,network_length_grid:length,
      nutrient_count:s.food.length,connected_nutrients:foodReached,blocked_nodes:blocked,
      total_abs_flux:+s.lastFlow.toFixed(3),flow_energy:+s.flowEnergy.toFixed(3),
      maximum_edge_flux:+maxFlux.toFixed(4)};
  }
  function network(s){
    return {
      schema:SCHEMA,organism_inspiration:"Physarum polycephalum",
      model_type:"qualitative software flow-reinforcement analogy; not a living specimen or measured biophysics",
      parameters:{...s.params},grid:{cols:s.cols,rows:s.rows},
      tick:s.tick,source_node:s.origin,nutrient_nodes:[...s.food],
      nodes:s.nodes.map(n=>({id:n.id,x:n.x,y:n.y,obstacle:n.blocked,trail:+n.trail.toFixed(4)})),
      edges:s.edges.filter(e=>!s.nodes[e.a].blocked&&!s.nodes[e.b].blocked).map(e=>({
        from:e.a,to:e.b,conductance:+e.d.toFixed(5),flux:+e.q.toFixed(5)
      })),
      metrics:stats(s),scientific_source:"https://pubmed.ncbi.nlm.nih.gov/17069858/",
      physical_output:"This JSON is an editable topology suggestion, not an actuator instruction."
    };
  }
  function svg(s){
    const w=s.cols*10,h=s.rows*10,selected=s.edges.filter(e=>!s.nodes[e.a].blocked&&!s.nodes[e.b].blocked&&e.d>=.23);
    const paths=selected.sort((a,b)=>a.a-b.a||a.b-b.b).map(e=>{
      const a=s.nodes[e.a],b=s.nodes[e.b],stroke=clamp(.3+e.d*1.3,.36,4.5);
      return '<path d="M '+(a.x*10+5)+' '+(a.y*10+5)+' L '+(b.x*10+5)+' '+(b.y*10+5)+'" stroke-width="'+stroke.toFixed(2)+'"/>';
    }).join("\n");
    const markers=[
      '<circle cx="'+(s.nodes[s.origin].x*10+5)+'" cy="'+(s.nodes[s.origin].y*10+5)+'" r="3.4" fill="#72f0e7"/>',
      ...s.food.map(id=>'<circle cx="'+(s.nodes[id].x*10+5)+'" cy="'+(s.nodes[id].y*10+5)+'" r="3.2" fill="#ffe66b"/>')
    ].join("\n");
    return '<?xml version="1.0" encoding="UTF-8"?>\n'+
      '<svg xmlns="http://www.w3.org/2000/svg" width="'+w+'mm" height="'+h+'mm" viewBox="0 0 '+w+' '+h+'">'+
      '<title>CL1 Physarum-inspired network vector blueprint</title>'+
      '<desc>Qualitative adaptive conductance design, not organism growth map or manufactured part. Verify print scale.</desc>'+
      '<rect width="'+w+'" height="'+h+'" fill="#101820"/>'+
      '<g stroke="#ffd64f" fill="none" stroke-linecap="round" stroke-linejoin="round">'+paths+'</g>'+
      '<g>'+markers+'</g></svg>\n';
  }
  return {SCHEMA,COLS,ROWS,create,nearest,addFood,setOrigin,barrier,resetConductance,
    tick,step,stats,network,svg};
});