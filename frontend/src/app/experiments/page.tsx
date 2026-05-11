"use client";

import { Badge, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ChartCard } from "@/components/ui/ChartCard";
import { EmptyState, ErrorBox } from "@/components/ui/EmptyState";
import { Field } from "@/components/ui/Field";
import { IconClock, IconDownload, IconGrid, IconSearch } from "@/components/ui/Icons";
import { Input, Select } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionEyebrow } from "@/components/ui/SectionEyebrow";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs } from "@/components/ui/Tabs";
import { chartAxisTick, chartGridStroke, chartTooltipStyle } from "@/lib/chart-theme";
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
  "rgb(99 102 241)",
  "rgb(16 185 129)",
  "rgb(239 68 68)",
  "rgb(124 58 237)",
  "rgb(8 145 178)",
  "rgb(202 138 4)",
  "rgb(219 39 119)",
  "rgb(71 85 105)",
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

  const selectedCount = selectedBacktests.length + selectedForecasts.length;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Experiments"
        title="History"
        description="Search every saved run, compare backtests and forecasts side-by-side, export reproducible results, and run bounded parameter sweeps."
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs
          value={tab}
          onChange={(v) => setTab(v)}
          tabs={[
            { value: "history", label: "History" },
            { value: "compare", label: `Compare${selectedCount > 0 ? ` · ${selectedCount}` : ""}` },
            { value: "sweeps", label: "Sweeps" },
          ]}
        />
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
          onJumpToCompare={() => setTab("compare")}
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
          onJumpToHistory={() => setTab("history")}
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
  onJumpToCompare,
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
  onJumpToCompare: () => void;
}) {
  const selectedCount = selectedBacktests.length + selectedForecasts.length;
  return (
    <section className="space-y-5">
      <Card>
        <div className="grid gap-4 md:grid-cols-[1fr_180px_180px]">
          <Field label="Search">
            <Input
              value={q}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="Name, ticker, id, strategy…"
              adornmentLeft={<IconSearch width={14} height={14} />}
            />
          </Field>
          <Field label="Kind">
            <Select value={kind} onChange={(e) => onKindChange(e.target.value as KindFilter)}>
              <option value="all">All</option>
              <option value="backtest">Backtests</option>
              <option value="forecast">Forecasts</option>
              <option value="model_run">Model runs</option>
              <option value="sweep">Sweeps</option>
            </Select>
          </Field>
          <Field label="Status">
            <Select value={status} onChange={(e) => onStatusChange(e.target.value)}>
              <option value="">All</option>
              <option value="completed">Completed</option>
              <option value="partial">Partial</option>
              <option value="failed">Failed</option>
              <option value="running">Running</option>
              <option value="queued">Queued</option>
            </Select>
          </Field>
        </div>
        {selectedCount > 0 && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-accent/30 bg-accent/[0.06] px-4 py-2.5 text-sm">
            <span className="text-fg">
              <span className="font-mono font-semibold text-accent">{selectedCount}</span> selected
              for comparison
            </span>
            <Button type="button" variant="primary" size="sm" onClick={onJumpToCompare}>
              Open compare
            </Button>
          </div>
        )}
      </Card>

      {error ? <ErrorBox message={errorMessage(error)} /> : null}

      <Card padded={false} className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b border-border bg-surface-2/60 text-xs uppercase tracking-eyebrow text-muted">
              <tr>
                <th className="w-12 px-4 py-3">Cmp</th>
                <th className="px-4 py-3">Run</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Metric</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading && (
                <tr>
                  <td colSpan={6} className="px-4 py-12">
                    <div className="flex items-center justify-center gap-3 text-sm text-muted">
                      <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-accent" />
                      Loading experiments…
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading && data.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12">
                    <EmptyState
                      icon={<IconClock width={18} height={18} />}
                      title="No experiments yet"
                      description="Run a backtest or forecast — every completed run lands here automatically."
                      compact
                    />
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
                  <tr
                    key={`${item.kind}-${item.id}`}
                    className="align-top transition-colors hover:bg-surface-2/40"
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selected}
                        disabled={!comparable}
                        onChange={() => onToggleCompare(item)}
                        aria-label={`Compare ${item.name ?? item.id}`}
                        className="h-4 w-4 accent-accent"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-fg">{item.name || item.label}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
                        <Badge tone="neutral" variant="outline" className="capitalize">
                          {item.kind}
                        </Badge>
                        <span className="truncate">{item.label}</span>
                        <span className="font-mono">{item.id.slice(0, 8)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={statusTone(item.status)} variant="soft">
                        {item.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs tabular-nums">
                      <div className="text-fg">
                        {formatMetric(item.primary_metric_label, item.primary_metric_value)}
                      </div>
                      <div className="mt-1 text-muted">
                        {formatMetric(item.secondary_metric_label, item.secondary_metric_value)}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted">{formatDate(item.created_at)}</td>
                    <td className="px-4 py-3">
                      <ExperimentActions item={item} onOpenSweep={onOpenSweep} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
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
  onJumpToHistory,
}: {
  selectedBacktests: string[];
  selectedForecasts: string[];
  comparison?: ExperimentCompareOut;
  isLoading: boolean;
  error: unknown;
  onClear: () => void;
  onExport: (format: "json" | "csv") => Promise<void>;
  onJumpToHistory: () => void;
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
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10 text-accent">
              <IconGrid width={18} height={18} />
            </span>
            <div className="space-y-0.5 text-sm">
              <div className="font-semibold text-fg">Selected runs</div>
              <div className="text-muted">
                <span className="font-mono text-fg">{selectedBacktests.length}</span> backtests ·{" "}
                <span className="font-mono text-fg">{selectedForecasts.length}</span> forecasts
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => runExport("csv")}
              disabled={!hasSelection}
              leadingIcon={<IconDownload width={12} height={12} />}
            >
              Export CSV
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => runExport("json")}
              disabled={!hasSelection}
              leadingIcon={<IconDownload width={12} height={12} />}
            >
              Export JSON
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={onClear} disabled={!hasSelection}>
              Clear
            </Button>
          </div>
        </div>
      </Card>

      {exportError && <ErrorBox message={exportError} />}
      {error ? <ErrorBox message={errorMessage(error)} /> : null}
      {!hasSelection && (
        <EmptyState
          icon={<IconGrid width={20} height={20} />}
          title="Nothing to compare yet"
          description="Pick completed backtests or forecasts on the History tab to see their metrics, equity curves, and percentile bands side-by-side."
          action={
            <Button type="button" variant="primary" size="sm" onClick={onJumpToHistory}>
              Browse history
            </Button>
          }
        />
      )}
      {isLoading && <Skeleton className="h-40" />}
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
      <SectionEyebrow as="h2">Backtest comparison</SectionEyebrow>
      <Card padded={false} className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-border bg-surface-2/60 text-xs uppercase tracking-eyebrow text-muted">
              <tr>
                <th className="px-4 py-3">Run</th>
                <th className="px-4 py-3">Strategy</th>
                <th className="px-4 py-3 text-right">Final</th>
                <th className="px-4 py-3 text-right">Return</th>
                <th className="px-4 py-3 text-right">Sharpe</th>
                <th className="px-4 py-3 text-right">Max DD</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {comparison.backtests.map((bt) => (
                <tr key={bt.id} className="transition-colors hover:bg-surface-2/40">
                  <td className="px-4 py-3 font-medium text-fg">{bt.name || bt.id.slice(0, 8)}</td>
                  <td className="px-4 py-3 text-muted">{bt.strategy}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtCurrency(bt.final_value)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtPct(bt.total_return)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtNum(bt.sharpe_ratio)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtPct(bt.max_drawdown)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <ChartCard title="Normalized equity curves" bodyClassName="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid stroke={chartGridStroke} strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={chartAxisTick}
              tickFormatter={(d) => formatDate(String(d))}
              minTickGap={40}
            />
            <YAxis tick={chartAxisTick} tickFormatter={(v) => `${Number(v).toFixed(0)}`} width={56} />
            <Tooltip contentStyle={chartTooltipStyle} labelFormatter={(d) => formatDate(String(d))} />
            <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
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
      </ChartCard>
    </div>
  );
}

function ForecastComparison({ comparison }: { comparison: ExperimentCompareOut }) {
  if (comparison.forecasts.length === 0) return null;
  return (
    <div className="space-y-4">
      <SectionEyebrow as="h2">Forecast comparison</SectionEyebrow>
      <Card padded={false} className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[840px] text-left text-sm">
            <thead className="border-b border-border bg-surface-2/60 text-xs uppercase tracking-eyebrow text-muted">
              <tr>
                <th className="px-4 py-3">Run</th>
                <th className="px-4 py-3">Method</th>
                <th className="px-4 py-3 text-right">Expected</th>
                <th className="px-4 py-3 text-right">Median</th>
                <th className="px-4 py-3 text-right">P10</th>
                <th className="px-4 py-3 text-right">P90</th>
                <th className="px-4 py-3 text-right">Loss prob.</th>
                <th className="px-4 py-3 text-right">Beat bench.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {comparison.forecasts.map((fc) => (
                <tr key={fc.id} className="transition-colors hover:bg-surface-2/40">
                  <td className="px-4 py-3 font-medium text-fg">{fc.name || fc.id.slice(0, 8)}</td>
                  <td className="px-4 py-3 text-muted">{fc.method}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtCurrency(fc.expected_value)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtCurrency(fc.median_value)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtCurrency(fc.p10_value)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtCurrency(fc.p90_value)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtPct(fc.probability_of_loss)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{fmtPct(fc.probability_beat_benchmark)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
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
      {mutation.error && <ErrorBox message={errorMessage(mutation.error)} />}
      {mutation.data && (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="font-semibold text-fg">{mutation.data.name || "Latest sweep"}</div>
              <div className="text-sm text-muted">
                <span className="font-mono text-fg">{mutation.data.completed_runs}</span>/
                <span className="font-mono text-fg">{mutation.data.total_runs}</span> completed,{" "}
                <span className="font-mono text-fg">{mutation.data.failed_runs}</span> failed.
              </div>
            </div>
            <Badge tone={statusTone(mutation.data.status)} variant="soft">
              {mutation.data.status}
            </Badge>
          </div>
        </Card>
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
    <Card as="form" onSubmit={submit}>
      <CardHeader
        eyebrow="Backtest"
        title="Backtest sweep"
        description="Grid over strategy, cost, top-N, and lookback. Capped at 50 runs."
      />
      <div className="mt-5 space-y-4">
        <Field label="Sweep name">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Tickers">
            <Input value={tickers} onChange={(e) => setTickers(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Weights">
            <Input value={weights} onChange={(e) => setWeights(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Initial cash">
            <Input
              type="number"
              value={initialCash}
              onChange={(e) => setInitialCash(Number(e.target.value))}
              adornmentLeft="$"
            />
          </Field>
          <Field label="Benchmark">
            <Input value={benchmark} onChange={(e) => setBenchmark(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Start date">
            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </Field>
          <Field label="End date">
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Strategies">
            <Input value={strategies} onChange={(e) => setStrategies(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Costs (bps)">
            <Input value={costs} onChange={(e) => setCosts(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Top N">
            <Input value={topNs} onChange={(e) => setTopNs(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Momentum lookback">
            <Input value={lookbacks} onChange={(e) => setLookbacks(e.target.value)} className="font-mono" />
          </Field>
        </div>
        {error && <div className="text-sm text-negative">{error}</div>}
        <Button type="submit" disabled={pending}>
          {pending ? "Running…" : "Run backtest sweep"}
        </Button>
      </div>
    </Card>
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
    <Card as="form" onSubmit={submit}>
      <CardHeader
        eyebrow="Forecast"
        title="Forecast sweep"
        description="Grid over method, horizon, sample count, and seed. Capped at 50 runs."
      />
      <div className="mt-5 space-y-4">
        <Field label="Sweep name">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Tickers">
            <Input value={tickers} onChange={(e) => setTickers(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Weights">
            <Input value={weights} onChange={(e) => setWeights(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Initial value">
            <Input
              type="number"
              value={initialValue}
              onChange={(e) => setInitialValue(Number(e.target.value))}
              adornmentLeft="$"
            />
          </Field>
          <Field label="Benchmark">
            <Input value={benchmark} onChange={(e) => setBenchmark(e.target.value)} className="font-mono" />
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Methods">
            <Input value={methods} onChange={(e) => setMethods(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Horizons">
            <Input value={horizons} onChange={(e) => setHorizons(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Simulations">
            <Input value={simulations} onChange={(e) => setSimulations(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Lookbacks">
            <Input value={lookbacks} onChange={(e) => setLookbacks(e.target.value)} className="font-mono" />
          </Field>
          <Field label="Seeds">
            <Input value={seeds} onChange={(e) => setSeeds(e.target.value)} className="font-mono" />
          </Field>
        </div>
        {error && <div className="text-sm text-negative">{error}</div>}
        <Button type="submit" disabled={pending}>
          {pending ? "Running…" : "Run forecast sweep"}
        </Button>
      </div>
    </Card>
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
        <SectionEyebrow as="h2">Sweep runs</SectionEyebrow>
        {sweepId && (
          <div className="flex gap-3 text-sm">
            <a href={api.exportSweepUrl(sweepId, "csv")} className="text-accent hover:underline">
              CSV
            </a>
            <a href={api.exportSweepUrl(sweepId, "json")} className="text-accent hover:underline">
              JSON
            </a>
          </div>
        )}
      </div>
      {error ? <ErrorBox message={errorMessage(error)} /> : null}
      <Card padded={false} className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="border-b border-border bg-surface-2/60 text-xs uppercase tracking-eyebrow text-muted">
              <tr>
                <th className="px-4 py-3">Index</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Linked run</th>
                <th className="px-4 py-3">Params</th>
                <th className="px-4 py-3">Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-muted">
                    Loading sweep runs…
                  </td>
                </tr>
              )}
              {!loading && runs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-12">
                    <EmptyState
                      icon={<IconGrid width={18} height={18} />}
                      title="No sweep selected yet"
                      description="Run a sweep above, or pick one from the History tab."
                      compact
                    />
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
                  <tr key={run.id} className="align-top transition-colors hover:bg-surface-2/40">
                    <td className="px-4 py-3 font-mono">{run.run_index}</td>
                    <td className="px-4 py-3">
                      <Badge tone={statusTone(run.status)} variant="soft">
                        {run.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {href && linkedId ? (
                        <Link href={href} className="text-accent hover:underline">
                          {linkedId.slice(0, 8)}
                        </Link>
                      ) : (
                        "–"
                      )}
                    </td>
                    <td className="max-w-sm px-4 py-3">
                      <code className="break-all rounded bg-surface-2/60 px-1.5 py-0.5 text-xs text-muted">
                        {JSON.stringify(run.params)}
                      </code>
                    </td>
                    <td className="max-w-xs px-4 py-3 text-xs text-negative">
                      {run.error_message ?? ""}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
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
      <div className="flex flex-wrap gap-3 text-sm">
        <Link
          href={`/backtest?id=${encodeURIComponent(item.id)}`}
          className="font-medium text-accent hover:underline"
        >
          Open
        </Link>
        <a
          href={api.exportBacktestUrl(item.id, "csv", "summary")}
          className="text-muted hover:text-fg"
        >
          CSV
        </a>
        <a href={api.exportBacktestUrl(item.id, "json")} className="text-muted hover:text-fg">
          JSON
        </a>
      </div>
    );
  }
  if (item.kind === "forecast") {
    return (
      <div className="flex flex-wrap gap-3 text-sm">
        <Link
          href={`/forecast?id=${encodeURIComponent(item.id)}`}
          className="font-medium text-accent hover:underline"
        >
          Open
        </Link>
        <a
          href={api.exportForecastUrl(item.id, "csv", "summary")}
          className="text-muted hover:text-fg"
        >
          CSV
        </a>
        <a href={api.exportForecastUrl(item.id, "json")} className="text-muted hover:text-fg">
          JSON
        </a>
      </div>
    );
  }
  if (item.kind === "sweep") {
    return (
      <div className="flex flex-wrap gap-3 text-sm">
        <button
          type="button"
          onClick={() => onOpenSweep(item.id)}
          className="font-medium text-accent hover:underline"
        >
          Runs
        </button>
        <a href={api.exportSweepUrl(item.id, "csv")} className="text-muted hover:text-fg">
          CSV
        </a>
        <a href={api.exportSweepUrl(item.id, "json")} className="text-muted hover:text-fg">
          JSON
        </a>
      </div>
    );
  }
  return <span className="text-sm text-muted">–</span>;
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

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) return `${error.code}: ${error.message}`;
  if (error instanceof Error) return error.message;
  return String(error);
}
