import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { formatCentsDisplay } from "../../lib/money";

export interface DonutSlice {
  key: string;
  label: string;
  cents: number;
  color: string;
}

interface CategoryDonutProps {
  slices: DonutSlice[];
  reduceMotion?: boolean;
}

interface TooltipPayloadEntry {
  payload: DonutSlice;
}

function DonutTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayloadEntry[] }) {
  if (!active || !payload?.length) return null;
  const slice = payload[0].payload;
  return (
    <div className="rounded-md border border-border/10 bg-surface-card px-2 py-1 text-xs shadow-lg">
      <p>{slice.label}</p>
      <p className="tabular-nums font-medium">{formatCentsDisplay(slice.cents)}</p>
    </div>
  );
}

// Legend is always shown (>= 2 series here) so category identity never
// relies on color alone -- each category already carries its own
// user-chosen brand color (set on the Categories page), which this chart
// reuses directly rather than assigning a new categorical palette.
export function CategoryDonut({ slices, reduceMotion = false }: CategoryDonutProps) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={slices}
          dataKey="cents"
          nameKey="label"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={2}
          isAnimationActive={!reduceMotion}
        >
          {slices.map((slice) => (
            <Cell key={slice.key} fill={slice.color} />
          ))}
        </Pie>
        <Tooltip content={<DonutTooltip />} />
        <Legend
          layout="vertical"
          verticalAlign="middle"
          align="right"
          wrapperStyle={{ fontSize: 12 }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
