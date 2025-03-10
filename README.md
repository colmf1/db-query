# Ask Q - Data Query Assistant

## Overview
Ask Q is a Streamlit-based application that allows users to upload purchase level CSV data and interact with it through natural language queries. The application leverages OpenAI's language models to translate user questions into SQL queries, execute them against the data, and present the results with optional visualizations.

## Features
- **Natural Language Data Querying**: Ask questions about your data in plain English
- **Data Visualization**: Automatically generates relevant charts based on your queries
- **CSV Data Support**: Upload your own CSV files or use sample data
- **Chat Interface**: Intuitive chat-based UI for asking sequential questions
- **SQL Generation**: Translates natural language to SQL using GPT-4 models
- **Interactive Results**: View both text analysis and visual representations of your data
- **Specialised to Purchase level data**: The method has been refined to work with certain data

## Requirements
- Python 3.7+
- OpenAI API key
- Required Python packages (see Installation)

## Installation

### Local Setup
1. Clone the repository:
```bash
git clone https://github.com/colmf1/df-query.git
cd ask-q
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
Create a `.env` file in the root directory with the following:
```
OPENAI_API_KEY=your_openai_api_key
PASSCODE=your_chosen_passcode
```

4. (Optional) Prepare a dummy dataset:
Place a file named `export.csv` in the project root to use as sample data.

### GitHub Codespaces
This application is designed to work with GitHub Codespaces:

1. Open the repository in GitHub Codespaces
2. The development environment will be automatically configured
3. Create a `.env` file with your OpenAI API key and passcode
4. Start the application with `streamlit run app.py`

## Usage

1. Start the application:
```bash
streamlit run app.py
```

2. In the sidebar:
   - Enter your passcode 
   - Choose to use dummy data or upload your own CSV
   - Click "Upload and Initialize" or "Load Dummy Data"

3. Ask questions in the chat input:
   - Example: "Which brand has seen the highest growth in 2024?"
   - Example: "Show me the top 5 products by volume"
   - Example: "What is the spend growth of brand 3 in the past year?"

4. View results in the chat interface, including any automatically generated visualizations

## How It Works

The application follows these steps to process your queries:

1. **Data Loading**: CSV is loaded into a PostgreSQL database
2. **Query Understanding**: Your question is analyzed using LangChain and OpenAI models
3. **SQL Generation**: An appropriate SQL query is generated to answer your question
4. **Query Execution**: The SQL is run against your data
5. **Response Generation**: Results are analyzed and formatted into a human-readable response
6. **Visualization**: If appropriate, Python code is generated to create relevant charts

## Project Structure
- `app.py`: The main Streamlit application
- `DBQ.py`: The core query processing logic and model interaction
- `sql_docs/`: Contains reference documentation for SQL query generation
- `export.csv`: Sample data file (if using dummy data option)
- `.env`: Environment variables (API keys, passcode)

## Codespaces Configuration
When using GitHub Codespaces:
- The application will be accessible via Codespaces' port forwarding
- Your environment variables need to be configured in Codespaces secrets or set manually
- Data uploaded to the application will be temporary unless specifically saved to persistent storage

## Limitations
- The accuracy of responses depends on the quality of the data and clarity of questions
- Large datasets may take longer to process
- Complex queries might require more specific phrasing

## Troubleshooting
- If visualizations aren't displaying, check that your question is specific enough for data visualization
- If receiving error messages, verify your OpenAI API key is valid and has sufficient quota
- For "Unable to answer" responses, try rephrasing your question to be more specific
- In Codespaces, ensure port forwarding is enabled for Streamlit's default port (typically 8501)