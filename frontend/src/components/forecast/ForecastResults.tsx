"use client";

import { ErrorBox } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
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

  if (!summary.data) return <ResultsSkeleton />;

  if (summary.data.status === "failed") {
    return (
      <ErrorBox message={`Forecast failed: ${summary.data.error_message ?? "(no message)"}`} />
    );
  }

  return (
    <div className="space-y-6">
      <ForecastMetrics forecast={summary.data} />

      {paths.isError && <ErrorBox message={errorMessage(paths.error)} />}
      {distribution.isError && <ErrorBox message={errorMessage(distribution.error)} />}

      {paths.data ? <ForecastPathChart paths={paths.data} /> : <Skeleton className="h-80" />}
      {distribution.data ? (
        <ForecastDistributionChart distribution={distribution.data} />
      ) : (
        <Skeleton className="h-72" />
      )}
    </div>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) return `${error.code}: ${error.message}`;
  return String(error);
}

function ResultsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-80" />
      <Skeleton className="h-72" />
    </div>
  );
}
