import { Area, AreaChart, ResponsiveContainer, Tooltip } from "recharts";

import { formatCentsDisplay } from "../../lib/money";

export interface SparklinePoint {
  date: string;
  value: number;
}

interface SparklineProps {
  data: SparklinePoint[];
  color: string;
  reduceMotion?: boolean;
}

interface TooltipPayloadEntry {
  value: number;
  payload: SparklinePoint;
}

function SparklineTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-md border border-border/10 bg-surface-card px-2 py-1 text-xs shadow-lg">
      <p className="text-text-primary/60">{point.date}</p>
      <p className="tabular-nums font-medium">{formatCentsDisplay(point.value)}</p>
    </div>
  );
}

// No default chart chrome (no axes/gridlines) -- a sparkline is a trend
// glance, not an analytical chart.
export function Sparkline({ data, color, reduceMotion = false }: SparklineProps) {
  return (
    <ResponsiveContainer width="100%" height={48}>
      <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={`sparkline-fill-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Tooltip content={<SparklineTooltip />} />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          fill={`url(#sparkline-fill-${color.replace("#", "")})`}
          isAnimationActive={!reduceMotion}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
