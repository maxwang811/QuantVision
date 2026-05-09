import { z } from "zod";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ApiError = z.object({
  error: z.object({ code: z.string(), message: z.string() }),
});

export class ApiRequestError extends Error {
  code: string;
  status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let code = "http_error";
    let message = res.statusText;
    try {
      const body = ApiError.parse(await res.json());
      code = body.error.code;
      message = body.error.message;
    } catch {
      // body wasn't a structured error; use status text
    }
    throw new ApiRequestError(res.status, code, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const Asset = z.object({
  id: z.string().uuid(),
  ticker: z.string(),
  name: z.string().nullable(),
  asset_class: z.string(),
  exchange: z.string().nullable(),
  currency: z.string(),
  created_at: z.string(),
});
export type Asset = z.infer<typeof Asset>;

export const PricePoint = z.object({
  date: z.string(),
  open: z.number().nullable().optional(),
  high: z.number().nullable().optional(),
  low: z.number().nullable().optional(),
  close: z.number().nullable().optional(),
  adj_close: z.number(),
  volume: z.number().nullable().optional(),
});
export type PricePoint = z.infer<typeof PricePoint>;

export const PriceSeries = z.object({
  ticker: z.string(),
  points: z.array(PricePoint),
});
export type PriceSeries = z.infer<typeof PriceSeries>;

export const Health = z.object({ status: z.string(), db: z.boolean() });
export type Health = z.infer<typeof Health>;

export const api = {
  health: () => apiFetch<Health>("/api/health").then((d) => Health.parse(d)),
  searchAssets: (q: string, limit = 20) =>
    apiFetch<unknown>(`/api/assets?q=${encodeURIComponent(q)}&limit=${limit}`).then((d) =>
      z.array(Asset).parse(d),
    ),
  prices: (ticker: string, opts: { start?: string; end?: string } = {}) => {
    const qs = new URLSearchParams();
    if (opts.start) qs.set("start", opts.start);
    if (opts.end) qs.set("end", opts.end);
    const path = `/api/prices/${encodeURIComponent(ticker)}${qs.toString() ? `?${qs}` : ""}`;
    return apiFetch<unknown>(path).then((d) => PriceSeries.parse(d));
  },
};
