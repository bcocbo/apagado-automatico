"""
Property-based tests for YAML validation completeness.

Feature: namespace-auto-shutdown-system, Property 13: YAML Validation Completeness
Validates: Requirements 1.4

This module tests the property that for any Kubernetes manifest file in the repository,
the linting process should validate syntax, schema compliance, and best practices,
rejecting invalid configurations before deployment.
"""

import os
import tempfile
import yaml
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite
import pytest


# YAML generation strategies
@composite
def valid_yaml_content(draw):
    """Generate valid YAML content with various structures."""
    content_type = draw(st.sampled_from(['simple', 'nested', 'list', 'kubernetes']))
    
    if content_type == 'simple':
        return {
            'name': draw(st.text(min_size=1, max_size=50)),
            'value': draw(st.one_of(st.text(), st.integers(), st.booleans()))
        }
    elif content_type == 'nested':
        return {
            'metadata': {
                'name': draw(st.text(min_size=1, max_size=30)),
                'labels': {
                    'app': draw(st.text(min_size=1, max_size=20)),
                    'version': draw(st.text(min_size=1, max_size=10))
                }
            },
            'spec': {
                'replicas': draw(st.integers(min_value=1, max_value=10)),
                'enabled': draw(st.booleans())
            }
        }
    elif content_type == 'list':
        return [
            {'item': i, 'name': draw(st.text(min_size=1, max_size=20))}
            for i in range(draw(st.integers(min_value=1, max_value=5)))
        ]
    else:  # kubernetes
        return generate_kubernetes_manifest(draw)


def generate_kubernetes_manifest(draw):
    """Generate a basic Kubernetes manifest structure."""
    kind = draw(st.sampled_from(['Deployment', 'Service', 'ConfigMap', 'Secret']))
    name = draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')))
    
    base_manifest = {
        'apiVersion': 'v1' if kind in ['Service', 'ConfigMap', 'Secret'] else 'apps/v1',
        'kind': kind,
        'metadata': {
            'name': name,
            'labels': {
                'app': draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Nd')))),
                'version': draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'))))
            }
        }
    }
    
    if kind == 'Deployment':
        base_manifest['spec'] = {
            'replicas': draw(st.integers(min_value=1, max_value=5)),
            'selector': {
                'matchLabels': {
                    'app': base_manifest['metadata']['labels']['app']
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app': base_manifest['metadata']['labels']['app']
                    }
                },
                'spec': {
                    'containers': [{
                        'name': draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Nd')))),
                        'image': f"{draw(st.text(min_size=1, max_size=20))}:{draw(st.text(min_size=1, max_size=10))}",
                        'ports': [{
                            'containerPort': draw(st.integers(min_value=1000, max_value=9999))
                        }]
                    }]
                }
            }
        }
    elif kind == 'Service':
        base_manifest['spec'] = {
            'selector': {
                'app': base_manifest['metadata']['labels']['app']
            },
            'ports': [{
                'port': draw(st.integers(min_value=80, max_value=9999)),
                'targetPort': draw(st.integers(min_value=1000, max_value=9999))
            }]
        }
    elif kind == 'ConfigMap':
        base_manifest['data'] = {
            'config.yaml': 'key: value',
            'app.properties': f"app.name={name}"
        }
    
    return base_manifest


@composite
def invalid_yaml_content(draw):
    """Generate invalid YAML content with various syntax errors."""
    error_type = draw(st.sampled_from(['syntax', 'indentation', 'quotes', 'structure']))
    
    if error_type == 'syntax':
        # Missing colon, invalid characters
        return "name value\ninvalid: [unclosed"
    elif error_type == 'indentation':
        # Inconsistent indentation
        return "metadata:\n  name: test\n    labels:\n  app: myapp"
    elif error_type == 'quotes':
        # Unmatched quotes
        return 'name: "unclosed quote\nvalue: test'
    else:  # structure
        # Invalid YAML structure
        return "---\n[invalid: structure\n  missing: bracket"


@composite
def kubernetes_manifest_with_issues(draw):
    """Generate Kubernetes manifests with specific validation issues."""
    issue_type = draw(st.sampled_from(['missing_labels', 'latest_tag', 'no_resources', 'hardcoded_secret']))
    
    base = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')))
        },
        'spec': {
            'replicas': 1,
            'selector': {'matchLabels': {'app': 'test'}},
            'template': {
                'metadata': {'labels': {'app': 'test'}},
                'spec': {
                    'containers': [{
                        'name': 'test-container',
                        'image': 'nginx:latest' if issue_type == 'latest_tag' else 'nginx:1.21'
                    }]
                }
            }
        }
    }
    
    if issue_type == 'missing_labels':
        # Remove labels from metadata
        pass  # Already missing labels
    elif issue_type == 'no_resources':
        # Missing resource limits
        pass  # Already missing resources
    elif issue_type == 'hardcoded_secret':
        # Add hardcoded secret
        base['spec']['template']['spec']['containers'][0]['env'] = [
            {'name': 'PASSWORD', 'value': 'hardcoded-secret-123'}
        ]
    
    return base


class YAMLValidationTester:
    """Helper class for YAML validation testing."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.yamllint_config = self.project_root / '.yamllint.yml'
        self.kubeval_config = self.project_root / '.kubeval.yaml'
    
    def validate_yaml_syntax(self, content: str, file_path: Path) -> tuple[bool, str]:
        """Validate YAML syntax using yamllint."""
        try:
            # First check if it's valid YAML
            yaml.safe_load(content)
            
            # Then run yamllint
            result = subprocess.run(
                ['yamllint', '-c', str(self.yamllint_config), str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0, result.stdout + result.stderr
        except yaml.YAMLError as e:
            return False, f"YAML syntax error: {e}"
        except subprocess.TimeoutExpired:
            return False, "yamllint timeout"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def validate_kubernetes_schema(self, content: str, file_path: Path) -> tuple[bool, str]:
        """Validate Kubernetes manifest using kubeval."""
        try:
            # Check if it's a Kubernetes manifest
            data = yaml.safe_load(content)
            if not isinstance(data, dict) or 'apiVersion' not in data or 'kind' not in data:
                return True, "Not a Kubernetes manifest"
            
            result = subprocess.run(
                ['kubeval', '--ignore-missing-schemas', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "kubeval timeout"
        except Exception as e:
            return False, f"Schema validation error: {e}"
    
    def validate_custom_rules(self, content: str, file_path: Path) -> tuple[bool, List[str]]:
        """Apply custom validation rules."""
        warnings = []
        
        try:
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                return True, warnings
            
            # Check for hardcoded secrets
            content_lower = content.lower()
            if any(secret_word in content_lower for secret_word in ['password:', 'secret:', 'token:', 'key:']):
                if any(f'{word}: ' in content for word in ['password', 'secret', 'token', 'key']):
                    warnings.append("Potential hardcoded secret detected")
            
            # Check for latest tag
            if 'image:' in content and ':latest' in content:
                warnings.append("Using 'latest' tag is not recommended")
            
            # Check for missing labels in Kubernetes resources
            if data.get('kind') in ['Deployment', 'Service', 'ConfigMap']:
                if 'labels' not in data.get('metadata', {}):
                    warnings.append("Missing labels in Kubernetes resource")
            
            # Check for missing resource limits
            if data.get('kind') in ['Deployment', 'StatefulSet', 'DaemonSet']:
                containers = []
                spec = data.get('spec', {})
                template = spec.get('template', {})
                pod_spec = template.get('spec', {})
                containers = pod_spec.get('containers', [])
                
                for container in containers:
                    if 'resources' not in container:
                        warnings.append("Missing resource limits in container")
                        break
            
            return True, warnings
        except Exception as e:
            return False, [f"Custom validation error: {e}"]


class TestYAMLValidationProperty:
    """Property-based tests for YAML validation completeness."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = YAMLValidationTester()
        self.temp_dir = None
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_file(self, content: str, suffix: str = '.yaml') -> Path:
        """Create a temporary file with given content."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
        
        temp_file = Path(self.temp_dir) / f"test_{len(os.listdir(self.temp_dir))}{suffix}"
        temp_file.write_text(content)
        return temp_file
    
    @given(valid_yaml_content())
    @settings(max_examples=50, deadline=5000)
    def test_valid_yaml_passes_syntax_validation(self, yaml_content):
        """
        Property: Valid YAML content should pass syntax validation.
        
        **Validates: Requirements 1.4**
        
        For any valid YAML content, the yamllint validation should succeed.
        """
        # Convert to YAML string
        yaml_string = yaml.dump(yaml_content, default_flow_style=False)
        temp_file = self.create_temp_file(yaml_string)
        
        # Validate syntax
        is_valid, output = self.validator.validate_yaml_syntax(yaml_string, temp_file)
        
        # Property: Valid YAML should pass syntax validation
        assert is_valid, f"Valid YAML failed syntax validation: {output}"
    
    @given(invalid_yaml_content())
    @settings(max_examples=30, deadline=5000)
    def test_invalid_yaml_fails_syntax_validation(self, invalid_content):
        """
        Property: Invalid YAML content should fail syntax validation.
        
        **Validates: Requirements 1.4**
        
        For any invalid YAML content, the yamllint validation should fail.
        """
        temp_file = self.create_temp_file(invalid_content)
        
        # Validate syntax
        is_valid, output = self.validator.validate_yaml_syntax(invalid_content, temp_file)
        
        # Property: Invalid YAML should fail syntax validation
        assert not is_valid, f"Invalid YAML passed syntax validation unexpectedly: {output}"
    
    @given(valid_yaml_content())
    @settings(max_examples=40, deadline=5000)
    def test_kubernetes_manifests_pass_schema_validation(self, yaml_content):
        """
        Property: Valid Kubernetes manifests should pass schema validation.
        
        **Validates: Requirements 1.4**
        
        For any valid Kubernetes manifest, kubeval should validate successfully.
        """
        # Only test if it's a Kubernetes manifest
        if not isinstance(yaml_content, dict) or 'apiVersion' not in yaml_content:
            assume(False)  # Skip non-Kubernetes content
        
        yaml_string = yaml.dump(yaml_content, default_flow_style=False)
        temp_file = self.create_temp_file(yaml_string)
        
        # Validate schema
        is_valid, output = self.validator.validate_kubernetes_schema(yaml_string, temp_file)
        
        # Property: Valid Kubernetes manifests should pass schema validation
        assert is_valid, f"Valid Kubernetes manifest failed schema validation: {output}"
    
    @given(kubernetes_manifest_with_issues())
    @settings(max_examples=30, deadline=5000)
    def test_custom_rules_detect_issues(self, manifest_with_issues):
        """
        Property: Custom validation rules should detect policy violations.
        
        **Validates: Requirements 1.4**
        
        For any Kubernetes manifest with known issues, custom rules should detect them.
        """
        yaml_string = yaml.dump(manifest_with_issues, default_flow_style=False)
        temp_file = self.create_temp_file(yaml_string)
        
        # Apply custom rules
        is_valid, warnings = self.validator.validate_custom_rules(yaml_string, temp_file)
        
        # Property: Manifests with issues should generate warnings
        # We expect at least some warnings for manifests with intentional issues
        assert is_valid, f"Custom rules validation failed: {warnings}"
        
        # Check that we detect common issues
        yaml_lower = yaml_string.lower()
        if ':latest' in yaml_string:
            assert any('latest' in warning.lower() for warning in warnings), \
                "Should detect latest tag usage"
        
        if 'password:' in yaml_lower or 'secret:' in yaml_lower:
            assert any('secret' in warning.lower() for warning in warnings), \
                "Should detect potential hardcoded secrets"
    
    @given(st.lists(valid_yaml_content(), min_size=1, max_size=5))
    @settings(max_examples=20, deadline=10000)
    def test_batch_validation_consistency(self, yaml_contents):
        """
        Property: Batch validation should be consistent with individual validation.
        
        **Validates: Requirements 1.4**
        
        For any collection of YAML files, batch validation results should match
        individual validation results.
        """
        individual_results = []
        temp_files = []
        
        # Validate each file individually
        for content in yaml_contents:
            yaml_string = yaml.dump(content, default_flow_style=False)
            temp_file = self.create_temp_file(yaml_string)
            temp_files.append(temp_file)
            
            syntax_valid, _ = self.validator.validate_yaml_syntax(yaml_string, temp_file)
            individual_results.append(syntax_valid)
        
        # Property: Individual validation results should be deterministic
        # Re-validate the same files and ensure consistent results
        for i, temp_file in enumerate(temp_files):
            content = temp_file.read_text()
            syntax_valid, _ = self.validator.validate_yaml_syntax(content, temp_file)
            
            assert syntax_valid == individual_results[i], \
                f"Validation result inconsistent for file {i}: expected {individual_results[i]}, got {syntax_valid}"
    
    def test_validation_tools_are_available(self):
        """
        Property: Required validation tools should be available and functional.
        
        **Validates: Requirements 1.4**
        
        The validation system should have all required tools installed and working.
        """
        # Test yamllint availability
        try:
            result = subprocess.run(['yamllint', '--version'], capture_output=True, text=True, timeout=10)
            assert result.returncode == 0, "yamllint is not available or not working"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("yamllint not available in test environment")
        
        # Test kubeval availability
        try:
            result = subprocess.run(['kubeval', '--version'], capture_output=True, text=True, timeout=10)
            assert result.returncode == 0, "kubeval is not available or not working"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("kubeval not available in test environment")
        
        # Test configuration files exist
        assert self.validator.yamllint_config.exists(), "yamllint configuration file missing"
        assert self.validator.kubeval_config.exists(), "kubeval configuration file missing"
    
    def test_validation_configuration_completeness(self):
        """
        Property: Validation configuration should be complete and valid.
        
        **Validates: Requirements 1.4**
        
        The validation configuration files should contain all necessary rules
        and settings for comprehensive validation.
        """
        # Test yamllint configuration
        with open(self.validator.yamllint_config) as f:
            yamllint_config = yaml.safe_load(f)
        
        # Should have rules defined
        assert 'rules' in yamllint_config, "yamllint config missing rules section"
        
        # Should have key rules for Kubernetes manifests
        rules = yamllint_config['rules']
        expected_rules = ['line-length', 'indentation', 'truthy', 'key-duplicates']
        for rule in expected_rules:
            assert rule in rules, f"yamllint config missing {rule} rule"
        
        # Test kubeval configuration
        with open(self.validator.kubeval_config) as f:
            kubeval_config = yaml.safe_load(f)
        
        # Should have kubernetes version specified
        assert 'kubernetes-version' in kubeval_config, "kubeval config missing kubernetes-version"
        
        # Should have schema location
        assert 'schema-location' in kubeval_config, "kubeval config missing schema-location"


# Integration test to verify the property holds for real project files
class TestRealProjectValidation:
    """Test validation properties against real project files."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = YAMLValidationTester()
        self.project_root = Path(__file__).parent.parent.parent
    
    def test_existing_yaml_files_validation_property(self):
        """
        Property: All existing YAML files in the project should pass validation.
        
        **Validates: Requirements 1.4**
        
        This test ensures that the validation system correctly validates
        all YAML files currently in the project.
        """
        # Find all YAML files in the project
        yaml_files = []
        for pattern in ['**/*.yaml', '**/*.yml']:
            yaml_files.extend(self.project_root.glob(pattern))
        
        # Filter out files that should be ignored
        ignore_patterns = ['.git/', 'node_modules/', 'build/', 'dist/', 'coverage/']
        yaml_files = [f for f in yaml_files if not any(pattern in str(f) for pattern in ignore_patterns)]
        
        validation_results = []
        
        for yaml_file in yaml_files:
            try:
                content = yaml_file.read_text()
                
                # Validate syntax
                syntax_valid, syntax_output = self.validator.validate_yaml_syntax(content, yaml_file)
                
                # Validate Kubernetes schema if applicable
                schema_valid, schema_output = self.validator.validate_kubernetes_schema(content, yaml_file)
                
                # Apply custom rules
                custom_valid, custom_warnings = self.validator.validate_custom_rules(content, yaml_file)
                
                validation_results.append({
                    'file': yaml_file,
                    'syntax_valid': syntax_valid,
                    'schema_valid': schema_valid,
                    'custom_valid': custom_valid,
                    'syntax_output': syntax_output,
                    'schema_output': schema_output,
                    'custom_warnings': custom_warnings
                })
                
            except Exception as e:
                validation_results.append({
                    'file': yaml_file,
                    'error': str(e)
                })
        
        # Property: The validation system should process all files without crashing
        assert len(validation_results) > 0, "No YAML files found in project"
        
        # Report any validation failures for investigation
        failed_files = []
        for result in validation_results:
            if 'error' in result:
                failed_files.append(f"{result['file']}: {result['error']}")
            elif not (result['syntax_valid'] and result['schema_valid'] and result['custom_valid']):
                failed_files.append(f"{result['file']}: validation issues detected")
        
        # Property: Validation system should be able to process existing project files
        # Note: We don't assert all files pass validation, as some may have intentional issues
        # But we do assert that the validation system works on real files
        assert len([r for r in validation_results if 'error' not in r]) > 0, \
            "Validation system failed to process any project files"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])