/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import ChartViewer from '@/components/ChartViewer';
import { ChartCandidate } from '@/types';
import { ToastProvider } from '@/components/Toast';

// Mock vega-embed
jest.mock('vega-embed', () => ({
  __esModule: true,
  default: jest.fn().mockResolvedValue({
    view: {
      toImageURL: jest.fn().mockResolvedValue('data:image/png;base64,test'),
      finalize: jest.fn(),
    },
  }),
}));

// Wrapper component for tests
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <ToastProvider>{children}</ToastProvider>
);

describe('ChartViewer Component', () => {
  const mockCandidate: ChartCandidate = {
    chart_type: 'bar',
    x_column: 'category',
    y_column: 'value',
    title: 'Test Chart',
    description: 'This is a test chart',
    score: 0.9,
    spec: {
      $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
      mark: 'bar',
      encoding: {
        x: { field: 'category', type: 'nominal' },
        y: { field: 'value', type: 'quantitative' },
      },
    },
  };

  const mockDataset = [
    { category: 'A', value: 10 },
    { category: 'B', value: 20 },
    { category: 'C', value: 30 },
  ];

  it('should render chart with title and description', () => {
    render(<ChartViewer candidate={mockCandidate} dataset={mockDataset} />, { wrapper: TestWrapper });

    expect(screen.getByText('Test Chart')).toBeInTheDocument();
    expect(screen.getByText(/This is a test chart/)).toBeInTheDocument();
    expect(screen.getByText('Best Chart')).toBeInTheDocument();
  });

  it('should render download button', () => {
    render(<ChartViewer candidate={mockCandidate} dataset={mockDataset} />, { wrapper: TestWrapper });

    const downloadButton = screen.getByTitle('Download as PNG (raster image)');
    expect(downloadButton).toBeInTheDocument();
  });

  it('should handle different chart types', () => {
    const lineCandidate: ChartCandidate = {
      ...mockCandidate,
      chart_type: 'line',
      title: 'Line Chart',
    };

    render(<ChartViewer candidate={lineCandidate} dataset={mockDataset} />, { wrapper: TestWrapper });

    expect(screen.getByText('Line Chart')).toBeInTheDocument();
  });

  it('should handle empty dataset', () => {
    render(<ChartViewer candidate={mockCandidate} dataset={[]} />, { wrapper: TestWrapper });

    expect(screen.getByText('Test Chart')).toBeInTheDocument();
  });
});
