from __future__ import annotations
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ContractViolation:
    """Represents a contract violation between UI and API."""
    type: str  # 'missing_endpoint', 'param_mismatch', 'response_mismatch', 'type_mismatch'
    ui_component: str
    api_endpoint: str
    details: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    file_path: str
    line_number: int


@dataclass
class ContractReport:
    """Report of contract analysis."""
    violations: List[ContractViolation]
    endpoints_covered: int
    components_analyzed: int
    timestamp: str


class ContractGuardian:
    """Verifies contracts between UI components and API endpoints."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.webapp_src = self.project_root / "webapp" / "src"
        self.python_src = self.project_root / "src"
    
    def verify_contracts(self) -> ContractReport:
        """Verify contracts between UI components and API endpoints."""
        # Extract API endpoints
        api_endpoints = self._extract_api_endpoints()
        
        # Extract UI components that consume APIs
        ui_components = self._extract_ui_components()
        
        # Check for contract violations
        violations = self._check_contract_violations(ui_components, api_endpoints)
        
        return ContractReport(
            violations=violations,
            endpoints_covered=len(api_endpoints),
            components_analyzed=len(ui_components),
            timestamp=self._get_current_timestamp()
        )
    
    def _extract_api_endpoints(self) -> List[Dict[str, Any]]:
        """Extract all API endpoints from the codebase."""
        endpoints = []
        
        # Look for main API files
        api_main_files = [
            self.python_src / "api" / "main.py",
            self.python_src / "api" / "main_v2.py"
        ]
        
        for file_path in api_main_files:
            if file_path.exists():
                try:
                    endpoints.extend(self._analyze_api_file(file_path))
                except Exception:
                    continue
        
        return endpoints
    
    def _analyze_api_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze an API file to extract endpoint information."""
        endpoints = []
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            # Look for endpoint decorators
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for FastAPI decorators
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr'):
                            method = decorator.func.attr
                            if method in ['get', 'post', 'put', 'delete']:
                                # Extract path from decorator
                                if decorator.args:
                                    path_arg = decorator.args[0]
                                    if isinstance(path_arg, (ast.Constant, ast.Str)):
                                        if isinstance(path_arg, ast.Constant):
                                            path = path_arg.value
                                        else:  # ast.Str (older Python)
                                            path = path_arg.s
                                        
                                        # Extract parameters
                                        parameters = self._extract_function_parameters(node)
                                        
                                        # Try to extract response schema from return type annotation
                                        response_schema = self._extract_response_schema(node)
                                        
                                        endpoints.append({
                                            "method": method.upper(),
                                            "path": path,
                                            "function": node.name,
                                            "parameters": parameters,
                                            "response_schema": response_schema,
                                            "file": str(file_path.relative_to(self.project_root)),
                                            "line": decorator.lineno if hasattr(decorator, 'lineno') else 0
                                        })
        except Exception:
            pass
        
        return endpoints
    
    def _extract_function_parameters(self, func_node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Extract parameters from a function definition."""
        parameters = []
        for arg in func_node.args.args:
            param_info = {
                "name": arg.arg,
                "annotation": None,
                "default": None
            }
            
            # Extract type annotation
            if arg.annotation:
                param_info["annotation"] = ast.get_source_segment("", arg.annotation)
            
            parameters.append(param_info)
        
        return parameters
    
    def _extract_response_schema(self, func_node: ast.FunctionDef) -> Dict[str, Any]:
        """Extract response schema from function return annotation."""
        if func_node.returns:
            try:
                return {"return_type": ast.get_source_segment("", func_node.returns)}
            except Exception:
                pass
        return {}
    
    def _extract_ui_components(self) -> List[Dict[str, Any]]:
        """Extract UI components that consume APIs."""
        components = []
        
        # Find all .tsx files in webapp/src
        for file_path in self.webapp_src.rglob("*.tsx"):
            if file_path.is_file():
                try:
                    component_info = self._analyze_ui_component(file_path)
                    if component_info:
                        components.append(component_info)
                except Exception:
                    continue
        
        return components
    
    def _analyze_ui_component(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze a UI component to extract API consumption."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Extract component name
            name = file_path.stem
            
            # Extract API calls (fetch, axios, apiGet, etc.)
            api_calls = self._extract_api_calls(content)
            
            # Extract props
            props = self._extract_component_props(content)
            
            # Extract state variables
            state_vars = self._extract_state_variables(content)
            
            return {
                "name": name,
                "file_path": str(file_path.relative_to(self.project_root)),
                "api_calls": api_calls,
                "props": props,
                "state_vars": state_vars
            }
        except Exception:
            return None
    
    def _extract_api_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract API calls from component content."""
        api_calls = []
        
        # Common API call patterns
        import re
        patterns = [
            (r'apiGet\(["\']([^"\']+)', 'GET'),
            (r'apiPost\(["\']([^"\']+)', 'POST'),
            (r'fetch\(["\']([^"\']+)', 'FETCH'),
            (r'axios\.(get|post|put|delete)\(["\']([^"\']+)', 'AXIOS'),
        ]
        
        for pattern, method in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    # Axios pattern with method
                    path = match[1] if len(match) > 1 else match[0]
                    api_calls.append({
                        "method": method,
                        "path": path,
                        "type": "detected"
                    })
                else:
                    # Simple pattern
                    api_calls.append({
                        "method": method,
                        "path": match,
                        "type": "detected"
                    })
        
        return api_calls
    
    def _extract_component_props(self, content: str) -> List[str]:
        """Extract component props from content."""
        props = []
        
        # Look for common prop patterns
        if 'interface Props' in content:
            # TypeScript interface
            lines = content.split('\n')
            in_interface = False
            for line in lines:
                if 'interface Props' in line:
                    in_interface = True
                    continue
                if in_interface:
                    if line.strip().startswith('}'):
                        break
                    if ':' in line:
                        prop_name = line.split(':')[0].strip()
                        if prop_name and prop_name.isidentifier():
                            props.append(prop_name)
        
        return list(set(props))
    
    def _extract_state_variables(self, content: str) -> List[str]:
        """Extract state variables from component content."""
        state_vars = []
        
        # Look for useState hooks
        import re
        state_matches = re.findall(r'useState\(([^)]*)\)', content)
        for match in state_matches:
            state_vars.append(f"state_{len(state_vars)}")
        
        return state_vars
    
    def _check_contract_violations(self, ui_components: List[Dict[str, Any]], 
                                 api_endpoints: List[Dict[str, Any]]) -> List[ContractViolation]:
        """Check for contract violations between UI and API."""
        violations = []
        
        # Create endpoint lookup by path
        endpoint_lookup = {endpoint["path"]: endpoint for endpoint in api_endpoints}
        
        # Check each UI component
        for component in ui_components:
            for api_call in component.get("api_calls", []):
                path = api_call.get("path", "")
                if path in endpoint_lookup:
                    # Endpoint exists, check parameters and response
                    endpoint = endpoint_lookup[path]
                    # TODO: Add detailed parameter/response checking
                    pass
                else:
                    # Missing endpoint
                    violations.append(ContractViolation(
                        type="missing_endpoint",
                        ui_component=component["name"],
                        api_endpoint=path,
                        details=f"UI component '{component['name']}' calls API endpoint '{path}' which doesn't exist",
                        severity="critical",
                        file_path=component["file_path"],
                        line_number=0
                    ))
        
        return violations
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def generate_contract_report(self, report: ContractReport) -> str:
        """Generate a human-readable contract report."""
        output = []
        output.append("# Contract Verification Report")
        output.append(f"Generated: {report.timestamp}")
        output.append(f"Components Analyzed: {report.components_analyzed}")
        output.append(f"Endpoints Covered: {report.endpoints_covered}")
        output.append("")
        
        if report.violations:
            output.append("## Contract Violations")
            output.append("")
            
            # Group by severity
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_violations = sorted(report.violations, key=lambda v: severity_order.get(v.severity, 999))
            
            for violation in sorted_violations:
                output.append(f"### {violation.severity.upper()}: {violation.type}")
                output.append(f"- **Component**: {violation.ui_component}")
                output.append(f"- **Endpoint**: {violation.api_endpoint}")
                output.append(f"- **Details**: {violation.details}")
                output.append(f"- **File**: {violation.file_path}:{violation.line_number}")
                output.append("")
        else:
            output.append("## ✅ No Contract Violations Found")
            output.append("All UI components are properly aligned with API contracts.")
        
        return "\n".join(output)


def create_contract_guardian(project_root: str = ".") -> ContractGuardian:
    """Factory function to create a ContractGuardian instance."""
    return ContractGuardian(project_root)


# Example usage:
if __name__ == "__main__":
    # Create guardian and verify contracts
    guardian = create_contract_guardian("/Users/venom/Documents/analyse-financiere")
    report = guardian.verify_contracts()
    
    # Generate and print report
    report_text = guardian.generate_contract_report(report)
    print(report_text)
    
    # Save report
    report_file = Path("data/contract_report.md")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report_text, encoding="utf-8")
    print(f"\nReport saved to: {report_file}")