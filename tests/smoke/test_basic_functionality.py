import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from analyzer import GitHubAnalyzer
from app import app, validate_github_url, extract_repo_info

class TestBasicFunctionality(unittest.TestCase):
    """Smoke tests for basic application functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = GitHubAnalyzer()
        self.temp_dir = tempfile.mkdtemp()
        
        # Flask app setup
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.app_context.pop()
    
    def test_analyzer_initialization(self):
        """Test that GitHubAnalyzer can be initialized."""
        analyzer = GitHubAnalyzer()
        self.assertIsNotNone(analyzer)
        self.assertIsNotNone(analyzer.session)
        self.assertEqual(analyzer.github_api_base, "https://api.github.com")
    
    def test_flask_app_starts(self):
        """Test that Flask application starts and responds."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GitHub Repository Analyzer', response.data)
    
    def test_url_validation_basic_cases(self):
        """Test basic URL validation functionality."""
        # Valid URL
        self.assertTrue(validate_github_url('https://github.com/user/repo'))
        
        # Invalid URLs
        self.assertFalse(validate_github_url('http://github.com/user/repo'))
        self.assertFalse(validate_github_url('https://gitlab.com/user/repo'))
        self.assertFalse(validate_github_url(''))
    
    def test_repo_info_extraction(self):
        """Test repository information extraction."""
        owner, repo = extract_repo_info('https://github.com/test/example')
        self.assertEqual(owner, 'test')
        self.assertEqual(repo, 'example')
        
        # Test with trailing slash
        owner, repo = extract_repo_info('https://github.com/test/example/')
        self.assertEqual(owner, 'test')
        self.assertEqual(repo, 'example')
    
    @patch('requests.Session.get')
    def test_github_api_connection(self, mock_get):
        """Test that GitHub API connection works."""
        # Mock a successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'test-repo',
            'full_name': 'test/test-repo',
            'description': 'Test repository',
            'language': 'Python',
            'size': 100,
            'stargazers_count': 5,
            'forks_count': 2,
            'open_issues_count': 1,
            'created_at': '2023-01-01T00:00:00Z',
            'updated_at': '2023-12-01T00:00:00Z',
            'pushed_at': '2023-12-01T00:00:00Z',
            'clone_url': 'https://github.com/test/test-repo.git',
            'default_branch': 'main',
            'archived': False,
            'disabled': False,
            'private': False,
            'has_wiki': False
        }
        mock_get.return_value = mock_response
        
        result = self.analyzer._get_repo_info('test', 'test-repo')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'test-repo')
        self.assertEqual(result['language'], 'Python')
    
    def test_code_metrics_empty_directory(self):
        """Test code metrics analysis on empty directory."""
        result = self.analyzer._analyze_code_metrics(self.temp_dir)
        
        self.assertIsInstance(result, dict)
        self.assertIn('total_files', result)
        self.assertIn('code_files', result)
        self.assertIn('languages', result)
        self.assertIn('complexity_score', result)
        
        self.assertEqual(result['total_files'], 0)
        self.assertEqual(result['code_files'], 0)
    
    def test_code_metrics_with_sample_files(self):
        """Test code metrics with sample files."""
        # Create sample files
        sample_py = os.path.join(self.temp_dir, 'sample.py')
        sample_js = os.path.join(self.temp_dir, 'sample.js')
        sample_txt = os.path.join(self.temp_dir, 'readme.txt')
        
        with open(sample_py, 'w') as f:
            f.write('print("Hello, World!")\n')
        
        with open(sample_js, 'w') as f:
            f.write('console.log("Hello, World!");\n')
        
        with open(sample_txt, 'w') as f:
            f.write('This is a readme file.\n')
        
        result = self.analyzer._analyze_code_metrics(self.temp_dir)
        
        self.assertGreater(result['total_files'], 0)
        self.assertGreater(result['total_lines'], 0)
        self.assertIn('Python', result['languages'])
        self.assertIn('JavaScript', result['languages'])
    
    def test_flask_form_submission_validation(self):
        """Test Flask form submission and validation."""
        # Test empty form submission
        response = self.client.post('/', data={'github_url': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please enter a GitHub repository URL', response.data)
        
        # Test invalid URL submission
        response = self.client.post('/', data={'github_url': 'invalid-url'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please enter a valid GitHub repository URL', response.data)
    
    def test_error_handling_404(self):
        """Test 404 error handling."""
        response = self.client.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)
    
    def test_session_configuration(self):
        """Test that requests session is properly configured."""
        session = self.analyzer.session
        
        self.assertIn('Accept', session.headers)
        self.assertIn('User-Agent', session.headers)
        self.assertEqual(session.headers['Accept'], 'application/vnd.github.v3+json')
        self.assertEqual(session.headers['User-Agent'], 'GitHub-Analyzer/1.0')
    
    def test_temporary_directory_handling(self):
        """Test temporary directory creation and cleanup."""
        # This test verifies that temp directory operations work
        test_temp = tempfile.mkdtemp()
        self.assertTrue(os.path.exists(test_temp))
        
        # Create a file in temp directory
        test_file = os.path.join(test_temp, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        self.assertTrue(os.path.exists(test_file))
        
        # Cleanup
        shutil.rmtree(test_temp)
        self.assertFalse(os.path.exists(test_temp))
    
    def test_file_extension_detection(self):
        """Test file extension detection in code metrics."""
        # Create files with different extensions
        extensions_to_test = ['.py', '.js', '.html', '.css', '.json', '.md']
        
        for ext in extensions_to_test:
            test_file = os.path.join(self.temp_dir, f'test{ext}')
            with open(test_file, 'w') as f:
                f.write('test content\n')
        
        result = self.analyzer._analyze_code_metrics(self.temp_dir)
        
        # Should detect multiple file types
        self.assertGreater(len(result['file_types']), 1)
        self.assertGreater(result['total_files'], 0)
    
    @patch('subprocess.run')
    def test_git_clone_command_format(self, mock_run):
        """Test that git clone command is formatted correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        clone_url = 'https://github.com/test/repo.git'
        clone_path = '/tmp/test-repo'
        
        result = self.analyzer._clone_repository(clone_url, clone_path)
        
        # Verify the command was called with correct parameters
        mock_run.assert_called_once_with(
            ['git', 'clone', '--depth', '1', clone_url, clone_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        self.assertTrue(result)
    
    def test_basic_data_structures(self):
        """Test that basic data structures are working correctly."""
        # Test defaultdict usage (used in code metrics)
        from collections import defaultdict
        
        test_dict = defaultdict(int)
        test_dict['python'] += 1
        test_dict['javascript'] += 2
        
        self.assertEqual(test_dict['python'], 1)
        self.assertEqual(test_dict['javascript'], 2)
        self.assertEqual(test_dict['nonexistent'], 0)  # defaultdict behavior
    
    def test_json_serialization(self):
        """Test JSON serialization of analysis results."""
        import json
        
        # Create a sample analysis result
        sample_result = {
            'repository': {'name': 'test-repo', 'language': 'Python'},
            'code_metrics': {'total_files': 10, 'languages': {'Python': 5}},
            'recommendations': ['Add more tests']
        }
        
        # Test JSON serialization
        json_str = json.dumps(sample_result)
        self.assertIsInstance(json_str, str)
        
        # Test JSON deserialization
        parsed_result = json.loads(json_str)
        self.assertEqual(parsed_result['repository']['name'], 'test-repo')
        self.assertEqual(parsed_result['code_metrics']['total_files'], 10)

if __name__ == '__main__':
    unittest.main()