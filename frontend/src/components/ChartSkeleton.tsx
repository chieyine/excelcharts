'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface ChartSkeletonProps {
  className?: string;
}

/**
 * Loading skeleton for chart display.
 * Shows animated placeholders for chart title, chart area, and insights.
 */
export default function ChartSkeleton({ className = '' }: ChartSkeletonProps) {
  return (
    <div className={`w-full max-w-4xl mx-auto space-y-4 sm:space-y-6 ${className}`}>
      {/* Main chart card skeleton */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="bg-white rounded-3xl p-6 sm:p-8 md:p-10 shadow-elegant border-refined"
      >
        {/* Header skeleton */}
        <div className="flex flex-col sm:flex-row justify-between items-start gap-4 mb-6">
          <div className="flex-1">
            {/* Badge skeleton */}
            <div className="h-6 w-24 bg-gray-200 rounded-full mb-3 animate-pulse" />
            {/* Title skeleton */}
            <div className="h-9 w-64 bg-gray-200 rounded-xl animate-pulse" />
          </div>
          
          {/* Buttons skeleton */}
          <div className="flex gap-2">
            <div className="h-10 w-10 bg-gray-200 rounded-xl animate-pulse" />
            <div className="h-10 w-10 bg-gray-200 rounded-xl animate-pulse" />
            <div className="h-10 w-10 bg-gray-200 rounded-xl animate-pulse" />
          </div>
        </div>

        {/* Chart area skeleton */}
        <div className="w-full h-[400px] bg-linear-to-br from-gray-100 to-gray-200 rounded-2xl animate-pulse flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-2 border-gray-300 border-t-gray-400 rounded-full animate-spin" />
            <div className="text-gray-400 text-sm font-medium">Loading chart...</div>
          </div>
        </div>

        {/* Insights skeleton */}
        <div className="mt-8 p-6 sm:p-8 bg-gray-50 rounded-2xl border border-gray-200">
          <div className="h-4 w-24 bg-gray-200 rounded mb-5 animate-pulse" />
          <div className="space-y-3">
            <div className="h-5 w-full bg-gray-200 rounded animate-pulse" />
            <div className="h-5 w-4/5 bg-gray-200 rounded animate-pulse" />
            <div className="h-5 w-3/5 bg-gray-200 rounded animate-pulse" />
          </div>
        </div>
      </motion.div>

      {/* Alternative views skeleton */}
      <div className="mt-8 sm:mt-10">
        <div className="h-4 w-20 bg-gray-200 rounded mb-5 animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-5 rounded-2xl border border-gray-200 bg-white"
            >
              <div className="h-3 w-16 bg-gray-200 rounded mb-2 animate-pulse" />
              <div className="h-5 w-full bg-gray-200 rounded mb-2 animate-pulse" />
              <div className="h-3 w-2/3 bg-gray-200 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
