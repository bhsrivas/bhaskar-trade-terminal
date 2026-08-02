# Bhaskar Trade Terminal — MVP

A mobile-first FastAPI web terminal that:

- polls the Dhan Option Chain API every 3 seconds;
- displays CE/PE LTP, Delta and OI change;
- lets the trader enter the number of lots;
- defaults the desired minimum net profit to ₹5,000;
- calculates the required option exit premium;
- estimates the corresponding NIFTY move and spot target using current Delta and Gamma;
- tracks current estimated P/L and target progress;
- includes a built-in demo feed so the interface can be tested immediately.

## Important scope

This MVP is **read-only**. It does not place, modify or exit broker orders. The exit value is a decision-support calculation, not a guaranteed fill. IV, Theta, changing Greeks, spread and slippage can materially alter the result.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.

On macOS/Linux, replace the activation and copy commands with:

```bash
source .venv/bin/activate
cp .env.example .env
```

## Enable live Dhan data

Edit `.env`:

```env
APP_MODE=live
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token
```

Dhan's individual access token is normally time-limited. Do not put the token in the browser or commit `.env` to GitHub. The backend keeps credentials server-side.

## Deploy on Render

1. Push this folder to a private GitHub repository.
2. In Render, create a Blueprint or Web Service from the repository.
3. Use the included `render.yaml`, or set:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add secret environment variables:
   - `APP_MODE=live`
   - `DHAN_CLIENT_ID`
   - `DHAN_ACCESS_TOKEN`
5. Test the generated `onrender.com` address.
6. Add your custom domain `trade.bhaskar.ai` in Render.
7. Create the DNS record Render provides.

## Exit calculation

```text
quantity = lots × lot_size
required_gross_profit = target_net_profit + charge_buffer
premium_gain_required = required_gross_profit ÷ quantity
required_exit_premium = entry_premium + premium_gain_required
```

The spot-move estimate solves:

```text
premium_gain ≈ |delta| × move + 0.5 × gamma × move²
```

## Next production upgrades

- Exact ICICI Direct/Dhan charge calculator instead of a fixed buffer
- Authentication and PIN/OTP protection
- Broker position import and actual average entry price
- WebSocket quote streaming for selected contracts
- Server-side alerts when the target becomes executable at the bid price
- Persistent trade journal and audit log
- Separate gross target, net target, stop loss and trailing-profit rules
