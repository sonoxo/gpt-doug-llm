/* 3D point-cloud CPU fallback if the browser administrator disables WebGL. */
window.SkullSoftware3D = function SkullSoftware3D(canvas, state) {
  'use strict';
  const context=canvas.getContext('2d',{alpha:false});
  if(!context)return false;
  const pts=[],edges=[],stars=[];
  let seed=55109;
  const rand=()=>((seed=(seed*1664525+1013904223)>>>0)/4294967296);
  function surface(cx,cy,cz,rx,ry,rz,count,rgb,noise=0,kind='bone'){
    for(let i=0;i<count;i++){
      const y=1-2*(i+.5)/count;
      const a=i*2.3999632; const r=Math.sqrt(1-y*y),xx=r*Math.cos(a),zz=r*Math.sin(a);
      const warp=1+noise*Math.sin(a*4)*Math.sin(16*y);
      const x=cx+rx*xx*warp, yy=cy+ry*y*warp,z=cz+rz*zz*warp;
      // Actual recess in the frontal cranial shell: two orbital openings.
      if(kind==='shell'&&zz>.20&&yy>-0.45&&yy<0.45) {
        const orbit=((Math.abs(x)-.50)/.35)**2+((yy-.08)/.42)**2;
        if(orbit<1.0)continue;
      }
      const nx=xx/rx,ny=y/ry,nz=zz/rz,nl=Math.hypot(nx,ny,nz)||1;
      const light=Math.max(0,(nx*(-.3)+ny*.55+nz*.82)/nl);
      pts.push({x,y:yy,z,color:rgb,bright:Math.min(1,0.29+light*.70+(rand()-.5)*.18),radius:kind==='bone'?.93:kind==='brain'?.9:1.35,kind});
    }
  }
  function line(a,b,count,color,width=1){
    let last=a;
    for(let i=1;i<=count;i++){
      const t=i/count;
      const next=a.map((v,j)=>v+(b[j]-v)*t);
      edges.push({a:last,b:next,color,width});last=next;
    }
  }
  function curve(f,n,color,width=1){let prev=f(0);for(let i=1;i<=n;i++){const now=f(i/n);edges.push({a:prev,b:now,color,width});prev=now;}}
  surface(0,.50,-.14,1.04,1.15,.82,5400,[150,190,178],.016,'shell');
  surface(0,-.69,.44,.65,.44,.51,2100,[172,199,183],.01,'bone');
  surface(0,-.31,.67,.18,.51,.24,550,[195,216,192],.01,'bone');
  surface(0,-.45,-.42,.78,.54,.53,770,[105,142,151],.02,'bone');
  for(const sign of [-1,1]){
    surface(sign*.85,-.43,.59,.19,.19,.31,660,[175,221,197],0,'bone');
    surface(sign*.5,.08,.86,.355,.39,.18,1050,[8,23,31],0,'cavity');
    const c=[150,218,201];
    curve(t=>[sign*.50+.36*Math.cos(t*Math.PI*2),.08+.41*Math.sin(t*Math.PI*2),.95+.04*Math.cos(t*Math.PI*4)],85,c,2.0);
    curve(t=>[sign*(.2+.68*t),.48+.11*Math.sin(t*Math.PI),.93-.15*t],38,[197,222,209],2.5);
    curve(t=>[sign*(.62+.29*t),-.42-.09*Math.sin(t*Math.PI),.76-.24*t],36,[181,221,199],2.3);
    curve(t=>[sign*(.76-.80*t),-.68-.78*Math.sin(t*Math.PI/2),.62+.29*Math.sin(t*Math.PI/2)],70,[164,191,181],3.3);
    curve(t=>[sign*.75,-.60-.52*t,.65],40,[121,156,165],2.7);
  }
  surface(0,-.63,1.03,.17,.27,.12,650,[6,19,26],0,'cavity');
  surface(0,-1.015,.95,.58,.075,.12,660,[10,24,31],0,'cavity');
  for(let i=0;i<12;i++){
    const k=(i-5.5)/5.5,x=k*.57,z=1.01-.2*k*k;
    surface(x,-1.028,z,.039,.075,.046,135,[229,227,210],0,'tooth');
    surface(x,-1.187,z-.018,.039,.073,.047,135,[223,225,208],0,'tooth');
  }
  surface(-.29,.60,-.17,.54,.73,.59,1500,[84,168,167],.07,'brain');
  surface(.29,.60,-.17,.54,.73,.59,1500,[92,170,168],.07,'brain');
  for(let i=0;i<210;i++){
    const u=rand()*2-1,a=rand()*2*Math.PI,rad=Math.sqrt(1-u*u);
    stars.push([1.27*rad*Math.cos(a),.35+1.26*u,1.12*rad*Math.sin(a),rand()]);
  }
  const rgb=(c,light,alpha=1)=>`rgba(${Math.min(255,c[0]*light)|0},${Math.min(255,c[1]*light)|0},${Math.min(255,c[2]*light)|0},${alpha})`;
  function transformed(p){
    const sy=Math.sin(state.yaw),cy=Math.cos(state.yaw),sx=Math.sin(state.pitch),cx=Math.cos(state.pitch);
    const xx=p[0]*cy+p[2]*sy, zz=-p[0]*sy+p[2]*cy;
    return [xx,p[1]*cx-zz*sx,p[1]*sx+zz*cx];
  }
  let lastFrame=0;
  function render(now){
    if(now-lastFrame<30){if(document.visibilityState==='visible')requestAnimationFrame(render);return;}
    lastFrame=now;
    const ratio=Math.min(window.devicePixelRatio||1,2),r=canvas.getBoundingClientRect();
    const w=Math.max(1,r.width*ratio|0),h=Math.max(1,r.height*ratio|0);
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    if(state.autorotate&&!window.document.hidden)state.yaw+=.0028;
    const cx=w*.50, cy=h*.54,scale=Math.min(w,h)*.88;
    const project=(p)=>{const [x,y,z]=transformed(p);const fact=scale/(state.distance-z);return [cx+x*fact,cy-y*fact,fact,z];};
    context.fillStyle='#0b1722';context.fillRect(0,0,w,h);
    const glow=context.createRadialGradient(cx,cy,0,cx,cy,Math.min(w,h)*.65);
    glow.addColorStop(0,'#1a343c');glow.addColorStop(.6,'#10212e');glow.addColorStop(1,'#0b1722');
    context.fillStyle=glow;context.fillRect(0,0,w,h);
    const renderPts=[];
    for(let i=0;i<pts.length;i++){
      const p=pts[i];
      if(state.mode==='anatomy'&&p.kind==='brain')continue;
      if(state.mode==='xray'&&p.kind==='shell'&&i%5!==0)continue;
      if(state.mode==='fusion'&&p.kind==='shell'&&i%2!==0)continue;
      const [x,y,f,z]=project([p.x,p.y,p.z]);
      if(x<-4||x>w+4||y<-4||y>h+4)continue;
      renderPts.push({x,y,z,f,p});
    }
    renderPts.sort((a,b)=>a.z-b.z);
    for(const v of renderPts){
      const p=v.p;
      let alpha=p.kind==='cavity'?1:p.kind==='shell'&&state.mode!=='anatomy'?.46:.84;
      let light=p.bright;
      if(p.kind==='brain')light*=state.mode==='anatomy'?0.15:1.2;
      context.fillStyle=rgb(p.color,light,alpha);
      const radius=Math.max(.52,Math.min(3.2,v.f*p.radius*.017));
      context.fillRect(v.x-radius,v.y-radius,2*radius,2*radius);
    }
    context.lineCap='round';
    for(const edge of edges){
      if(edge.color[0]===0)continue;
      const a=project(edge.a),b=project(edge.b);
      context.strokeStyle=rgb(edge.color,.9,state.mode==='xray'?.55:.8);
      context.lineWidth=edge.width*Math.min(1.4,(a[2]+b[2])*.008);
      context.beginPath();context.moveTo(a[0],a[1]);context.lineTo(b[0],b[1]);context.stroke();
    }
    if(state.nodes&&state.mode!=='anatomy'){
      for(let i=0;i<stars.length;i++){
        const p=stars[i],q=project(p);
        const blink=.4+.6*Math.sin(now*.002+i*1.37)**2;
        context.fillStyle=`rgba(108,247,230,${(.26+blink*.58).toFixed(2)})`;
        context.beginPath();context.arc(q[0],q[1],.5+1.1*blink+state.activity*.4,0,Math.PI*2);context.fill();
      }
    }
    // Operational readouts: orientation / distance are factual controls.
    $('#fallback-label').textContent='3D SOFTWARE MODE';
    if(window.document.visibilityState==='visible')window.requestAnimationFrame(render);
  }
  const $=(selector)=>document.querySelector(selector);
  const flag=$('#webgl-error');
  flag.hidden=true;
  const label=document.createElement('span');label.id='fallback-label';label.className='fallback-label';label.textContent='3D SOFTWARE MODE';
  canvas.parentElement.append(label);
  // Point cloud is rasterized in 3D perspective at a reduced cadence on CPU.
  window.requestAnimationFrame(render);
  document.addEventListener('visibilitychange',()=>{
    if(document.visibilityState==='visible')window.requestAnimationFrame(render);
  });
  return true;
};
