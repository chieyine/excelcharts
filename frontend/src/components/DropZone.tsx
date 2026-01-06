"use client";

import React, { useCallback, useState, useEffect } from 'react';
import { Upload, FileSpreadsheet, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface DropZoneProps {
    onFileSelected: (file: File) => void;
    isUploading: boolean;
    onError?: (error: string) => void;
}

// Sample data CSV content
const SAMPLE_DATA = `Category,Sales,Quarter,Region
Electronics,45000,Q1,North
Clothing,32000,Q1,South
Food,28000,Q1,East
Electronics,52000,Q2,North
Clothing,38000,Q2,South
Food,31000,Q2,East
Electronics,48000,Q3,North
Clothing,35000,Q3,South
Food,29000,Q3,East
Electronics,61000,Q4,North
Clothing,42000,Q4,South
Food,36000,Q4,East`;

// Configuration constants
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const ALLOWED_TYPES = [
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
];
const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];

function validateFile(file: File): string | null {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
        return `File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB. Your file is ${(file.size / 1024 / 1024).toFixed(2)}MB`;
    }
    
    if (file.size === 0) {
        return 'File is empty';
    }
    
    // Check file extension
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    if (!ALLOWED_EXTENSIONS.includes(fileExtension)) {
        return `Invalid file type. Please upload CSV or Excel files (.csv, .xlsx, .xls)`;
    }
    
    // Check MIME type (if available)
    if (file.type && !ALLOWED_TYPES.includes(file.type) && !file.type.startsWith('application/octet-stream')) {
        // Allow octet-stream as some systems don't provide MIME types
        // The backend will do final validation
    }
    
    return null;
}

export default function DropZone({ onFileSelected, isUploading, onError }: DropZoneProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [validationError, setValidationError] = useState<string | null>(null);
    const [filePreview, setFilePreview] = useState<{ name: string; size: number; rows?: number } | null>(null);

    const handleFile = useCallback((file: File) => {
        const error = validateFile(file);
        if (error) {
            setValidationError(error);
            if (onError) {
                onError(error);
            }
            return;
        }
        
        setValidationError(null);
        onFileSelected(file);
    }, [onFileSelected, onError]);

    const handleSampleData = useCallback(() => {
        const blob = new Blob([SAMPLE_DATA], { type: 'text/csv' });
        const file = new File([blob], 'sample-sales-data.csv', { type: 'text/csv' });
        onFileSelected(file);
    }, [onFileSelected]);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
        setValidationError(null);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        setValidationError(null);
        setFilePreview(null);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        setFilePreview(null);
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            handleFile(files[0]);
        }
    }, [handleFile]);

    const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    }, [handleFile]);

    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            document.getElementById('file-upload')?.click();
        }
    }, []);

    // Paste from clipboard handler
    useEffect(() => {
        if (isUploading) return;
        
        const handlePaste = async (e: ClipboardEvent) => {
            const items = e.clipboardData?.items;
            if (!items) return;

            // Check for file paste
            for (let i = 0; i < items.length; i++) {
                const item = items[i];
                if (item.kind === 'file') {
                    const file = item.getAsFile();
                    if (file) {
                        handleFile(file);
                        return;
                    }
                }
            }

            // Check for text paste (CSV data)
            const text = e.clipboardData?.getData('text');
            if (text && text.includes(',')) {
                try {
                    // Create a CSV file from pasted text
                    const blob = new Blob([text], { type: 'text/csv' });
                    const file = new File([blob], 'pasted-data.csv', { type: 'text/csv' });
                    handleFile(file);
                } catch (err) {
                    console.error('Error handling paste:', err);
                }
            }
        };

        window.addEventListener('paste', handlePaste);
        return () => window.removeEventListener('paste', handlePaste);
    }, [isUploading, handleFile]);

    // File preview on drag over
    const handleDragOverWithPreview = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
        setValidationError(null);
        
        // Try to get file info for preview
        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
            const file = files[0];
            setFilePreview({
                name: file.name,
                size: file.size
            });
        }
    }, []);

    return (
        <div 
            className="relative w-full max-w-2xl mx-auto h-64"
            onDragOver={handleDragOverWithPreview}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            role="region"
            aria-label="File upload area"
        >
            <input
                type="file"
                id="file-upload"
                className="hidden"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileInput}
                disabled={isUploading}
                aria-label="Upload CSV or Excel file"
                aria-describedby="file-upload-description"
            />
            
            <motion.label
                htmlFor="file-upload"
                tabIndex={0}
                role="button"
                aria-label="Upload file by clicking or dragging and dropping"
                onKeyDown={handleKeyDown}
                className={`
                    flex flex-col items-center justify-center w-full h-full 
                    rounded-3xl cursor-pointer 
                    transition-all duration-300 ease-out
                    focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2
                    border-2 shadow-elegant
                    ${isDragging 
                        ? 'bg-blue-50 border-blue-400 scale-[1.02] shadow-lg shadow-blue-100' 
                        : 'bg-white hover:bg-gray-50/50 border-gray-200 hover:border-gray-300 border-dashed'
                    }
                `}
                animate={{
                    scale: isDragging ? 1.01 : 1,
                }}
                whileHover={{ scale: 1.005 }}
                whileTap={{ scale: 0.998 }}
            >
                <AnimatePresence mode="wait">
                    {isUploading ? (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                            className="flex flex-col items-center"
                        >
                            <div className="w-12 h-12 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin mb-5" />
                            <p className="text-gray-600 font-medium text-sm tracking-wide">Analyzing your data...</p>
                        </motion.div>
                    ) : (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 10 }}
                            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                            className="flex flex-col items-center text-center p-8"
                        >
                            <motion.div 
                                className="mb-6 p-5 bg-gray-100 rounded-2xl" 
                                aria-hidden="true"
                                animate={{ 
                                    scale: isDragging ? 1.1 : 1,
                                    rotate: isDragging ? 5 : 0
                                }}
                                transition={{ duration: 0.3 }}
                            >
                                {isDragging ? (
                                    <ArrowRight className="w-10 h-10 text-gray-900" aria-hidden="true" />
                                ) : (
                                    <FileSpreadsheet className="w-10 h-10 text-gray-400" aria-hidden="true" />
                                )}
                            </motion.div>
                            
                            <h3 className="text-2xl font-light text-gray-900 mb-2 tracking-tight">
                                {isDragging ? 'Drop it here' : 'Upload your data'}
                            </h3>
                            <p id="file-upload-description" className="text-sm text-gray-500 mb-8 font-light">
                                Drag & drop, paste (Cmd/Ctrl+V), or click to browse
                            </p>
                            {filePreview && isDragging && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="mt-2 px-4 py-2 bg-gray-100 rounded-xl text-xs text-gray-700 font-medium border border-gray-200"
                                >
                                    {filePreview.name} — {(filePreview.size / 1024).toFixed(1)} KB
                                </motion.div>
                            )}
                            
                            <motion.div 
                                className="px-8 py-3 bg-gray-900 text-white rounded-full text-sm font-medium shadow-elegant"
                                whileHover={{ scale: 1.02, backgroundColor: '#171717' }}
                                whileTap={{ scale: 0.98 }}
                            >
                                Browse Files
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.label>
            
            {/* Sample Data Button */}
            {!isUploading && (
                <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="mt-4 text-center"
                >
                    <button
                        onClick={handleSampleData}
                        className="text-sm text-gray-500 hover:text-gray-900 underline underline-offset-2 transition-colors"
                    >
                        Or try with sample data →
                    </button>
                </motion.div>
            )}
            
            {validationError && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="mt-4 text-center text-red-700 bg-red-50/80 backdrop-blur-sm border border-red-200/50 py-3 px-5 rounded-2xl text-sm font-medium shadow-elegant"
                >
                    {validationError}
                </motion.div>
            )}
        </div>
    );
}
