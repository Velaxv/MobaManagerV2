import React, { useState, useMemo } from 'react';
import { ArrowUpDown, ChevronDown, ChevronUp, Search } from 'lucide-react';

export interface ColumnDef<T> {
  header: string;
  accessorKey: keyof T | ((row: T) => any);
  cell?: (value: any, row: T) => React.ReactNode;
  sortable?: boolean;
}

interface DataGridProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  searchPlaceholder?: string;
  searchKey?: keyof T;
  rowsPerPage?: number;
}

export function DataGrid<T extends { id: string | number }>({
  data,
  columns,
  searchPlaceholder = "Buscar...",
  searchKey,
  rowsPerPage = 10,
}: DataGridProps<T>) {
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Lógica de ordenação
  const handleSort = (key: string, sortable?: boolean) => {
    if (!sortable) return;
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  // Filtragem e busca
  const filteredData = useMemo(() => {
    return data.filter((row) => {
      if (!searchTerm || !searchKey) return true;
      const val = row[searchKey];
      if (val === undefined || val === null) return false;
      return String(val).toLowerCase().includes(searchTerm.toLowerCase());
    });
  }, [data, searchTerm, searchKey]);

  // Ordenação dos dados filtrados
  const sortedData = useMemo(() => {
    const sortableItems = [...filteredData];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        const col = columns.find((c, idx) => {
          const key = typeof c.accessorKey === 'string' ? c.accessorKey : String(idx);
          return key === sortConfig.key;
        });

        let aVal = (a as any)[sortConfig.key];
        let bVal = (b as any)[sortConfig.key];

        if (col && typeof col.accessorKey === 'function') {
          aVal = col.accessorKey(a);
          bVal = col.accessorKey(b);
        }
        
        // Se for string, compara local
        if (typeof aVal === 'string' && typeof bVal === 'string') {
          return sortConfig.direction === 'asc' 
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal);
        }
        
        // Compara numérico
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sortableItems;
  }, [filteredData, sortConfig]);

  // Paginação
  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * rowsPerPage;
    return sortedData.slice(startIndex, startIndex + rowsPerPage);
  }, [sortedData, currentPage, rowsPerPage]);

  const totalPages = Math.ceil(sortedData.length / rowsPerPage);

  // Helper para formatar atributos no estilo brutalista do FM (escala 1-20)
  const renderAttributeBadge = (value: number) => {
    if (value >= 16) {
      return (
        <span className="font-mono font-bold text-emerald-400 bg-emerald-950/50 border border-emerald-700/60 px-2 py-0.5 rounded text-sm tracking-tighter">
          {value}
        </span>
      );
    } else if (value >= 11) {
      return (
        <span className="font-mono font-bold text-sky-400 bg-sky-950/50 border border-sky-700/60 px-2 py-0.5 rounded text-sm tracking-tighter">
          {value}
        </span>
      );
    } else if (value >= 6) {
      return (
        <span className="font-mono text-neutral-400 bg-neutral-900 border border-neutral-800 px-2 py-0.5 rounded text-sm tracking-tighter">
          {value}
        </span>
      );
    } else {
      return (
        <span className="font-mono font-semibold text-red-400 bg-red-950/30 border border-red-900/50 px-2 py-0.5 rounded text-sm tracking-tighter">
          {value}
        </span>
      );
    }
  };

  return (
    <div className="flex flex-col h-full bg-black/40 border border-lol-hq-cyan/15 text-white font-sans rounded-sm overflow-hidden shadow-hq-glass backdrop-blur-sm">
      {searchKey && (
        <div className="flex items-center gap-2 p-3 bg-hq-header border-b border-lol-hq-cyan/12">
          <Search className="w-4 h-4 text-lol-hq-cyan/70" />
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full max-w-sm bg-black/50 border border-white/10 focus:border-lol-hq-cyan focus:outline-none focus:shadow-hq-cyan-sm text-sm px-3 py-1.5 font-mono text-white placeholder:text-white/30 rounded-sm transition-all"
          />
          <div className="ml-auto text-[10px] text-lol-hq-cyan/50 font-mono uppercase tracking-wider">
            {sortedData.length} registros
          </div>
        </div>
      )}

      <div className="overflow-x-auto flex-grow">
        <table className="w-full text-left border-collapse select-none">
          <thead>
            <tr className="bg-black/35 border-b border-lol-hq-cyan/15 font-mono text-[10px] uppercase tracking-wider text-white/45">
              {columns.map((col, idx) => {
                const sortKey = typeof col.accessorKey === 'string' ? col.accessorKey : String(idx);
                const isSorted = sortConfig?.key === sortKey;

                return (
                  <th
                    key={idx}
                    onClick={() => handleSort(sortKey, col.sortable)}
                    className={`px-4 py-3 font-semibold select-none ${col.sortable ? 'cursor-pointer hover:bg-white/5 hover:text-lol-hq-cyan transition-colors' : ''}`}
                  >
                    <div className="flex items-center gap-1.5">
                      {col.header}
                      {col.sortable &&
                        (isSorted ? (
                          sortConfig.direction === 'asc' ? (
                            <ChevronUp className="w-3 h-3 text-lol-hq-cyan" />
                          ) : (
                            <ChevronDown className="w-3 h-3 text-lol-hq-cyan" />
                          )
                        ) : (
                          <ArrowUpDown className="w-3 h-3 text-white/20" />
                        ))}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-sm">
            {paginatedData.length > 0 ? (
              paginatedData.map((row) => (
                <tr key={row.id} className="hover:bg-lol-hextech/20 transition-colors">
                  {columns.map((col, colIdx) => {
                    let value;
                    if (typeof col.accessorKey === 'function') {
                      value = col.accessorKey(row);
                    } else {
                      value = row[col.accessorKey];
                    }

                    return (
                      <td key={colIdx} className="px-4 py-2 text-white/75 font-sans">
                        {col.cell ? (
                          col.cell(value, row)
                        ) : typeof value === 'number' ? (
                          renderAttributeBadge(value)
                        ) : (
                          <span className="text-white/90">{String(value ?? '')}</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-white/35 font-mono text-xs">
                  Nenhum registro encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between p-3 bg-black/40 border-t border-white/5 text-[10px] font-mono">
          <button
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((c) => Math.max(1, c - 1))}
            className="btn-lol py-1 px-2 disabled:opacity-30"
          >
            Anterior
          </button>
          <span className="text-white/40">
            Página <span className="text-white">{currentPage}</span> / {totalPages}
          </span>
          <button
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((c) => Math.min(totalPages, c + 1))}
            className="btn-lol py-1 px-2 disabled:opacity-30"
          >
            Próximo
          </button>
        </div>
      )}
    </div>
  );
}
