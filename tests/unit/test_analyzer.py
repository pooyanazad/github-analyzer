import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import shutil
import json
from collections import defaultdict
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from analyzer import GitHubAnalyzer

class TestGitHubAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.analyzer = GitHubAnalyzer()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test GitHubAnalyzer initialization."""
        self.assertEqual(self.analyzer.github_api_base, "https://api.github.com")
        self.assertIsNotNone(self.analyzer.session)
        self.assertEqual(self.analyzer.session.headers['Accept'], 'application/vnd.github.v3+json')
        self.assertEqual(self.analyzer.session.headers['User-Agent'], 'GitHub-Analyzer/1.0')
    
    @patch('analyzer.GitHubAnalyzer._get_repo_info')
    @patch('analyzer.GitHubAnalyzer._clone_repository')
    @patch('analyzer.GitHubAnalyzer._analyze_code_metrics')
    @patch('analyzer.GitHubAnalyzer._analyze_project_structure')
    @patch('analyzer.GitHubAnalyzer._detect_build_systems')
    @patch('analyzer.GitHubAnalyzer._basic_security_scan')
    @patch('analyzer.GitHubAnalyzer._analyze_repo_health')
    @patch('analyzer.GitHubAnalyzer._analyze_code_quality')
    @patch('analyzer.GitHubAnalyzer._generate_recommendations')
    def test_analyze_repository_success(self, mock_recommendations, mock_quality, 
                                      mock_health, mock_security, mock_build,
                                      mock_structure, mock_metrics, mock_clone, mock_repo_info):
        """Test successful repository analysis."""
        # Mock return values
        mock_repo_info.return_value = {'name': 'test-repo', 'clone_url': 'https://github.com/test/repo.git'}
        mock_clone.return_value = True
        mock_metrics.return_value = {'total_files': 10}
        mock_structure.return_value = {'directories': 5}
        mock_build.return_value = {'build_tools': ['npm']}
        mock_security.return_value = {'issues': []}
        mock_health.return_value = {'score': 85}
        mock_quality.return_value = {'issues': []}
        mock_recommendations.return_value = ['Use more tests']
        
        result = self.analyzer.analyze_repository('test', 'repo', self.temp_dir)
        
        self.assertNotIn('error', result)
        self.assertIn('repository', result)
        self.assertIn('code_metrics', result)
        self.assertIn('recommendations', result)
        
        # Verify all methods were called
        mock_repo_info.assert_called_once_with('test', 'repo')
        mock_clone.assert_called_once()
        mock_metrics.assert_called_once()
    
    @patch('analyzer.GitHubAnalyzer._get_repo_info')
    def test_analyze_repository_repo_not_found(self, mock_repo_info):
        """Test repository analysis when repo is not found."""
        mock_repo_info.return_value = None
        
        result = self.analyzer.analyze_repository('test', 'nonexistent', self.temp_dir)
        
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Repository not found or not accessible')
    
    @patch('analyzer.GitHubAnalyzer._get_repo_info')
    @patch('analyzer.GitHubAnalyzer._clone_repository')
    def test_analyze_repository_clone_failed(self, mock_clone, mock_repo_info):
        """Test repository analysis when cloning fails."""
        mock_repo_info.return_value = {'name': 'test-repo', 'clone_url': 'https://github.com/test/repo.git'}
        mock_clone.return_value = False
        
        result = self.analyzer.analyze_repository('test', 'repo', self.temp_dir)
        
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Failed to clone repository')
    
    @patch('requests.Session.get')
    def test_get_repo_info_success(self, mock_get):
        """Test successful repository info retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'test-repo',
            'full_name': 'test/test-repo',
            'description': 'A test repository',
            'language': 'Python',
            'size': 1024,
            'stargazers_count': 10,
            'forks_count': 5,
            'open_issues_count': 2,
            'created_at': '2023-01-01T00:00:00Z',
            'updated_at': '2023-12-01T00:00:00Z',
            'pushed_at': '2023-12-01T00:00:00Z',
            'clone_url': 'https://github.com/test/test-repo.git',
            'default_branch': 'main',
            'archived': False,
            'disabled': False,
            'private': False,
            'has_wiki': True
        }
        mock_get.return_value = mock_response
        
        result = self.analyzer._get_repo_info('test', 'test-repo')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'test-repo')
        self.assertEqual(result['language'], 'Python')
        self.assertEqual(result['stars'], 10)
        self.assertEqual(result['forks'], 5)
    
    @patch('requests.Session.get')
    def test_get_repo_info_not_found(self, mock_get):
        """Test repository info retrieval when repo is not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = self.analyzer._get_repo_info('test', 'nonexistent')
        
        self.assertIsNone(result)
    
    @patch('requests.Session.get')
    def test_get_repo_info_api_error(self, mock_get):
        """Test repository info retrieval when API returns error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = self.analyzer._get_repo_info('test', 'repo')
        
        self.assertIsNone(result)
    
    @patch('requests.Session.get')
    def test_get_repo_info_exception(self, mock_get):
        """Test repository info retrieval when exception occurs."""
        mock_get.side_effect = Exception("Network error")
        
        result = self.analyzer._get_repo_info('test', 'repo')
        
        self.assertIsNone(result)
    
    @patch('subprocess.run')
    def test_clone_repository_success(self, mock_run):
        """Test successful repository cloning."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.analyzer._clone_repository('https://github.com/test/repo.git', '/tmp/repo')
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ['git', 'clone', '--depth', '1', 'https://github.com/test/repo.git', '/tmp/repo'],
            capture_output=True, text=True, timeout=60
        )
    
    @patch('subprocess.run')
    def test_clone_repository_failure(self, mock_run):
        """Test repository cloning failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        result = self.analyzer._clone_repository('https://github.com/test/repo.git', '/tmp/repo')
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_clone_repository_exception(self, mock_run):
        """Test repository cloning when exception occurs."""
        mock_run.side_effect = Exception("Git command failed")
        
        result = self.analyzer._clone_repository('https://github.com/test/repo.git', '/tmp/repo')
        
        self.assertFalse(result)
    
    def test_analyze_code_metrics_empty_directory(self):
        """Test code metrics analysis on empty directory."""
        result = self.analyzer._analyze_code_metrics(self.temp_dir)
        
        self.assertEqual(result['total_files'], 0)
        self.assertEqual(result['code_files'], 0)
        self.assertEqual(result['total_lines'], 0)
        self.assertEqual(result['complexity_score'], 'Low')
        self.assertIsInstance(result['languages'], dict)
        self.assertIsInstance(result['file_types'], dict)
    
    def test_analyze_code_metrics_with_files(self):
        """Test code metrics analysis with sample files."""
        # Create test files
        test_file_py = os.path.join(self.temp_dir, 'test.py')
        test_file_js = os.path.join(self.temp_dir, 'test.js')
        
        with open(test_file_py, 'w') as f:
            f.write('# Python comment\nprint("Hello World")\n\n')
        
        with open(test_file_js, 'w') as f:
            f.write('// JavaScript comment\nconsole.log("Hello World");\n')
        
        result = self.analyzer._analyze_code_metrics(self.temp_dir)
        
        self.assertEqual(result['total_files'], 2)
        self.assertGreater(result['total_lines'], 0)
        self.assertIn('Python', result['languages'])
        self.assertIn('JavaScript', result['languages'])

if __name__ == '__main__':
    unittest.main()