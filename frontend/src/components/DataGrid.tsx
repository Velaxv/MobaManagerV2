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
    <div className="flex flex-col h-full bg-neutral-900 border-2 border-neutral-800 text-neutral-100 font-sans shadow-md">
      {/* Barra de busca e utilitários */}
      {searchKey && (
        <div className="flex items-center gap-2 p-3 bg-neutral-950 border-b border-neutral-800">
          <Search className="w-4 h-4 text-neutral-500" />
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full max-w-sm bg-neutral-900 border border-neutral-800 focus:border-red-500 focus:outline-none text-sm px-3 py-1.5 font-mono text-neutral-200 placeholder:text-neutral-600 rounded transition-all"
          />
          <div className="ml-auto text-xs text-neutral-500 font-mono">
            Mostrando {sortedData.length} registros
          </div>
        </div>
      )}

      {/* Grid de Dados */}
      <div className="overflow-x-auto flex-grow">
        <table className="w-full text-left border-collapse select-none">
          <thead>
            <tr className="bg-neutral-950/80 border-b border-neutral-800 font-mono text-xs uppercase tracking-wider text-neutral-400">
              {columns.map((col, idx) => {
                const sortKey = typeof col.accessorKey === 'string' ? col.accessorKey : String(idx);
                const isSorted = sortConfig?.key === sortKey;
                
                return (
                  <th
                    key={idx}
                    onClick={() => handleSort(sortKey, col.sortable)}
                    className={`px-4 py-3 font-semibold select-none ${col.sortable ? 'cursor-pointer hover:bg-neutral-900 hover:text-white transition-colors' : ''}`}
                  >
                    <div className="flex items-center gap-1.5">
                      {col.header}
                      {col.sortable && (
                        isSorted ? (
                          sortConfig.direction === 'asc' ? <ChevronUp className="w-3 h-3 text-red-500" /> : <ChevronDown className="w-3 h-3 text-red-500" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 text-neutral-600" />
                        )
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800 font-mono text-sm">
            {paginatedData.length > 0 ? (
              paginatedData.map((row) => (
                <tr
                  key={row.id}
                  className="hover:bg-neutral-800/40 transition-colors border-b border-neutral-800"
                >
                  {columns.map((col, colIdx) => {
                    let value;
                    if (typeof col.accessorKey === 'function') {
                      value = col.accessorKey(row);
                    } else {
                      value = row[col.accessorKey];
                    }

                    return (
                      <td key={colIdx} className="px-4 py-2 text-neutral-300 font-sans">
                        {col.cell ? (
                          col.cell(value, row)
                        ) : typeof value === 'number' ? (
                          renderAttributeBadge(value)
                        ) : (
                          <span className="font-sans text-neutral-200">{value}</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-neutral-500 font-mono">
                  Nenhum registro encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Paginação */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between p-3 bg-neutral-950 border-t border-neutral-800 text-xs font-mono">
          <button
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((c) => Math.max(1, c - 1))}
            className="px-2.5 py-1.5 bg-neutral-900 border border-neutral-800 disabled:opacity-30 hover:border-red-500 hover:text-white transition-all rounded disabled:hover:border-neutral-800"
          >
            Anterior
          </button>
          <span className="text-neutral-500">
            Página <span className="text-neutral-200">{currentPage}</span> de <span className="text-neutral-200">{totalPages}</span>
          </span>
          <button
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((c) => Math.min(totalPages, c + 1))}
            className="px-2.5 py-1.5 bg-neutral-900 border border-neutral-800 disabled:opacity-30 hover:border-red-500 hover:text-white transition-all rounded disabled:hover:border-neutral-800"
          >
            Próximo
          </button>
        </div>
      )}
    </div>
  );
}
