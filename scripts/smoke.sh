#!/usr/bin/env bash
# QuantVision end-to-end smoke harness.
#
# Boots the dev stack via docker-compose, ingests a small set of tickers, and
# exercises every API surface (backtest, forecast, sweep, compare, optimize).
# Exits non-zero on any failure with a one-line summary at the end.
#
# Override the API URL by setting E2E_API_URL.
# Requires: docker, docker-compose, curl, python3.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API="${E2E_API_URL:-http://localhost:8000}"
PASS=0
FAIL=0

log()  { printf '[smoke] %s\n' "$*"; }
ok()   { PASS=$((PASS + 1)); printf '[ ok ] %s\n' "$*"; }
fail() { FAIL=$((FAIL + 1)); printf '[fail] %s\n' "$*" >&2; }

# Pluck a JSON field (top-level only) from stdin via python3.
jget() {
  local field="$1"
  python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    v = d.get('$field')
    print('' if v is None else v)
except Exception as e:
    print('', file=sys.stderr)
    sys.exit(1)
"
}

# 1. boot stack
log "docker-compose up -d --build"
docker-compose up -d --build >/dev/null

# 2. wait for backend healthcheck
log "waiting for $API/api/health (up to 120s)"
ready=false
for _ in $(seq 1 60); do
  if curl -fsS "$API/api/health" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done
$ready && ok "backend healthy" || { fail "backend never became healthy"; exit 1; }

# 3. migrate + seed (idempotent)
log "make migrate seed"
make migrate >/dev/null
make seed >/dev/null
ok "migrations + asset seed applied"

# 4. ingest 3 tickers (~2 years), retry up to 3 times for yfinance flake
log "ingest SPY,AAPL,MSFT (2y) — retries on yfinance flake"
ingested=false
for attempt in 1 2 3; do
  if docker-compose exec -T backend python scripts/ingest_prices.py \
        --tickers SPY,AAPL,MSFT --years 2 >/dev/null 2>&1; then
    ingested=true
    break
  fi
  log "ingest attempt $attempt failed; retrying"
  sleep 3
done
$ingested && ok "ingested SPY/AAPL/MSFT" || { fail "yfinance ingest failed after 3 attempts"; exit 1; }

# Pick a date range that fits within the last ~2y of ingested data.
END_DATE="$(date -u -v-30d +%Y-%m-%d 2>/dev/null || date -u -d "30 days ago" +%Y-%m-%d)"
START_DATE="$(date -u -v-1y +%Y-%m-%d 2>/dev/null || date -u -d "1 year ago" +%Y-%m-%d)"

# 5. POST buy_and_hold backtest
BT_REQ=$(cat <<EOF
{
  "strategy": "buy_and_hold",
  "tickers": ["SPY","AAPL","MSFT"],
  "weights": [0.5, 0.25, 0.25],
  "initial_cash": 10000,
  "start_date": "$START_DATE",
  "end_date": "$END_DATE",
  "transaction_cost_bps": 10,
  "benchmark_ticker": "SPY"
}
EOF
)
BT_RESP=$(curl -fsS -X POST "$API/api/backtests" -H 'content-type: application/json' -d "$BT_REQ")
BT_ID=$(echo "$BT_RESP" | jget id)
FINAL=$(echo "$BT_RESP" | jget final_value)
if python3 -c "import sys; v='$FINAL'; sys.exit(0 if v and float(v) > 0 else 1)" 2>/dev/null; then
  ok "backtest final_value=$FINAL ($BT_ID)"
else
  fail "backtest final_value not positive: $FINAL"
fi

# 6. POST forecast (monte_carlo, 1000 sims, 6mo)
FC_REQ=$(cat <<EOF
{
  "method": "monte_carlo",
  "tickers": ["SPY","AAPL","MSFT"],
  "weights": [0.5, 0.25, 0.25],
  "initial_value": 10000,
  "horizon_months": 6,
  "n_simulations": 1000,
  "lookback_days": 252
}
EOF
)
FC_RESP=$(curl -fsS -X POST "$API/api/forecasts" -H 'content-type: application/json' -d "$FC_REQ")
P5=$(echo "$FC_RESP" | jget p5_value)
P95=$(echo "$FC_RESP" | jget p95_value)
[ -n "$P5" ] && [ -n "$P95" ] && ok "forecast percentiles (p5=$P5 p95=$P95)" \
  || fail "forecast missing percentiles"

# 7. POST sweep (2 strategies × 2 transaction costs)
SW_REQ=$(cat <<EOF
{
  "kind": "backtest",
  "base_request": {
    "strategy": "buy_and_hold",
    "tickers": ["SPY","AAPL","MSFT"],
    "weights": [0.5, 0.25, 0.25],
    "initial_cash": 10000,
    "start_date": "$START_DATE",
    "end_date": "$END_DATE",
    "transaction_cost_bps": 10,
    "benchmark_ticker": "SPY"
  },
  "sweep_parameters": {
    "strategy": ["buy_and_hold", "monthly_rebalance"],
    "transaction_cost_bps": [5, 20]
  }
}
EOF
)
SW_RESP=$(curl -fsS -X POST "$API/api/experiment-sweeps" -H 'content-type: application/json' -d "$SW_REQ")
SW_ID=$(echo "$SW_RESP" | jget id)
TOTAL=$(echo "$SW_RESP" | jget total_runs)
COMPLETED=$(echo "$SW_RESP" | jget completed_runs)
if [ "$TOTAL" = "$COMPLETED" ] && [ "$TOTAL" = "4" ]; then
  ok "sweep complete ($COMPLETED/$TOTAL) ($SW_ID)"
else
  fail "sweep partial: $COMPLETED/$TOTAL ($SW_ID)"
fi

# 8. Compare the resulting backtests
RUNS_JSON=$(curl -fsS "$API/api/experiment-sweeps/$SW_ID/runs")
CMP_REQ=$(echo "$RUNS_JSON" | python3 -c '
import json, sys
d = json.load(sys.stdin)
ids = [r["backtest_id"] for r in d.get("runs", []) if r.get("backtest_id")]
print(json.dumps({"backtest_ids": ids, "forecast_ids": []}))
')
CMP_RESP=$(curl -fsS -X POST "$API/api/experiments/compare" -H 'content-type: application/json' -d "$CMP_REQ")
CMP_OK=$(echo "$CMP_RESP" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(1 if isinstance(d.get("backtests"), list) and len(d["backtests"]) >= 1 else 0)
except Exception:
    print(0)
')
[ "$CMP_OK" = "1" ] && ok "compare returned ${CMP_OK} backtest items" \
  || fail "compare response shape unexpected"

# 9. POST /api/optimize for the 3 tickers
OPT_REQ='{
  "tickers": ["SPY","AAPL","MSFT"],
  "lookback_days": 252,
  "risk_free_rate": 0.04
}'
OPT_RESP=$(curl -fsS -X POST "$API/api/optimize" -H 'content-type: application/json' -d "$OPT_REQ")
SUM=$(echo "$OPT_RESP" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(round(sum(d["max_sharpe"]["weights"]), 4))
except Exception:
    print("nan")
')
if python3 -c "import sys; v='$SUM'; sys.exit(0 if v != 'nan' and abs(float(v) - 1.0) < 1e-2 else 1)" 2>/dev/null; then
  ok "optimize max_sharpe weights sum to $SUM"
else
  fail "optimize weights sum invalid: $SUM"
fi

# 10. summary
echo
log "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
