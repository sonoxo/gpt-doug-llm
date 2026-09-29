
(() => {
  "use strict";
  document.body.classList.add("ops-motion-on");

  const stateKey = "xunia.maven.fold.v1";
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(stateKey) || "{}"); } catch {}

  function slug(text, i){
    return String(text || "panel-"+i).toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,64) || "panel-"+i;
  }

  document.querySelectorAll("aside .card").forEach((card, i) => {
    if (card.dataset.foldReady === "1") return;
    const heading = card.querySelector(":scope > h2");
    if (!heading) return;

    const id = slug(heading.textContent, i);
    const inner = document.createElement("div");
    inner.className = "fold-inner";
    const body = document.createElement("div");
    body.className = "fold-body";

    while (heading.nextSibling) inner.appendChild(heading.nextSibling);
    body.appendChild(inner);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "fold-head";
    button.setAttribute("aria-expanded", saved[id] === false ? "false" : "true");
    button.innerHTML = '<span class="fold-title"></span><span class="fold-chevron" aria-hidden="true">⌄</span>';
    button.querySelector(".fold-title").textContent = heading.textContent;

    heading.replaceWith(button);
    card.appendChild(body);
    card.dataset.foldReady = "1";
    card.dataset.foldId = id;

    if (saved[id] === false) card.classList.add("collapsed");

    button.addEventListener("click", () => {
      const collapsed = card.classList.toggle("collapsed");
      button.setAttribute("aria-expanded", String(!collapsed));
      saved[id] = !collapsed;
      try { localStorage.setItem(stateKey, JSON.stringify(saved)); } catch {}
    });
  });

  const dock = document.createElement("div");
  dock.className = "ops-dock";
  dock.setAttribute("data-no-translate","true");
  dock.innerHTML = [
    '<button type="button" data-ops="expand">▾ ALL</button>',
    '<button type="button" data-ops="collapse">▸ ALL</button>',
    '<button type="button" data-ops="map">◎ MAP</button>',
    '<button type="button" data-ops="sensors">◉ SENSORS</button>'
  ].join("");
  document.body.appendChild(dock);

  const scan = document.createElement("div");
  scan.className = "ops-live-scan";
  scan.setAttribute("aria-hidden","true");
  document.body.appendChild(scan);

  function setAll(collapsed){
    document.querySelectorAll("aside .card[data-fold-ready='1']").forEach(card => {
      card.classList.toggle("collapsed", collapsed);
      const btn = card.querySelector(":scope > .fold-head");
      if (btn) btn.setAttribute("aria-expanded", String(!collapsed));
      saved[card.dataset.foldId] = !collapsed;
    });
    try { localStorage.setItem(stateKey, JSON.stringify(saved)); } catch {}
  }

  function focusPanel(term){
    const card = [...document.querySelectorAll("aside .card[data-fold-ready='1']")].find(c =>
      (c.querySelector(".fold-title")?.textContent || "").toLowerCase().includes(term)
    );
    if (!card) return;
    card.classList.remove("collapsed");
    card.querySelector(".fold-head")?.setAttribute("aria-expanded","true");
    card.scrollIntoView({behavior:"smooth",block:"center"});
    card.animate(
      [{boxShadow:"0 0 0 rgba(215,255,100,0)"},{boxShadow:"0 0 32px rgba(215,255,100,.28)"},{boxShadow:"0 0 0 rgba(215,255,100,0)"}],
      {duration:900,easing:"ease-out"}
    );
  }

  dock.addEventListener("click", e => {
    const action = e.target.closest("button")?.dataset.ops;
    if (action === "expand") setAll(false);
    if (action === "collapse") setAll(true);
    if (action === "map") window.scrollTo({top:0,behavior:"smooth"});
    if (action === "sensors") focusPanel("sensor");
  });

  document.addEventListener("keydown", e => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
    if (e.key === "[") setAll(true);
    if (e.key === "]") setAll(false);
    if (e.key.toLowerCase() === "s") focusPanel("sensor");
  });

  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.animate(
          [{opacity:.1,transform:"translateY(12px)"},{opacity:1,transform:"translateY(0)"}],
          {duration:420,easing:"cubic-bezier(.2,.78,.2,1)",fill:"both"}
        );
        io.unobserve(entry.target);
      });
    },{threshold:.06});
    document.querySelectorAll("aside .card").forEach(card => io.observe(card));
  }
})();
