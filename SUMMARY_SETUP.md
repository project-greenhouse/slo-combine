# Summary Feature Setup Instructions

## Supabase Table Setup

To enable persistent storage of athlete summaries, you need to create a table in your Supabase database.

### SQL Command to Create Table

Run the following SQL command in your Supabase SQL editor:

```sql
CREATE TABLE athlete_summaries (
    id SERIAL PRIMARY KEY,
    athlete_name VARCHAR(255) NOT NULL,
    summary_html TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX idx_athlete_summaries_name ON athlete_summaries(athlete_name);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE athlete_summaries ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (adjust as needed for your security requirements)
CREATE POLICY "Allow all operations on athlete_summaries" ON athlete_summaries
    FOR ALL USING (true);
```

### Table Structure

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-incrementing unique identifier |
| athlete_name | VARCHAR(255) | Name of the athlete (must match names in roster) |
| summary_html | TEXT | HTML content of the rich text summary |
| created_at | TIMESTAMP | When the record was created |
| updated_at | TIMESTAMP | When the record was last modified |

## Features

### Summary Button
- Located in the sidebar when an athlete is selected
- Opens a modal with rich text editor
- Allows creating, editing, and deleting summaries

### Rich Text Editor
- Uses Quill.js editor via streamlit-quill
- Supports formatting: bold, italic, underline
- Supports bullet points and numbered lists
- Supports text alignment and colors

### Display
- Summary appears between "Athlete Information" and "Movement Data" sections
- Only shows when an athlete is selected and has a summary
- Renders HTML content safely

## Fallback Mode

If Supabase is not available or not configured, the system will:
1. Show a warning message
2. Use browser session state for temporary storage
3. Data will be lost when the browser session ends

## Usage

1. Select an athlete from the sidebar dropdown
2. Click "📝 Add/Edit Summary" button
3. Use the rich text editor to create your summary
4. Click "💾 Save" to store the summary
5. The summary will appear on the main dashboard
6. Use "🗑️ Delete" to remove a summary
7. Use "❌ Cancel" to close without saving
