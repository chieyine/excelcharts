"use client";

import { useState, useCallback, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import DropZone from '@/components/DropZone';
import ChartSkeleton from '@/components/ChartSkeleton';
import { uploadFile, createUploadController } from '@/services/api';
import { AnalysisResult } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';

// Dynamically import ChartViewer to reduce initial bundle size
const ChartViewer = dynamic(() => import('@/components/ChartViewer'), {
  loading: () => <ChartSkeleton />,
  ssr: false, // Disable SSR for chart component
});

export default function Home() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleFileSelected = useCallback(async (file: File) => {
    // Cancel any existing upload
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this upload
    const controller = createUploadController();
    abortControllerRef.current = controller;

    setIsUploading(true);
    setError(null);
    setSelectedFile(file);
    
    try {
      const data = await uploadFile(file, { signal: controller.signal });
      setResult(data);
    } catch (err) {
      // Don't show error if upload was cancelled
      if (err instanceof Error && err.message === 'Upload cancelled') {
        return;
      }

      // Extract error message from structured error response
      let errorMessage = 'Something went wrong. Please try again.';
      if (err instanceof Error) {
        errorMessage = err.message;
        // Check if it's a structured error with suggestion
        const errorObj = err as Error & { suggestion?: string };
        if (errorObj.suggestion) {
          errorMessage = `${err.message}. ${errorObj.suggestion}`;
        }
      }
      
      setError(errorMessage);
      console.error('Upload error:', err);
    } finally {
      setIsUploading(false);
      abortControllerRef.current = null;
    }
  }, []);

  const handleFileError = useCallback((error: string) => {
    setError(error);
  }, []);

  const reset = useCallback(() => {
    // Cancel any ongoing upload
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setResult(null);
    setError(null);
    setSelectedFile(null);
    setIsUploading(false);
  }, []);

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 text-gray-900 font-sans selection:bg-gray-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12 md:py-24">
        
        {/* Header */}
        <motion.div 
          layout
          className={`flex flex-col ${result ? 'items-start mb-12' : 'items-center text-center mb-16 md:mb-24'} relative`}
        >
          <motion.h1 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="text-4xl sm:text-5xl md:text-7xl font-light tracking-tight mb-6 text-gray-900"
            style={{ 
              fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif',
              letterSpacing: '-0.02em'
            }}
          >
            Instant Charts
          </motion.h1>
          {!result && (
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2, duration: 0.6 }}
              className="text-lg sm:text-xl md:text-2xl text-gray-600 max-w-2xl font-light leading-relaxed"
            >
              Upload your data. See your story.
              <br className="hidden sm:block"/>
              <span className="text-gray-400 block mt-2 text-base sm:text-lg">No setup. No learning curve.</span>
            </motion.p>
          )}
        </motion.div>

        {/* Content */}
        <AnimatePresence mode="wait">
          {!result ? (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="w-full"
            >
              <DropZone 
                onFileSelected={handleFileSelected} 
                isUploading={isUploading}
                onError={handleFileError}
              />
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-6 text-center text-red-700 bg-red-50/80 backdrop-blur-sm border border-red-200/50 py-3 px-6 rounded-2xl inline-block text-sm font-medium shadow-elegant"
                >
                  {error}
                </motion.div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="result"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="w-full"
            >
              <motion.button 
                onClick={reset}
                whileHover={{ x: -2 }}
                className="mb-8 text-sm text-gray-500 hover:text-gray-900 flex items-center gap-2 group transition-all duration-200 font-medium"
                aria-label="Upload another file"
              >
                <span className="group-hover:-translate-x-1 transition-transform duration-200">←</span>
                <span>Upload another file</span>
              </motion.button>
              
              {result.recommended_chart && (
                <ChartViewer 
                  candidate={result.recommended_chart} 
                  dataset={result.dataset}
                  alternatives={result.alternatives}
                  insights={result.insights}
                  surprise={result.surprise}
                  result={result}
                  file={selectedFile || undefined}
                />
              )}
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </main>
  );
}
