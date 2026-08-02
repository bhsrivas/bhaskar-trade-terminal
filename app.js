\
const $ = (id) => document.getElementById(id);
const state = { chain: {}, spot: 0, config: {}, selectedStrike: null, selectedSide: "ce", lastEntryAuto: true };

const money = n => Number.isFinite(n) ? `₹${n.toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2})}` : "—";
const num = n => Number.isFinite(n) ? n.toLocaleString("en-IN",{maximumFractionDigits:2}) : "—";

async function getJSON(url){
  const r = await fetch(url);
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}

function parseExpiries(payload){
  const x = payload.data || payload;
  if(Array.isArray(x)) return x;
  if(Array.isArray(x?.data)) return x.data;
  return [];
}

async function init(){
  try{
    state.config = await getJSON("/api/config");
    $("lots").value = 1;
    $("target").value = state.config.target_net;
    $("charges").value = state.config.charge_buffer;
    updateQuantity();

    const expPayload = await getJSON("/api/expiries");
    const exps = parseExpiries(expPayload);
    $("expiry").innerHTML = exps.map(x=>`<option>${x}</option>`).join("");
    if(!exps.length) throw new Error("No active expiries returned.");
    await refresh();
    setInterval(refresh, (state.config.poll_seconds || 3) * 1000);
  }catch(e){ setStatus("ERROR", false); console.error(e); alert(`Setup error: ${e.message}`); }
}

async function refresh(){
  try{
    const payload = await getJSON(`/api/chain?expiry=${encodeURIComponent($("expiry").value)}`);
    const data = payload.data || {};
    state.chain = data.oc || {};
    state.spot = Number(data.last_price || 0);
    $("spot").textContent = num(state.spot);
    $("updated").textContent = `Updated ${new Date(payload.as_of || Date.now()).toLocaleTimeString()} · ${payload.mode || state.config.mode}`;
    setStatus(payload.mode === "live" ? "LIVE" : "DEMO", true);
    populateStrikes();
    renderChain();
    calculate();
  }catch(e){ setStatus("FEED ERROR", false); console.error(e); }
}

function setStatus(text, live){
  $("status").textContent = text;
  $("status").className = live ? "status live" : "status";
}

function strikeKeys(){
  return Object.keys(state.chain).map(Number).sort((a,b)=>a-b);
}

function populateStrikes(){
  const keys = strikeKeys();
  if(!keys.length) return;
  const old = Number($("strike").value);
  const atm = keys.reduce((a,b)=>Math.abs(b-state.spot)<Math.abs(a-state.spot)?b:a);
  const selected = old && keys.includes(old) ? old : (state.selectedStrike || atm);
  $("strike").innerHTML = keys.map(k=>`<option value="${k}" ${k===selected?"selected":""}>${k}</option>`).join("");
  state.selectedStrike = selected;
  syncEntryFromLtp();
}

function getOption(){
  const strike = Number($("strike").value);
  const side = $("side").value;
  return state.chain[strike.toFixed(6)]?.[side] || state.chain[String(strike)]?.[side];
}

function syncEntryFromLtp(){
  const opt = getOption();
  if(opt && state.lastEntryAuto){
    $("entry").value = Number(opt.top_ask_price || opt.last_price || 0).toFixed(2);
  }
}

function updateQuantity(){
  const lots = Math.max(1, Number($("lots").value || 1));
  $("quantity").textContent = `Quantity: ${lots * Number(state.config.lot_size || 65)}`;
}

function solveSpotMove(requiredPremiumGain, deltaAbs, gamma){
  // Approximation: gain = delta*x + 0.5*gamma*x².
  if(requiredPremiumGain <= 0) return 0;
  if(gamma > 0.000001){
    const disc = deltaAbs*deltaAbs + 2*gamma*requiredPremiumGain;
    return (-deltaAbs + Math.sqrt(disc)) / gamma;
  }
  return requiredPremiumGain / Math.max(deltaAbs, .01);
}

function calculate(){
  const opt = getOption();
  if(!opt) return;

  const lots = Math.max(1, Number($("lots").value || 1));
  const lotSize = Number(state.config.lot_size || 65);
  const qty = lots * lotSize;
  const targetNet = Math.max(0, Number($("target").value || 0));
  const charges = Math.max(0, Number($("charges").value || 0));
  const entry = Math.max(0, Number($("entry").value || 0));
  const ltp = Number(opt.last_price || 0);
  const delta = Math.abs(Number(opt.greeks?.delta || 0));
  const gamma = Math.abs(Number(opt.greeks?.gamma || 0));

  const requiredGross = targetNet + charges;
  const premiumGain = requiredGross / qty;
  const exitPrice = entry + premiumGain;
  const move = solveSpotMove(premiumGain, delta, gamma);
  const side = $("side").value;
  const signedMove = side === "ce" ? move : -move;
  const targetSpot = state.spot + signedMove;
  const pnl = (ltp - entry) * qty - charges;
  const progress = targetNet > 0 ? Math.max(0, Math.min(100, pnl / targetNet * 100)) : 0;

  $("exitPrice").textContent = money(exitPrice);
  $("premiumGain").textContent = money(premiumGain);
  $("spotMove").textContent = `${side==="ce"?"+":"−"}${num(move)} pts`;
  $("spotTarget").textContent = num(targetSpot);
  $("currentPnl").textContent = money(pnl);
  $("currentPnl").className = pnl >= 0 ? "pos" : "neg";
  $("targetStatus").textContent = pnl >= targetNet ? "EXIT TARGET MET" : "WAIT";
  $("targetStatus").className = pnl >= targetNet ? "pos" : "";
  $("progressText").textContent = `${progress.toFixed(0)}%`;
  $("progressBar").style.width = `${progress}%`;
}

function renderChain(){
  const filter = $("filter").value.trim();
  const atm = strikeKeys().reduce((a,b)=>Math.abs(b-state.spot)<Math.abs(a-state.spot)?b:a, 0);
  const rows = [];
  for(const strike of strikeKeys()){
    if(filter && !String(strike).includes(filter)) continue;
    const node = state.chain[strike.toFixed(6)] || state.chain[String(strike)];
    if(!node?.ce || !node?.pe) continue;
    const ce = node.ce, pe = node.pe;
    const ceChg = Number(ce.oi||0)-Number(ce.previous_oi||0);
    const peChg = Number(pe.oi||0)-Number(pe.previous_oi||0);
    rows.push(`<tr class="${strike===atm?"atm":""}" data-strike="${strike}">
      <td data-side="ce">${num(Number(ce.last_price))}</td>
      <td>${num(Number(ce.greeks?.delta))}</td>
      <td class="${ceChg>=0?"pos":"neg"}">${num(ceChg/100000)}L</td>
      <td>${strike}</td>
      <td class="${peChg>=0?"pos":"neg"}">${num(peChg/100000)}L</td>
      <td>${num(Number(pe.greeks?.delta))}</td>
      <td data-side="pe">${num(Number(pe.last_price))}</td>
    </tr>`);
  }
  $("chainBody").innerHTML = rows.join("");
  $("chainBody").querySelectorAll("td[data-side]").forEach(td=>{
    td.addEventListener("click", ()=>{
      const row = td.closest("tr");
      $("strike").value = row.dataset.strike;
      $("side").value = td.dataset.side;
      state.lastEntryAuto = true;
      syncEntryFromLtp();
      calculate();
      window.scrollTo({top:0,behavior:"smooth"});
    });
  });
}

["lots","target","charges"].forEach(id=>$(id).addEventListener("input",()=>{updateQuantity();calculate()}));
$("entry").addEventListener("input",()=>{state.lastEntryAuto=false;calculate()});
$("side").addEventListener("change",()=>{state.lastEntryAuto=true;syncEntryFromLtp();calculate()});
$("strike").addEventListener("change",()=>{state.lastEntryAuto=true;syncEntryFromLtp();calculate()});
$("expiry").addEventListener("change",refresh);
$("filter").addEventListener("input",renderChain);

init();
