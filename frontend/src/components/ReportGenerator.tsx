import React, { useEffect, useRef } from 'react';
import { ChartCandidate } from '../types';
import embed from 'vega-embed';
import { motion } from 'framer-motion';
// import jsPDF from 'jspdf';

interface ReportGeneratorProps {
    markdown: string;
    charts: ChartCandidate[];
    dataset: Record<string, unknown>[]; // Data for the charts
    onClose: () => void;
}

const ChartWrapper = ({ spec, data, title }: { spec: any, data: any[], title: string }) => {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (containerRef.current) {
            // Inject data into spec
            const fullSpec = {
                ...spec,
                width: "container",
                height: 300,
                padding: 10,
                data: { values: data },
                config: {
                    ...spec.config,
                    background: "white",
                    font: "Inter, sans-serif"
                }
            };

            embed(containerRef.current, fullSpec, { 
                actions: false,
                renderer: 'svg'
            }).catch(console.error);
        }
    }, [spec, data]);

    return <div ref={containerRef} className="w-full h-[320px]" />;
};

export default function ReportGenerator({ markdown, charts, dataset, onClose }: ReportGeneratorProps) {
    const handlePrint = () => {
        window.print();
    };

    // Parse logic similar to MarkdownRenderer but looking for chart tokens
    const renderContent = () => {
        if (!markdown) return null;
        
        // Split by lines first
        const lines = markdown.split('\n');
        
        return lines.map((line, index) => {
            const trimmedLine = line.trim();
            
            // Check for Chart Token: {{CHART_N}}
            const chartMatch = trimmedLine.match(/^{{CHART_(\d+)}}/);
            if (chartMatch) {
                const chartIndex = parseInt(chartMatch[1]);
                const chart = charts[chartIndex];
                
                if (!chart) return null;
                
                return (
                    <div key={`chart-${index}`} className="my-8 break-inside-avoid">
                        <div className="bg-white p-4 border border-gray-100 rounded-xl shadow-sm">
                            <h4 className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">
                                Figure {chartIndex + 1}: {chart.title}
                            </h4>
                            <ChartWrapper 
                                spec={chart.spec} 
                                data={dataset} 
                                title={chart.title} 
                            />
                            <p className="text-xs text-gray-400 mt-2 italic text-center">
                                {chart.description}
                            </p>
                        </div>
                    </div>
                );
            }
            
            // Re-use basic markdown styling from current simple renderer
            // Check headers
            if (trimmedLine.startsWith('# ')) {
                return <h1 key={index} className="text-3xl font-bold mt-8 mb-4 text-gray-900 border-b pb-2">{trimmedLine.slice(2)}</h1>;
            }
            if (trimmedLine.startsWith('## ')) {
                return <h2 key={index} className="text-2xl font-semibold mt-6 mb-3 text-gray-800">{trimmedLine.slice(3)}</h2>;
            }
            if (trimmedLine.startsWith('### ')) {
                return <h3 key={index} className="text-xl font-semibold mt-4 mb-2 text-gray-800">{trimmedLine.slice(4)}</h3>;
            }
            if (trimmedLine.startsWith('- ')) {
                return <li key={index} className="ml-4 list-disc mb-1 text-gray-700">{trimmedLine.slice(2)}</li>;
            }
            if (trimmedLine === '') return <div key={index} className="h-2" />;
            
            // Regular Paragraph
            return <p key={index} className="mb-2 text-gray-700 leading-relaxed text-justify">{trimmedLine}</p>;
        });
    };

    return (
        <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-gray-900/50 overflow-y-auto print:bg-white print:overflow-visible"
        >
            <div className="min-h-screen px-4 text-center">
                {/* Overlay background for centering */}
                <div className="inline-block align-middle h-screen" aria-hidden="true">&#8203;</div>
                
                <motion.div 
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    className="inline-block w-full max-w-4xl p-6 my-8 text-left align-middle transition-all transform bg-white shadow-xl rounded-2xl print:shadow-none print:w-full print:max-w-none print:p-0 print:m-0"
                >
                    
                    {/* Header (Hidden in Print) */}
                    <div className="flex justify-between items-center mb-6 print:hidden border-b pb-4">
                        <h2 className="text-xl font-semibold text-gray-900">Detailed Report</h2>
                        <div className="flex gap-3">
                            <button
                                onClick={handlePrint}
                                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                            >
                                🖨️ Print / Save PDF
                            </button>
                            <button
                                onClick={onClose}
                                className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                            >
                                Close
                            </button>
                        </div>
                    </div>

                    {/* Report Content */}
                    <div className="prose max-w-none font-serif print:p-8">
                        {renderContent()}
                        
                        {/* Footer for Print */}
                        <div className="hidden print:block mt-12 pt-8 border-t text-center text-gray-400 text-sm">
                            Generated by Instant Charts AI
                        </div>
                    </div>
                </motion.div>
            </div>
            
            {/* Print Styles */}
            <style jsx global>{`
                @media print {
                    body {
                        visibility: hidden;
                        background: white;
                    }
                    .fixed {
                        position: static !important;
                        background: white !important;
                        overflow: visible !important;
                    }
                    .print\\:block {
                        display: block !important;
                    }
                    .print\\:hidden {
                        display: none !important;
                    }
                    .print\\:shadow-none {
                        box-shadow: none !important;
                    }
                    .print\\:w-full {
                        width: 100% !important;
                    }
                    .print\\:max-w-none {
                        max-width: none !important;
                    }
                    .print\\:p-0 {
                        padding: 0 !important;
                    }
                    .print\\:m-0 {
                        margin: 0 !important;
                    }
                    /* Make the modal content visible */
                    .inline-block {
                        visibility: visible;
                        width: 100%;
                        max-width: none;
                        margin: 0;
                        box-shadow: none;
                    }
                    /* Ensure charts don't break across pages awkwardly */
                    .break-inside-avoid {
                        break-inside: avoid;
                    }
                }
            `}</style>
        </motion.div>
    );
}
