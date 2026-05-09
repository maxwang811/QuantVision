"use client";

import {
  ApiRequestError,
  api,
  type ExperimentCompareOut,
  type ExperimentCompareRequest,
  type ExperimentKind,
  type ExperimentSummary,
  type ExperimentSweepCreate,
  type ExperimentSweepOut,
  type ExperimentSweepRunOut,
} from "@/lib/api";
import { formatCurrency, formatDate, formatNumber, formatPercent } from "@/lib/format";
import { useMutation, useQuery, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Tab = "history" | "compare" | "sweeps";
type KindFilter = ExperimentKind | "all";

const COLORS = [
  "#2563eb",
  "#16a34a",
  "#dc2626",
  "#7c3aed",
  "#0891b2",
  "#ca8a04",
  "#db2777",
  "#475569",
];

export default function ExperimentsPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("history");
  const [kind, setKind] = useState<KindFilter>("all");
  const [status, setStatus] = useState<string>("");
  const [q, setQ] = useState<string>("");
  const [selectedBacktests, setSelectedBacktests] = useState<string[]>([]);
  const [selectedForecasts, setSelectedForecasts] = useState<string[]>([]);
  const [activeSweepId, setActiveSweepId] = useState<string | null>(null);

  const history = useQuery({
    queryKey: ["experiments", kind, status, q],
    queryFn: () =>
      api.listExperiments({
        kind,
        status: status || undefined,
        q: q || undefined,
        limit: 100,
      }),
  });

  const comparePayload: ExperimentCompareRequest = useMemo(
    () => ({ backtest_ids: selectedBacktests, forecast_ids: selectedForecasts }),
    [selectedBacktests, selectedForecasts],
  );
  const hasCompareSelection = selectedBacktests.length > 0 || selectedForecasts.length > 0;

  const comparison = useQuery({
    queryKey: ["experiment-compare", selectedBacktests, selectedForecasts],
    queryFn: () => api.compareExperiments(comparePayload),
    enabled: hasCompareSelection,
  });

  const createSweep = useMutation({
    mutationFn: (payload: ExperimentSweepCreate) => api.createSweep(payload),
    onSuccess: (sweep) => {
      setActiveSweepId(sweep.id);
      queryClient.invalidateQueries({ queryKey: ["experiments"] });
      queryClient.invalidateQueries({ queryKey: ["sweep-runs", sweep.id] });
    },
  });

  const sweepRuns = useQuery({
    queryKey: ["sweep-runs", activeSweepId],
    queryFn: () => api.getSweepRuns(activeSweepId as string),
    enabled: !!activeSweepId,
  });

  const toggleCompare = (item: ExperimentSummary) => {
    if (item.kind === "backtest") {
      setSelectedBacktests((current) => toggleId(current, item.id, 8));
    }
    if (item.kind === "forecast") {
      setSelectedForecasts((current) => toggleId(current, item.id, 8));
    }
  };

  const compareExport = async (format: "json" | "csv") => {
    const blob = await api.exportCompare(comparePayload, format);
    downloadBlob(blob, `experiment-comparison.${format}`);
  };

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Experiment History</h1>
        <p className="max-w-3xl text-sm text-muted">
          Search saved runs, compare backtests and forecasts, export reproducible results, and run
          bounded parameter sweeps.
        </p>
      </header>

      <div className="inline-flex rounded-md border border-border p-1">
        <TabButton active={tab === "history"} onClick={() => setTab("history")}>
          History
        </TabButton>
        <TabButton active={tab === "compare"} onClick={() => setTab("compare")}>
          Compare
        </TabButton>
        <TabButton active={tab === "sweeps"} onClick={() => setTab("sweeps")}>
          Sweeps
        </TabButton>
      </div>

      {tab === "history" && (
        <HistoryTab
          data={history.data?.items ?? []}
          isLoading={history.isLoading}
          error={history.error}
          kind={kind}
          status={status}
          q={q}
          selectedBacktests={selectedBacktests}
          selectedForecasts={selectedForecasts}
          onKindChange={setKind}
          onStatusChange={setStatus}
          onQueryChange={setQ}
          onToggleCompare={toggleCompare}
          onOpenSweep={(id) => {
            setActiveSweepId(id);
            setTab("sweeps");
          }}
        />
      )}

      {tab === "compare" && (
        <CompareTab
          selectedBacktests={selectedBacktests}
          selectedForecasts={selectedForecasts}
          comparison={comparison.data}
          isLoading={comparison.isLoading}
          error={comparison.error}
          onClear={() => {
            setSelectedBacktests([]);
            setSelectedForecasts([]);
          }}
          onExport={compareExport}
        />
      )}

      {tab === "sweeps" && (
        <SweepsTab
          mutation={createSweep}
          activeSweepId={activeSweepId}
          runs={sweepRuns.data?.runs ?? []}
          runsLoading={sweepRuns.isLoading}
          runsError={sweepRuns.error}
        />
      )}
    </div>
  );
}

function HistoryTab({
  data,
  isLoading,
  error,
  kind,
  status,
  q,
  selectedBacktests,
  selectedForecasts,
  onKindChange,
  onStatusChange,
  onQueryChange,
  onToggleCompare,
  onOpenSweep,
}: {
  data: ExperimentSummary[];
  isLoading: boolean;
  error: unknown;
  kind: KindFilter;
  status: string;
  q: string;
  selectedBacktests: string[];
  selectedForecasts: string[];
  onKindChange: (kind: KindFilter) => void;
  onStatusChange: (status: string) => void;
  onQueryChange: (q: string) => void;
  onToggleCompare: (item: ExperimentSummary) => void;
  onOpenSweep: (id: string) => void;
}) {
  return (
    <section className="space-y-4">
      <div className="grid gap-3 rounded-lg border border-border p-4 md:grid-cols-[1fr_180px_180px]">
        <Field label="Search">
          <input
            value={q}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Name, ticker, id, strategy..."
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
          />
        </Field>
        <Field label="Kind">
          <select
            value={kind}
            onChange={(e) => onKindChange(e.target.value as KindFilter)}
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
          >
            <option value="all">All</option>
            <option value="backtest">Backtests</option>
            <option value="forecast">Forecasts</option>
            <option value="model_run">Model runs</option>
            <option value="sweep">Sweeps</option>
          </select>
        </Field>
        <Field label="Status">
          <select
            value={status}
            onChange={(e) => onStatusChange(e.target.value)}
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
          >
            <option value="">All</option>
            <option value="completed">Completed</option>
            <option value="partial">Partial</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
            <option value="queued">Queued</option>
          </select>
        </Field>
      </div>

      {error ? <ErrorBox error={error} /> : null}

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="border-b border-border bg-border/20 text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="w-12 px-3 py-2">Cmp</th>
              <th className="px-3 py-2">Run</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Metric</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted">
                  Loading experiments...
                </td>
              </tr>
            )}
            {!isLoading && data.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted">
                  No experiments found.
                </td>
              </tr>
            )}
            {data.map((item) => {
              const comparable =
                item.status === "completed" && (item.kind === "backtest" || item.kind === "forecast");
              const selected =
                item.kind === "backtest"
                  ? selectedBacktests.includes(item.id)
                  : item.kind === "forecast"
                    ? selectedForecasts.includes(item.id)
                    : false;
              return (
                <tr key={`${item.kind}-${item.id}`} className="align-top">
                  <td className="px-3 py-3">
                    <input
                      type="checkbox"
                      checked={selected}
                      disabled={!comparable}
                      onChange={() => onToggleCompare(item)}
                      aria-label={`Compare ${item.name ?? item.id}`}
                    />
                  </td>
                  <td className="px-3 py-3">
                    <div className="font-medium text-fg">{item.name || item.label}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
                      <span className="rounded border border-border px-1.5 py-0.5">{item.kind}</span>
                      <span>{item.label}</span>
                      <span className="font-mono">{item.id.slice(0, 8)}</span>
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <StatusChip status={item.status} />
                  </td>
                  <td className="px-3 py-3 font-mono text-xs tabular-nums">
                    <div>{formatMetric(item.primary_metric_label, item.primary_metric_value)}</div>
                    <div className="mt-1 text-muted">
                      {formatMetric(item.secondary_metric_label, item.secondary_metric_value)}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-muted">{formatDate(item.created_at)}</td>
                  <td className="px-3 py-3">
                    <ExperimentActions item={item} onOpenSweep={onOpenSweep} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function CompareTab({
  selectedBacktests,
  selectedForecasts,
  comparison,
  isLoading,
  error,
  onClear,
  onExport,
}: {
  selectedBacktests: string[];
  selectedForecasts: string[];
  comparison?: ExperimentCompareOut;
  isLoading: boolean;
  error: unknown;
  onClear: () => void;
  onExport: (format: "json" | "csv") => Promise<void>;
}) {
  const [exportError, setExportError] = useState<string | null>(null);
  const hasSelection = selectedBacktests.length > 0 || selectedForecasts.length > 0;

  const runExport = async (format: "json" | "csv") => {
    setExportError(null);
    try {
      await onExport(format);
    } catch (e) {
      setExportError(String(e));
    }
  };

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border p-4">
        <div className="text-sm text-muted">
          Selected{" "}
          <span className="font-mono text-fg">{selectedBacktests.length}</span> backtests and{" "}
          <span className="font-mono text-fg">{selectedForecasts.length}</span> forecasts.
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => runExport("csv")}
            disabled={!hasSelection}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-fg disabled:opacity-50"
          >
            Export CSV
          </button>
          <button
            type="button"
            onClick={() => runExport("json")}
            disabled={!hasSelection}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-fg disabled:opacity-50"
          >
            Export JSON
          </button>
          <button
            type="button"
            onClick={onClear}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-muted hover:text-fg"
          >
            Clear
          </button>
        </div>
      </div>

      {exportError && <div className="text-sm text-negative">{exportError}</div>}
      {error ? <ErrorBox error={error} /> : null}
      {!hasSelection && (
        <div className="rounded-lg border border-border p-6 text-sm text-muted">
          Select completed backtests or forecasts from History to compare them here.
        </div>
      )}
      {isLoading && <div className="h-40 animate-pulse rounded-lg border border-border bg-border/20" />}
      {comparison && (
        <>
          <BacktestComparison comparison={comparison} />
          <ForecastComparison comparison={comparison} />
        </>
      )}
    </section>
  );
}

function BacktestComparison({ comparison }: { comparison: ExperimentCompareOut }) {
  if (comparison.backtests.length === 0) return null;
  const chartData = buildBacktestChartData(comparison);
  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
        Backtest comparison
      </h2>
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-border bg-border/20 text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Run</th>
              <th className="px-3 py-2">Strategy</th>
              <th className="px-3 py-2">Final</th>
              <th className="px-3 py-2">Return</th>
              <th className="px-3 py-2">Sharpe</th>
              <th className="px-3 py-2">Max DD</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {comparison.backtests.map((bt) => (
              <tr key={bt.id}>
                <td className="px-3 py-2">{bt.name || bt.id.slice(0, 8)}</td>
                <td className="px-3 py-2">{bt.strategy}</td>
                <td className="px-3 py-2 font-mono">{fmtCurrency(bt.final_value)}</td>
                <td className="px-3 py-2 font-mono">{fmtPct(bt.total_return)}</td>
                <td className="px-3 py-2 font-mono">{fmtNum(bt.sharpe_ratio)}</td>
                <td className="px-3 py-2 font-mono">{fmtPct(bt.max_drawdown)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="rounded-lg border border-border p-4">
        <h3 className="mb-3 text-sm font-semibold text-fg">Normalized equity curves</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
              <CartesianGrid stroke="rgb(var(--border))" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fill: "rgb(var(--muted))", fontSize: 11 }}
                tickFormatter={(d) => formatDate(String(d))}
                minTickGap={40}
              />
              <YAxis
                tick={{ fill: "rgb(var(--muted))", fontSize: 11 }}
                tickFormatter={(v) => `${Number(v).toFixed(0)}`}
                width={56}
              />
              <Tooltip
                contentStyle={{
                  background: "rgb(var(--bg))",
                  border: "1px solid rgb(var(--border))",
                  borderRadius: 6,
                  fontSize: 12,
                }}
                labelFormatter={(d) => formatDate(String(d))}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {comparison.backtests.map((bt, index) => (
                <Line
                  key={bt.id}
                  type="monotone"
                  dataKey={bt.id}
                  name={bt.name || bt.strategy}
                  stroke={COLORS[index % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function ForecastComparison({ comparison }: { comparison: ExperimentCompareOut }) {
  if (comparison.forecasts.length === 0) return null;
  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
        Forecast comparison
      </h2>
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full min-w-[840px] text-left text-sm">
          <thead className="border-b border-border bg-border/20 text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Run</th>
              <th className="px-3 py-2">Method</th>
              <th className="px-3 py-2">Expected</th>
              <th className="px-3 py-2">Median</th>
              <th className="px-3 py-2">P10</th>
              <th className="px-3 py-2">P90</th>
              <th className="px-3 py-2">Loss prob.</th>
              <th className="px-3 py-2">Beat bench.</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {comparison.forecasts.map((fc) => (
              <tr key={fc.id}>
                <td className="px-3 py-2">{fc.name || fc.id.slice(0, 8)}</td>
                <td className="px-3 py-2">{fc.method}</td>
                <td className="px-3 py-2 font-mono">{fmtCurrency(fc.expected_value)}</td>
                <td className="px-3 py-2 font-mono">{fmtCurrency(fc.median_value)}</td>
                <td className="px-3 py-2 font-mono">{fmtCurrency(fc.p10_value)}</td>
                <td className="px-3 py-2 font-mono">{fmtCurrency(fc.p90_value)}</td>
                <td className="px-3 py-2 font-mono">{fmtPct(fc.probability_of_loss)}</td>
                <td className="px-3 py-2 font-mono">{fmtPct(fc.probability_beat_benchmark)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SweepsTab({
  mutation,
  activeSweepId,
  runs,
  runsLoading,
  runsError,
}: {
  mutation: UseMutationResult<ExperimentSweepOut, Error, ExperimentSweepCreate>;
  activeSweepId: string | null;
  runs: ExperimentSweepRunOut[];
  runsLoading: boolean;
  runsError: unknown;
}) {
  return (
    <section className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-2">
        <BacktestSweepForm
          pending={mutation.isPending}
          onSubmit={(payload) => mutation.mutate(payload)}
        />
        <ForecastSweepForm
          pending={mutation.isPending}
          onSubmit={(payload) => mutation.mutate(payload)}
        />
      </div>
      {mutation.error && <ErrorBox error={mutation.error} />}
      {mutation.data && (
        <div className="rounded-lg border border-border p-4 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="font-medium text-fg">{mutation.data.name || "Latest sweep"}</div>
              <div className="mt-1 text-muted">
                {mutation.data.completed_runs}/{mutation.data.total_runs} completed,{" "}
                {mutation.data.failed_runs} failed.
              </div>
            </div>
            <StatusChip status={mutation.data.status} />
          </div>
        </div>
      )}
      <SweepRunsTable
        sweepId={activeSweepId}
        runs={runs}
        loading={runsLoading}
        error={runsError}
      />
    </section>
  );
}

function BacktestSweepForm({
  pending,
  onSubmit,
}: {
  pending: boolean;
  onSubmit: (payload: ExperimentSweepCreate) => void;
}) {
  const [name, setName] = useState("Backtest strategy sweep");
  const [tickers, setTickers] = useState("SPY,AAPL,MSFT");
  const [weights, setWeights] = useState("0.5,0.25,0.25");
  const [initialCash, setInitialCash] = useState(10000);
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [benchmark, setBenchmark] = useState("SPY");
  const [strategies, setStrategies] = useState("monthly_rebalance,momentum");
  const [costs, setCosts] = useState("0,10");
  const [topNs, setTopNs] = useState("2,3");
  const [lookbacks, setLookbacks] = useState("63");
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setError(null);
      const payload: ExperimentSweepCreate = {
        kind: "backtest",
        name: name.trim() || null,
        max_runs: 50,
        base_request: {
          name: name.trim() || null,
          strategy: "monthly_rebalance",
          tickers: parseStringList(tickers, true),
          weights: parseNumberList(weights),
          initial_cash: initialCash,
          start_date: startDate,
          end_date: endDate,
          transaction_cost_bps: 10,
          benchmark_ticker: benchmark.trim() || null,
          strategy_params: {
            top_n: 3,
            rebalance_frequency: "monthly",
            lookback_days: 63,
          },
        },
        sweep_parameters: {
          strategy: parseStringList(strategies),
          transaction_cost_bps: parseNumberList(costs),
          "strategy_params.top_n": parseNumberList(topNs),
          "strategy_params.lookback_days": parseNumberList(lookbacks),
        },
      };
      onSubmit(payload);
    } catch (err) {
      setError(String(err));
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4 rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Backtest sweep</h2>
      <Field label="Sweep name">
        <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Tickers">
          <input value={tickers} onChange={(e) => setTickers(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Weights">
          <input value={weights} onChange={(e) => setWeights(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Initial cash">
          <input
            type="number"
            value={initialCash}
            onChange={(e) => setInitialCash(Number(e.target.value))}
            className={inputClass}
          />
        </Field>
        <Field label="Benchmark">
          <input value={benchmark} onChange={(e) => setBenchmark(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Start date">
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={inputClass} />
        </Field>
        <Field label="End date">
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={inputClass} />
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Strategies">
          <input value={strategies} onChange={(e) => setStrategies(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Costs (bps)">
          <input value={costs} onChange={(e) => setCosts(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Top N">
          <input value={topNs} onChange={(e) => setTopNs(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Momentum lookback">
          <input value={lookbacks} onChange={(e) => setLookbacks(e.target.value)} className={inputClass} />
        </Field>
      </div>
      {error && <div className="text-sm text-negative">{error}</div>}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
      >
        {pending ? "Running..." : "Run Backtest Sweep"}
      </button>
    </form>
  );
}

function ForecastSweepForm({
  pending,
  onSubmit,
}: {
  pending: boolean;
  onSubmit: (payload: ExperimentSweepCreate) => void;
}) {
  const [name, setName] = useState("Forecast method sweep");
  const [tickers, setTickers] = useState("SPY,AAPL,MSFT");
  const [weights, setWeights] = useState("0.5,0.25,0.25");
  const [initialValue, setInitialValue] = useState(10000);
  const [benchmark, setBenchmark] = useState("SPY");
  const [methods, setMethods] = useState("monte_carlo,bootstrap");
  const [horizons, setHorizons] = useState("6,12");
  const [simulations, setSimulations] = useState("1000");
  const [lookbacks, setLookbacks] = useState("252");
  const [seeds, setSeeds] = useState("7,42");
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setError(null);
      const payload: ExperimentSweepCreate = {
        kind: "forecast",
        name: name.trim() || null,
        max_runs: 50,
        base_request: {
          name: name.trim() || null,
          method: "monte_carlo",
          tickers: parseStringList(tickers, true),
          weights: parseNumberList(weights),
          initial_value: initialValue,
          horizon_months: 12,
          n_simulations: 1000,
          lookback_days: 252,
          benchmark_ticker: benchmark.trim() || null,
        },
        sweep_parameters: {
          method: parseStringList(methods),
          horizon_months: parseNumberList(horizons),
          n_simulations: parseNumberList(simulations),
          lookback_days: parseNumberList(lookbacks),
          random_seed: parseNumberList(seeds),
        },
      };
      onSubmit(payload);
    } catch (err) {
      setError(String(err));
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4 rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Forecast sweep</h2>
      <Field label="Sweep name">
        <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Tickers">
          <input value={tickers} onChange={(e) => setTickers(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Weights">
          <input value={weights} onChange={(e) => setWeights(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Initial value">
          <input
            type="number"
            value={initialValue}
            onChange={(e) => setInitialValue(Number(e.target.value))}
            className={inputClass}
          />
        </Field>
        <Field label="Benchmark">
          <input value={benchmark} onChange={(e) => setBenchmark(e.target.value)} className={inputClass} />
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Methods">
          <input value={methods} onChange={(e) => setMethods(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Horizons">
          <input value={horizons} onChange={(e) => setHorizons(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Simulations">
          <input value={simulations} onChange={(e) => setSimulations(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Lookbacks">
          <input value={lookbacks} onChange={(e) => setLookbacks(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Seeds">
          <input value={seeds} onChange={(e) => setSeeds(e.target.value)} className={inputClass} />
        </Field>
      </div>
      {error && <div className="text-sm text-negative">{error}</div>}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
      >
        {pending ? "Running..." : "Run Forecast Sweep"}
      </button>
    </form>
  );
}

function SweepRunsTable({
  sweepId,
  runs,
  loading,
  error,
}: {
  sweepId: string | null;
  runs: ExperimentSweepRunOut[];
  loading: boolean;
  error: unknown;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Sweep runs</h2>
        {sweepId && (
          <div className="flex gap-2 text-sm">
            <a href={api.exportSweepUrl(sweepId, "csv")} className="text-accent hover:underline">
              CSV
            </a>
            <a href={api.exportSweepUrl(sweepId, "json")} className="text-accent hover:underline">
              JSON
            </a>
          </div>
        )}
      </div>
      {error ? <ErrorBox error={error} /> : null}
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="border-b border-border bg-border/20 text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Index</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Linked run</th>
              <th className="px-3 py-2">Params</th>
              <th className="px-3 py-2">Error</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted">
                  Loading sweep runs...
                </td>
              </tr>
            )}
            {!loading && runs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted">
                  No sweep selected yet.
                </td>
              </tr>
            )}
            {runs.map((run) => {
              const linkedId = run.backtest_id ?? run.forecast_id;
              const href =
                run.backtest_id != null
                  ? `/backtest?id=${encodeURIComponent(run.backtest_id)}`
                  : run.forecast_id != null
                    ? `/forecast?id=${encodeURIComponent(run.forecast_id)}`
                    : null;
              return (
                <tr key={run.id} className="align-top">
                  <td className="px-3 py-3 font-mono">{run.run_index}</td>
                  <td className="px-3 py-3">
                    <StatusChip status={run.status} />
                  </td>
                  <td className="px-3 py-3 font-mono text-xs">
                    {href && linkedId ? (
                      <Link href={href} className="text-accent hover:underline">
                        {linkedId.slice(0, 8)}
                      </Link>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="max-w-sm px-3 py-3">
                    <code className="break-all text-xs text-muted">
                      {JSON.stringify(run.params)}
                    </code>
                  </td>
                  <td className="max-w-xs px-3 py-3 text-xs text-negative">
                    {run.error_message ?? ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ExperimentActions({
  item,
  onOpenSweep,
}: {
  item: ExperimentSummary;
  onOpenSweep: (id: string) => void;
}) {
  if (item.kind === "backtest") {
    return (
      <div className="flex flex-wrap gap-2 text-sm">
        <Link href={`/backtest?id=${encodeURIComponent(item.id)}`} className="text-accent hover:underline">
          Open
        </Link>
        <a href={api.exportBacktestUrl(item.id, "csv", "summary")} className="text-accent hover:underline">
          CSV
        </a>
        <a href={api.exportBacktestUrl(item.id, "json")} className="text-accent hover:underline">
          JSON
        </a>
      </div>
    );
  }
  if (item.kind === "forecast") {
    return (
      <div className="flex flex-wrap gap-2 text-sm">
        <Link href={`/forecast?id=${encodeURIComponent(item.id)}`} className="text-accent hover:underline">
          Open
        </Link>
        <a href={api.exportForecastUrl(item.id, "csv", "summary")} className="text-accent hover:underline">
          CSV
        </a>
        <a href={api.exportForecastUrl(item.id, "json")} className="text-accent hover:underline">
          JSON
        </a>
      </div>
    );
  }
  if (item.kind === "sweep") {
    return (
      <div className="flex flex-wrap gap-2 text-sm">
        <button type="button" onClick={() => onOpenSweep(item.id)} className="text-accent hover:underline">
          Runs
        </button>
        <a href={api.exportSweepUrl(item.id, "csv")} className="text-accent hover:underline">
          CSV
        </a>
        <a href={api.exportSweepUrl(item.id, "json")} className="text-accent hover:underline">
          JSON
        </a>
      </div>
    );
  }
  return <span className="text-sm text-muted">-</span>;
}

function StatusChip({ status }: { status: string }) {
  const cls =
    status === "completed"
      ? "border-positive/40 bg-positive/10 text-positive"
      : status === "failed"
        ? "border-negative/40 bg-negative/10 text-negative"
        : status === "partial"
          ? "border-accent/40 bg-accent/10 text-accent"
          : "border-border bg-border/20 text-muted";
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
        active ? "bg-accent text-white" : "text-muted hover:text-fg"
      }`}
    >
      {children}
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium uppercase tracking-wide text-muted">{label}</span>
      {children}
    </label>
  );
}

function ErrorBox({ error }: { error: unknown }) {
  const message =
    error instanceof ApiRequestError
      ? `${error.code}: ${error.message}`
      : error instanceof Error
        ? error.message
        : String(error);
  return (
    <div className="rounded-lg border border-negative/40 bg-negative/5 p-4 text-sm text-negative">
      {message}
    </div>
  );
}

function buildBacktestChartData(comparison: ExperimentCompareOut) {
  const byDate = new Map<string, Record<string, string | number>>();
  for (const bt of comparison.backtests) {
    for (const point of bt.normalized_curve) {
      const row = byDate.get(point.date) ?? { date: point.date };
      row[bt.id] = point.value;
      byDate.set(point.date, row);
    }
  }
  return Array.from(byDate.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)));
}

function toggleId(current: string[], id: string, max: number): string[] {
  if (current.includes(id)) return current.filter((item) => item !== id);
  if (current.length >= max) return current;
  return [...current, id];
}

function formatMetric(label: string | null, value: number | null): string {
  if (!label) return "-";
  const lower = label.toLowerCase();
  if (value == null) return `${label}: -`;
  if (lower.includes("return") || lower.includes("probability")) {
    return `${label}: ${formatPercent(value, 2)}`;
  }
  if (lower.includes("value")) return `${label}: ${formatCurrency(value)}`;
  return `${label}: ${formatNumber(value, 2)}`;
}

function fmtCurrency(value: number | null): string {
  return value == null ? "-" : formatCurrency(value);
}

function fmtPct(value: number | null): string {
  return value == null ? "-" : formatPercent(value, 2);
}

function fmtNum(value: number | null): string {
  return value == null ? "-" : formatNumber(value, 2);
}

function parseStringList(raw: string, uppercase = false): string[] {
  const values = raw
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
  if (values.length === 0) throw new Error("Enter at least one comma-separated value.");
  return uppercase ? values.map((v) => v.toUpperCase()) : values;
}

function parseNumberList(raw: string): number[] {
  const values = raw
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean)
    .map(Number);
  if (values.length === 0 || values.some((v) => !Number.isFinite(v))) {
    throw new Error("Enter valid comma-separated numbers.");
  }
  return values;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const inputClass =
  "w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent";
