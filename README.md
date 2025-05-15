# Bitbucket Galaxy Code Review

An intelligent code review assistant that integrates with Bitbucket Cloud to provide high-quality automated code reviews and give comments in PRs.

## Key Features

- **Advanced Code Analysis**: Detects bugs, security vulnerabilities, performance issues, and style violations
- **Context-Aware Suggestions**: Understands code context to provide relevant and accurate feedback
- **Custom Rule Integration**: Support for company-specific coding standards and best practices
- **Natural Language Explanations**: Clear, developer-friendly explanations of issues and recommendations
- **Seamless Bitbucket Integration**: Works directly within Bitbucket's pull request workflow

## Architecture

The system consists of several key components:
- **Diff Parser**: Extracts and understands code changes
- **Context Retriever**: Collects relevant context from the codebase
- **Reviewer Agent**: LLM-powered component that performs the actual code review
- **Comment Formatter**: Generates clear, actionable Bitbucket comments

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

# Optional environment variables to set
env_vars:
  OPENAI_API_KEY: "your_openai_api_key"  # Alternative to setting in reviewer section
```

## Usage

```bash
# Review a pull request
galaxy-review --config config.yaml --repo workspace/repo-slug --pr-id 123

# Enable debug logging
galaxy-review --config config.yaml --repo workspace/repo-slug --pr-id 123 --debug
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