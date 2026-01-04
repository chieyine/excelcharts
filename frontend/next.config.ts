import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable compression
  compress: true,
  
  // Optimize images (if using next/image)
  images: {
    formats: ['image/avif', 'image/webp'],
  },
  
  // Use webpack explicitly (Turbopack is default in Next.js 16)
  // Webpack optimizations for better bundle splitting
  webpack: (config, { isServer }) => {
    // Optimize bundle splitting
    if (!isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            default: false,
            vendors: false,
            // Separate vendor chunks
            vendor: {
              name: 'vendor',
              chunks: 'all',
              test: /node_modules/,
              priority: 20,
            },
            // Separate large libraries
            vega: {
              name: 'vega',
              chunks: 'all',
              test: /[\\/]node_modules[\\/](vega|vega-lite|vega-embed)[\\/]/,
              priority: 30,
            },
          },
        },
      };
    }
    return config;
  },
  
  // Empty turbopack config to use webpack
  turbopack: {},
};

export default nextConfig;
