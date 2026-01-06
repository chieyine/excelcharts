"use client";

import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { ChartCandidate, AnalysisResult } from '@/types';
import embed, { VisualizationSpec } from 'vega-embed';
import { View } from 'vega';
import { Download, Copy, Sparkles, Share2, Settings } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { createShareLink, generateNarrativeReport } from '@/services/api';
import { useToast } from '@/components/Toast';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import DataPreview from '@/components/DataPreview';
import ReportGenerator from '@/components/ReportGenerator';
import { FileText, X } from 'lucide-react';

interface ChartViewerProps {
    candidate: ChartCandidate;
    dataset: Record<string, unknown>[];
    alternatives?: ChartCandidate[];
    insights?: string[];
    surprise?: AnalysisResult['surprise'];
    onChartChange?: (candidate: ChartCandidate) => void;
    result?: AnalysisResult; // Full result for sharing
    file?: File; // For generating things that require re-upload like executive summary
}

export default function ChartViewer({ 
    candidate, 
    dataset, 
    alternatives = [], 
    insights = [],
    surprise,
    onChartChange,
    result,
    file
}: ChartViewerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const viewRef = useRef<View | null>(null);
    const [view, setView] = useState<View | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedChart, setSelectedChart] = useState<ChartCandidate>(candidate);
    const [showSurprise, setShowSurprise] = useState(false);
    const [isSharing, setIsSharing] = useState(false);
    
    // Detailed Report State
    const [isGeneratingReport, setIsGeneratingReport] = useState(false);
    const [reportMarkdown, setReportMarkdown] = useState<string | null>(null);

    const toast = useToast();
    
    // Axis customization state
    const [showAxisPanel, setShowAxisPanel] = useState(false);
    const [showGrid, setShowGrid] = useState(true);
    const [showLabels, setShowLabels] = useState(true);
    const [xAxisTitle, setXAxisTitle] = useState('');
    const [yAxisTitle, setYAxisTitle] = useState('');
    
    // Chart categorization state
    const [activeFilter, setActiveFilter] = useState<string>('all');
    const [expandedColumns, setExpandedColumns] = useState<Set<string>>(new Set());
    const [allChartsExpanded, setAllChartsExpanded] = useState(false); // Section collapsed by default
    const [showAllCharts, setShowAllCharts] = useState(false); // Show only 6 initially
    
    // Compute unique chart types for filter tabs
    const chartTypes = useMemo(() => {
        const types = new Set(alternatives.map(alt => alt.chart_type));
        return ['all', ...Array.from(types)];
    }, [alternatives]);
    
    // Group charts by column and filter by type
    const { topCharts, groupedByColumn, filteredCharts } = useMemo(() => {
        // Top 5 recommendations (highest score)
        const top = alternatives.slice(0, 5);
        
        // Filter by active type
        const filtered = activeFilter === 'all' 
            ? alternatives 
            : alternatives.filter(alt => alt.chart_type === activeFilter);
        
        // Group remaining by column (x_column)
        const grouped: Record<string, typeof alternatives> = {};
        filtered.slice(5).forEach(alt => {
            const column = alt.x_column || 'Other';
            if (!grouped[column]) grouped[column] = [];
            grouped[column].push(alt);
        });
        
        return { topCharts: top, groupedByColumn: grouped, filteredCharts: filtered };
    }, [alternatives, activeFilter]);

    // AI Grouping for Organized Display (AI Sections)
    const groupedCharts = useMemo(() => {
        const groups: Record<string, typeof alternatives> = {};
        filteredCharts.forEach(chart => {
            const name = chart.group_name || 'Additional Analysis';
            if (!groups[name]) groups[name] = [];
            groups[name].push(chart);
        });
        return groups;
    }, [filteredCharts]);
    
    const toggleColumnExpand = (column: string) => {
        setExpandedColumns(prev => {
            const next = new Set(prev);
            if (next.has(column)) next.delete(column);
            else next.add(column);
            return next;
        });
    };


    // Filter out null/undefined values from dataset to prevent "undefined" labels in charts
    const cleanDataset = useMemo(() => {
        return dataset.map(row => {
            const cleanRow: Record<string, unknown> = {};
            for (const [key, value] of Object.entries(row)) {
                // Replace null/undefined with empty string for categorical, keep as-is for numbers
                cleanRow[key] = value === null || value === undefined ? '' : value;
            }
            return cleanRow;
        }).filter(row => {
            // Also filter out rows where the main categorical field is empty
            const values = Object.values(row);
            return values.some(v => v !== '' && v !== null && v !== undefined);
        });
    }, [dataset]);

    // Helper to truncate title
    const truncateTitle = (title: string, maxLength: number = 60) => {
        if (title.length <= maxLength) return title;
        return title.slice(0, maxLength - 3) + '...';
    };

    // Helper to extract meaningful part of title (e.g., bracketed text)
    const extractSmartTitle = (title: string, maxLength: number = 50) => {
        // Try to extract text in brackets [text] or (text)
        const bracketMatch = title.match(/\[([^\]]+)\]/);
        if (bracketMatch && bracketMatch[1]) {
            const extracted = bracketMatch[1].trim();
            if (extracted.length <= maxLength) return extracted;
            return extracted.slice(0, maxLength - 3) + '...';
        }
        
        const parenMatch = title.match(/\(([^)]+)\)/);
        if (parenMatch && parenMatch[1]) {
            const extracted = parenMatch[1].trim();
            if (extracted.length <= maxLength) return extracted;
            return extracted.slice(0, maxLength - 3) + '...';
        }
        
        // Fallback: truncate the title
        if (title.length <= maxLength) return title;
        return title.slice(0, maxLength - 3) + '...';
    };

    // Memoize the spec to prevent unnecessary re-renders
    const chartSpec = useMemo(() => {
        const activeCandidate = showSurprise && surprise ? {
            spec: surprise.spec,
            title: surprise.insight,
            chart_type: surprise.chart_type
        } : selectedChart;
        
        if (!activeCandidate.spec) return null;
        const spec = JSON.parse(JSON.stringify({ ...activeCandidate.spec, data: { values: cleanDataset } })) as VisualizationSpec;
        
        // Apply smart title extraction to the chart's internal title
        const specWithTitle = spec as VisualizationSpec & { title?: { text?: string } | string };
        if (specWithTitle.title) {
            if (typeof specWithTitle.title === 'object' && specWithTitle.title.text) {
                specWithTitle.title.text = extractSmartTitle(specWithTitle.title.text, 50);
            } else if (typeof specWithTitle.title === 'string') {
                (specWithTitle as { title: string }).title = extractSmartTitle(specWithTitle.title, 50);
            }
        }
        
        // Apply axis customizations
        const specWithConfig = spec as VisualizationSpec & { 
            config?: { axis?: Record<string, unknown> }, 
            encoding?: { x?: { title?: string, axis?: Record<string, unknown> }, y?: { title?: string, axis?: Record<string, unknown> } } 
        };
        
        // Configure grid visibility
        if (specWithConfig.config) {
            specWithConfig.config.axis = {
                ...specWithConfig.config.axis,
                grid: showGrid,
                labels: showLabels
            };
        }
        
        // Apply custom axis titles
        if (specWithConfig.encoding) {
            if (xAxisTitle && specWithConfig.encoding.x) {
                specWithConfig.encoding.x.title = xAxisTitle;
            }
            if (yAxisTitle && specWithConfig.encoding.y) {
                specWithConfig.encoding.y.title = yAxisTitle;
            }
        }
        
        // Add animations - use type guard for mark property
        const specWithMark = spec as VisualizationSpec & { mark?: { type?: string } };
        if (specWithMark.mark && typeof specWithMark.mark === 'object' && specWithMark.mark.type) {
            if (specWithMark.mark.type === 'line') {
                specWithMark.mark = { ...specWithMark.mark, strokeWidth: 3, interpolate: 'monotone' } as typeof specWithMark.mark;
            } else if (specWithMark.mark.type === 'bar') {
                specWithMark.mark = { ...specWithMark.mark, cornerRadiusEnd: 4 } as typeof specWithMark.mark;
            }
        }
        
        return spec;
    }, [selectedChart, cleanDataset, showSurprise, surprise, showGrid, showLabels, xAxisTitle, yAxisTitle]);

    useEffect(() => {
        if (!containerRef.current || !chartSpec) {
            setIsLoading(false);
            return;
        }

        setIsLoading(true);
        setError(null);

        // Clean up previous view
        if (viewRef.current) {
            try {
                viewRef.current.finalize();
            } catch {
                // Ignore errors during cleanup
            }
            viewRef.current = null;
        }

        let isMounted = true;

        embed(containerRef.current, chartSpec, { 
            actions: false,
            renderer: 'svg',
            // Enable animations
            tooltip: true
        }).then((res) => {
            if (isMounted) {
                viewRef.current = res.view;
                setView(res.view);
                setIsLoading(false);
            }
        }).catch(err => {
            if (isMounted) {
                console.error('Chart rendering error:', err);
                setError('Failed to render chart. Please try again.');
                setIsLoading(false);
            }
        });

        return () => {
            isMounted = false;
            if (viewRef.current) {
                try {
                    viewRef.current.finalize();
                } catch {
                    // Ignore errors during cleanup
                }
                viewRef.current = null;
            }
        };
    }, [chartSpec]); // Only re-render when spec changes

    const handleDownload = useCallback(async (format: 'png' | 'svg') => {
        if (!view) return;
        
        try {
            const url = await view.toImageURL(format);
            const link = document.createElement('a');
            link.href = url;
            link.download = `chart.${format}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            toast.success(`Chart downloaded as ${format.toUpperCase()}!`);
        } catch (err) {
            console.error('Download error:', err);
            setError('Failed to download chart. Please try again.');
        }
    }, [view, toast]);

    const handleCopyToClipboard = useCallback(async () => {
        if (!view) return;
        
        try {
            const url = await view.toImageURL('png');
            const response = await fetch(url);
            const blob = await response.blob();
            await navigator.clipboard.write([
                new ClipboardItem({ 'image/png': blob })
            ]);
            toast.success('Chart copied to clipboard!');
        } catch (err) {
            console.error('Copy error:', err);
            setError('Failed to copy chart. Please try again.');
        }
    }, [view, toast]);

    const handleChartSelect = useCallback((alt: ChartCandidate) => {
        setSelectedChart(alt);
        setShowSurprise(false);
        // Scroll to top to show the selected chart
        window.scrollTo({ top: 0, behavior: 'smooth' });
        if (onChartChange) {
            onChartChange(alt);
        }
    }, [onChartChange]);

    const handleSurpriseMe = useCallback(() => {
        if (surprise) {
            setShowSurprise(true);
            if (onChartChange) {
                onChartChange({
                    ...candidate,
                    spec: surprise.spec,
                    title: surprise.insight,
                    chart_type: surprise.chart_type
                });
            }
        }
    }, [surprise, candidate, onChartChange]);

    const handleShare = useCallback(async () => {
        if (!result || isSharing) return;
        
        setIsSharing(true);
        try {
            const shareData = await createShareLink(result);
            const fullUrl = `${window.location.origin}/share/${shareData.share_token}`;
            
            // Copy to clipboard
            await navigator.clipboard.writeText(fullUrl);
            toast.success(`Share link copied! Expires in ${shareData.expires_in_hours} hours.`);
        } catch (err) {
            console.error('Share error:', err);
            setError('Failed to create share link. Please try again.');
        } finally {
            setIsSharing(false);
        }
    }, [result, isSharing, toast]);



    const handleGenerateReport = useCallback(async () => {
        if (!result) return;
        
        setIsGeneratingReport(true);
        try {
            const columns = result.profile.columns.map(c => ({
                name: c.name,
                dtype: c.dtype,
                unique_count: c.unique_count,
                null_count: c.null_count
            }));
            
            const chartDescs = [candidate, ...alternatives].slice(0, 5).map(c => c.title + ': ' + c.description);
            
            const { markdown } = await generateNarrativeReport(
                { row_count: result.profile.row_count, column_count: result.profile.col_count },
                columns,
                chartDescs
            );
            setReportMarkdown(markdown);
        } catch (err) {
            console.error('Report error:', err);
            toast.error('Failed to generate report');
        } finally {
            setIsGeneratingReport(false);
        }
    }, [result, candidate, alternatives, toast]);

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Cmd/Ctrl + C - Copy chart
            if ((e.metaKey || e.ctrlKey) && e.key === 'c' && !e.shiftKey) {
                // Only if not in an input
                if (document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                    handleCopyToClipboard();
                }
            }
            // Cmd/Ctrl + S - Save as PNG
            if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                e.preventDefault();
                handleDownload('png');
            }
            // Esc - Close modals
            if (e.key === 'Escape') {
                setShowAxisPanel(false);
                setShowAxisPanel(false);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleCopyToClipboard, handleDownload]);

    // Helper for color-coded chart type badges
    const getChartTypeColor = (type: string) => {
        const colors: Record<string, string> = {
            'bar': 'bg-orange-100 text-orange-700',
            'donut': 'bg-blue-100 text-blue-700',
            'scatter': 'bg-green-100 text-green-700',
            'line': 'bg-purple-100 text-purple-700',
            'area': 'bg-teal-100 text-teal-700',
            'histogram': 'bg-pink-100 text-pink-700',
            'heatmap': 'bg-red-100 text-red-700',
        };
        return colors[type.toLowerCase()] || 'bg-gray-200 text-gray-600';
    };

    // Get the current title
    const currentTitle = showSurprise && surprise ? surprise.insight : selectedChart.title;
    const displayTitle = extractSmartTitle(currentTitle, 60);  // Use smart title extraction
    const isTitleTruncated = currentTitle.length > 60 || currentTitle.includes('[') || currentTitle.includes('(');

    return (
        <div className="w-full max-w-5xl mx-auto space-y-4 sm:space-y-6">
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="bg-white rounded-3xl p-6 sm:p-8 md:p-10 shadow-elegant border-refined"
            >
                {/* Title Section - Full Width, Centered */}
                <div className="text-center mb-6 sm:mb-8">
                    {showSurprise && surprise ? (
                        <div 
                            className="inline-flex items-center px-3 py-1.5 rounded-full bg-gray-100 text-gray-700 text-xs font-medium tracking-wide mb-4 border border-gray-200"
                            role="status"
                            aria-label="Surprise discovery"
                        >
                            🎲 Surprise Discovery
                        </div>
                    ) : (
                        <div 
                            className="inline-flex items-center px-3 py-1.5 rounded-full bg-gray-900 text-white text-xs font-medium tracking-wide mb-4"
                            role="status"
                            aria-label="Recommended chart"
                        >
                            Best Chart
                        </div>
                    )}
                    <h2 
                        className="text-2xl sm:text-3xl md:text-4xl font-semibold text-gray-900 leading-tight tracking-tight max-w-3xl mx-auto" 
                        id="chart-title" 
                        style={{ letterSpacing: '-0.02em' }}
                        title={isTitleTruncated ? currentTitle : undefined}
                    >
                        {displayTitle}
                    </h2>
                    {isTitleTruncated && (
                        <p className="text-sm text-gray-500 mt-2 italic">Hover for full title</p>
                    )}
                </div>
                
                {/* Action Buttons - Centered */}
                <div className="flex justify-center gap-2 flex-wrap mb-6 sm:mb-8">
                    {result && (
                         <motion.button
                            onClick={handleGenerateReport}
                            disabled={isGeneratingReport}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            className="px-4 py-2 sm:px-5 bg-gradient-to-r from-blue-500 to-cyan-600 text-white rounded-xl hover:shadow-lg hover:shadow-blue-500/20 transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 text-sm font-medium flex items-center gap-2 border border-transparent shadow-sm disabled:opacity-70 disabled:cursor-not-allowed"
                        >
                            {isGeneratingReport ? (
                                <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                            ) : (
                                <FileText className="w-4 h-4" />
                            )}
                            <span className="hidden sm:inline">{isGeneratingReport ? 'Writing...' : 'Detailed Report'}</span>
                        </motion.button>
                    )}
                        {surprise && (
                            <motion.button
                                onClick={handleSurpriseMe}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                className="px-4 py-2 sm:px-5 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 text-sm font-medium flex items-center gap-2 border border-gray-200 shadow-sm"
                                title="Discover something surprising"
                                aria-label="Surprise me with unexpected insights"
                            >
                                <Sparkles className="w-4 h-4" />
                                <span className="hidden sm:inline">Surprise Me</span>
                            </motion.button>
                        )}
                        <motion.button 
                            onClick={handleShare}
                            disabled={isSharing}
                            whileHover={{ scale: isSharing ? 1 : 1.02 }}
                            whileTap={{ scale: isSharing ? 1 : 0.98 }}
                            className="px-4 py-2 sm:px-5 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 text-sm font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                            title="Create shareable link"
                            aria-label="Create shareable link"
                        >
                            <Share2 className="w-4 h-4" />
                            <span className="hidden sm:inline">{isSharing ? 'Sharing...' : 'Share'}</span>
                        </motion.button>
                        <motion.button 
                            onClick={handleCopyToClipboard}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            className="p-2.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 rounded-xl"
                            title="Copy to clipboard"
                            aria-label="Copy chart to clipboard"
                        >
                            <Copy className="w-5 h-5" aria-hidden="true" />
                        </motion.button>
                        <motion.button 
                            onClick={() => handleDownload('png')}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    handleDownload('png');
                                }
                            }}
                            className="p-2.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 rounded-xl flex items-center gap-1.5"
                            title="Download as PNG (raster image)"
                            aria-label="Download chart as PNG image"
                        >
                            <Download className="w-5 h-5" aria-hidden="true" />
                            <span className="text-xs font-medium hidden sm:inline">PNG</span>
                        </motion.button>
                        <motion.button 
                            onClick={() => handleDownload('svg')}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    handleDownload('svg');
                                }
                            }}
                            className="p-2.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 rounded-xl flex items-center gap-1.5"
                            title="Download as SVG (vector image)"
                            aria-label="Download chart as SVG vector image"
                        >
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                                <path d="M4 22h14a2 2 0 0 0 2-2V7.5L14.5 2H6a2 2 0 0 0-2 2v4" />
                                <polyline points="14 2 14 8 20 8" />
                                <path d="m3 15 2 2 4-4" />
                            </svg>
                            <span className="text-xs font-medium hidden sm:inline">SVG</span>
                        </motion.button>
                        <motion.button 
                            onClick={() => setShowAxisPanel(!showAxisPanel)}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            className={`p-2.5 transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 rounded-xl ${showAxisPanel ? 'text-gray-900 bg-gray-100' : 'text-gray-400 hover:text-gray-900 hover:bg-gray-100'}`}
                            title="Chart Settings"
                            aria-label="Toggle chart settings"
                            aria-expanded={showAxisPanel}
                        >
                        <Settings className="w-5 h-5" aria-hidden="true" />
                    </motion.button>
                </div>

                {/* Axis Customization Panel */}
                {showAxisPanel && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mb-6 p-4 bg-gray-50 rounded-xl border border-gray-200"
                    >
                        <h4 className="text-sm font-semibold text-gray-700 mb-4">Chart Settings</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="flex items-center gap-3">
                                <input 
                                    type="checkbox" 
                                    id="showGrid" 
                                    checked={showGrid} 
                                    onChange={(e) => setShowGrid(e.target.checked)}
                                    className="w-4 h-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900" 
                                />
                                <label htmlFor="showGrid" className="text-sm text-gray-600">Show Grid Lines</label>
                            </div>
                            <div className="flex items-center gap-3">
                                <input 
                                    type="checkbox" 
                                    id="showLabels" 
                                    checked={showLabels} 
                                    onChange={(e) => setShowLabels(e.target.checked)}
                                    className="w-4 h-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900" 
                                />
                                <label htmlFor="showLabels" className="text-sm text-gray-600">Show Axis Labels</label>
                            </div>
                            <div className="flex flex-col gap-1.5">
                                <label htmlFor="xAxisTitle" className="text-xs text-gray-500 font-medium">X-Axis Title</label>
                                <input 
                                    type="text" 
                                    id="xAxisTitle"
                                    value={xAxisTitle}
                                    onChange={(e) => setXAxisTitle(e.target.value)}
                                    placeholder="Custom X-axis label"
                                    className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
                                />
                            </div>
                            <div className="flex flex-col gap-1.5">
                                <label htmlFor="yAxisTitle" className="text-xs text-gray-500 font-medium">Y-Axis Title</label>
                                <input 
                                    type="text" 
                                    id="yAxisTitle"
                                    value={yAxisTitle}
                                    onChange={(e) => setYAxisTitle(e.target.value)}
                                    placeholder="Custom Y-axis label"
                                    className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
                                />
                            </div>
                        </div>
                    </motion.div>
                )}

                {isLoading && (
                    <div className="w-full min-h-[400px] flex items-center justify-center">
                        <div className="flex flex-col items-center">
                            <div className="w-12 h-12 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin mb-5" />
                            <p className="text-gray-600 font-medium text-sm tracking-wide">Rendering chart...</p>
                        </div>
                    </div>
                )}
                
                {error && (
                    <div className="w-full min-h-[400px] flex items-center justify-center">
                        <div className="text-center">
                            <p className="text-red-700 mb-6 font-medium">{error}</p>
                            <motion.button
                                onClick={() => {
                                    setError(null);
                                    setIsLoading(true);
                                    if (containerRef.current && chartSpec) {
                                        const event = new Event('resize');
                                        window.dispatchEvent(event);
                                    }
                                }}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault();
                                        setError(null);
                                        setIsLoading(true);
                                    }
                                }}
                                className="px-6 py-3 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 font-medium shadow-sm"
                                aria-label="Retry rendering chart"
                            >
                                Retry
                            </motion.button>
                        </div>
                    </div>
                )}
                
                <div 
                    ref={containerRef} 
                    className={`w-full min-h-[400px] overflow-hidden ${isLoading || error ? 'hidden' : ''}`}
                    role="img"
                    aria-label={`Chart: ${candidate.title}`}
                    aria-describedby="chart-description"
                    tabIndex={0}
                    aria-live="polite"
                    aria-atomic="true"
                ></div>
                
                {!isLoading && !error && (
                    <div className="mt-8 space-y-4">
                        {/* Enhanced Insights */}
                        {insights && insights.length > 0 && (
                            <motion.div 
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.2 }}
                                id="chart-description"
                                className="p-6 sm:p-8 bg-gray-50 rounded-2xl border border-gray-200"
                                role="region"
                                aria-label="Chart insights"
                            >
                                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-5">
                                    Key Insights
                                </h3>
                                <ul className="space-y-3">
                                    {insights.map((insight, idx) => (
                                        <li key={idx} className="text-gray-900 text-base leading-relaxed font-light">
                                            <MarkdownRenderer content={insight} />
                                        </li>
                                    ))}
                                </ul>
                            </motion.div>
                        )}
                        
                        {/* Fallback description if no insights */}
                        {(!insights || insights.length === 0) && (
                            <motion.div 
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.2 }}
                                id="chart-description"
                                className="p-6 sm:p-8 bg-gray-50 rounded-2xl border border-gray-200"
                                role="region"
                                aria-label="Chart description"
                            >
                                <p className="text-gray-900 text-lg leading-relaxed font-light">
                                    {selectedChart.description}
                                </p>
                            </motion.div>
                        )}
                    </div>
                )}
            </motion.div>
            
            {/* Alternative Chart Views - Simplified & Collapsible */}
            {alternatives && alternatives.length > 0 && (
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="mt-8 sm:mt-10"
                >
                    {/* All Charts - Collapsible Section */}
                    <div className="border border-gray-200 rounded-2xl overflow-hidden bg-white">
                        {/* Collapsible Header */}
                        <button
                            onClick={() => setAllChartsExpanded(!allChartsExpanded)}
                            className="w-full px-5 py-4 bg-gray-50 hover:bg-gray-100 flex justify-between items-center text-left transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <Sparkles className="w-4 h-4 text-yellow-500" />
                                <span className="font-semibold text-gray-900">All Charts</span>
                                <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                                    {alternatives.length}
                                </span>
                            </div>
                            <span className={`text-gray-400 transition-transform ${allChartsExpanded ? 'rotate-180' : ''}`}>
                                ▼
                            </span>
                        </button>
                        
                        {/* Expanded Content */}
                        {allChartsExpanded && (
                            <div className="p-4">
                                {/* Filter Tabs */}
                                <div className="flex flex-wrap gap-2 mb-4">
                                    {chartTypes.map(type => (
                                        <button
                                            key={type}
                                            onClick={() => setActiveFilter(type)}
                                            className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all ${
                                                activeFilter === type
                                                    ? 'bg-gray-900 text-white'
                                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                            }`}
                                        >
                                            {type === 'all' ? 'All Types' : type.toUpperCase()}
                                        </button>
                                    ))}
                                </div>
                                
                                {/* Chart List - Grouped or Limited */}
                                <div className="space-y-4">
                                    {showAllCharts ? (
                                        // Grouped View (Full Analysis)
                                        Object.entries(groupedCharts).map(([section, charts]) => (
                                            <div key={section} className="mb-4">
                                                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 pb-1 border-b border-gray-100 flex items-center gap-2">
                                                    {section}
                                                    <span className="bg-gray-100 text-gray-500 rounded-full px-1.5 py-0.5 text-[10px]">{charts.length}</span>
                                                </h4>
                                                <div className="space-y-2">
                                                    {charts.map((alt, idx) => (
                                                        <button
                                                            key={`chart-${section}-${idx}`}
                                                            onClick={() => handleChartSelect(alt)}
                                                            className={`w-full p-3 rounded-lg border text-left transition-all flex items-center gap-3 ${
                                                                selectedChart.title === alt.title
                                                                    ? 'border-gray-900 bg-gray-900 text-white'
                                                                    : 'border-gray-200 hover:border-gray-300 bg-gray-50 hover:bg-gray-100'
                                                            }`}
                                                        >
                                                            <span className={`text-xs font-medium uppercase px-2 py-0.5 rounded ${
                                                                selectedChart.title === alt.title 
                                                                    ? 'bg-gray-700 text-gray-300' 
                                                                    : getChartTypeColor(alt.chart_type)
                                                            }`}>
                                                                {alt.chart_type}
                                                            </span>
                                                            <span className={`text-sm flex-1 truncate ${
                                                                selectedChart.title === alt.title ? 'text-white' : 'text-gray-800'
                                                            }`}>
                                                                {extractSmartTitle(alt.title)}
                                                            </span>
                                                            {/* Features Badges */}
                                                            {alt.description?.includes('Likert') && (
                                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 whitespace-nowrap">📊 LIKERT</span>
                                                            )}
                                                            {(alt.description?.includes('multi-choice') || alt.description?.includes('Multi-select')) && (
                                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700 whitespace-nowrap">☑️ MULTI</span>
                                                            )}
                                                            {(alt.description?.includes('grid question') || alt.description?.includes('Grid')) && (
                                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-600 whitespace-nowrap">📋 GRID</span>
                                                            )}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        // Limited View (Top 6)
                                        <div className="space-y-2">
                                            {filteredCharts.slice(0, 6).map((alt, idx) => (
                                                <button
                                                    key={`chart-${idx}`}
                                                    onClick={() => handleChartSelect(alt)}
                                                    className={`w-full p-3 rounded-lg border text-left transition-all flex items-center gap-3 ${
                                                        selectedChart.title === alt.title
                                                            ? 'border-gray-900 bg-gray-900 text-white'
                                                            : 'border-gray-200 hover:border-gray-300 bg-gray-50 hover:bg-gray-100'
                                                    }`}
                                                >
                                                    <span className={`text-xs font-medium uppercase px-2 py-0.5 rounded ${
                                                        selectedChart.title === alt.title 
                                                            ? 'bg-gray-700 text-gray-300' 
                                                            : getChartTypeColor(alt.chart_type)
                                                    }`}>
                                                        {alt.chart_type}
                                                    </span>
                                                    <span className={`text-sm flex-1 truncate ${
                                                        selectedChart.title === alt.title ? 'text-white' : 'text-gray-800'
                                                    }`}>
                                                        {extractSmartTitle(alt.title)}
                                                    </span>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                
                                {/* Show More Button */}
                                {filteredCharts.length > 6 && (
                                    <button
                                        onClick={() => setShowAllCharts(!showAllCharts)}
                                        className="w-full mt-4 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors border border-gray-200"
                                    >
                                        {showAllCharts 
                                            ? 'Show less' 
                                            : `Show ${filteredCharts.length - 6} more charts →`
                                        }
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                </motion.div>
            )}

            {/* Data Preview Panel */}
            <DataPreview 
                dataset={dataset} 
                filename={result?.filename}
            />

            {/* Report Generator Modal */}
            <AnimatePresence>
                {reportMarkdown && (
                    <ReportGenerator 
                        markdown={reportMarkdown}
                        charts={[candidate, ...alternatives]}
                        dataset={dataset}
                        onClose={() => setReportMarkdown(null)}
                    />
                )}
            </AnimatePresence>
            
            {/* Executive Summary Modal Removed */}

        </div>
    );
}
