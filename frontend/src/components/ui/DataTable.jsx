import React, { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown, Search } from 'lucide-react';

export default function DataTable({ columns, data = [], onRowClick, searchable = true, pageSize = 20, emptyMessage = 'No data available' }) {
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    if (!query) return data;
    const q = query.toLowerCase();
    return data.filter(row =>
      columns.some(col => {
        const val = col.accessor ? row[col.accessor] : col.cell?.(row);
        return String(val ?? '').toLowerCase().includes(q);
      })
    );
  }, [data, query, columns]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    return [...filtered].sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      const cmp = String(av).localeCompare(String(bv), undefined, { numeric: true });
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  const pages = Math.ceil(sorted.length / pageSize);
  const paginated = sorted.slice(page * pageSize, (page + 1) * pageSize);

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
    setPage(0);
  };

  return (
    <div className="flex flex-col gap-3">
      {searchable && (
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input
            className="form-input pl-9 py-2"
            placeholder="Search..."
            value={query}
            onChange={e => { setQuery(e.target.value); setPage(0); }}
          />
        </div>
      )}
      <div className="overflow-x-auto rounded-lg border border-neutral-200">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              {columns.map(col => (
                <th
                  key={col.key || col.accessor}
                  className={`table-header select-none ${col.sortable !== false && col.accessor ? 'cursor-pointer hover:bg-neutral-100' : ''}`}
                  onClick={() => col.sortable !== false && col.accessor && handleSort(col.accessor)}
                >
                  <div className="flex items-center gap-1">
                    {col.header}
                    {col.accessor && sortKey === col.accessor && (
                      sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr><td colSpan={columns.length} className="table-cell text-center text-neutral-400 py-10">{emptyMessage}</td></tr>
            ) : paginated.map((row, i) => (
              <tr key={i} className={`table-row ${onRowClick ? 'cursor-pointer' : ''}`} onClick={() => onRowClick?.(row)}>
                {columns.map(col => (
                  <td key={col.key || col.accessor} className="table-cell">
                    {col.cell ? col.cell(row) : (row[col.accessor] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="flex items-center justify-between text-xs text-neutral-500">
          <span>{sorted.length} results</span>
          <div className="flex gap-1">
            <button className="btn btn-secondary btn-sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Prev</button>
            <span className="px-3 py-1.5 rounded border border-neutral-200 bg-white">{page + 1} / {pages}</span>
            <button className="btn btn-secondary btn-sm" disabled={page >= pages - 1} onClick={() => setPage(p => p + 1)}>Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
