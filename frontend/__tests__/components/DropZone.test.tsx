/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DropZone from '@/components/DropZone';

describe('DropZone Component', () => {
  const mockOnFileSelected = jest.fn();
  const mockOnError = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render drop zone', () => {
    render(
      <DropZone
        onFileSelected={mockOnFileSelected}
        isUploading={false}
      />
    );

    expect(screen.getByText('Upload your data')).toBeInTheDocument();
    expect(screen.getByText('Drag & drop CSV or Excel files')).toBeInTheDocument();
  });

  it('should show loading state when uploading', () => {
    render(
      <DropZone
        onFileSelected={mockOnFileSelected}
        isUploading={true}
      />
    );

    expect(screen.getByText('Analyzing your data...')).toBeInTheDocument();
  });

  it('should handle file selection via input', async () => {
    const user = userEvent.setup();
    const file = new File(['test content'], 'test.csv', { type: 'text/csv' });

    render(
      <DropZone
        onFileSelected={mockOnFileSelected}
        isUploading={false}
      />
    );

    const input = screen.getByLabelText(/browse files/i).closest('label')?.querySelector('input');
    if (input) {
      await user.upload(input, file);
      await waitFor(() => {
        expect(mockOnFileSelected).toHaveBeenCalledWith(file);
      });
    }
  });

  it('should validate file size and show error', async () => {
    const user = userEvent.setup();
    // Create a file larger than 50MB
    const largeFile = new File(['x'.repeat(51 * 1024 * 1024)], 'large.csv', { type: 'text/csv' });

    render(
      <DropZone
        onFileSelected={mockOnFileSelected}
        isUploading={false}
        onError={mockOnError}
      />
    );

    const input = screen.getByLabelText(/browse files/i).closest('label')?.querySelector('input');
    if (input) {
      await user.upload(input, largeFile);
      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled();
        expect(mockOnFileSelected).not.toHaveBeenCalled();
      });
    }
  });

  it('should validate file type and show error', async () => {
    const user = userEvent.setup();
    const invalidFile = new File(['test'], 'test.txt', { type: 'text/plain' });

    render(
      <DropZone
        onFileSelected={mockOnFileSelected}
        isUploading={false}
        onError={mockOnError}
      />
    );

    const input = screen.getByLabelText(/browse files/i).closest('label')?.querySelector('input');
    if (input) {
      await user.upload(input, invalidFile);
      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled();
        expect(mockOnFileSelected).not.toHaveBeenCalled();
      });
    }
  });

  it('should handle drag and drop', () => {
    const file = new File(['test'], 'test.csv', { type: 'text/csv' });
    const dataTransfer = {
      files: [file],
    };

    render(
      <DropZone
        onFileSelected={mockOnFileSelected}
        isUploading={false}
      />
    );

    const dropZone = screen.getByText('Upload your data').closest('div');
    if (dropZone) {
      fireEvent.dragOver(dropZone, { dataTransfer });
      fireEvent.drop(dropZone, { dataTransfer });

      expect(mockOnFileSelected).toHaveBeenCalledWith(file);
    }
  });
});

