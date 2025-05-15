# Bitbucket Galaxy Code Review

An intelligent code review assistant that integrates with Bitbucket Cloud to provide high-quality automated code reviews and give comments in PRs.

## Key Features

- **Advanced Code Analysis**: Detects bugs, security vulnerabilities, performance issues, and style violations
- **Context-Aware Suggestions**: Understands code context to provide relevant and accurate feedback
- **Custom Rule Integration**: Support for company-specific coding standards and best practices
- **Natural Language Explanations**: Clear, developer-friendly explanations of issues and recommendations
- **Seamless Bitbucket Integration**: Works directly within Bitbucket's pull request workflow
- **Feedback Loop**: Collects user feedback on review comments to improve future reviews
- **Model Fine-Tuning**: Uses collected feedback to fine-tune the LLM for better code reviews

## Architecture

The system consists of several key components:
- **Diff Parser**: Extracts and understands code changes
- **Context Retriever**: Collects relevant context from the codebase
- **Reviewer Agent**: LLM-powered component that performs the actual code review
- **Comment Formatter**: Generates clear, actionable Bitbucket comments
- **Feedback Collector**: Collects and stores user feedback on review comments
- **Model Fine-Tuner**: Uses feedback data to fine-tune the LLM for improved reviews

## Installation

```bash
# Install from PyPI
pip install bitbucket-galaxy-code-review

# Or install from source
git clone https://github.com/galaxy/bitbucket-code-review.git
cd bitbucket-code-review
pip install -e .
```

## Configuration

Create a configuration file `config.yaml` with the following structure:

```yaml
bitbucket:
  username: "your_bitbucket_username"
  app_password: "your_bitbucket_app_password"
  api_url: "https://api.bitbucket.org/2.0/"

reviewer:
  model: "gpt-4"
  temperature: 0.2
  api_key: "your_openai_api_key"  # Optional, can also use OPENAI_API_KEY env var

# Feedback collection configuration
feedback:
  storage_dir: "feedback_data"
  enable_links: true
  server_url: "http://localhost:8000"

# Fine-tuning configuration
fine_tuning:
  base_model: "gpt-3.5-turbo"
  training_file_dir: "training_data"
  min_records: 10
  min_rating: 4
  epochs: 3

# Optional environment variables to set
env_vars:
  OPENAI_API_KEY: "your_openai_api_key"  # Alternative to setting in reviewer section
```

## Usage

### Code Review

```bash
# Review a pull request
galaxy-review --config config.yaml --repo workspace/repo-slug --pr-id 123

# Enable debug logging
galaxy-review --config config.yaml --repo workspace/repo-slug --pr-id 123 --debug
```

### Feedback Collection

```bash
# Start the feedback collection server
galaxy-review --config config.yaml --collect-feedback --feedback-port 8000

# View feedback statistics
galaxy-review --config config.yaml --feedback-stats
```

### Model Fine-Tuning

```bash
# Start the fine-tuning process
galaxy-review --config config.yaml --fine-tune

# Check the status of a fine-tuning job
galaxy-review --config config.yaml --check-fine-tuning job-123456
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
flake8
```

## License

MIT License