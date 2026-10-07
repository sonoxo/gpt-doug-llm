import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, BatteryCharging, Compass, Radio, ShieldCheck, Wifi } from "lucide-react";
import "./style.css";

type Entity = {
  id: string; kind: string; label: string; lat: number; lon: number;
  alt_m: number; heading_deg: number; confidence: number; source: string;
  classification: string; ts: string;
};

const API = import.meta.env.VITE_API_BASE || "http://localhost:8787";

function App() {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [heading, setHeading] = useState(73);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const url = API.replace(/^http/, "ws") + "/ws";
    const sock = new WebSocket(url);
    sock.onopen = () => setConnected(true);
    sock.onclose = () => setConnected(false);
    sock.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.entities) setEntities(msg.entities);
    };
    return () => sock.close();
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      setHeading(Math.round(((e.clientX / innerWidth) * 360) % 360));
    };
    addEventListener("mousemove", onMove);
    return () => removeEventListener("mousemove", onMove);
  }, []);

  const focus = entities[0];
  const tickMarks = useMemo(() => Array.from({length: 13}, (_,i)=> (heading - 90 + i*15 + 360) % 360), [heading]);

  return <main className="visor">
    <div className="scanlines"/>
    <header>
      <div className="brand">GPT-DOUG // EAGLEEYE <span>SIM</span></div>
      <div className="status">
        <span><ShieldCheck size={16}/> HUMAN-FIRST</span>
        <span><Wifi size={16}/> {connected ? "LINKED" : "OFFLINE"}</span>
        <span><BatteryCharging size={16}/> 92%</span>
      </div>
    </header>

    <div className="compass">
      <Compass size={18}/>
      {tickMarks.map(v => <span key={v} className={Math.abs(v-heading)<8 ? "hot":""}>{String(Math.round(v)).padStart(3,"0")}°</span>)}
    </div>

    <section className="leftPanel glass">
      <h3>SENSOR FUSION</h3>
      <div className="metric"><Activity size={16}/><b>{entities.length}</b><small>ENTITIES</small></div>
      <div className="metric"><Radio size={16}/><b>6</b><small>FEEDS</small></div>
      <div className="metric"><ShieldCheck size={16}/><b>SAFE</b><small>POLICY</small></div>
      <div className="divider"/>
      {entities.slice(0,5).map(e => <div className="row" key={e.id}>
        <span className={"dot "+e.kind}/>
        <div><b>{e.label}</b><small>{e.kind.toUpperCase()} · {Math.round(e.confidence*100)}%</small></div>
      </div>)}
    </section>

    <section className="rightPanel glass">
      <h3>ONTOLOGY</h3>
      <div className="graph">
        <div className="node operator">OPERATOR</div>
        <div className="line l1"/>
        <div className="node sensor">SENSOR</div>
        <div className="line l2"/>
        <div className="node track">TRACK</div>
        <div className="line l3"/>
        <div className="node robot">ROBOT</div>
        <div className="line l4"/>
        <div className="node alert">ALERT</div>
      </div>
      <div className="divider"/>
      <p>Sources</p>
      <small>Lattice-shaped entity bus</small>
      <small>RoboParty ROS2 digital twin</small>
      <small>Public/authorized internet connectors</small>
    </section>

    <div className="reticle">
      <div className="ring"/>
      <div className="cross h"/>
      <div className="cross v"/>
      <div className="tag">{focus ? focus.label : "SEARCHING"}</div>
      <div className="sub">{focus ? focus.classification+" · "+focus.source : "SYNTHETIC FEED"}</div>
    </div>

    <div className="world">
      {entities.map((e,i) => <div key={e.id} className={"marker "+e.kind}
        style={{left: (18 + ((e.lon + 77.46)*1800 + i*19)%64)+"%", top:(22 + ((e.lat-37.52)*1400 + i*13)%56)+"%"}}>
        <i/><label>{e.label}</label><small>{Math.round(e.alt_m)}m</small>
      </div>)}
    </div>

    <footer>
      <span>SIMULATION / PUBLIC-DATA MODE</span>
      <span>HDG {String(heading).padStart(3,"0")}°</span>
      <span>NO WEAPON CONTROL</span>
    </footer>
  </main>
}

createRoot(document.getElementById("root")!).render(<App/>);
