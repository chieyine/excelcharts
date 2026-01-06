import { VisualizationSpec } from 'vega-embed';

export interface ColumnProfile {
    name: string;
    original_name: string;
    dtype: 'numeric' | 'temporal' | 'nominal' | 'ordinal';
    null_count: number;
    unique_count: number;
    examples: (string | number | boolean | null)[];
    min?: number;
    max?: number;
    mean?: number;
    
    // Survey data detection
    is_checkbox?: boolean;  // True if column contains comma-separated multi-select values
    is_likert?: boolean;    // True if column contains Likert scale responses
    likert_order?: string[]; // Ordered list of Likert values (positive to negative)
    grid_group?: string;    // Group name for grid questions
}

export interface DatasetProfile {
    row_count: number;
    col_count: number;
    columns: ColumnProfile[];
}

export interface ChartCandidate {
    chart_type: string;
    x_column: string;
    y_column?: string | null;
    color_column?: string | null;
    description: string;
    title: string;
    score: number;
    spec: VisualizationSpec;
    group_name?: string; // Section title for grouping
    group_score?: number; // Sorting priority for groups
}

export interface AnalysisResult {
    filename: string;
    profile: DatasetProfile;
    recommended_chart: ChartCandidate;
    alternatives: ChartCandidate[];
    dataset: Record<string, unknown>[];
    insights?: string[];
    surprise?: {
        insight: string;
        chart_type: string;
        x_column: string;
        y_column?: string;
        spec: VisualizationSpec;
    };
}
