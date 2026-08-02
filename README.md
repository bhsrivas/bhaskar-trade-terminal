# Bhaskar Trade Terminal v2

Cloud-hosted NIFTY option-chain and exit-target calculator.

## Current features

- Live Dhan option-chain integration
- CE/PE LTP and Delta display
- OI change display
- Lots input
- Default ₹5,000 net-profit target
- Required option exit premium
- Approximate NIFTY move and spot target
- Current estimated P/L
- Mobile-friendly dashboard
- Demo mode for testing

## Repository structure

All application files stay in the repository root:

```text
main.py
index.html
app.js
styles.css
requirements.txt
render.yaml
```

No `static` directory is required.

## Render deployment

The included `render.yaml` creates the web service automatically.

Required protected environment variables:

```text
DHAN_CLIENT_ID
DHAN_ACCESS_TOKEN
```

Do not store credentials in GitHub.

## Health check

After deployment, open:

```text
https://YOUR-SERVICE.onrender.com/api/health
```

Expected:

```json
{
  "status": "ok",
  "mode": "live",
  "credentials_configured": true
}
```

## Important

This version is read-only and does not place orders.
