import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'

// ---------------------------------------------------------------------------
// Shared Recharts configuration so every chart keeps the race-control theme.
// ---------------------------------------------------------------------------

export const PALETTE = [
  '#e10600',
  '#2ea8ff',
  '#00d17a',
  '#ffb400',
  '#a06bff',
  '#ff6f91',
  '#4dd0e1',
  '#c0ca33',
  '#ff8a65',
  '#7986cb',
]

export const AXIS = {
  stroke: 'var(--line-strong)',
  tick: { fill: 'var(--muted)', fontSize: 11 },
}

export function ChartBox({ height = 300, children, empty }) {
  if (empty) return <div className="chart-empty">{empty}</div>
  return (
    <div className="chart-box" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  )
}

const tooltipStyle = {
  contentStyle: {
    background: 'var(--tooltip-bg)',
    border: '1px solid var(--line-strong)',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: 'var(--text)' },
  itemStyle: { color: 'var(--text-dim)' },
}

export function TelemetryLine({
  data,
  x,
  lines,
  height = 300,
  xLabel,
  yLabel,
}) {
  return (
    <ChartBox height={height} empty={!data || data.length === 0 ? 'No series data' : null}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid stroke="var(--line-strong)" strokeDasharray="3 3" />
        <XAxis dataKey={x} {...AXIS} label={xLabel} />
        <YAxis {...AXIS} label={yLabel} width={48} />
        <Tooltip {...tooltipStyle} />
        {lines.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {lines.map((line, i) => (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            name={line.name || line.key}
            stroke={line.color || PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ChartBox>
  )
}

export function TelemetryBar({
  data,
  x,
  bars,
  height = 300,
  layout = 'horizontal',
  stacked = false,
}) {
  return (
    <ChartBox height={height} empty={!data || data.length === 0 ? 'No series data' : null}>
      <BarChart
        data={data}
        layout={layout}
        margin={{ top: 8, right: 16, left: layout === 'vertical' ? 30 : 0, bottom: 4 }}
      >
        <CartesianGrid stroke="var(--line-strong)" strokeDasharray="3 3" />
        {layout === 'vertical' ? (
          <>
            <XAxis type="number" {...AXIS} />
            <YAxis type="category" dataKey={x} {...AXIS} width={110} />
          </>
        ) : (
          <>
            <XAxis dataKey={x} {...AXIS} />
            <YAxis {...AXIS} width={48} />
          </>
        )}
        <Tooltip {...tooltipStyle} cursor={{ fill: 'var(--grid-hover)' }} />
        {bars.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {bars.map((bar, i) => (
          <Bar
            key={bar.key}
            dataKey={bar.key}
            name={bar.name || bar.key}
            stackId={stacked ? 'a' : undefined}
            fill={bar.color || PALETTE[i % PALETTE.length]}
            radius={[3, 3, 0, 0]}
          >
            {bar.cellColorBy
              ? data.map((entry, idx) => (
                  <Cell key={idx} fill={bar.cellColorBy(entry, idx)} />
                ))
              : null}
          </Bar>
        ))}
      </BarChart>
    </ChartBox>
  )
}

export function ScatterPlot({
  data,
  x,
  y,
  color = '#e10600',
  height = 320,
  xLabel,
  yLabel,
  tooltipFormatter,
}) {
  return (
    <ChartBox height={height} empty={!data || data.length === 0 ? 'No point data' : null}>
      <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="var(--line-strong)" strokeDasharray="3 3" />
        <XAxis type="number" dataKey={x} name={xLabel || x} {...AXIS} />
        <YAxis type="number" dataKey={y} name={yLabel || y} {...AXIS} width={48} />
        <ZAxis range={[36, 36]} />
        <Tooltip {...tooltipStyle} formatter={tooltipFormatter} />
        <Scatter data={data} fill={color} fillOpacity={0.7} />
      </ScatterChart>
    </ChartBox>
  )
}

export function MultiScatter({ series, x, y, height = 340, xLabel, yLabel }) {
  return (
    <ChartBox height={height} empty={!series || series.length === 0 ? 'No point data' : null}>
      <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="var(--line-strong)" strokeDasharray="3 3" />
        <XAxis type="number" dataKey={x} name={xLabel || x} {...AXIS} />
        <YAxis type="number" dataKey={y} name={yLabel || y} {...AXIS} width={48} />
        <ZAxis range={[30, 30]} />
        <Tooltip {...tooltipStyle} />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {series.map((group, i) => (
          <Scatter
            key={group.name}
            name={group.name}
            data={group.data}
            fill={PALETTE[i % PALETTE.length]}
            fillOpacity={0.75}
          />
        ))}
      </ScatterChart>
    </ChartBox>
  )
}

export function Donut({ data, nameKey = 'name', valueKey = 'value', height = 300, colors }) {
  return (
    <ChartBox height={height} empty={!data || data.length === 0 ? 'No distribution' : null}>
      <PieChart>
        <Tooltip {...tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={nameKey}
          innerRadius="52%"
          outerRadius="78%"
          paddingAngle={2}
          stroke="var(--bg)"
        >
          {data.map((entry, idx) => (
            <Cell
              key={idx}
              fill={(colors && colors[entry[nameKey]]) || PALETTE[idx % PALETTE.length]}
            />
          ))}
        </Pie>
      </PieChart>
    </ChartBox>
  )
}

export function TelemetryArea({ data, x, areas, height = 300 }) {
  return (
    <ChartBox height={height} empty={!data || data.length === 0 ? 'No series data' : null}>
      <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
        <defs>
          {areas.map((area, i) => (
            <linearGradient key={area.key} id={`grad-${area.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={area.color || PALETTE[i % PALETTE.length]} stopOpacity={0.55} />
              <stop offset="100%" stopColor={area.color || PALETTE[i % PALETTE.length]} stopOpacity={0.04} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid stroke="var(--line-strong)" strokeDasharray="3 3" />
        <XAxis dataKey={x} {...AXIS} />
        <YAxis {...AXIS} width={48} />
        <Tooltip {...tooltipStyle} />
        {areas.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {areas.map((area, i) => (
          <Area
            key={area.key}
            type="monotone"
            dataKey={area.key}
            name={area.name || area.key}
            stroke={area.color || PALETTE[i % PALETTE.length]}
            fill={`url(#grad-${area.key})`}
            strokeWidth={2}
          />
        ))}
      </AreaChart>
    </ChartBox>
  )
}
