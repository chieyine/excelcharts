import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ToastProvider } from "@/components/Toast";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Analytics } from "@vercel/analytics/next";
import JsonLd from "@/components/JsonLd";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://exceltocharts.com"),
  title: "ExcelToCharts.com - Convert Excel & CSV to Charts Instantly",
  description: "Turn your Excel, CSV, and Google Sheets into beautiful, interactive charts in seconds. No signup required. The best free Excel to chart converter.",
  keywords: ["excel to charts", "csv visualizer", "spreadsheet to graph", "free chart maker", "instant data visualization", "google sheets to chart", "excel charts online"],
  alternates: {
    canonical: "https://exceltocharts.com",
  },
  openGraph: {
    title: "ExcelToCharts.com - Convert Excel & CSV to Charts Instantly",
    description: "Turn your Excel, CSV, and Google Sheets into beautiful, interactive charts in seconds. Free and instant.",
    url: "https://exceltocharts.com",
    siteName: "ExcelToCharts.com",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "ExcelToCharts.com - Convert Excel & CSV to Charts Instantly",
    description: "Turn your Excel, CSV, and Google Sheets into beautiful, interactive charts in seconds. Free and instant.",
    creator: "@exceltocharts",
  },
  icons: {
    icon: "/icon-192.png",
    apple: "/icon-192.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#ffffff" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <JsonLd />
        <ThemeProvider>
          <ToastProvider>
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </ToastProvider>
        </ThemeProvider>
        <Analytics />
      </body>
    </html>
  );
}
