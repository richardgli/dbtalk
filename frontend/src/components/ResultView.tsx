import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import type { QueryResultRow } from '../data/types';

interface ResultViewProps {
  rows?: QueryResultRow[];
}

type Shape =
  | { kind: 'empty' }
  | { kind: 'timeseries'; timeCol: string; valueCol: string; columns: string[] }
  | { kind: 'table'; columns: string[] };

const detectShape = (rows?: QueryResultRow[]): Shape => {
  if (!rows || rows.length === 0) return { kind: 'empty' };

  const columns = Object.keys(rows[0]);
  const timeCol = columns.find((col) => {
    const sample = rows[0][col];
    return typeof sample === 'string' && !Number.isNaN(Date.parse(sample));
  });
  const numericCols = columns.filter(
    (col) => col !== timeCol && typeof rows[0][col] === 'number'
  );

  if (timeCol && numericCols.length > 0) {
    return { kind: 'timeseries', timeCol, valueCol: numericCols[0], columns };
  }
  return { kind: 'table', columns };
}

export default function ResultView({ rows }: ResultViewProps) {
  const shape = detectShape(rows);

  if (shape.kind === 'empty') {
    return <p className="result-view__empty">No rows returned.</p>;
  }

  if (shape.kind === 'timeseries') {
    const data = rows!.map((r) => ({
      ...r,
      [shape.timeCol]: new Date(r[shape.timeCol] as string).toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: 'numeric',
      }),
    }));

    return (
      <div className="result-view__chart">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey={shape.timeCol} fontSize={12} tickLine={false} />
            <YAxis fontSize={12} tickLine={false} axisLine={false} width={36} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey={shape.valueCol}
              stroke="#587b7f"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Plain table fallback
  return (
    <div className="result-view__table-wrap">
      <table className="result-view__table">
        <thead>
          <tr>
            {shape.columns.map((col) => <th key={col}>{col}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows!.map((row, i) => (
            <tr key={i}>
              {shape.columns.map((col) => <td key={col}>{String(row[col])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}