const $ = (id) => document.getElementById(id);

const state = { chain: null, config: null, lastEntryAuto: true };

const money = n => Number.isFinite(n) ? `₹${n.toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2})}` : "—";
const num = n => Number.isFinite(n) ? n.toLocaleString("en-IN",{maximumFractionDigits:2}) : "—";

async function getJSON(url, options={}) {
  const r = await fetch(url, options);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function init() {
  try {
    state.config = await getJSON("/api/config");
    $("target").value = state.config.target_net;
    updateQuantity();

    const exp = await getJSON("/api/expiries");
    const expiries = exp.data || [];
    $("expiry").innerHTML = expiries.map(x=>`<option>${x}</option>`).join("");
    if (!expiries.length) throw new Error("No expiry returned.");

    await refresh();
    setInterval(refresh, (state.config.poll_seconds || 3) * 1000);
  } catch (e) {
    setStatus("ERROR", false);
    console.error(e);
  }
}

function setStatus(text, live) {
  $("status").textContent = text;
  $("status").className = live ? "status live" : "status";
}

async function refresh() {
  try {
    state.chain = await getJSON(`/api/chain?expiry=${encodeURIComponent($("expiry").value)}`);
    $("spot").textContent = num(Number(state.chain.spot || 0));
    $("updated").textContent = `Updated ${new Date(state.chain.as_of).toLocaleTimeString()} · ${state.chain.mode}`;
    setStatus(state.chain.mode === "live" ? "LIVE" : "DEMO", true);
    populateStrikes();
    renderChain();
  } catch (e) {
    setStatus("FEED ERROR", false);
    console.error(e);
  }
}

function contracts(side) {
  return (state.chain?.contracts || []).filter(x => x.side === side);
}

function getContract(strike, side) {
  return (state.chain?.contracts || []).find(x => x.side === side && Math.abs(Number(x.strike)-Number(strike))<0.01);
}

function populateStrikes() {
  const strikes = [...new Set((state.chain?.contracts || []).map(x=>Number(x.strike)))].sort((a,b)=>a-b);
  if (!strikes.length) return;
  const old = Number($("strike").value);
  const spot = Number(state.chain.spot || 0);
  const atm = strikes.reduce((a,b)=>Math.abs(b-spot)<Math.abs(a-spot)?b:a);
  const selected = strikes.includes(old) ? old : atm;
  $("strike").innerHTML = strikes.map(x=>`<option value="${x}" ${x===selected?"selected":""}>${x}</option>`).join("");
  syncEntry();
}

function syncEntry() {
  const c = getContract($("strike").value, $("side").value);
  if (c && state.lastEntryAuto) {
    $("entry").value = Number(c.ask || c.last_price || 0).toFixed(2);
  }
}

function updateQuantity() {
  const lots = Math.max(1, Number($("lots").value || 1));
  const qty = lots * Number(state.config?.lot_size || 65);
  $("quantity").textContent = `Quantity: ${qty}`;
}

async function analyse() {
  const payload = {
    expiry: $("expiry").value,
    strike: Number($("strike").value),
    side: $("side").value,
    lots: Number($("lots").value),
    target_net_profit: Number($("target").value),
    entry_price: Number($("entry").value),
    charge_buffer: Number(state.config.charge_buffer || 150),
    expected_range_remaining: $("expectedRange").value ? Number($("expectedRange").value) : null
  };

  try {
    const r = await getJSON("/api/viability", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(payload)
    });

    $("verdict").textContent = r.verdict.replace("_"," ");
    $("verdict").className =
      r.verdict === "VIABLE" ? "verdict-good" :
      r.verdict === "MARGINAL" ? "verdict-mid" : "verdict-bad";

    $("score").textContent = `${r.score}/100`;
    $("requiredExit").textContent = money(r.required_exit_premium);
    $("requiredMove").textContent = `${$("side").value==="ce"?"+":"−"}${num(r.required_nifty_move)} pts`;
    $("spotTarget").textContent = num(r.estimated_spot_target);
    $("betterStrike").textContent = r.better_strike ? `${r.better_strike} (${r.better_strike_score})` : "Selected strike is best";
    $("delta").textContent = r.delta_efficiency;
    $("gamma").textContent = r.gamma_support;
    $("spread").textContent = `${r.spread_pct}%`;
    $("liquidity").textContent = `${r.liquidity_score}/100`;
    $("oiSignal").textContent = r.oi_signal;
    $("qtyDetail").textContent = r.quantity;
    $("reasons").innerHTML = r.reasons.map(x=>`<li>${x}</li>`).join("");
  } catch (e) {
    alert(`Viability analysis failed: ${e.message}`);
  }
}

function renderChain() {
  const filter = $("filter").value.trim();
  const strikes = [...new Set((state.chain?.contracts || []).map(x=>Number(x.strike)))].sort((a,b)=>a-b);
  const rows = [];

  for (const strike of strikes) {
    if (filter && !String(strike).includes(filter)) continue;
    const ce = getContract(strike,"ce");
    const pe = getContract(strike,"pe");
    if (!ce || !pe) continue;

    const ceChange = Number(ce.oi)-Number(ce.previous_oi);
    const peChange = Number(pe.oi)-Number(pe.previous_oi);

    rows.push(`<tr data-strike="${strike}">
      <td data-side="ce">${num(Number(ce.last_price))}</td>
      <td>${num(Number(ce.greeks.delta))}</td>
      <td>${num(Number(ce.implied_volatility))}</td>
      <td class="${ceChange>=0?"pos":"neg"}">${num(ceChange/100000)}L</td>
      <td>${strike}</td>
      <td class="${peChange>=0?"pos":"neg"}">${num(peChange/100000)}L</td>
      <td>${num(Number(pe.implied_volatility))}</td>
      <td>${num(Number(pe.greeks.delta))}</td>
      <td data-side="pe">${num(Number(pe.last_price))}</td>
    </tr>`);
  }

  $("chainBody").innerHTML = rows.join("");
  $("chainBody").querySelectorAll("td[data-side]").forEach(cell=>{
    cell.addEventListener("click",()=>{
      $("strike").value = cell.closest("tr").dataset.strike;
      $("side").value = cell.dataset.side;
      state.lastEntryAuto = true;
      syncEntry();
      window.scrollTo({top:0,behavior:"smooth"});
    });
  });
}

$("analyseBtn").addEventListener("click", analyse);
$("lots").addEventListener("input", updateQuantity);
$("side").addEventListener("change", ()=>{state.lastEntryAuto=true;syncEntry();});
$("strike").addEventListener("change", ()=>{state.lastEntryAuto=true;syncEntry();});
$("entry").addEventListener("input", ()=>{state.lastEntryAuto=false;});
$("expiry").addEventListener("change", refresh);
$("filter").addEventListener("input", renderChain);

init();
