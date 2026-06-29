import { useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import type { MetricsTable as MetricsData, MetricRow } from "../../api/types";

// The metrics grid (TanStack Table). Rows arrive in the canonical parity order
// from reports.metrics(mode="full"); we preserve that order by default and make
// columns sortable on demand. Numeric columns are right-aligned with tabular
// numerals — the signature of a pro financial UI.

export function MetricsTable({ data }: { data: MetricsData }) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const columns = useMemo<ColumnDef<MetricRow>[]>(() => {
    const cols: ColumnDef<MetricRow>[] = [
      {
        id: "label",
        header: "Metric",
        accessorKey: "label",
        cell: (c) => <span className="text-ink">{c.getValue() as string}</span>,
        enableSorting: false,
      },
    ];
    for (const col of data.columns) {
      cols.push({
        id: col,
        header: col,
        accessorFn: (row) => row.values[col],
        cell: (c) => (
          <span className="nums tabular-nums">{c.row.original.display[col] ?? "—"}</span>
        ),
        sortingFn: (a, b) => {
          const av = a.original.values[col];
          const bv = b.original.values[col];
          if (av === null && bv === null) return 0;
          if (av === null) return -1;
          if (bv === null) return 1;
          return (av as number) - (bv as number);
        },
      });
    }
    return cols;
  }, [data.columns]);

  const table = useReactTable({
    data: data.rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-hair">
              {hg.headers.map((h, i) => (
                <th
                  key={h.id}
                  onClick={h.column.getToggleSortingHandler()}
                  className={`py-2 px-3 font-medium text-muted select-none ${
                    i === 0 ? "text-left" : "text-right cursor-pointer"
                  }`}
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                  {{ asc: " ↑", desc: " ↓" }[h.column.getIsSorted() as string] ?? ""}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className="border-b border-hair/60 hover:bg-panel-2/60 transition-colors"
            >
              {row.getVisibleCells().map((cell, i) => (
                <td
                  key={cell.id}
                  className={`py-1.5 px-3 ${i === 0 ? "text-left" : "text-right"}`}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
