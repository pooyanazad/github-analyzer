import requests
import os
import subprocess
import json
from datetime import datetime, timedelta
import tempfile
import shutil
from collections import defaultdict, Counter
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import ast
import math

class GitHubAnalyzer:
    def __init__(self):
        self.github_api_base = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Analyzer/1.0'
        })
    
    def analyze_repository(self, owner, repo, temp_dir):
        """Main analysis function that orchestrates all analysis steps"""
        try:
            # Get basic repository information
            repo_info = self._get_repo_info(owner, repo)
            if not repo_info:
                return {'error': 'Repository not found or not accessible'}
            
            # Clone repository for deep analysis
            clone_path = os.path.join(temp_dir, repo)
            if not self._clone_repository(repo_info['clone_url'], clone_path):
                return {'error': 'Failed to clone repository'}
            
            # Perform various analyses
            analysis = {
                'repository': repo_info,
                'code_metrics': self._analyze_code_metrics(clone_path),
                'project_structure': self._analyze_project_structure(clone_path, repo_info),
                'build_systems': self._detect_build_systems(clone_path),
                'security': self._basic_security_scan(clone_path),
                'health_indicators': self._analyze_repo_health(repo_info, owner, repo),
                'code_quality': self._analyze_code_quality(clone_path),
                'recommendations': []
            }
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _get_repo_info(self, owner, repo):
        """Get repository information from GitHub API"""
        try:
            url = f"{self.github_api_base}/repos/{owner}/{repo}"
            response = self.session.get(url)
            
            if response.status_code == 404:
                return None
            elif response.status_code != 200:
                return None
            
            data = response.json()
            return {
                'owner': owner,
                'name': data['name'],
                'full_name': data['full_name'],
                'description': data.get('description', 'No description'),
                'language': data.get('language', 'Unknown'),
                'size': data['size'],
                'stars': data['stargazers_count'],
                'forks': data['forks_count'],
                'issues': data['open_issues_count'],
                'created_at': data['created_at'],
                'updated_at': data['updated_at'],
                'pushed_at': data['pushed_at'],
                'clone_url': data['clone_url'],
                'default_branch': data['default_branch'],
                'archived': data['archived'],
                'disabled': data['disabled'],
                'private': data['private'],
                'has_wiki': data.get('has_wiki', False)
            }
        except Exception:
            return None
    
    def _clone_repository(self, clone_url, clone_path):
        """Clone repository to temporary directory"""
        try:
            cmd = ['git', 'clone', '--depth', '1', clone_url, clone_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False
    
    def _analyze_code_metrics(self, repo_path):
        """Analyze code metrics like file count, languages, complexity with parallel processing"""
        metrics = {
            'total_files': 0,
            'code_files': 0,
            'languages': defaultdict(int),
            'file_types': defaultdict(int),
            'total_lines': 0,
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'largest_files': [],
            'complexity_score': 'Low'
        }
        
        # Language extensions mapping
        lang_extensions = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.cs': 'C#',
            '.php': 'PHP', '.rb': 'Ruby', '.go': 'Go', '.rs': 'Rust',
            '.swift': 'Swift', '.kt': 'Kotlin', '.scala': 'Scala',
            '.html': 'HTML', '.css': 'CSS', '.scss': 'SCSS',
            '.json': 'JSON', '.xml': 'XML', '.yaml': 'YAML', '.yml': 'YAML',
            '.md': 'Markdown', '.txt': 'Text', '.sh': 'Shell',
            '.sql': 'SQL', '.r': 'R', '.m': 'Objective-C'
        }
        
        # Collect all files first (single walk)
        all_files = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)
        
        # Thread-safe counters
        lock = threading.Lock()
        file_sizes = []
        lang_lines = defaultdict(int)
        
        def process_file(file_path):
            """Process a single file and return its metrics"""
            try:
                file_size = os.path.getsize(file_path)
                file_ext = Path(file_path).suffix.lower()
                filename = os.path.basename(file_path)
                
                result = {
                    'filename': filename,
                    'size': file_size,
                    'ext': file_ext if file_ext else 'no_extension',
                    'lang': None,
                    'total_lines': 0,
                    'code_lines': 0,
                    'comment_lines': 0,
                    'blank_lines': 0,
                    'lang_code_lines': 0
                }
                
                # Language detection
                if file_ext in lang_extensions:
                    lang = lang_extensions[file_ext]
                    result['lang'] = lang
                    
                    # Count lines for code files
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            result['total_lines'] = len(lines)
                            
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    result['blank_lines'] += 1
                                elif line.startswith('#') or line.startswith('//'):
                                    result['comment_lines'] += 1
                                else:
                                    result['code_lines'] += 1
                            
                            # For primary language detection (exclude docs)
                            if lang not in ['Markdown', 'Text', 'JSON', 'XML', 'YAML']:
                                result['lang_code_lines'] = result['code_lines']
                    except Exception:
                        pass
                
                return result
            except Exception:
                return None
        
        # Process files in parallel
        max_workers = min(32, (os.cpu_count() or 1) + 4)  # Reasonable thread count
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all file processing tasks
            future_to_file = {executor.submit(process_file, file_path): file_path 
                            for file_path in all_files}
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                result = future.result()
                if result is None:
                    continue
                
                with lock:
                    metrics['total_files'] += 1
                    metrics['file_types'][result['ext']] += 1
                    file_sizes.append((result['filename'], result['size']))
                    
                    if result['lang']:
                        metrics['languages'][result['lang']] += 1
                        metrics['code_files'] += 1
                        metrics['total_lines'] += result['total_lines']
                        metrics['code_lines'] += result['code_lines']
                        metrics['comment_lines'] += result['comment_lines']
                        metrics['blank_lines'] += result['blank_lines']
                        
                        # Track lines for primary language detection
                        if result['lang_code_lines'] > 0:
                            lang_lines[result['lang']] += result['lang_code_lines']
        
        # Get largest files
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        metrics['largest_files'] = file_sizes[:5]
        
        # Determine primary language based on lines of code
        if lang_lines:
            metrics['primary_language'] = max(lang_lines.items(), key=lambda x: x[1])[0]
        elif metrics['languages']:
            # Fallback to most common file type (excluding docs)
            code_langs = {k: v for k, v in metrics['languages'].items() 
                         if k not in ['Markdown', 'Text', 'JSON', 'XML', 'YAML']}
            if code_langs:
                metrics['primary_language'] = max(code_langs.items(), key=lambda x: x[1])[0]
            else:
                metrics['primary_language'] = max(metrics['languages'].items(), key=lambda x: x[1])[0]
        else:
            metrics['primary_language'] = 'Unknown'
        
        # Simple complexity estimation
        if metrics['code_files'] > 100 or metrics['code_lines'] > 10000:
            metrics['complexity_score'] = 'High'
        elif metrics['code_files'] > 50 or metrics['code_lines'] > 5000:
            metrics['complexity_score'] = 'Medium'
        
        # Sort languages to prioritize programming languages over documentation
        def language_priority(lang_name):
            # Documentation and config languages get lower priority (higher number)
            doc_languages = ['Markdown', 'Text', 'JSON', 'XML', 'YAML', 'HTML', 'CSS']
            if lang_name in doc_languages:
                return 1
            return 0
        
        # Sort languages by priority (programming first) then by file count
        sorted_languages = dict(sorted(
            metrics['languages'].items(),
            key=lambda x: (language_priority(x[0]), -x[1])
        ))
        metrics['languages'] = sorted_languages
        
        return dict(metrics)
    
    def _analyze_project_structure(self, repo_path, repo_info=None):
        """Analyze project structure and organization"""
        structure = {
            'has_readme': False,
            'has_license': False,
            'has_contributing': False,
            'has_changelog': False,
            'has_tests': False,
            'has_docs': False,
            'has_ci_cd': False,
            'directory_structure': [],
            'organization_score': 0
        }
        
        # Check for important files
        important_files = {
            'readme': ['README.md', 'README.txt', 'README.rst', 'readme.md'],
            'license': ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING'],
            'contributing': ['CONTRIBUTING.md', 'CONTRIBUTING.txt'],
            'changelog': ['CHANGELOG.md', 'CHANGELOG.txt', 'HISTORY.md']
        }
        
        # Check for directories
        test_dirs = ['test', 'tests', '__tests__', 'spec', 'specs']
        doc_dirs = ['docs', 'doc', 'documentation']
        ci_files = ['.gitlab-ci.yml', '.travis.yml', 'Jenkinsfile', 'azure-pipelines.yml', 'bitbucket-pipelines.yml']
        
        for root, dirs, files in os.walk(repo_path):
            level = root.replace(repo_path, '').count(os.sep)
            if level < 3:  # Only show first 3 levels
                indent = ' ' * 2 * level
                structure['directory_structure'].append(f"{indent}{os.path.basename(root)}/")
            
            # Check for important files
            for file in files:
                file_lower = file.lower()
                
                for category, patterns in important_files.items():
                    if any(pattern.lower() == file_lower for pattern in patterns):
                        structure[f'has_{category}'] = True
                
                # Check for CI/CD files
                if file in ci_files:
                    structure['has_ci_cd'] = True
                
                # Check for GitHub Actions workflows
                if '.github' in root and 'workflows' in root and (file.endswith('.yml') or file.endswith('.yaml')):
                    structure['has_ci_cd'] = True
                
                # Check for Docker Compose (more indicative of CI/CD than just Dockerfile)
                if file.lower() in ['docker-compose.yml', 'docker-compose.yaml']:
                    structure['has_ci_cd'] = True
                
                # Check for Dockerfile only if it's in a CI/CD context (with other indicators)
                if file.lower() == 'dockerfile':
                    # Only consider Dockerfile as CI/CD if there are other CI/CD indicators
                    # This prevents false positives from standalone Dockerfiles
                    pass  # We'll check this later with more context
                
                # Check for CircleCI
                if '.circleci' in root and file.lower() == 'config.yml':
                    structure['has_ci_cd'] = True
            
            # Check for test and doc directories
            for dir_name in dirs:
                if dir_name.lower() in test_dirs:
                    structure['has_tests'] = True
                if dir_name.lower() in doc_dirs:
                    structure['has_docs'] = True
                
                # Check for CI/CD directories (more specific)
                if dir_name in ['.gitlab', '.circleci', '.azure']:
                    structure['has_ci_cd'] = True
                # For .github, we already check for workflows in the file loop above
        
        # Check for GitHub wiki if repo_info is available and verify it has content
        if repo_info and repo_info.get('has_wiki', False):
            # Verify wiki actually has content by checking the raw wiki Home page
            try:
                # Try to access the wiki's Home page via raw content URL
                wiki_home_url = f"https://raw.githubusercontent.com/wiki/{repo_info.get('owner', '')}/{repo_info.get('name', '')}/Home.md"
                wiki_response = requests.get(wiki_home_url)
                if wiki_response.status_code == 200 and len(wiki_response.text.strip()) > 0:
                    structure['has_docs'] = True
            except:
                # If wiki check fails, don't mark as having docs
                pass
        
        # Calculate organization score
        score = 0
        if structure['has_readme']: score += 2
        if structure['has_license']: score += 1
        if structure['has_contributing']: score += 1
        if structure['has_tests']: score += 2
        if structure['has_docs']: score += 1
        if structure['has_ci_cd']: score += 1
        if structure['has_changelog']: score += 1
        
        structure['organization_score'] = min(score, 10)
        
        return structure

    def _analyze_code_quality(self, repo_path):
        """Analyze code quality metrics including complexity, maintainability, and technical debt"""
        quality = {
            'overall_score': 0,
            'complexity_score': 0,
            'maintainability_score': 0,
            'technical_debt_score': 0,
            'code_smells': [],
            'complexity_metrics': {
                'cyclomatic_complexity': 0,
                'cognitive_complexity': 0,
                'max_complexity': 0,
                'avg_complexity': 0
            },
            'maintainability_metrics': {
                'maintainability_index': 0,
                'code_coverage_estimate': 0,
                'documentation_ratio': 0
            },
            'technical_debt': {
                'code_duplication': 0,
                'long_methods': 0,
                'large_classes': 0,
                'deep_nesting': 0
            },
            'language_quality': {}
        }
        
        # Collect all code files
        code_files = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    file_ext = Path(file_path).suffix.lower()
                    if file_ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go']:
                        code_files.append((file_path, file_ext))
        
        if not code_files:
            return quality
        
        # Analyze each file
        total_complexity = 0
        total_methods = 0
        total_lines = 0
        total_comment_lines = 0
        complexity_scores = []
        
        for file_path, file_ext in code_files:
            try:
                file_quality = self._analyze_file_quality(file_path, file_ext)
                
                # Aggregate complexity metrics
                if file_quality['complexity'] > 0:
                    total_complexity += file_quality['complexity']
                    total_methods += file_quality['methods_count']
                    complexity_scores.append(file_quality['complexity'])
                    
                    if file_quality['complexity'] > quality['complexity_metrics']['max_complexity']:
                        quality['complexity_metrics']['max_complexity'] = file_quality['complexity']
                
                # Aggregate maintainability metrics
                total_lines += file_quality['lines_of_code']
                total_comment_lines += file_quality['comment_lines']
                
                # Collect code smells
                quality['code_smells'].extend(file_quality['code_smells'])
                
                # Technical debt indicators
                quality['technical_debt']['long_methods'] += file_quality['long_methods']
                quality['technical_debt']['large_classes'] += file_quality['large_classes']
                quality['technical_debt']['deep_nesting'] += file_quality['deep_nesting']
                
                # Language-specific quality
                lang = self._get_language_from_extension(file_ext)
                if lang not in quality['language_quality']:
                    quality['language_quality'][lang] = {'files': 0, 'avg_complexity': 0, 'issues': 0, 'lines': 0}
                
                quality['language_quality'][lang]['files'] += 1
                quality['language_quality'][lang]['avg_complexity'] += file_quality['complexity']
                quality['language_quality'][lang]['issues'] += len(file_quality['code_smells'])
                quality['language_quality'][lang]['lines'] += file_quality['lines_of_code']
                
            except Exception:
                continue
        
        # Calculate aggregate metrics
        if total_methods > 0:
            quality['complexity_metrics']['cyclomatic_complexity'] = total_complexity
            quality['complexity_metrics']['avg_complexity'] = total_complexity / total_methods
        
        # Calculate maintainability index (Microsoft's formula)
        if total_lines > 0:
            halstead_volume = max(total_lines * 0.5, 1)  # Simplified Halstead volume
            avg_complexity = quality['complexity_metrics']['avg_complexity']
            comment_ratio = total_comment_lines / total_lines if total_lines > 0 else 0
            
            maintainability_index = max(0, (
                171 - 5.2 * math.log(halstead_volume) - 
                0.23 * avg_complexity - 
                16.2 * math.log(total_lines) + 
                50 * math.sin(math.sqrt(2.4 * comment_ratio))
            ))
            
            quality['maintainability_metrics']['maintainability_index'] = min(100, maintainability_index)
            quality['maintainability_metrics']['documentation_ratio'] = comment_ratio * 100
        
        # Calculate scores (0-10 scale)
        complexity_score = max(0, 10 - (quality['complexity_metrics']['avg_complexity'] / 2))
        quality['complexity_score'] = min(10, complexity_score)
        
        maintainability_score = quality['maintainability_metrics']['maintainability_index'] / 10
        quality['maintainability_score'] = min(10, maintainability_score)
        
        # Technical debt score (inverse of issues)
        total_issues = len(quality['code_smells']) + sum(quality['technical_debt'].values())
        debt_score = max(0, 10 - (total_issues / len(code_files)) if code_files else 10)
        quality['technical_debt_score'] = debt_score
        
        # Overall quality score (weighted average)
        quality['overall_score'] = (
            quality['complexity_score'] * 0.3 + 
            quality['maintainability_score'] * 0.4 + 
            quality['technical_debt_score'] * 0.3
        )
        
        # Finalize language quality averages
        for lang_data in quality['language_quality'].values():
            if lang_data['files'] > 0:
                lang_data['avg_complexity'] /= lang_data['files']
        
        # Sort languages to prioritize programming languages over documentation
        def language_priority(lang_name):
            # Documentation and config languages get lower priority (higher number)
            doc_languages = ['Markdown', 'Text', 'JSON', 'XML', 'YAML', 'HTML', 'CSS']
            if lang_name in doc_languages:
                return 1
            return 0
        
        # Sort languages by priority (programming first) then by file count
        sorted_languages = dict(sorted(
            quality['language_quality'].items(),
            key=lambda x: (language_priority(x[0]), -x[1]['files'])
        ))
        
        # Add languages key for template compatibility
        quality['languages'] = sorted_languages
        
        # Add issues list for template compatibility
        quality['issues'] = quality['code_smells']
        
        return quality
    
    def _analyze_file_quality(self, file_path, file_ext):
        """Analyze quality metrics for a single file"""
        quality = {
            'complexity': 0,
            'methods_count': 0,
            'lines_of_code': 0,
            'comment_lines': 0,
            'code_smells': [],
            'long_methods': 0,
            'large_classes': 0,
            'deep_nesting': 0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
            quality['lines_of_code'] = len([line for line in lines if line.strip()])
            quality['comment_lines'] = len([line for line in lines if line.strip().startswith(('#', '//', '/*', '*', '<!--'))])
            
            # Language-specific analysis
            if file_ext == '.py':
                quality.update(self._analyze_python_quality(content, file_path))
            elif file_ext in ['.js', '.ts']:
                quality.update(self._analyze_javascript_quality(content, file_path))
            else:
                quality.update(self._analyze_generic_quality(content, file_path))
                
        except Exception:
            pass
            
        return quality
    
    def _analyze_python_quality(self, content, file_path):
        """Analyze Python-specific code quality"""
        quality = {
            'complexity': 0,
            'methods_count': 0,
            'code_smells': [],
            'long_methods': 0,
            'large_classes': 0,
            'deep_nesting': 0
        }
        
        try:
            tree = ast.parse(content)
            
            class QualityVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.complexity = 0
                    self.methods_count = 0
                    self.code_smells = []
                    self.long_methods = 0
                    self.large_classes = 0
                    self.max_nesting = 0
                    self.current_nesting = 0
                
                def visit_FunctionDef(self, node):
                    self.methods_count += 1
                    method_complexity = self._calculate_complexity(node)
                    self.complexity += method_complexity
                    
                    # Check for long methods (>50 lines)
                    method_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    if method_lines > 50:
                        self.long_methods += 1
                        self.code_smells.append({
                            'type': 'Long Method',
                            'location': f"Line {node.lineno}",
                            'description': f"Method '{node.name}' is {method_lines} lines long"
                        })
                    
                    # Check for high complexity
                    if method_complexity > 10:
                        self.code_smells.append({
                            'type': 'High Complexity',
                            'location': f"Line {node.lineno}",
                            'description': f"Method '{node.name}' has complexity {method_complexity}"
                        })
                    
                    self.generic_visit(node)
                
                def visit_ClassDef(self, node):
                    # Check for large classes (>500 lines)
                    class_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    if class_lines > 500:
                        self.large_classes += 1
                        self.code_smells.append({
                            'type': 'Large Class',
                            'location': f"Line {node.lineno}",
                            'description': f"Class '{node.name}' is {class_lines} lines long"
                        })
                    
                    self.generic_visit(node)
                
                def visit_If(self, node):
                    self.current_nesting += 1
                    self.max_nesting = max(self.max_nesting, self.current_nesting)
                    self.complexity += 1
                    self.generic_visit(node)
                    self.current_nesting -= 1
                
                def visit_For(self, node):
                    self.current_nesting += 1
                    self.max_nesting = max(self.max_nesting, self.current_nesting)
                    self.complexity += 1
                    self.generic_visit(node)
                    self.current_nesting -= 1
                
                def visit_While(self, node):
                    self.current_nesting += 1
                    self.max_nesting = max(self.max_nesting, self.current_nesting)
                    self.complexity += 1
                    self.generic_visit(node)
                    self.current_nesting -= 1
                
                def visit_Try(self, node):
                    self.complexity += 1
                    self.generic_visit(node)
                
                def _calculate_complexity(self, node):
                    """Calculate cyclomatic complexity for a function"""
                    complexity = 1  # Base complexity
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                            complexity += 1
                        elif isinstance(child, ast.BoolOp):
                            complexity += len(child.values) - 1
                    return complexity
            
            visitor = QualityVisitor()
            visitor.visit(tree)
            
            quality['complexity'] = visitor.complexity
            quality['methods_count'] = visitor.methods_count
            quality['code_smells'] = visitor.code_smells
            quality['long_methods'] = visitor.long_methods
            quality['large_classes'] = visitor.large_classes
            quality['deep_nesting'] = 1 if visitor.max_nesting > 4 else 0
            
            if visitor.max_nesting > 4:
                quality['code_smells'].append({
                    'type': 'Deep Nesting',
                    'location': 'Multiple locations',
                    'description': f'Maximum nesting depth: {visitor.max_nesting}'
                })
                
        except Exception:
            pass
            
        return quality
    
    def _analyze_javascript_quality(self, content, file_path):
        """Analyze JavaScript/TypeScript code quality using pattern matching"""
        quality = {
            'complexity': 0,
            'methods_count': 0,
            'code_smells': [],
            'long_methods': 0,
            'large_classes': 0,
            'deep_nesting': 0
        }
        
        lines = content.split('\n')
        
        # Simple pattern-based analysis
        function_pattern = re.compile(r'\b(function|=>|\w+\s*\(.*\)\s*{)')
        class_pattern = re.compile(r'\bclass\s+\w+')
        complexity_patterns = [
            re.compile(r'\bif\s*\('),
            re.compile(r'\bfor\s*\('),
            re.compile(r'\bwhile\s*\('),
            re.compile(r'\btry\s*{'),
            re.compile(r'\bcatch\s*\('),
            re.compile(r'&&|\|\|')
        ]
        
        current_function_lines = 0
        in_function = False
        brace_count = 0
        max_nesting = 0
        current_nesting = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Count functions
            if function_pattern.search(line):
                quality['methods_count'] += 1
                in_function = True
                current_function_lines = 0
            
            # Count classes
            if class_pattern.search(line):
                # Simple class size estimation
                pass
            
            # Track nesting
            if '{' in line:
                current_nesting += line.count('{')
                max_nesting = max(max_nesting, current_nesting)
            if '}' in line:
                current_nesting -= line.count('}')
                if in_function and current_nesting == 0:
                    in_function = False
                    if current_function_lines > 50:
                        quality['long_methods'] += 1
                        quality['code_smells'].append({
                            'type': 'Long Function',
                            'location': f'Line {i+1}',
                            'description': f'Function is {current_function_lines} lines long'
                        })
            
            if in_function:
                current_function_lines += 1
            
            # Count complexity indicators
            for pattern in complexity_patterns:
                quality['complexity'] += len(pattern.findall(line))
        
        if max_nesting > 4:
            quality['deep_nesting'] = 1
            quality['code_smells'].append({
                'type': 'Deep Nesting',
                'location': 'Multiple locations',
                'description': f'Maximum nesting depth: {max_nesting}'
            })
        
        return quality
    
    def _analyze_generic_quality(self, content, file_path):
        """Generic code quality analysis for other languages"""
        quality = {
            'complexity': 0,
            'methods_count': 0,
            'code_smells': [],
            'long_methods': 0,
            'large_classes': 0,
            'deep_nesting': 0
        }
        
        lines = content.split('\n')
        
        # Generic complexity indicators
        complexity_keywords = ['if', 'else', 'for', 'while', 'switch', 'case', 'try', 'catch']
        method_keywords = ['function', 'def', 'public', 'private', 'protected']
        
        current_method_lines = 0
        in_method = False
        brace_count = 0
        max_nesting = 0
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Count methods (rough estimation)
            if any(keyword in line_lower for keyword in method_keywords):
                quality['methods_count'] += 1
                in_method = True
                current_method_lines = 0
            
            # Count complexity
            for keyword in complexity_keywords:
                quality['complexity'] += line_lower.count(keyword)
            
            # Track method length
            if in_method:
                current_method_lines += 1
                if '}' in line and current_method_lines > 50:
                    quality['long_methods'] += 1
                    quality['code_smells'].append({
                        'type': 'Long Method',
                        'location': f'Line {i+1}',
                        'description': f'Method is approximately {current_method_lines} lines long'
                    })
                    in_method = False
            
            # Track nesting (rough estimation)
            brace_count += line.count('{') - line.count('}')
            max_nesting = max(max_nesting, brace_count)
        
        if max_nesting > 4:
            quality['deep_nesting'] = 1
            quality['code_smells'].append({
                'type': 'Deep Nesting',
                'location': 'Multiple locations',
                'description': f'Estimated maximum nesting depth: {max_nesting}'
            })
        
        return quality
    
    def _get_language_from_extension(self, ext):
        """Get language name from file extension"""
        lang_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.go': 'Go'
        }
        return lang_map.get(ext, 'Unknown')

    def _detect_build_systems(self, repo_path):
        """Detect build systems and dependency management"""
        build_systems = {
            'detected_systems': [],
            'package_managers': [],
            'build_files': [],
            'dependencies_count': 0
        }
        
        # Build system indicators
        build_indicators = {
            'npm': ['package.json', 'package-lock.json', 'yarn.lock'],
            'pip': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
            'maven': ['pom.xml'],
            'gradle': ['build.gradle', 'build.gradle.kts'],
            'composer': ['composer.json'],
            'bundler': ['Gemfile'],
            'cargo': ['Cargo.toml'],
            'go_modules': ['go.mod'],
            'cmake': ['CMakeLists.txt'],
            'make': ['Makefile', 'makefile'],
            'docker': ['Dockerfile', 'docker-compose.yml']
        }
        
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                for system, indicators in build_indicators.items():
                    if file in indicators:
                        if system not in build_systems['detected_systems']:
                            build_systems['detected_systems'].append(system)
                        build_systems['build_files'].append(file)
                        
                        # Try to count dependencies
                        file_path = os.path.join(root, file)
                        deps = self._count_dependencies(file_path, file)
                        if deps > 0:
                            build_systems['dependencies_count'] += deps
        
        return build_systems
    
    def _count_dependencies(self, file_path, filename):
        """Count dependencies in various package files"""
        try:
            if filename == 'package.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    deps = len(data.get('dependencies', {}))
                    dev_deps = len(data.get('devDependencies', {}))
                    return deps + dev_deps
            
            elif filename == 'requirements.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    return len(lines)
            
            elif filename == 'Gemfile':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return len(re.findall(r'^\s*gem\s+', content, re.MULTILINE))
            
        except Exception:
            pass
        
        return 0
    
    def _basic_security_scan(self, repo_path):
        """Perform basic security scanning with parallel processing"""
        security = {
            'potential_issues': [],
            'sensitive_files': [],
            'security_score': 10,
            'recommendations': []
        }
        
        # Patterns for potential security issues
        sensitive_patterns = {
            'hardcoded_secrets': [
                r'password\s*=\s*["\'][^"\'\']+["\']',
                r'api_key\s*=\s*["\'][^"\'\']+["\']',
                r'secret\s*=\s*["\'][^"\'\']+["\']'
            ],
            'sql_injection': [r'SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*\+'],
            'xss_vulnerable': [r'innerHTML\s*=\s*.*\+', r'document\.write\s*\(']
        }
        
        sensitive_files = ['.env', '.env.local', 'config.json', 'secrets.json', 
                          'private_key', 'id_rsa', '.aws/credentials']
        
        # Collect all files to scan
        files_to_scan = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    files_to_scan.append((file_path, file))
        
        # Thread-safe collections
        lock = threading.Lock()
        
        def scan_file(file_info):
            """Scan a single file for security issues"""
            file_path, filename = file_info
            result = {
                'sensitive_file': False,
                'issues': [],
                'score_penalty': 0
            }
            
            try:
                # Check for sensitive files
                if any(sensitive in filename.lower() for sensitive in sensitive_files):
                    result['sensitive_file'] = True
                    result['score_penalty'] += 1
                
                # Scan code files for patterns
                if filename.endswith(('.py', '.js', '.php', '.java', '.cpp', '.c')):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            for issue_type, patterns in sensitive_patterns.items():
                                for pattern in patterns:
                                    if re.search(pattern, content, re.IGNORECASE):
                                        result['issues'].append({
                                            'type': issue_type,
                                            'file': filename,
                                            'severity': 'Medium'
                                        })
                                        result['score_penalty'] += 0.5
                    except Exception:
                        pass
            except Exception:
                pass
            
            return result
        
        # Process files in parallel
        max_workers = min(16, (os.cpu_count() or 1) + 2)  # Fewer threads for I/O intensive security scan
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(scan_file, file_info): file_info 
                            for file_info in files_to_scan}
            
            for future in as_completed(future_to_file):
                result = future.result()
                
                with lock:
                    if result['sensitive_file']:
                        _, filename = future_to_file[future]
                        security['sensitive_files'].append(filename)
                    
                    security['potential_issues'].extend(result['issues'])
                    security['security_score'] -= result['score_penalty']
        
        security['security_score'] = max(0, min(10, security['security_score']))
        
        # Generate recommendations
        if security['sensitive_files']:
            security['recommendations'].append('Remove or secure sensitive files')
        if security['potential_issues']:
            security['recommendations'].append('Review code for security vulnerabilities')
        if security['security_score'] < 8:
            security['recommendations'].append('Consider implementing security best practices')
        
        return security
    
    def _analyze_repo_health(self, repo_info, owner, repo):
        """Analyze repository health indicators"""
        health = {
            'activity_score': 0,
            'maintenance_score': 0,
            'community_score': 0,
            'overall_health': 'Unknown',
            'last_commit': repo_info.get('pushed_at', 'Unknown'),
            'age_days': 0,
            'commit_frequency': 'Unknown'
        }
        
        try:
            # Calculate repository age
            created_date = datetime.fromisoformat(repo_info['created_at'].replace('Z', '+00:00'))
            age_days = (datetime.now().replace(tzinfo=created_date.tzinfo) - created_date).days
            health['age_days'] = age_days
            
            # Calculate activity score based on recent activity
            if repo_info.get('pushed_at'):
                last_push = datetime.fromisoformat(repo_info['pushed_at'].replace('Z', '+00:00'))
                days_since_push = (datetime.now().replace(tzinfo=last_push.tzinfo) - last_push).days
                
                if days_since_push < 7:
                    health['activity_score'] = 10
                elif days_since_push < 30:
                    health['activity_score'] = 8
                elif days_since_push < 90:
                    health['activity_score'] = 6
                elif days_since_push < 365:
                    health['activity_score'] = 4
                else:
                    health['activity_score'] = 2
            
            # Maintenance score based on various factors
            maintenance_score = 0
            if repo_info['stars'] > 10: maintenance_score += 2
            if repo_info['forks'] > 5: maintenance_score += 2
            if repo_info['issues'] < 20: maintenance_score += 2
            if not repo_info['archived']: maintenance_score += 2
            if not repo_info['disabled']: maintenance_score += 2
            
            health['maintenance_score'] = maintenance_score
            
            # Community score
            community_score = min(10, (repo_info['stars'] // 10) + (repo_info['forks'] // 5))
            health['community_score'] = community_score
            
            # Overall health calculation
            overall = (health['activity_score'] + health['maintenance_score'] + health['community_score']) / 3
            
            if overall >= 8:
                health['overall_health'] = 'Excellent'
            elif overall >= 6:
                health['overall_health'] = 'Good'
            elif overall >= 4:
                health['overall_health'] = 'Fair'
            else:
                health['overall_health'] = 'Poor'
                
        except Exception:
            pass
        
        return health
    
    def _generate_recommendations(self, analysis):
        """Generate recommendations based on analysis results"""
        recommendations = []
        
        # Structure recommendations
        structure = analysis['project_structure']
        if not structure['has_readme']:
            recommendations.append('Add a comprehensive README.md file')
        if not structure['has_license']:
            recommendations.append('Add a LICENSE file to clarify usage rights')
        if not structure['has_tests']:
            recommendations.append('Implement unit tests to improve code quality')
        if not structure['has_docs']:
            recommendations.append('Add documentation for better maintainability')
        
        # Code quality recommendations
        metrics = analysis['code_metrics']
        if metrics['complexity_score'] == 'High':
            recommendations.append('Consider refactoring to reduce code complexity')
        if metrics['comment_lines'] < metrics['code_lines'] * 0.1:
            recommendations.append('Add more code comments for better readability')
        
        # Security recommendations
        security = analysis['security']
        recommendations.extend(security['recommendations'])
        
        # Health recommendations
        health = analysis['health_indicators']
        if health['overall_health'] in ['Poor', 'Fair']:
            recommendations.append('Increase development activity and community engagement')
        
        return recommendations[:10]  # Limit to top 10 recommendations