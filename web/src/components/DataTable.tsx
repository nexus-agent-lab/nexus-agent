import { cn } from "@/lib/utils";

interface Column<T> {
  header: string;
  accessorKey: keyof T;
  cell?: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  className?: string;
  onRowClick?: (item: T) => void;
}

/**
 * A reusable table component for displaying data.
 */
export default function DataTable<T>({
  columns,
  data,
  className,
  onRowClick,
}: DataTableProps<T>) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-900",
        className
      )}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-neutral-500 dark:text-neutral-400">
          <thead className="bg-neutral-50 text-xs font-semibold uppercase text-neutral-700 dark:bg-neutral-800/50 dark:text-neutral-300">
            <tr>
              {columns.map((column, idx) => (
                <th key={idx} className="px-6 py-4">
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
            {data.length > 0 ? (
              data.map((item, rowIdx) => (
                <tr
                  key={rowIdx}
                  className={cn(
                    "bg-white transition-colors hover:bg-neutral-50 dark:bg-neutral-900 dark:hover:bg-neutral-800/50",
                    onRowClick && "cursor-pointer"
                  )}
                  onClick={() => onRowClick?.(item)}
                >
                  {columns.map((column, colIdx) => (
                    <td key={colIdx} className="whitespace-nowrap px-6 py-4">
                      {column.cell
                        ? column.cell(item)
                        : (item[column.accessorKey] as React.ReactNode)}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-6 py-12 text-center text-neutral-400 dark:text-neutral-500"
                >
                  No data available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
