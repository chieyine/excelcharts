import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.describe('Survey Data Flow', () => {
  const fixturesDir = path.join(__dirname, '../fixtures');
  const csvPath = path.join(fixturesDir, 'real_survey_data.csv');

  test.beforeAll(() => {
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }
  });

  test.afterAll(() => {
    if (fs.existsSync(csvPath)) {
      fs.unlinkSync(csvPath);
    }
  });

  test('should handle realistic survey data with long headers', async ({ page }) => {
    // 1. Generate Realistic Survey Data with Long Headers
    const headers = [
      "Respondent ID",
      "Which age group do you currently belong to?",
      "How would you rate your overall satisfaction with our premium services? (1-5)",
      "How likely are you to recommend our product to a friend or colleague? (NPS)",
      "Please select your primary device for accessing our platform",
      "What is your employment status?"
    ];

    const rows = [
        "1,18-24,4,9,Mobile,Student",
        "2,25-34,5,10,Desktop,Employed Full-Time",
        "3,35-44,2,3,Tablet,Employed Full-Time",
        "4,18-24,4,8,Mobile,Student",
        "5,45-54,1,2,Desktop,Self-Employed",
        "6,25-34,5,9,Mobile,Employed Full-Time",
        "7,55-64,3,6,Tablet,Retired",
        "8,25-34,4,8,Desktop,Employed Full-Time",
        "9,18-24,2,4,Mobile,Unemployed",
        "10,35-44,5,10,Desktop,Employed Full-Time",
        "11,25-34,5,9,Mobile,Employed Part-Time",
        "12,45-54,3,5,Tablet,Self-Employed"
    ];

    const csvContent = [headers.join(','), ...rows].join('\n');
    fs.writeFileSync(csvPath, csvContent);

    // 2. Upload the file
    await page.goto('/');
    
    // Ensure properly loaded
    await expect(page.getByRole('heading', { name: 'Upload your data' })).toBeVisible();
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);

    // 3. Wait for processing (Loading check)
    // We expect the loading state or directly the result if fast
    await expect(page.locator('.animate-pulse, .bg-white')).toBeVisible();

    // 4. Verify Success State
    // Increase timeout for analysis
    await expect(page.getByText('Best Chart')).toBeVisible({ timeout: 20000 });

    // 5. Check if Long Headers are handled in the Chart Title or Description
    // The app might display the chart title which often includes column names
    // We verify that the chart rendered successfully.
    // We check for some text from the long headers to ensure they weren't just dropped/errored.
    // Note: The UI might truncate, so we check for partial match or just presence of data.
    
    // Check if "Satisfaction" or "Recommendation" (keywords from long headers) appear
    // This confirms the columns were parsed.
    const pageContent = await page.content();
    const hasKeywords = pageContent.includes('Satisfaction') || pageContent.includes('satisfaction') || pageContent.includes('Recommend');
    expect(hasKeywords).toBeTruthy();

    // 6. Verify Chart Interaction (Basic)
    // Click "Surprise Me" if available (optional, but good for testing robustness of analysis)
    // or just check for alternative charts.
    const altCharts = page.locator('button').filter({ hasText: /bar|line|scatter/i });
    if (await altCharts.count() > 0) {
        await altCharts.first().click();
        // Wait for re-render
        await page.waitForTimeout(500); 
    }
    
    // 7. Accessibility Check for the new content
    await expect(page.locator('#chart-title')).toBeVisible();
  });
});
