import { AnalysisResult } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Retry configuration
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504];

// File validation
const MAX_FILE_SIZE_MB = 50;
const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];
const ALLOWED_MIME_TYPES = [
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/octet-stream', // Some browsers report this for Excel files
];

interface RetryOptions {
    maxRetries?: number;
    retryDelay?: number;
    signal?: AbortSignal;
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Check if error is retryable
 */
function isRetryableError(status: number, error: Error): boolean {
    if (RETRYABLE_STATUS_CODES.includes(status)) {
        return true;
    }
    // Network errors are retryable
    if (error.name === 'TypeError' || error.name === 'NetworkError') {
        return true;
    }
    return false;
}

/**
 * Upload file with retry logic and cancellation support
 */
export async function uploadFile(
    file: File,
    options: RetryOptions = {}
): Promise<AnalysisResult> {
    const {
        maxRetries = MAX_RETRIES,
        retryDelay = RETRY_DELAY,
        signal
    } = options;

    // Client-side file validation
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > MAX_FILE_SIZE_MB) {
        throw new Error(`File is too large (${fileSizeMB.toFixed(1)}MB). Maximum size is ${MAX_FILE_SIZE_MB}MB.`);
    }

    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(fileExtension)) {
        throw new Error(`Invalid file type. Please upload a CSV or Excel file (.csv, .xlsx, .xls).`);
    }

    // Additional MIME type check (if browser provides it)
    if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) {
        console.warn(`Unexpected MIME type: ${file.type}, but extension is valid. Proceeding.`);
    }

    const formData = new FormData();
    formData.append('file', file);

    let lastError: Error | null = null;
    let lastStatus: number | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        // Check if request was cancelled
        if (signal?.aborted) {
            throw new Error('Upload cancelled');
        }

        try {
            const controller = new AbortController();
            
            // Combine external signal with internal controller
            if (signal) {
                signal.addEventListener('abort', () => controller.abort());
            }

            const response = await fetch(`${API_URL}/upload`, {
                method: 'POST',
                body: formData,
                signal: controller.signal,
            });

            lastStatus = response.status;

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                
                // Extract error message from structured error response
                const errorMessage = errorData.detail?.detail || 
                                   errorData.detail?.message || 
                                   errorData.detail || 
                                   errorData.message || 
                                   `Failed to upload file (${response.status})`;
                
                const error = new Error(errorMessage) as Error & { status?: number; correlationId?: string };
                error.status = response.status;
                error.correlationId = errorData.detail?.correlation_id || errorData.correlation_id;
                
                // Check if we should retry
                if (attempt < maxRetries && isRetryableError(response.status, error)) {
                    lastError = error;
                    const delay = retryDelay * Math.pow(2, attempt); // Exponential backoff
                    console.warn(`Upload failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${delay}ms...`, error);
                    await sleep(delay);
                    continue;
                }
                
                throw error;
            }

            const result = await response.json();
            
            // Log correlation ID if available
            const correlationId = response.headers.get('X-Correlation-ID');
            if (correlationId) {
                console.debug('Request correlation ID:', correlationId);
            }
            
            return result;
            
        } catch (error) {
            // Check if request was cancelled
            if (error instanceof Error && error.name === 'AbortError') {
                throw new Error('Upload cancelled');
            }

            // Check if it's a network error (retryable)
            if (error instanceof TypeError && error.message.includes('fetch')) {
                lastError = error as Error;
                if (attempt < maxRetries) {
                    const delay = retryDelay * Math.pow(2, attempt);
                    console.warn(`Network error (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${delay}ms...`, error);
                    await sleep(delay);
                    continue;
                }
            }

            // If we've exhausted retries or it's not retryable, throw
            if (attempt === maxRetries || !isRetryableError(lastStatus || 0, error as Error)) {
                if (error instanceof Error) {
                    throw error;
                }
                throw new Error('An unexpected error occurred while uploading the file');
            }

            lastError = error as Error;
        }
    }

    // Should never reach here, but TypeScript needs it
    throw lastError || new Error('Upload failed after all retries');
}

/**
 * Create an abort controller for cancelling uploads
 */
export function createUploadController(): AbortController {
    return new AbortController();
}

/**
 * Create a shareable link for analysis result
 */
export async function createShareLink(result: AnalysisResult, expiresHours: number = 24): Promise<{ share_token: string; share_url: string; expires_in_hours: number }> {
    const response = await fetch(`${API_URL}/share?expires_hours=${expiresHours}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(result),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create share link');
    }

    return response.json();
}

/**
 * Get shared analysis result
 */
export async function getShareLink(token: string): Promise<AnalysisResult> {
    const response = await fetch(`${API_URL}/share/${token}`);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Share link not found or expired');
    }

    return response.json();
}

/**
 * Export analysis as Story Mode PDF
 */
export async function exportStory(result: AnalysisResult, format: 'pdf' | 'json' = 'pdf'): Promise<Blob | object> {
    const response = await fetch(`${API_URL}/story?format=${format}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(result),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to generate story');
    }

    if (format === 'pdf') {
        return response.blob();
    }
    return response.json();
}

/**
 * Get executive summary for a file
 */
export async function getExecutiveSummary(file: File): Promise<{ summary: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_URL}/insights/summary`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.detail || errorData.detail || 'Failed to generate summary');
    }

    return response.json();
}

/**
 * Generate detailed narrative report
 */
export async function generateNarrativeReport(
    summary: any,
    columns: any[],
    charts: string[]
): Promise<{ markdown: string }> {
    const response = await fetch(`${API_URL}/analyze/report`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ summary, columns, charts }),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.detail || errorData.detail || 'Failed to generate report');
    }

    return response.json();
}
