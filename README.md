# SLO Combine - Athlete Performance Dashboard

A comprehensive Streamlit application for managing and visualizing athlete performance data from the San Luis Obispo County Combine 2025.

## Features

### 🏃‍♂️ Athlete Management
- **Athlete Selection**: Dropdown menu in sidebar to select athletes from the roster
- **Comprehensive Information Display**: Shows athlete details including name, age, school, height, position, and more

### 📝 Summary & Notes Feature
- **Rich Text Editor**: Add formatted notes and observations for each athlete
- **Persistent Storage**: Summaries are saved using Supabase database (with session state fallback)
- **Styled Display**: Summaries appear in a styled container between athlete information and performance data
- **Easy Management**: Create, edit, and delete summaries directly from the sidebar

### 📊 Performance Data Visualization
- **Movement Data**: Valor system integration for movement analysis
- **Speed Data**: Sprint times, pro-agility, and other speed metrics
- **Power Data**: Vertical jump, broad jump, and force plate measurements
- **Force Plate Data**: Hawking Dynamics integration for detailed biomechanical analysis

### 🔧 Data Sources
- **Hawking Dynamics**: Force plate and jump analysis
- **Valor**: Movement screening and assessment
- **Swift**: Speed and agility timing systems
- **Manual Data**: CSV imports for additional metrics

## Installation

1. Clone the repository:
```bash
git clone https://github.com/project-greenhouse/slo-combine.git
cd slo-combine
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Supabase (optional but recommended for persistent summaries):
   - Create a Supabase project
   - Run the SQL commands from `SUMMARY_SETUP.md` to create the athlete_summaries table
   - Update the credentials in `functions/supabase.py`

5. Configure your secrets:
   - Add HD_TOKEN for Hawking Dynamics API
   - Add other API keys as needed

## Usage

1. Start the application:
```bash
streamlit run app.py
```

2. Select an athlete from the sidebar dropdown

3. View comprehensive athlete information and performance data

4. Add summaries and notes:
   - Click the "📝 Athlete Summary" expander in the sidebar
   - Use the rich text editor to format your notes
   - Click "💾 Save" to store the summary
   - Summaries will appear on the main dashboard

## File Structure

```
├── app.py                          # Main Streamlit application
├── views/                          # Page components
│   ├── home_dash.py               # Main dashboard
│   ├── hd_data.py                 # Force plate data
│   ├── swift_data.py              # Speed data
│   ├── valor_data.py              # Movement data
│   ├── vert_jump_data.py          # Vertical jump analysis
│   └── broad_jump_data.py         # Broad jump analysis
├── functions/                      # Core functionality
│   ├── data.py                    # Data loading and processing
│   ├── func_summary.py            # Summary management (Supabase)
│   ├── func_summary_session.py    # Summary management (session state)
│   ├── func_swift.py              # Swift system integration
│   ├── func_valor.py              # Valor system integration
│   ├── func_player_info.py        # Athlete information
│   └── supabase.py                # Database connection
├── data/                          # CSV data files
├── assets/                        # Images and static files
└── requirements.txt               # Python dependencies
```

## Dependencies

- **streamlit**: Web application framework
- **streamlit-quill**: Rich text editor component
- **pandas**: Data manipulation and analysis
- **supabase**: Database integration
- **hdforce**: Hawking Dynamics API client
- **requests**: HTTP client for API calls

## Configuration

### Supabase Setup
For persistent summary storage, create a table with the following structure:

```sql
CREATE TABLE athlete_summaries (
    id SERIAL PRIMARY KEY,
    athlete_name VARCHAR(255) NOT NULL,
    summary_html TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

See `SUMMARY_SETUP.md` for detailed setup instructions.

### API Integrations
- **Hawking Dynamics**: Requires authentication token in Streamlit secrets
- **Valor**: Handles JWT token authentication automatically
- **Swift**: Processes CSV data files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is proprietary to Code 8 Performance and Greenhouse Performance.

## Support

For technical support or questions, contact the development team.