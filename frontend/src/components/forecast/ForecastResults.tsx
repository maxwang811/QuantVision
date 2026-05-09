"use client";

import {
  ApiRequestError,
  api,
  type ForecastOut,
} from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { ForecastDistributionChart } from "./ForecastDistributionChart";
import { ForecastMetrics } from "./ForecastMetrics";
import { ForecastPathChart } from "./ForecastPathChart";

interface Props {
  forecastId: string;
  initial?: ForecastOut;
}

export function ForecastResults({ forecastId, initial }: Props) {
  const summary = useQuery({
    queryKey: ["forecast", forecastId],
    queryFn: () => api.getForecast(forecastId),
    initialData: initial && initial.id === forecastId ? initial : undefined,
  });

  const completed = summary.data?.status === "completed";

  const paths = useQuery({
    queryKey: ["forecast", forecastId, "paths"],
    queryFn: () => api.getForecastPaths(forecastId),
    enabled: completed,
  });

  const distribution = useQuery({
    queryKey: ["forecast", forecastId, "distribution"],
    queryFn: () => api.getForecastDistribution(forecastId),
    enabled: completed,
  });

  if (summary.isError) {
    return <ErrorBox message={errorMessage(summary.error)} />;
  }

  if (!summary.data) return <Skeleton />;

  if (summary.data.status === "failed") {
    return (
      <div className="rounded-lg border border-negative/40 bg-negative/5 p-4 text-sm text-negative">
        Forecast failed: {summary.data.error_message ?? "(no message)"}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ForecastMetrics forecast={summary.data} />

      {paths.isError && <ErrorBox message={errorMessage(paths.error)} />}
      {distribution.isError && <ErrorBox message={errorMessage(distribution.error)} />}

      {paths.data ? <ForecastPathChart paths={paths.data} /> : <ChartSkeleton />}
      {distribution.data ? (
        <ForecastDistributionChart distribution={distribution.data} />
      ) : (
        <ChartSkeleton compact />
      )}
    </div>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) return `${error.code}: ${error.message}`;
  return String(error);
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-negative/40 bg-negative/5 p-4 text-sm text-negative">
      {message}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-3">
      <div className="h-28 animate-pulse rounded-lg border border-border bg-border/20" />
      <ChartSkeleton />
      <ChartSkeleton compact />
    </div>
  );
}

function ChartSkeleton({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={`animate-pulse rounded-lg border border-border bg-border/20 ${
        compact ? "h-72" : "h-80"
      }`}
    />
  );
}
