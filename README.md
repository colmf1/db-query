---
license: mit
sdk: gradio
colorFrom: yellow
colorTo: gray
pinned: true
short_description: Use natural language to extract insights from your data
sdk_version: 5.15.0
---
Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

# Ask Diallo

Welcome to **Ask Diallo**, a Hugging Face application that allows you to interact with your CSV data using natural language. This application leverages **gpt-4o-mini** to generate SQL queries, execute them on your data, and provide insightful answers. Additionally, it can generate visualizations using **Matplotlib** when necessary.

## Features

- **Natural Language Interaction**: Chat with your data in plain English.
- **SQL Query Generation**: Automatically generates SQL queries based on your questions.
- **Data Visualization**: Produces Matplotlib plots to visualize data insights.
- **CSV Support**: Upload your CSV file and start querying immediately.

## How It Works
1. **Upload Your CSV**: Start by uploading a CSV file containing your data.
2. **Ask Questions**: Type your question in natural language (e.g., "What is the average sales per region?").
3. **SQL Query Generation**: The application uses **gpt-4o-mini** to generate an appropriate SQL query.
4. **Query Execution**: The generated SQL query is executed on your CSV data.
5. **Get Answers**: The application provides an answer based on the query results.
6. **Visualizations**: If applicable, the app generates a Matplotlib plot to visualize the data.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Hugging Face account
- Required Python packages (listed in `requirements.txt`)

## Example Queries

- **Basic Query**: "What is the total sales for each region?"
- **Aggregation**: "What is the average age of customers?"
- **Filtering**: "Show me all transactions above $500."
- **Visualization**: "Plot the monthly sales trend."

## Supported Models
- **gpt-4o-mini**: A lightweight model for quick SQL query generation.

## Contributing

We welcome contributions! If you have any ideas, suggestions, or bug reports, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Hugging Face** for providing the infrastructure and models.
- **Matplotlib** for data visualization.
- **Pandas** for data manipulation.
- **Gradio** for chatbot application.

## Future Improvements
- Implement chat history, so users can ask questions about previous answers