/* XUNIA KRAKEN ground-drone exercise simulation. No physical robot, tracking, or pursuit interfaces. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  else root.KrakenCore=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const W=36,H=24;
  const zones=[{x:17.0,y:5.4,rx:3.1,ry:2.8,label:'PROTECTED HABITAT'},
               {x:21.5,y:18.3,rx:3.1,ry:2.9,label:'NO-GO / UTILITY'}];
  const base={x:4,y:12.5};
  const beacon={x:29.3,y:10.6};
  const template=[
    {id:'DEVIL-01',name:'DEVIL 01',role:'SEARCH / SURVEY',color:'#90f6cf',x:4.8,y:12.7,speed:1.65,patrol:[[9,12],[15,12],[21,10],[27,10],[31,14],[26,14]]},
    {id:'DRILL-02',name:'BORER 02',role:'VIRTUAL SUBSURFACE',color:'#f4bb75',x:3.8,y:13.6,speed:1.35,patrol:[[8,16],[13,19],[19,12],[25,12],[30,16]]},
    {id:'MAP-03',name:'MAPPER 03',role:'TERRAIN MAPPING',color:'#78b6ff',x:4.4,y:11.2,speed:1.5,patrol:[[8,6],[13,10],[18,12],[24,7],[31,7]]},
    {id:'SAFE-04',name:'SENTINEL 04',role:'SAFETY OBSERVER',color:'#bd9fff',x:4.0,y:12.3,speed:1.05,patrol:[[7,14],[7,10],[5,8],[5,16]]}
  ];
  function key(x,y){return x+','+y}
  function terrain(x,y){return Math.sin(x*.48+Math.cos(y*.31))*.52+Math.cos(y*.67-x*.12)*.26+Math.sin(x*.19+y*.37)*.22}
  function inBounds(x,y){return x>=1&&y>=1&&x<W-1&&y<H-1}
  function inNoGo(x,y){return zones.some(z=>((x-z.x)/z.rx)**2+((y-z.y)/z.ry)**2<=1)}
  function isRock(x,y){
    // Abstract rock patches drawn on the training grid; never terrain survey data.
    return (x>=11&&x<=13&&y>=3&&y<=8)||(x>=13&&x<=15&&y>=17&&y<=20)||
      (x>=25&&x<=27&&y>=3&&y<=5)||(x>=28&&x<=31&&y>=17&&y<=19)||
      (x>=20&&x<=22&&y>=2&&y<=3);
  }
  function isBlocked(x,y){
    x=Math.round(x);y=Math.round(y);
    return !inBounds(x,y)||inNoGo(x,y)||isRock(x,y);
  }
  const directions=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
  function findPath(from,to){
    const sx=Math.round(from.x),sy=Math.round(from.y),tx=Math.round(to.x),ty=Math.round(to.y);
    if(isBlocked(tx,ty)||isBlocked(sx,sy))return [];
    const origin=key(sx,sy),target=key(tx,ty);
    const open=[{x:sx,y:sy,f:0}],best=new Map([[origin,0]]),parent=new Map(),closed=new Set();
    while(open.length){
      open.sort((a,b)=>a.f-b.f);const cur=open.shift(),ck=key(cur.x,cur.y);
      if(closed.has(ck))continue;
      if(ck===target){let node=target,path=[];while(node!==origin){const [x,y]=node.split(',').map(Number);path.push({x,y});node=parent.get(node);if(!node)return []}return path.reverse()}
      closed.add(ck);
      for(const [dx,dy] of directions){
        const nx=cur.x+dx,ny=cur.y+dy,nk=key(nx,ny);
        if(isBlocked(nx,ny)||closed.has(nk))continue;
        if(dx&&dy&&(isBlocked(cur.x+dx,cur.y)||isBlocked(cur.x,cur.y+dy)))continue;
        const tentative=best.get(ck)+(dx&&dy?Math.SQRT2:1)+(terrain(nx,ny)+1)*.04;
        if(tentative>=(best.get(nk)??Infinity))continue;
        parent.set(nk,ck);best.set(nk,tentative);
        const heuristic=Math.hypot(nx-tx,ny-ty);
        open.push({x:nx,y:ny,f:tentative+heuristic});
      }
    }
    return [];
  }
  function escapeXml(s){return String(s).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[ch]))}
  function clamp(n,min,max){return Math.min(max,Math.max(min,n))}
  class Mission{
    constructor(){this.reset()}
    reset(){
      this.time=0;this.speed=1;this.running=true;this.phase='SURVEY';this.discovered=false;this.secured=false;this.carrier=null;
      this.beacons=0;this.selected='DEVIL-01';this.covered=new Set();this.events=[];this.seq=0;
      this.robots=template.map(t=>({...t,battery:98,link:97,patrolIndex:0,path:[],goal:null,manual:null,
        status:'SURVEYING',heading:0,history:[{x:t.x,y:t.y}],depth:t.id==='DRILL-02'?1.8:0}));
      this.log('EXERCISE INITIALIZED','4 synthetic ground assets online');
      this.log('SAFETY ENFORCED','Human tracking, restraints, hardware control disabled');
      this.scanAll();
    }
    get selectedRobot(){return this.robots.find(r=>r.id===this.selected)||this.robots[0]}
    select(id){if(!this.robots.some(r=>r.id===id))return false;this.selected=id;return true}
    log(type,message){this.events.unshift({t:this.time,type,message});this.events.length=Math.min(this.events.length,80)}
    setManualWaypoint(id,x,y){
      const robot=this.robots.find(r=>r.id===id);
      if(!robot||!Number.isFinite(x)||!Number.isFinite(y)||isBlocked(x,y)){
        this.log('WAYPOINT REJECTED','Outside simulation grid, obstacle, or protected zone');return false;
      }
      const p=findPath(robot,{x,y});if(!p.length&&Math.hypot(robot.x-x,robot.y-y)>.9){this.log('WAYPOINT REJECTED','No safe simulated path');return false}
      robot.manual={x:Math.round(x),y:Math.round(y)};robot.goal=null;robot.path=[];
      this.log('WAYPOINT ACCEPTED',`${robot.id} rerouted on abstract training grid`);
      return true;
    }
    robotTarget(r){
      if(r.manual)return r.manual;
      if(this.phase==='RETURN'&&r.id===this.carrier)return base;
      if(this.phase==='RECOVERED'&&r.id===this.carrier)return null;
      if(this.discovered&&!this.secured&&r.id==='DEVIL-01')return beacon;
      const points=r.patrol;
      return {x:points[r.patrolIndex%points.length][0],y:points[r.patrolIndex%points.length][1]};
    }
    scanAll(){
      for(const r of this.robots){
        const radius=r.role.includes('MAPPING')?3.4:2.8;
        for(let x=Math.floor(r.x-radius);x<=Math.ceil(r.x+radius);x++)for(let y=Math.floor(r.y-radius);y<=Math.ceil(r.y+radius);y++){
          if(x>=0&&y>=0&&x<W&&y<H&&Math.hypot(x-r.x,y-r.y)<=radius)this.covered.add(key(x,y));
        }
        if(!this.discovered&&Math.hypot(r.x-beacon.x,r.y-beacon.y)<5.3){
          this.discovered=true;this.phase='BEACON FOUND';
          this.log('BEACON DETECTED','Inert exercise beacon detected by synthetic proximity sensor');
        }
      }
    }
    step(delta){
      if(!this.running)return;
      const dt=clamp(delta,0,.25)*this.speed;this.time+=dt;
      for(const r of this.robots){
        if(r.battery<=6){r.status='STANDBY / LOW ENERGY';continue}
        let dest=this.robotTarget(r);
        if(!dest){r.status='MISSION COMPLETE';continue}
        const destinationChanged=!r.goal||Math.hypot(r.goal.x-dest.x,r.goal.y-dest.y)>.12;
        if(destinationChanged){r.goal={x:dest.x,y:dest.y};r.path=findPath(r,dest)}
        if(r.path.length){
          const p=r.path[0],vx=p.x-r.x,vy=p.y-r.y,d=Math.hypot(vx,vy);
          const stride=r.speed*dt;
          if(d<=stride+.0001){r.x=p.x;r.y=p.y;r.path.shift()}
          else{r.x+=vx/d*stride;r.y+=vy/d*stride}
          if(d>.002)r.heading=Math.atan2(vy,vx);
          r.battery=Math.max(0,r.battery-dt*.018*(r.id==='DRILL-02'?1.2:1));
          r.link=clamp(94+Math.sin(this.time*.16+r.x*.28)*5,65,99);
          if(r.history.length===0||Math.hypot(r.x-r.history[r.history.length-1].x,r.y-r.history[r.history.length-1].y)>.28){
            r.history.push({x:r.x,y:r.y});if(r.history.length>75)r.history.shift();
          }
          r.status=r.manual?'MANUAL WAYPOINT':this.phase==='RETURN'&&r.id===this.carrier?'RETURNING WITH BEACON':r.id==='DRILL-02'?'VIRTUAL TUNNEL SURVEY':'AUTONOMOUS SURVEY';
        }
        const dist=Math.hypot(r.x-dest.x,r.y-dest.y);
        if(!r.path.length&&dist<1.2){
          if(r.manual){r.manual=null;r.goal=null;r.status='WAYPOINT REACHED';this.log('WAYPOINT REACHED',r.id+' completed simulated waypoint')}
          else if(this.phase==='RETURN'&&r.id===this.carrier){
            this.secured=true;this.beacons=1;this.phase='RECOVERED';r.status='MISSION COMPLETE';r.goal=null;
            this.log('EXERCISE COMPLETE','Inert beacon returned to home pad; no person or object was physically contacted');
          } else if(this.discovered&&!this.secured&&r.id==='DEVIL-01'&&dest===beacon){
            this.phase='RETURN';this.carrier=r.id;r.goal=null;r.path=[];r.status='SIMULATED BEACON PICKUP';
            this.log('BEACON TAGGED','Exercise capture registered virtually; robot returns to home pad');
          } else {r.patrolIndex++;r.goal=null}
        }
      }
      this.scanAll();
    }
    get coverage(){return Math.round(100*this.covered.size/(W*H))}
    get snapshot(){return {schema:'xunia.kraken.ground-training.v1',mode:'simulation',time:Math.round(this.time*100)/100,
      phase:this.phase,coverage_pct:this.coverage,beacons_secured:this.beacons,assets:this.robots.map(r=>({id:r.id,
        role:r.role,x:+r.x.toFixed(3),y:+r.y.toFixed(3),depth_m:r.depth,energy_pct:+r.battery.toFixed(1),link_pct:+r.link.toFixed(1),
        status:r.status})),events:this.events.slice(),physical_control:false,person_tracking:false}}
    get aegisFrame(){
      return {schema:'xunia.friendly-telemetry.v1',mode:'training',source:'kraken_sim',sequence:this.seq++,assets:this.robots.map(r=>({
        id:r.id,kind:'friendly',label:r.name,position:{x:+((r.x-18)*2.4).toFixed(4),z:+((r.y-12)*2.4).toFixed(4),y:0},
        energy_pct:+r.battery.toFixed(2),link_pct:+r.link.toFixed(2)}))};
    }
  }
  function cotForRobot(robot,clock=new Date()){
    if(!robot||!template.some(r=>r.id===robot.id)||!Number.isFinite(robot.x)||!Number.isFinite(robot.y))throw new TypeError('Known simulated friendly robot required');
    const timestamp=new Date(clock);if(!Number.isFinite(timestamp.getTime()))throw new TypeError('Valid clock required');
    const start=timestamp.toISOString(),stale=new Date(timestamp.getTime()+30000).toISOString();
    // Explicitly synthetic coordinates near 0/0 (NOT geographic asset positions), do not use operationally.
    const lat=(robot.y-12)*0.00011,lon=(robot.x-18)*0.00011;
    return '<?xml version="1.0" encoding="UTF-8"?>\n'+
      `<event version="2.0" uid="XUNIA-SIM-${escapeXml(robot.id)}" type="a-f-G" how="h-e" time="${start}" start="${start}" stale="${stale}">`+
      `<point lat="${lat.toFixed(6)}" lon="${lon.toFixed(6)}" hae="0" ce="9999999" le="9999999"/>`+
      `<detail><contact callsign="SIM-${escapeXml(robot.id)}"/>`+
      '<remarks>SIMULATION ONLY - SYNTHETIC NON-GEOGRAPHIC EXERCISE COORDINATES. No actual robot or human location; not for operational use.</remarks>'+
      '</detail></event>';
  }
  return Object.freeze({Mission,W,H,zones,base,beacon,terrain,inBounds,inNoGo,isRock,isBlocked,findPath,cotForRobot});
});
