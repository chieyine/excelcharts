export default function JsonLd() {
  const webAppSchema = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "ExcelToCharts",
    "url": "https://exceltocharts.com",
    "description": "Turn your Excel, CSV, and Google Sheets into beautiful, interactive charts in seconds.",
    "applicationCategory": "BusinessApplication",
    "operatingSystem": "Any",
    "offers": {
      "@type": "Offer",
      "price": "0",
      "priceCurrency": "USD"
    },
    "featureList": [
      "Convert CSV to Chart",
      "Excel Data Visualization",
      "AI Chart Recommendations",
      "Instant Analysis"
    ]
  };

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {
        "@type": "Question",
        "name": "How do I convert Excel to a chart?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Simply upload your Excel file (.xlsx or .xls) to ExcelToCharts.com and our AI will instantly generate the best chart for your data. No signup required."
        }
      },
      {
        "@type": "Question",
        "name": "How do I convert a CSV file to a chart?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Upload your CSV file directly to ExcelToCharts.com. Our tool automatically detects columns and data types, then recommends the best visualization for your data."
        }
      },
      {
        "@type": "Question",
        "name": "Can I visualize Google Sheets data?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Yes! Export your Google Sheets as CSV or Excel, then upload to ExcelToCharts.com. We support all standard spreadsheet export formats."
        }
      },
      {
        "@type": "Question",
        "name": "What file formats are supported?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "We support Excel files (.xlsx, .xls), CSV files, and data exported from Google Sheets, Numbers, and other spreadsheet applications. Any tabular data works."
        }
      },
      {
        "@type": "Question",
        "name": "Can I create charts from survey data?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Absolutely! ExcelToCharts is perfect for survey data. It automatically detects Likert scales, multiple-choice responses, and generates appropriate bar charts, pie charts, and more."
        }
      },
      {
        "@type": "Question",
        "name": "Is ExcelToCharts free to use?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Yes! ExcelToCharts is completely free. Upload your data and get instant charts without any cost or signup."
        }
      },
      {
        "@type": "Question",
        "name": "What types of charts can I create?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "ExcelToCharts supports bar charts, line charts, area charts, scatter plots, pie/donut charts, histograms, heatmaps, and more. Our AI recommends the best chart type for your data."
        }
      },
      {
        "@type": "Question",
        "name": "Do I need to sign up or create an account?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "No signup required! Just upload your file and get instant charts. Your data is processed securely and never stored."
        }
      }
    ]
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(webAppSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
    </>
  );
}
