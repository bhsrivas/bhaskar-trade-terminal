const $ = (id) => document.getElementById(id);

const state = {
  chain: {},
  spot: 0,
  config: {},
  selectedStrike: null,
  lastEntryAuto: true
};

const money = (n) =>
  Number.isFinite(n)
    ? `₹${n.toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`
    : "—";

const num = (n) =>
  Number.isFinite(n)
    ? n.toLocaleString("en-IN", { maximumFractionDigits: 2 })
    : "—";

async function getJSON(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function parseExpiries(payload) {
  const value = payload.data || payload;
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.data)) return value.data;
  return [];
}

async function init() {
  try {
    state.config = await getJSON("/api/config");
    $("lots").value = 1;
    $("target").value = state.config.target_net;
    $("charges").value = state.config.charge_buffer;
    updateQuantity();

    const expiryPayload = await getJSON("/api/expiries");
    const expiries = parseExpiries(expiryPayload);

    $("expiry").innerHTML = expiries
      .map((expiry) => `<option>${expiry}</option>`)
      .join("");

    if (!expiries.length) {
      throw new Error("No active expiries returned.");
    }

    await refresh();
    setInterval(refresh, (state.config.poll_seconds || 3) * 1000);
  } catch (error) {
    setStatus("ERROR", false);
    console.error(error);
    alert(`Setup error: ${error.message}`);
  }
}

async function refresh() {
  try {
    const expiry = encodeURIComponent($("expiry").value);
    const payload = await getJSON(`/api/chain?expiry=${expiry}`);
    const data = payload.data || {};

    state.chain = data.oc || {};
    state.spot = Number(data.last_price || 0);

    $("spot").textContent = num(state.spot);
    $("updated").textContent =
      `Updated ${new Date(payload.as_of || Date.now()).toLocaleTimeString()} · ` +
      `${payload.mode || state.config.mode}`;

    setStatus(payload.mode === "live" ? "LIVE" : "DEMO", true);
    populateStrikes();
    renderChain();
    calculate();
  } catch (error) {
    setStatus("FEED ERROR", false);
    console.error(error);
  }
}

function setStatus(text, active) {
  $("status").textContent = text;
  $("status").className = active ? "status live" : "status";
}

function strikeKeys() {
  return Object.keys(state.chain)
    .map(Number)
    .sort((a, b) => a - b);
}

function getNode(strike) {
  return (
    state.chain[Number(strike).toFixed(6)] ||
    state.chain[String(Number(strike))]
  );
}

function populateStrikes() {
  const keys = strikeKeys();
  if (!keys.length) return;

  const oldStrike = Number($("strike").value);
  const atm = keys.reduce((a, b) =>
    Math.abs(b - state.spot) < Math.abs(a - state.spot) ? b : a
  );

  const selected =
    oldStrike && keys.includes(oldStrike)
      ? oldStrike
      : state.selectedStrike || atm;

  $("strike").innerHTML = keys
    .map(
      (strike) =>
        `<option value="${strike}" ${strike === selected ? "selected" : ""}>${strike}</option>`
    )
    .join("");

  state.selectedStrike = selected;
  syncEntryFromLtp();
}

function getOption() {
  const strike = Number($("strike").value);
  const side = $("side").value;
  return getNode(strike)?.[side];
}

function syncEntryFromLtp() {
  const option = getOption();
  if (option && state.lastEntryAuto) {
    $("entry").value = Number(
      option.top_ask_price || option.last_price || 0
    ).toFixed(2);
  }
}

function updateQuantity() {
  const lots = Math.max(1, Number($("lots").value || 1));
  const lotSize = Number(state.config.lot_size || 65);
  $("quantity").textContent = `Quantity: ${lots * lotSize}`;
}

function solveSpotMove(requiredPremiumGain, deltaAbs, gamma) {
  if (requiredPremiumGain <= 0) return 0;

  if (gamma > 0.000001) {
    const discriminant =
      deltaAbs * deltaAbs + 2 * gamma * requiredPremiumGain;
    return (-deltaAbs + Math.sqrt(discriminant)) / gamma;
  }

  return requiredPremiumGain / Math.max(deltaAbs, 0.01);
}

function calculate() {
  const option = getOption();
  if (!option) return;

  const lots = Math.max(1, Number($("lots").value || 1));
  const lotSize = Number(state.config.lot_size || 65);
  const quantity = lots * lotSize;

  const targetNet = Math.max(0, Number($("target").value || 0));
  const charges = Math.max(0, Number($("charges").value || 0));
  const entry = Math.max(0, Number($("entry").value || 0));
  const ltp = Number(option.last_price || 0);

  const delta = Math.abs(Number(option.greeks?.delta || 0));
  const gamma = Math.abs(Number(option.greeks?.gamma || 0));

  const requiredGross = targetNet + charges;
  const premiumGain = requiredGross / quantity;
  const exitPrice = entry + premiumGain;
  const move = solveSpotMove(premiumGain, delta, gamma);

  const side = $("side").value;
  const signedMove = side === "ce" ? move : -move;
  const targetSpot = state.spot + signedMove;

  const currentPnl = (ltp - entry) * quantity - charges;
  const progress =
    targetNet > 0
      ? Math.max(0, Math.min(100, (currentPnl / targetNet) * 100))
      : 0;

  $("exitPrice").textContent = money(exitPrice);
  $("premiumGain").textContent = money(premiumGain);
  $("spotMove").textContent = `${side === "ce" ? "+" : "−"}${num(move)} pts`;
  $("spotTarget").textContent = num(targetSpot);
  $("currentPnl").textContent = money(currentPnl);
  $("currentPnl").className = currentPnl >= 0 ? "pos" : "neg";
  $("targetStatus").textContent =
    currentPnl >= targetNet ? "EXIT TARGET MET" : "WAIT";
  $("targetStatus").className =
    currentPnl >= targetNet ? "pos" : "";

  $("progressText").textContent = `${progress.toFixed(0)}%`;
  $("progressBar").style.width = `${progress}%`;
}

function renderChain() {
  const filter = $("filter").value.trim();
  const keys = strikeKeys();
  if (!keys.length) return;

  const atm = keys.reduce((a, b) =>
    Math.abs(b - state.spot) < Math.abs(a - state.spot) ? b : a
  );

  const rows = [];

  for (const strike of keys) {
    if (filter && !String(strike).includes(filter)) continue;

    const node = getNode(strike);
    if (!node?.ce || !node?.pe) continue;

    const ce = node.ce;
    const pe = node.pe;

    const ceChange = Number(ce.oi || 0) - Number(ce.previous_oi || 0);
    const peChange = Number(pe.oi || 0) - Number(pe.previous_oi || 0);

    rows.push(`
      <tr class="${strike === atm ? "atm" : ""}" data-strike="${strike}">
        <td data-side="ce">${num(Number(ce.last_price))}</td>
        <td>${num(Number(ce.greeks?.delta))}</td>
        <td class="${ceChange >= 0 ? "pos" : "neg"}">${num(ceChange / 100000)}L</td>
        <td>${strike}</td>
        <td class="${peChange >= 0 ? "pos" : "neg"}">${num(peChange / 100000)}L</td>
        <td>${num(Number(pe.greeks?.delta))}</td>
        <td data-side="pe">${num(Number(pe.last_price))}</td>
      </tr>
    `);
  }

  $("chainBody").innerHTML = rows.join("");

  $("chainBody")
    .querySelectorAll("td[data-side]")
    .forEach((cell) => {
      cell.addEventListener("click", () => {
        const row = cell.closest("tr");
        $("strike").value = row.dataset.strike;
        $("side").value = cell.dataset.side;
        state.lastEntryAuto = true;
        syncEntryFromLtp();
        calculate();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    });
}

["lots", "target", "charges"].forEach((id) =>
  $(id).addEventListener("input", () => {
    updateQuantity();
    calculate();
  })
);

$("entry").addEventListener("input", () => {
  state.lastEntryAuto = false;
  calculate();
});

$("side").addEventListener("change", () => {
  state.lastEntryAuto = true;
  syncEntryFromLtp();
  calculate();
});

$("strike").addEventListener("change", () => {
  state.lastEntryAuto = true;
  syncEntryFromLtp();
  calculate();
});

$("expiry").addEventListener("change", refresh);
$("filter").addEventListener("input", renderChain);

init();
