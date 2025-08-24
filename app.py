from flask import Flask, render_template, request, flash, redirect, url_for
import os
import tempfile
import shutil
from analyzer import GitHubAnalyzer
import re

app = Flask(__name__)
app.secret_key = 'github-analyzer-secret-key-2024'

def validate_github_url(url):
    """Validate if the URL is a valid GitHub repository URL"""
    pattern = r'^https://github\.com/[\w\.-]+/[\w\.-]+/?$'
    return re.match(pattern, url) is not None

def extract_repo_info(url):
    """Extract owner and repo name from GitHub URL"""
    url = url.rstrip('/')
    parts = url.split('/')
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return None, None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        github_url = request.form.get('github_url', '').strip()
        
        if not github_url:
            flash('Please enter a GitHub repository URL', 'error')
            return render_template('index.html')
        
        if not validate_github_url(github_url):
            flash('Please enter a valid GitHub repository URL (e.g., https://github.com/user/repo)', 'error')
            return render_template('index.html')
        
        owner, repo = extract_repo_info(github_url)
        if not owner or not repo:
            flash('Could not extract repository information from URL', 'error')
            return render_template('index.html')
        
        try:
            # Create temporary directory for analysis
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Initialize analyzer and perform analysis
                analyzer = GitHubAnalyzer()
                analysis_result = analyzer.analyze_repository(owner, repo, temp_dir)
                
                if analysis_result.get('error'):
                    flash(f"Analysis failed: {analysis_result['error']}", 'error')
                    return render_template('index.html')
                
                return render_template('index.html', 
                                     analysis=analysis_result, 
                                     github_url=github_url)
            
            finally:
                # Clean up temporary directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
        
        except Exception as e:
            flash(f'An error occurred during analysis: {str(e)}', 'error')
            return render_template('index.html')
    
    return render_template('index.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    flash('An internal error occurred. Please try again.', 'error')
    return render_template('index.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)