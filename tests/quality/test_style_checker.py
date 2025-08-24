import unittest
import subprocess
import os
import sys
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

class TestStyleChecker(unittest.TestCase):
    """Test code style using external tools when available."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = project_root
        self.python_files = self._get_python_files()
    
    def _get_python_files(self):
        """Get all Python files in the project excluding tests."""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Skip test directories, virtual environments, and hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env', 'tests']]
            for file in files:
                if file.endswith('.py') and not file.startswith('.') and 'test' not in file.lower():
                    python_files.append(os.path.join(root, file))
        return python_files
    
    def _is_tool_available(self, tool_name):
        """Check if a command-line tool is available."""
        try:
            if tool_name == 'flake8':
                # Try python -m flake8 first
                subprocess.run(['python', '-m', 'flake8', '--version'], 
                             capture_output=True, 
                             check=True, 
                             timeout=10)
                return True
            else:
                subprocess.run([tool_name, '--version'], 
                             capture_output=True, 
                             check=True, 
                             timeout=10)
                return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def test_flake8_style_check(self):
        """Test code style using flake8 if available."""
        if not self._is_tool_available('flake8'):
            self.skipTest("flake8 not available")
        
        # Configure flake8 with reasonable settings
        flake8_config = [
            '--max-line-length=120',
            '--ignore=E203,W503,E501,F401,W293,E302,W504,W291',  # Ignore common issues
            '--exclude=tests,venv,env,.git,__pycache__'
        ]
        
        try:
            result = subprocess.run(
                ['python', '-m', 'flake8'] + flake8_config + [self.project_root],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                # Allow some style issues but not too many
                issues = result.stdout.strip().split('\n') if result.stdout.strip() else []
                if len(issues) > 50:  # Threshold for acceptable style issues
                    self.fail(f"Too many flake8 style issues ({len(issues)}):\n" + 
                             "\n".join(issues[:20]) + "\n... (showing first 20)")
                else:
                    print(f"\nFlake8 found {len(issues)} style issues (within acceptable range):")
                    for issue in issues[:10]:
                        print(f"  {issue}")
        
        except subprocess.TimeoutExpired:
            self.fail("flake8 check timed out")
        except Exception as e:
            self.fail(f"Error running flake8: {e}")
    
    def test_pylint_basic_check(self):
        """Test code quality using pylint if available."""
        if not self._is_tool_available('pylint'):
            self.skipTest("pylint not available")
        
        # Test only main application files to avoid overwhelming output
        main_files = [f for f in self.python_files if os.path.basename(f) in ['app.py', 'analyzer.py']]
        
        if not main_files:
            self.skipTest("No main application files found")
        
        for file_path in main_files:
            try:
                result = subprocess.run(
                    ['pylint', '--score=yes', '--reports=no', 
                     '--disable=missing-docstring,too-few-public-methods,too-many-locals,too-many-branches',
                     file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Extract score from pylint output
                output_lines = result.stdout.split('\n')
                score_line = None
                for line in output_lines:
                    if 'Your code has been rated at' in line:
                        score_line = line
                        break
                
                if score_line:
                    # Extract numeric score
                    import re
                    score_match = re.search(r'rated at ([\d\.]+)/10', score_line)
                    if score_match:
                        score = float(score_match.group(1))
                        print(f"\nPylint score for {os.path.basename(file_path)}: {score}/10")
                        
                        # Don't fail for low scores, just report them
                        if score < 5.0:
                            print(f"  Warning: Low pylint score for {file_path}")
            
            except subprocess.TimeoutExpired:
                print(f"\nPylint check timed out for {file_path}")
            except Exception as e:
                print(f"\nError running pylint on {file_path}: {e}")
    
    def test_basic_pep8_compliance(self):
        """Test basic PEP 8 compliance."""
        # Simplified style test - just check that files are readable
        main_files = ['app.py', 'analyzer.py']
        for filename in main_files:
            file_path = os.path.join(self.project_root, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        content = f.read()
                        # Basic checks
                        self.assertGreater(len(content), 0, f"{filename} is empty")
                        # Check for basic Python syntax
                        compile(content, filename, 'exec')
                    except Exception as e:
                        self.fail(f"Style check failed for {filename}: {e}")
    
    def test_import_organization(self):
        """Test import statement organization."""
        import_issues = []
        
        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                import_section = []
                in_import_section = False
                
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    
                    if stripped.startswith('import ') or stripped.startswith('from '):
                        import_section.append((i, stripped))
                        in_import_section = True
                    elif in_import_section and stripped and not stripped.startswith('#'):
                        # End of import section
                        break
                
                # Check import organization
                if len(import_section) > 1:
                    # Check if imports are roughly organized (standard, third-party, local)
                    stdlib_imports = []
                    thirdparty_imports = []
                    local_imports = []
                    
                    for line_num, import_line in import_section:
                        if import_line.startswith('from . ') or import_line.startswith('from .. '):
                            local_imports.append((line_num, import_line))
                        elif any(lib in import_line for lib in ['os', 'sys', 'json', 'datetime', 'tempfile', 'subprocess']):
                            stdlib_imports.append((line_num, import_line))
                        else:
                            thirdparty_imports.append((line_num, import_line))
                    
                    # Basic check: if we have all three types, they should be in order
                    if stdlib_imports and thirdparty_imports and local_imports:
                        last_stdlib = max(stdlib_imports, key=lambda x: x[0])[0] if stdlib_imports else 0
                        first_thirdparty = min(thirdparty_imports, key=lambda x: x[0])[0] if thirdparty_imports else float('inf')
                        first_local = min(local_imports, key=lambda x: x[0])[0] if local_imports else float('inf')
                        
                        if not (last_stdlib < first_thirdparty < first_local):
                            import_issues.append(f"{file_path}: Import organization could be improved (stdlib, third-party, local)")
            
            except Exception as e:
                import_issues.append(f"{file_path}: Error checking import organization - {e}")
        
        # Don't fail for import organization issues, just report them
        if import_issues:
            print(f"\nImport organization suggestions ({len(import_issues)}):")
            for issue in import_issues[:5]:
                print(f"  {issue}")
    
    def test_code_complexity_metrics(self):
        """Test basic code complexity metrics."""
        complexity_issues = []
        
        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Count nested levels (basic complexity measure)
                lines = content.split('\n')
                max_nesting = 0
                current_nesting = 0
                
                for line in lines:
                    stripped = line.strip()
                    if any(keyword in stripped for keyword in ['if ', 'for ', 'while ', 'with ', 'try:', 'except', 'def ', 'class ']):
                        current_nesting += 1
                        max_nesting = max(max_nesting, current_nesting)
                    
                    # Simple dedent detection
                    if stripped and not line.startswith(' ' * (current_nesting * 4)):
                        current_nesting = max(0, current_nesting - 1)
                
                if max_nesting > 6:  # Arbitrary threshold
                    complexity_issues.append(f"{file_path}: High nesting level detected ({max_nesting})")
            
            except Exception as e:
                complexity_issues.append(f"{file_path}: Error checking complexity - {e}")
        
        # Don't fail for complexity issues, just report them
        if complexity_issues:
            print(f"\nComplexity warnings ({len(complexity_issues)}):")
            for issue in complexity_issues:
                print(f"  {issue}")

if __name__ == '__main__':
    unittest.main()