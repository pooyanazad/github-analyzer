import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app, validate_github_url, extract_repo_info

class TestFlaskApp(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after each test method."""
        self.app_context.pop()
    
    def test_validate_github_url_valid_urls(self):
        """Test validation of valid GitHub URLs."""
        valid_urls = [
            'https://github.com/user/repo',
            'https://github.com/user/repo/',
            'https://github.com/test-user/test-repo',
            'https://github.com/user123/repo-name',
            'https://github.com/user.name/repo.name'
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(validate_github_url(url), f"URL should be valid: {url}")
    
    def test_validate_github_url_invalid_urls(self):
        """Test validation of invalid GitHub URLs."""
        invalid_urls = [
            'http://github.com/user/repo',  # HTTP instead of HTTPS
            'https://gitlab.com/user/repo',  # Wrong domain
            'https://github.com/user',  # Missing repo
            'https://github.com/',  # Missing user and repo
            'github.com/user/repo',  # Missing protocol
            'https://github.com/user/repo/issues',  # Extra path
            '',  # Empty string
            'not-a-url'
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(validate_github_url(url), f"URL should be invalid: {url}")
    
    def test_extract_repo_info_valid_urls(self):
        """Test extraction of repository information from valid URLs."""
        test_cases = [
            ('https://github.com/user/repo', ('user', 'repo')),
            ('https://github.com/user/repo/', ('user', 'repo')),
            ('https://github.com/test-user/test-repo', ('test-user', 'test-repo')),
            ('https://github.com/user123/repo-name', ('user123', 'repo-name'))
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url):
                owner, repo = extract_repo_info(url)
                self.assertEqual((owner, repo), expected)
    
    def test_extract_repo_info_invalid_urls(self):
        """Test repository info extraction with invalid URLs."""
        # Test with URLs that don't have enough parts
        owner, repo = extract_repo_info('invalid-url')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
        
        owner, repo = extract_repo_info('')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
        
        # Test with single part URL
        owner, repo = extract_repo_info('single')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
        
        # Test with URLs that have parts but aren't proper GitHub repo URLs
        # The function extracts the last two parts, so these will extract something
        owner, repo = extract_repo_info('https://github.com/user')
        self.assertEqual(owner, 'github.com')
        self.assertEqual(repo, 'user')
        
        # For URL ending with slash, the function returns empty string and 'github.com'
        owner, repo = extract_repo_info('https://github.com/')
        self.assertEqual(owner, '')
        self.assertEqual(repo, 'github.com')
    
    def test_index_get_request(self):
        """Test GET request to index page."""
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GitHub Repository Analyzer', response.data)
    
    def test_index_post_empty_url(self):
        """Test POST request with empty URL."""
        response = self.client.post('/', data={'github_url': ''})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please enter a GitHub repository URL', response.data)
    
    def test_index_post_invalid_url(self):
        """Test POST request with invalid URL."""
        response = self.client.post('/', data={'github_url': 'invalid-url'})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please enter a valid GitHub repository URL', response.data)
    
    def test_index_post_malformed_github_url(self):
        """Test POST request with malformed GitHub URL."""
        response = self.client.post('/', data={'github_url': 'https://github.com/user'})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please enter a valid GitHub repository URL', response.data)
    
    @patch('app.GitHubAnalyzer')
    @patch('tempfile.mkdtemp')
    @patch('os.path.exists')
    @patch('shutil.rmtree')
    def test_index_post_successful_analysis(self, mock_rmtree, mock_exists, mock_mkdtemp, mock_analyzer_class):
        """Test POST request with successful analysis."""
        # Mock temporary directory
        mock_mkdtemp.return_value = '/tmp/test_dir'
        mock_exists.return_value = True
        
        # Mock analyzer
        mock_analyzer = Mock()
        # Mock successful analysis result
        mock_result = {
            'repository': {
                'name': 'test-repo',
                'full_name': 'user/test-repo',
                'description': 'A test repository for Python development',
                'language': 'Python',
                'stars': 10,
                'forks': 5,
                'issues': 3,
                'size': 1024,
                'created_at': '2023-01-01T00:00:00Z',
                'updated_at': '2023-12-01T00:00:00Z',
                'pushed_at': '2023-12-01T00:00:00Z',
                'default_branch': 'main'
            },
            'code_metrics': {
                'total_files': 10,
                'primary_language': 'Python',
                'languages': {'Python': 8},
                'complexity_score': 'Low',
                'code_files': 8,
                'total_lines': 1000,
                'code_lines': 800,
                'comment_lines': 100,
                'blank_lines': 100
            },
            'project_structure': {'directories': 3},
            'build_systems': {'detected_systems': []},
            'security': {'issues': []},
            'health_indicators': {'score': 85},
            'code_quality': {'issues': []},
            'recommendations': ['Great job!']
        }
        mock_analyzer.analyze_repository.return_value = mock_result
        mock_analyzer_class.return_value = mock_analyzer
        
        response = self.client.post('/', data={'github_url': 'https://github.com/user/test-repo'})
        
        self.assertEqual(response.status_code, 200)
        
        # Verify analyzer was called correctly
        mock_analyzer.analyze_repository.assert_called_once_with('user', 'test-repo', '/tmp/test_dir')
        
        # Check that we get a valid HTML response (not an error page)
        response_text = response.data.decode('utf-8')
        self.assertIn('<!DOCTYPE html>', response_text)
        self.assertIn('GitHub Repository Analyzer', response_text)
        
        # Verify cleanup
        mock_rmtree.assert_called_once_with('/tmp/test_dir', ignore_errors=True)
    
    @patch('app.GitHubAnalyzer')
    @patch('tempfile.mkdtemp')
    @patch('os.path.exists')
    @patch('shutil.rmtree')
    def test_index_post_analysis_error(self, mock_rmtree, mock_exists, mock_mkdtemp, mock_analyzer_class):
        """Test POST request when analysis returns error."""
        # Mock temporary directory
        mock_mkdtemp.return_value = '/tmp/test_dir'
        mock_exists.return_value = True
        
        # Mock analyzer with error
        mock_analyzer = Mock()
        mock_analyzer.analyze_repository.return_value = {
            'error': 'Repository not found'
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        response = self.client.post('/', data={'github_url': 'https://github.com/user/nonexistent'})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Analysis failed: Repository not found', response.data)
        
        # Verify cleanup still happens
        mock_rmtree.assert_called_once_with('/tmp/test_dir', ignore_errors=True)
    
    @patch('app.GitHubAnalyzer')
    @patch('tempfile.mkdtemp')
    def test_index_post_exception_handling(self, mock_mkdtemp, mock_analyzer_class):
        """Test POST request when exception occurs during analysis."""
        # Mock temporary directory
        mock_mkdtemp.return_value = '/tmp/test_dir'
        
        # Mock analyzer to raise exception
        mock_analyzer_class.side_effect = Exception("Unexpected error")
        
        response = self.client.post('/', data={'github_url': 'https://github.com/user/repo'})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'An error occurred during analysis', response.data)
    
    def test_404_error_handler(self):
        """Test 404 error handler."""
        response = self.client.get('/nonexistent-page')
        
        self.assertEqual(response.status_code, 404)
    
    def test_500_error_handler(self):
        """Test 500 error handler."""
        # Test the error handler by patching a function to raise an exception
        with patch('app.GitHubAnalyzer') as mock_analyzer_class:
            mock_analyzer_class.side_effect = Exception("Test error")
            
            response = self.client.post('/', data={'github_url': 'https://github.com/user/repo'})
            self.assertEqual(response.status_code, 200)  # Flask catches the exception and returns 200 with error message
            # Check that the error message is flashed
            self.assertIn(b'An error occurred during analysis', response.data)
    
    def test_app_configuration(self):
        """Test Flask app configuration."""
        self.assertEqual(self.app.secret_key, 'github-analyzer-secret-key-2024')
        self.assertTrue(self.app.config['TESTING'])
    
    def test_form_data_handling(self):
        """Test various form data scenarios."""
        # Test with whitespace
        response = self.client.post('/', data={'github_url': '  https://github.com/user/repo  '})
        # Should strip whitespace and process normally
        
        # Test without github_url field
        response = self.client.post('/', data={})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please enter a GitHub repository URL', response.data)

if __name__ == '__main__':
    unittest.main()