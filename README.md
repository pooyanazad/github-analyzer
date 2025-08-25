# GitHub Repository Analyzer

A comprehensive Flask web application that analyzes GitHub repositories and provides detailed insights about code quality, project structure, security, and overall repository health.

## Features

- **Repository Analysis**: Deep analysis of GitHub repositories including code metrics, project structure, and build systems
- **Security Scanning**: Basic security vulnerability detection and sensitive file identification
- **Health Indicators**: Repository activity, maintenance, and community engagement metrics
- **Smart Recommendations**: AI-powered suggestions for improving repository quality
- **Modern UI**: Clean, responsive Bootstrap-based interface with dark mode support
- **Real-time Analysis**: Live analysis with progress indicators and detailed reporting

## Screenshots

The application provides a clean, modern interface for analyzing GitHub repositories with comprehensive reporting.

<img width="1270" height="421" alt="image" src="https://github.com/user-attachments/assets/dcbb7f68-53fe-45e1-a09f-6c3363c81348" />


## Installation

### Prerequisites

- Python 3.7 or higher
- Git (for repository cloning)
- Internet connection (for GitHub API access)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd 20-GitAnalyzer
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Access the application**:
   Open your web browser and navigate to `http://localhost:5000`

## Usage

1. **Enter GitHub URL**: Paste any public GitHub repository URL in the input field
2. **Start Analysis**: Click "Analyze Repository" to begin the comprehensive analysis
3. **View Results**: The application will display detailed insights including:
   - Repository overview and basic statistics
   - Code metrics (file counts, languages, complexity)
   - Project structure and organization score
   - Security analysis and potential vulnerabilities
   - Repository health indicators
   - Personalized recommendations for improvement

### Supported Repository URLs

The application accepts various GitHub URL formats:
- `https://github.com/owner/repo`
- `https://github.com/owner/repo.git`
- `github.com/owner/repo`
- `owner/repo`

## Analysis Features

### Code Metrics
- Total files and code files count
- Programming languages detection
- Lines of code analysis (code, comments, blank lines)
- File size analysis
- Complexity scoring

### Project Structure
- Essential files detection (README, LICENSE, etc.)
- Test directory identification
- Documentation presence
- CI/CD configuration detection
- Organization score calculation

### Build Systems
- Package manager detection (npm, pip, maven, etc.)
- Build file identification
- Dependency counting
- Technology stack analysis

### Security Analysis
- Sensitive file detection
- Basic vulnerability patterns
- Hardcoded secrets identification
- Security score calculation
- Security recommendations

### Health Indicators
- Repository activity scoring
- Maintenance indicators
- Community engagement metrics
- Overall health assessment

## Technical Details

### Architecture

- **Backend**: Flask web framework
- **Frontend**: Bootstrap 5.3 with custom CSS
- **Analysis Engine**: Custom Python analyzer with GitHub API integration
- **Repository Handling**: GitPython for repository cloning and analysis
- **Security Scanning**: Pattern-based vulnerability detection

### Dependencies

- `Flask==2.3.3` - Web framework
- `requests==2.31.0` - HTTP library for GitHub API
- `GitPython==3.1.40` - Git repository handling
- `PyGithub==1.59.1` - GitHub API wrapper
- `bandit==1.7.5` - Security linting
- `flake8==6.1.0` - Code quality checking

### File Structure

```
20-GitAnalyzer/
├── app.py                 # Main Flask application
├── analyzer.py            # Repository analysis engine
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Main HTML template
├── static/
│   └── style.css         # Custom CSS styles
└── README.md             # This file
```

## Configuration

### Environment Variables

Optional environment variables for enhanced functionality:

- `GITHUB_TOKEN`: Personal access token for higher API rate limits
- `FLASK_ENV`: Set to `development` for debug mode
- `FLASK_DEBUG`: Set to `1` for debug mode

### GitHub API Rate Limits

The application uses the GitHub API for repository information. Without authentication:
- 60 requests per hour per IP address

With a GitHub token:
- 5,000 requests per hour

To use a token, set the `GITHUB_TOKEN` environment variable.

## Troubleshooting

### Common Issues

1. **Repository not found**: Ensure the repository is public and the URL is correct
2. **Analysis timeout**: Large repositories may take longer to analyze
3. **Git not found**: Ensure Git is installed and available in PATH
4. **Permission denied**: Check if the repository requires authentication

### Error Messages

- **"Repository not found"**: The repository doesn't exist or is private
- **"Failed to clone repository"**: Network issues or repository access problems
- **"Analysis failed"**: Internal error during analysis process

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments

- GitHub API for repository data
- Bootstrap for UI components
- Flask community for the excellent web framework
- All contributors and users of this tool

## Support

If you encounter any issues or have questions, please:
1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information about the problem

---

**Note**: This tool is designed for educational and analysis purposes. Always respect repository owners' rights and GitHub's terms of service when analyzing repositories.
