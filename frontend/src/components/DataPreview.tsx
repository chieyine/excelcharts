"use client";

import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Table, ChevronDown, ChevronUp, Search, X } from 'lucide-react';

interface DataPreviewProps {
    dataset: Record<string, unknown>[];
    filename?: string;
    maxRows?: number;
}

export default function DataPreview({ 
    dataset, 
    filename = "Your Data",
    maxRows = 100 
}: DataPreviewProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [sortColumn, setSortColumn] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

    // Get column headers
    const columns = useMemo(() => {
        if (dataset.length === 0) return [];
        return Object.keys(dataset[0]);
    }, [dataset]);

    // Filter and sort data
    const processedData = useMemo(() => {
        let data = [...dataset];

        // Apply search filter
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            data = data.filter(row => 
                Object.values(row).some(value => 
                    String(value).toLowerCase().includes(query)
                )
            );
        }

        // Apply sorting
        if (sortColumn) {
            data.sort((a, b) => {
                const aVal = a[sortColumn];
                const bVal = b[sortColumn];
                
                // Handle null/undefined
                if (aVal == null) return sortDirection === 'asc' ? 1 : -1;
                if (bVal == null) return sortDirection === 'asc' ? -1 : 1;
                
                // Numeric comparison
                if (typeof aVal === 'number' && typeof bVal === 'number') {
                    return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
                }
                
                // String comparison
                const aStr = String(aVal).toLowerCase();
                const bStr = String(bVal).toLowerCase();
                return sortDirection === 'asc' 
                    ? aStr.localeCompare(bStr) 
                    : bStr.localeCompare(aStr);
            });
        }

        return data.slice(0, maxRows);
    }, [dataset, searchQuery, sortColumn, sortDirection, maxRows]);

    const handleSort = (column: string) => {
        if (sortColumn === column) {
            setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortColumn(column);
            setSortDirection('asc');
        }
    };

    const formatCellValue = (value: unknown): string => {
        if (value == null) return '—';
        if (typeof value === 'number') {
            // Format numbers nicely
            if (Number.isInteger(value)) return value.toLocaleString();
            return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
        }
        if (typeof value === 'boolean') return value ? 'Yes' : 'No';
        return String(value);
    };

    if (dataset.length === 0) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-8 bg-white rounded-3xl shadow-elegant border-refined overflow-hidden"
        >
            {/* Header - Always visible */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full px-6 py-4 sm:px-8 sm:py-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-100 rounded-lg">
                        <Table className="w-5 h-5 text-gray-600" />
                    </div>
                    <div className="text-left">
                        <h3 className="text-base font-medium text-gray-900">
                            {filename ? `View: ${filename}` : 'View Your Data'}
                        </h3>
                        <p className="text-sm text-gray-500">
                            {dataset.length.toLocaleString()} rows • {columns.length} columns
                        </p>
                    </div>
                </div>
                <motion.div
                    animate={{ rotate: isExpanded ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="p-2 text-gray-400"
                >
                    <ChevronDown className="w-5 h-5" />
                </motion.div>
            </button>

            {/* Expandable Content */}
            {isExpanded && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="border-t border-gray-100"
                >
                    {/* Search Bar */}
                    <div className="px-6 py-4 sm:px-8 bg-gray-50 border-b border-gray-100">
                        <div className="relative max-w-md">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Search your data..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-10 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent bg-white"
                            />
                            {searchQuery && (
                                <button
                                    onClick={() => setSearchQuery('')}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                        {searchQuery && (
                            <p className="mt-2 text-xs text-gray-500">
                                Found {processedData.length} matching rows
                            </p>
                        )}
                    </div>

                    {/* Table */}
                    <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-gray-50 sticky top-0">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12">
                                        #
                                    </th>
                                    {columns.map((col) => (
                                        <th
                                            key={col}
                                            onClick={() => handleSort(col)}
                                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors whitespace-nowrap"
                                        >
                                            <div className="flex items-center gap-1">
                                                <span className="truncate max-w-[150px]" title={col}>
                                                    {col}
                                                </span>
                                                {sortColumn === col && (
                                                    sortDirection === 'asc' 
                                                        ? <ChevronUp className="w-3 h-3" />
                                                        : <ChevronDown className="w-3 h-3" />
                                                )}
                                            </div>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-100">
                                {processedData.map((row, idx) => (
                                    <tr 
                                        key={idx} 
                                        className="hover:bg-gray-50 transition-colors"
                                    >
                                        <td className="px-4 py-3 text-gray-400 text-xs">
                                            {idx + 1}
                                        </td>
                                        {columns.map((col) => (
                                            <td 
                                                key={col}
                                                className="px-4 py-3 text-gray-700 whitespace-nowrap"
                                                title={formatCellValue(row[col])}
                                            >
                                                <span className="block truncate max-w-[200px]">
                                                    {formatCellValue(row[col])}
                                                </span>
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Footer */}
                    {dataset.length > maxRows && (
                        <div className="px-6 py-3 sm:px-8 bg-gray-50 border-t border-gray-100 text-center">
                            <p className="text-xs text-gray-500">
                                Showing first {maxRows} of {dataset.length.toLocaleString()} rows
                            </p>
                        </div>
                    )}
                </motion.div>
            )}
        </motion.div>
    );
}
