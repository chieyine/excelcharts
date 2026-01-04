/**
 * @jest-environment jsdom
 */
import { uploadFile } from '@/services/api';
import { AnalysisResult } from '@/types';

// Mock fetch
global.fetch = jest.fn();

describe('API Service', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  it('should upload file successfully', async () => {
    const mockResponse: AnalysisResult = {
      filename: 'test.csv',
      profile: {
        row_count: 2,
        col_count: 2,
        columns: [],
      },
      recommended_chart: {
        chart_type: 'bar',
        x_column: 'x',
        y_column: 'y',
        title: 'Test Chart',
        description: 'Test description',
        score: 0.9,
        spec: {},
      },
      alternatives: [],
      dataset: [],
    };

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const file = new File(['test content'], 'test.csv', { type: 'text/csv' });
    const result = await uploadFile(file);

    expect(result).toEqual(mockResponse);
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/upload',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
  });

  it('should throw error when upload fails', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'File too large' }),
    });

    const file = new File(['test content'], 'test.csv', { type: 'text/csv' });

    await expect(uploadFile(file)).rejects.toThrow('File too large');
  });

  it('should throw error with default message when no detail provided', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({}),
    });

    const file = new File(['test content'], 'test.csv', { type: 'text/csv' });

    await expect(uploadFile(file)).rejects.toThrow('Failed to upload file');
  });

  it('should handle network errors', async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    const file = new File(['test content'], 'test.csv', { type: 'text/csv' });

    await expect(uploadFile(file)).rejects.toThrow('Network error');
  });
});

