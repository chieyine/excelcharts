#!/usr/bin/env python3
"""Test script to verify survey data processing."""

import sys
sys.path.insert(0, '/Users/macbookpro/Documents/excelcharts/backend')

import pandas as pd
from app.services.parser import clean_dataframe, strip_parenthetical_content
from app.services.profiler import profile_dataset, detect_checkbox_column, detect_likert_scale

# Load test data
df = pd.read_csv('/Users/macbookpro/Documents/excelcharts/backend/test_survey.csv')
print("=== Original Data ===")
print(df.head(3).to_string())
print(f"\nColumns: {list(df.columns)}")

# Clean the dataframe
df = clean_dataframe(df)
print("\n=== After clean_dataframe ===")
print(f"Columns: {list(df.columns)}")

# Test strip_parenthetical_content
print("\n=== Testing strip_parenthetical_content ===")
test_values = [
    "Pain relievers/Analgesics (e.g., Paracetamol, Ibuprofen)",
    "Health Sciences (e.g., Public Health, Health Management)",
    "Cold/Flu remedies (e.g., Decongestants, Cough syrups)",
    "Headache",
    "20-25 years"
]
for val in test_values:
    result = strip_parenthetical_content(val)
    print(f"  '{val}' -> '{result}'")

# Apply strip to all text columns
print("\n=== Applying strip to text columns ===")
for col in df.columns:
    if df[col].dtype == 'object':
        df[col] = df[col].apply(lambda x: strip_parenthetical_content(x) if pd.notna(x) else x)

# Check each column for checkbox detection
print("\n=== Checkbox Detection ===")
for col in df.columns:
    is_checkbox = detect_checkbox_column(df[col])
    sample = df[col].dropna().iloc[:2].tolist() if len(df[col].dropna()) > 0 else []
    print(f"  {col[:50]}: is_checkbox={is_checkbox}, sample={sample[:2] if sample else 'N/A'}")

# Check Likert detection
print("\n=== Likert Detection ===")
for col in df.columns:
    if df[col].dtype == 'object':
        unique_vals = [str(v) for v in df[col].dropna().unique()[:10]]
        is_likert, order = detect_likert_scale(unique_vals)
        if is_likert:
            print(f"  {col[:50]}: is_likert={is_likert}, order={order}")

# Profile the dataset
print("\n=== Profile Dataset ===")
profile = profile_dataset(df)
for col_profile in profile.columns:
    attrs = []
    if col_profile.is_checkbox:
        attrs.append("CHECKBOX")
    if col_profile.is_likert:
        attrs.append(f"LIKERT(order={col_profile.likert_order})")
    if col_profile.grid_group:
        attrs.append(f"GRID({col_profile.grid_group})")
    if attrs:
        print(f"  {col_profile.name[:50]}: {', '.join(attrs)}")

print("\n=== Done ===")
