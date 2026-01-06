import pandas as pd
from app.services.profiler import profile_dataset
from app.services.inference import infer_charts

# 1. Text Likert
df_text = pd.DataFrame({
    'satisfaction': ['Agree', 'Strongly Agree', 'Disagree', 'Neutral', 'Agree']
})
profile_text = profile_dataset(df_text)
likert_col = next(c for c in profile_text.columns if c.name == 'satisfaction')
print(f"Text Likert Detected: {likert_col.is_likert}")
print(f"Text Likert Order: {likert_col.likert_order}")

charts = infer_charts(profile_text)
likert_chart = next((c for c in charts if c.x_column == 'satisfaction'), None)
if likert_chart:
    print(f"Chart Sort Order: {likert_chart.spec['encoding']['x'].get('sort')}")

# 2. Numeric Likert (should be numeric)
df_num = pd.DataFrame({
    'rating': [5, 4, 3, 5, 1, 2]
})
profile_num = profile_dataset(df_num)
num_col = next(c for c in profile_num.columns if c.name == 'rating')
print(f"Numeric Type: {num_col.dtype}")
print(f"Numeric Likert Detected: {num_col.is_likert}") # Should be False
