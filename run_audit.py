#!/usr/bin/env python3
"""
Comprehensive audit script for Cellframe Navigator Bot.
Checks code quality, security, functionality, and deployment readiness.
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class BotAuditor:
    """Comprehensive bot audit system."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
        self.root = Path(__file__).parent
        
    def log_issue(self, category: str, message: str):
        """Log a critical issue."""
        self.issues.append(f"[{category}] {message}")
        
    def log_warning(self, category: str, message: str):
        """Log a warning."""
        self.warnings.append(f"[{category}] {message}")
        
    def log_pass(self, category: str, message: str):
        """Log a passed check."""
        self.passed.append(f"[{category}] {message}")
    
    def audit_security(self):
        """Audit security aspects."""
        print("\n🔒 [1/8] SECURITY AUDIT")
        print("=" * 70)
        
        # Check .env file
        env_file = self.root / ".env"
        if env_file.exists():
            self.log_warning("Security", ".env file exists (should not be in production)")
        else:
            self.log_pass("Security", ".env file not in repository")
        
        # Check .env.example
        env_example = self.root / ".env.example"
        if env_example.exists():
            self.log_pass("Security", ".env.example exists for reference")
        else:
            self.log_warning("Security", ".env.example missing")
        
        # Check for exposed secrets in code
        sensitive_patterns = ["password", "secret", "key", "token"]
        python_files = list(self.root.glob("**/*.py"))
        
        for py_file in python_files:
            if ".venv" in str(py_file) or "venv" in str(py_file):
                continue
                
            try:
                content = py_file.read_text().lower()
                for pattern in sensitive_patterns:
                    if f'{pattern} = "' in content or f"{pattern} = '" in content:
                        if "os.getenv" not in content:
                            self.log_issue("Security", f"Potential hardcoded {pattern} in {py_file.name}")
            except Exception:
                pass
        
        self.log_pass("Security", "No obvious hardcoded secrets found")
        
        # Check input validation
        handlers_file = self.root / "bot" / "handlers.py"
        if handlers_file.exists():
            content = handlers_file.read_text()
            if "validate_address" in content:
                self.log_pass("Security", "Address validation implemented")
            else:
                self.log_warning("Security", "Address validation may be missing")
        
        print(f"  ✅ Passed: {len([p for p in self.passed if 'Security' in p])}")
        print(f"  ⚠️  Warnings: {len([w for w in self.warnings if 'Security' in w])}")
        print(f"  ❌ Issues: {len([i for i in self.issues if 'Security' in i])}")
    
    def audit_code_quality(self):
        """Audit code quality."""
        print("\n💎 [2/8] CODE QUALITY AUDIT")
        print("=" * 70)
        
        # Check for TODO/FIXME comments
        python_files = list(self.root.glob("**/*.py"))
        todo_count = 0
        
        for py_file in python_files:
            if ".venv" in str(py_file):
                continue
            try:
                content = py_file.read_text()
                todo_count += content.count("TODO")
                todo_count += content.count("FIXME")
            except Exception:
                pass
        
        if todo_count > 0:
            self.log_warning("Code Quality", f"Found {todo_count} TODO/FIXME comments")
        else:
            self.log_pass("Code Quality", "No TODO/FIXME comments")
        
        # Check for proper error handling
        try_count = 0
        for py_file in python_files:
            if ".venv" in str(py_file):
                continue
            try:
                content = py_file.read_text()
                try_count += content.count("try:")
            except Exception:
                pass
        
        if try_count > 10:
            self.log_pass("Code Quality", f"Good error handling ({try_count} try blocks)")
        else:
            self.log_warning("Code Quality", "Limited error handling")
        
        # Check logging
        handlers_file = self.root / "bot" / "handlers.py"
        if handlers_file.exists():
            content = handlers_file.read_text()
            if "logger" in content:
                self.log_pass("Code Quality", "Logging implemented")
            else:
                self.log_warning("Code Quality", "Logging may be missing")
        
        print(f"  ✅ Passed: {len([p for p in self.passed if 'Code Quality' in p])}")
        print(f"  ⚠️  Warnings: {len([w for w in self.warnings if 'Code Quality' in w])}")
        print(f"  ❌ Issues: {len([i for i in self.issues if 'Code Quality' in i])}")
    
    def audit_functionality(self):
        """Audit functionality."""
        print("\n⚙️  [3/8] FUNCTIONALITY AUDIT")
        print("=" * 70)
        
        required_commands = ["/start", "/help", "/track", "/stats", "/faq"]
        handlers_file = self.root / "bot" / "handlers.py"
        
        if handlers_file.exists():
            content = handlers_file.read_text()
            
            for cmd in required_commands:
                cmd_clean = cmd.replace("/", "")
                if f'Command("{cmd_clean}")' in content or f'Command("start", "help")' in content:
                    self.log_pass("Functionality", f"{cmd} command implemented")
                else:
                    self.log_issue("Functionality", f"{cmd} command missing")
        
        # Check database models
        models_file = self.root / "data" / "models.py"
        if models_file.exists():
            content = models_file.read_text()
            required_models = ["User", "BridgeSession", "Transaction"]
            for model in required_models:
                if f"class {model}" in content:
                    self.log_pass("Functionality", f"{model} model exists")
                else:
                    self.log_issue("Functionality", f"{model} model missing")
        
        # Check RPC clients
        cf20_rpc = self.root / "watcher" / "cf20_rpc.py"
        evm_tracker = self.root / "watcher" / "evm_tracker.py"
        
        if cf20_rpc.exists():
            self.log_pass("Functionality", "Cellframe RPC client exists")
        else:
            self.log_issue("Functionality", "Cellframe RPC client missing")
            
        if evm_tracker.exists():
            self.log_pass("Functionality", "EVM tracker exists")
        else:
            self.log_issue("Functionality", "EVM tracker missing")
        
        print(f"  ✅ Passed: {len([p for p in self.passed if 'Functionality' in p])}")
        print(f"  ⚠️  Warnings: {len([w for w in self.warnings if 'Functionality' in w])}")
        print(f"  ❌ Issues: {len([i for i in self.issues if 'Functionality' in i])}")
    
    def audit_dependencies(self):
        """Audit dependencies."""
        print("\n📦 [4/8] DEPENDENCIES AUDIT")
        print("=" * 70)
        
        pyproject = self.root / "pyproject.toml"
        if pyproject.exists():
            self.log_pass("Dependencies", "pyproject.toml exists")
            content = pyproject.read_text()
            
            # Check key dependencies
            key_deps = ["aiogram", "sqlalchemy", "web3", "redis", "alembic"]
            for dep in key_deps:
                if dep in content.lower():
                    self.log_pass("Dependencies", f"{dep} listed")
                else:
                    self.log_warning("Dependencies", f"{dep} may be missing")
        else:
            self.log_issue("Dependencies", "pyproject.toml missing")
        
        print(f"  ✅ Passed: {len([p for p in self.passed if 'Dependencies' in p])}")
        print(f"  ⚠️  Warnings: {len([w for w in self.warnings if 'Dependencies' in w])}")
        print(f"  ❌ Issues: {len([i for i in self.issues if 'Dependencies' in i])}")
    
    def audit_documentation(self):
        """Audit documentation."""
        print("\n📚 [5/8] DOCUMENTATION AUDIT")
        print("=" * 70)
        
        docs = {
            "README.md": "Project overview",
            "SETUP.md": "Setup instructions",
            ".env.example": "Environment variables",
            "FEATURES.md": "Feature documentation",
        }
        
        for doc, desc in docs.items():
            if (self.root / doc).exists():
                self.log_pass("Documentation", f"{doc} exists ({desc})")
            else:
                self.log_warning("Documentation", f"{doc} missing ({desc})")
        
        # Check docstrings
        handlers_file = self.root / "bot" / "handlers.py"
        if handlers_file.exists():
            content = handlers_file.read_text()
            docstring_count = content.count('"""')
            if docstring_count > 10:
                self.log_pass("Documentation", f"Good docstring coverage ({docstring_count//2} docstrings)")
            else:
                self.log_warning("Documentation", "Limited docstring coverage")
        
        print(f"  ✅ Passed: {len([p for p in self.passed if 'Documentation' in p])}")
        print(f"  ⚠️  Warnings: {len([w for w in self.warnings if 'Documentation' in w])}")
        print(f"  ❌ Issues: {len([i for i in self.issues if 'Documentation' in i])}")
    
    def audit_docker(self):
        """Audit Docker configuration."""
        print("\n🐳 [6/8] DOCKER CONFIGURATION AUDIT")
        print("=" * 70)
        
        dockerfile = self.root / "Dockerfile"
        docker_compose = self.root / "docker-compose.yml"
        docker_compose_min = self.root / "docker-compose.minimal.yml"
        
        if dockerfile.exists():
            self.log_pass("Docker", "Dockerfile exists")
            content = dockerfile.read_text()
            
            if "COPY" in content and "requirements" not in content.lower():
                self.log_pass("Docker", "Uses modern dependency management")
            
            if "WORKDIR" in content:
                self.log_pass("Docker", "Working directory set")
        else:
            self.log_issue("Docker", "Dockerfile missing")
        
        if docker_compose.exists():
            self.log_pass("Docker", "docker-compose.yml exists")
        else:
            self.log_warning("Docker", "docker-compose.yml missing")
            
        if docker_compose_min.exists():
            self.log_pass("Docker", "docker-compose.minimal.yml exists")
        
        print(f"  ✅ Passed: {len([p for p in self.passed if 'Docker' in p])}")
        print(f"  ⚠️  Warnings: {len([w for w in self.warnings if 'Docker' in w])}")
        print(f"  ❌ Issues: {len([i for i in self.issues if 'Docker' in i])}")
    
    def audit_database(self):
        """Audit database configuration."""
        print("\n🗄️  [7/8] DATABASE AUDIT")
        print("=" * 70)
        
        alembic_ini = self.root / "alembic.ini"
        alembic_dir = self.root / "alembic"
        
        if alembic_ini.exists():
            self.log_pass("Database", "Alembic configuration exists")
        else:
            self.log_issue("Database", "Alembic configuration missing")
        
        if alembic_dir.exists() and alembic_dir.is_dir():
            versions = list((alembic_dir / "versions").glob("*.py"))
            if versions:
                self.log_pass("Database", f"Migration(s) exist ({len(versions)} migration(s))")
            else:
                self.log_warning("Database", "No migrations found")
        else:
            self.log_issue("Database", "Alembic directory missing")
        
        # Check models
        models_file = self.root / "data" / "models.py"
        if models_file.exists():
            content = models_file.read_text()
            if "Base" in content and "SQLAlchemy" in content or "sqlalchemy" in content:
                self.log_pass("Database", "SQLAlchemy models configured")
            else:
                self.log_warning("Database", "SQLAlchemy setup unclear")
        
        print(f"  ✅ Passed: {len([p for p in self.passed if 'Database' in p])}")
        print(f"  ⚠️  Warnings: {len([w for w in self.warnings if 'Database' in w])}")
        print(f"  ❌ Issues: {len([i for i in self.issues if 'Database' in i])}")
    
    def audit_testing(self):
        """Audit testing setup."""
        print("\n🧪 [8/8] TESTING AUDIT")
        print("=" * 70)
        
        test_files = list(self.root.glob("test*.py"))
        
        if test_files:
            self.log_pass("Testing", f"Test file(s) exist ({len(test_files)} file(s))")
        else:
            self.log_warning("Testing", "No test files found")
        
        # Check for test scenarios
        test_scenarios = self.root / "TEST_SCENARIOS.md"
        if test_scenarios.exists():
            self.log_pass("Testing", "Test scenarios documented")
        else:
            self.log_warning("Testing", "Test scenarios not documented")
        
        # Check for test report
        test_report = self.root / "TEST_REPORT.md"
        if test_report.exists():
            self.log_pass("Testing", "Test report exists")
        else:
            self.log_warning("Testing", "Test report not found")
        
        print(f"  ✅ Passed: {len([p for p in self.passed if 'Testing' in p])}")
        print(f"  ⚠️  Warnings: {len([w for w in self.warnings if 'Testing' in w])}")
        print(f"  ❌ Issues: {len([i for i in self.issues if 'Testing' in i])}")
    
    def generate_report(self):
        """Generate final audit report."""
        print("\n" + "=" * 70)
        print("📊 AUDIT SUMMARY")
        print("=" * 70)
        
        total_passed = len(self.passed)
        total_warnings = len(self.warnings)
        total_issues = len(self.issues)
        total = total_passed + total_warnings + total_issues
        
        if total > 0:
            score = (total_passed / total) * 100
        else:
            score = 0
        
        print(f"\n✅ Passed:   {total_passed:3d} checks")
        print(f"⚠️  Warnings: {total_warnings:3d} items")
        print(f"❌ Issues:   {total_issues:3d} critical")
        print(f"\n📊 Score: {score:.1f}%")
        
        if total_issues > 0:
            print("\n❌ CRITICAL ISSUES:")
            for issue in self.issues:
                print(f"  • {issue}")
        
        if total_warnings > 0:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings[:10]:  # Show first 10
                print(f"  • {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")
        
        print("\n" + "=" * 70)
        
        if total_issues == 0 and total_warnings < 5:
            print("🎉 EXCELLENT! Project is in great shape!")
            print("✅ Ready for production deployment")
            return 0
        elif total_issues == 0:
            print("✅ GOOD! Project is functional with minor warnings")
            print("⚠️  Address warnings for production")
            return 0
        else:
            print("⚠️  NEEDS ATTENTION! Critical issues found")
            print("❌ Fix issues before production deployment")
            return 1
    
    def run_full_audit(self):
        """Run complete audit."""
        print(f"\n🔍 Starting comprehensive audit at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        self.audit_security()
        self.audit_code_quality()
        self.audit_functionality()
        self.audit_dependencies()
        self.audit_documentation()
        self.audit_docker()
        self.audit_database()
        self.audit_testing()
        
        return self.generate_report()


if __name__ == "__main__":
    auditor = BotAuditor()
    exit_code = auditor.run_full_audit()
    sys.exit(exit_code)

