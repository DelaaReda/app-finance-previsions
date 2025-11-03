from __future__ import annotations
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class FileStructure:
    """Represents a file structure."""
    name: str
    type: str  # 'file' or 'directory'
    path: str
    children: Optional[List[FileStructure]] = None
    language: Optional[str] = None
    size: Optional[int] = None


@dataclass
class APIEndpoint:
    """Represents an API endpoint."""
    method: str
    path: str
    function_name: str
    parameters: List[Dict[str, Any]]
    return_type: Optional[str]
    file_path: str
    line_number: int


@dataclass
class ReactComponent:
    """Represents a React component."""
    name: str
    file_path: str
    props: List[str]
    state_variables: List[str]
    hooks: List[str]
    api_calls: List[Dict[str, Any]]
    dependencies: List[str]


@dataclass
class PythonService:
    """Represents a Python service."""
    name: str
    file_path: str
    functions: List[str]
    classes: List[str]
    imports: List[str]
    endpoints: List[APIEndpoint]


@dataclass
class RepoMap:
    """Complete repository map."""
    file_structure: FileStructure
    api_endpoints: List[APIEndpoint]
    react_components: List[ReactComponent]
    python_services: List[PythonService]
    last_updated: str


class RepoMapper:
    """Maps repository structure for intelligence."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.webapp_src = self.project_root / "webapp" / "src"
        self.python_src = self.project_root / "src"
    
    def generate_repo_map(self) -> RepoMap:
        """
        Generate a complete map of the repository.
        
        Returns:
            RepoMap with complete repository information
        """
        # Generate file structure
        file_structure = self._map_file_structure()
        
        # Extract API endpoints
        api_endpoints = self._map_api_endpoints()
        
        # Extract React components
        react_components = self._map_react_components()
        
        # Extract Python services
        python_services = self._map_python_services()
        
        return RepoMap(
            file_structure=file_structure,
            api_endpoints=api_endpoints,
            react_components=react_components,
            python_services=python_services,
            last_updated=self._get_current_timestamp()
        )
    
    def _map_file_structure(self) -> FileStructure:
        """Map the file structure of the repository."""
        def _build_tree(path: Path) -> FileStructure:
            if path.is_file():
                # Determine language by extension
                language = None
                if path.suffix in ['.py']:
                    language = "python"
                elif path.suffix in ['.ts', '.tsx']:
                    language = "typescript"
                elif path.suffix in ['.js', '.jsx']:
                    language = "javascript"
                elif path.suffix in ['.md']:
                    language = "markdown"
                elif path.suffix in ['.json']:
                    language = "json"
                
                return FileStructure(
                    name=path.name,
                    type="file",
                    path=str(path.relative_to(self.project_root)),
                    language=language,
                    size=path.stat().st_size if path.exists() else 0
                )
            elif path.is_dir():
                children = []
                try:
                    for item in path.iterdir():
                        # Skip hidden files/directories and common exclusions
                        if not item.name.startswith('.') and item.name not in ['__pycache__', 'node_modules']:
                            children.append(_build_tree(item))
                except PermissionError:
                    pass
                
                return FileStructure(
                    name=path.name,
                    type="directory",
                    path=str(path.relative_to(self.project_root)),
                    children=children
                )
            else:
                return FileStructure(
                    name=path.name,
                    type="unknown",
                    path=str(path.relative_to(self.project_root))
                )
        
        return _build_tree(self.project_root)
    
    def _map_api_endpoints(self) -> List[APIEndpoint]:
        """Map API endpoints from Python files."""
        endpoints = []
        
        # Look for API files
        api_files = []
        if (self.python_src / "api").exists():
            for file in (self.python_src / "api").rglob("*.py"):
                if file.is_file():
                    api_files.append(file)
        
        # Also check main.py files
        for main_file in [self.python_src / "api" / "main.py", self.python_src / "api" / "main_v2.py"]:
            if main_file.exists():
                api_files.append(main_file)
        
        # Extract endpoints from each file
        for file_path in api_files:
            try:
                endpoints.extend(self._extract_endpoints_from_file(file_path))
            except Exception:
                continue
        
        return endpoints
    
    def _extract_endpoints_from_file(self, file_path: Path) -> List[APIEndpoint]:
        """Extract API endpoints from a Python file."""
        endpoints = []
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            # Look for FastAPI decorators (@app.get, @app.post, etc.)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check decorators
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            # Check if it's a FastAPI endpoint decorator
                            if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                method = decorator.func.attr.upper()
                                
                                # Extract path from decorator arguments
                                path = None
                                if decorator.args:
                                    arg = decorator.args[0]
                                    if isinstance(arg, ast.Constant):
                                        path = arg.value
                                    elif isinstance(arg, ast.Str):
                                        path = arg.s
                                
                                if path:
                                    # Extract parameters
                                    parameters = []
                                    for arg in node.args.args:
                                        param_info = {
                                            "name": arg.arg,
                                            "annotation": None
                                        }
                                        
                                        # Extract annotation if available
                                        if arg.annotation:
                                            param_info["annotation"] = ast.get_source_segment(content, arg.annotation)
                                        
                                        parameters.append(param_info)
                                    
                                    # Extract return type
                                    return_type = None
                                    if node.returns:
                                        return_type = ast.get_source_segment(content, node.returns)
                                    
                                    endpoints.append(APIEndpoint(
                                        method=method,
                                        path=path,
                                        function_name=node.name,
                                        parameters=parameters,
                                        return_type=return_type,
                                        file_path=str(file_path.relative_to(self.project_root)),
                                        line_number=decorator.lineno
                                    ))
        except Exception:
            pass
        
        return endpoints
    
    def _map_react_components(self) -> List[ReactComponent]:
        """Map React components from TypeScript/JavaScript files."""
        components = []
        
        # Look for React files
        react_files = []
        if self.webapp_src.exists():
            for file in self.webapp_src.rglob("*.tsx"):
                if file.is_file():
                    react_files.append(file)
            for file in self.webapp_src.rglob("*.jsx"):
                if file.is_file():
                    react_files.append(file)
        
        # Extract components from each file
        for file_path in react_files:
            try:
                components.extend(self._extract_components_from_file(file_path))
            except Exception:
                continue
        
        return components
    
    def _extract_components_from_file(self, file_path: Path) -> List[ReactComponent]:
        """Extract React components from a file."""
        components = []
        
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Simple regex-based extraction for now
            # In a real implementation, you would use a proper AST parser for JS/TS
            
            # Look for component definitions
            import re
            
            # Look for function components
            function_pattern = r"function\s+(\w+)\s*\("
            function_matches = re.findall(function_pattern, content)
            
            # Look for arrow function components
            arrow_pattern = r"const\s+(\w+)\s*=\s*\([^)]*\)\s*=>"
            arrow_matches = re.findall(arrow_pattern, content)
            
            # Combine all component names
            component_names = list(set(function_matches + arrow_matches))
            
            # Extract basic information for each component
            for component_name in component_names:
                # Extract props
                props = self._extract_props(content, component_name)
                
                # Extract state variables
                state_vars = self._extract_state_variables(content)
                
                # Extract hooks
                hooks = self._extract_hooks(content)
                
                # Extract API calls
                api_calls = self._extract_api_calls(content)
                
                # Extract dependencies (imports)
                dependencies = self._extract_dependencies(content)
                
                components.append(ReactComponent(
                    name=component_name,
                    file_path=str(file_path.relative_to(self.project_root)),
                    props=props,
                    state_variables=state_vars,
                    hooks=hooks,
                    api_calls=api_calls,
                    dependencies=dependencies
                ))
        except Exception:
            pass
        
        return components
    
    def _extract_props(self, content: str, component_name: str) -> List[str]:
        """Extract props from component definition."""
        props = []
        
        # Look for destructuring patterns
        import re
        destructuring_pattern = rf"{component_name}\s*{{([^}}]+)}}"
        matches = re.findall(destructuring_pattern, content)
        
        for match in matches:
            # Split by commas and clean up
            prop_list = [prop.strip() for prop in match.split(',')]
            props.extend([prop.split(':')[0].strip() for prop in prop_list if prop.strip()])
        
        return list(set(props))
    
    def _extract_state_variables(self, content: str) -> List[str]:
        """Extract state variables from React components."""
        state_vars = []
        
        # Look for useState patterns
        import re
        useState_pattern = r"useState\(([^)]*)\)"
        matches = re.findall(useState_pattern, content)
        
        for match in matches:
            # Simple extraction of state variable names
            state_vars.append(f"state_{len(state_vars)}")
        
        return state_vars
    
    def _extract_hooks(self, content: str) -> List[str]:
        """Extract React hooks used in the component."""
        hooks = []
        
        # Look for common React hooks
        common_hooks = [
            "useState", "useEffect", "useContext", "useReducer", 
            "useCallback", "useMemo", "useRef", "useImperativeHandle",
            "useLayoutEffect", "useDebugValue"
        ]
        
        for hook in common_hooks:
            if hook in content:
                hooks.append(hook)
        
        return list(set(hooks))
    
    def _extract_api_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract API calls from the component."""
        api_calls = []
        
        # Look for common API call patterns
        import re
        
        # Look for fetch calls
        fetch_pattern = r"fetch\(['\"]([^'\"]+)['\"]"
        fetch_matches = re.findall(fetch_pattern, content)
        
        for match in fetch_matches:
            api_calls.append({
                "method": "FETCH",
                "url": match,
                "line": self._find_line_number(content, match)
            })
        
        # Look for axios calls
        axios_pattern = r"axios\.(get|post|put|delete)\(['\"]([^'\"]+)['\"]"
        axios_matches = re.findall(axios_pattern, content)
        
        for method, url in axios_matches:
            api_calls.append({
                "method": method.upper(),
                "url": url,
                "line": self._find_line_number(content, url)
            })
        
        # Look for apiGet/apiPost calls (custom API client)
        custom_pattern = r"api(Get|Post|Put|Delete)\(['\"]([^'\"]+)['\"]"
        custom_matches = re.findall(custom_pattern, content)
        
        for method, url in custom_matches:
            api_calls.append({
                "method": method.upper(),
                "url": url,
                "line": self._find_line_number(content, url)
            })
        
        return api_calls
    
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract import dependencies."""
        dependencies = []
        
        # Look for import statements
        import re
        import_pattern = r"from\s+['\"]([^'\"]+)['\"]"
        matches = re.findall(import_pattern, content)
        
        for match in matches:
            # Filter out relative imports and node_modules
            if not match.startswith('.') and 'node_modules' not in match:
                dependencies.append(match)
        
        return list(set(dependencies))
    
    def _map_python_services(self) -> List[PythonService]:
        """Map Python services from the repository."""
        services = []
        
        # Look for Python service files
        service_files = []
        if (self.python_src / "api" / "services").exists():
            for file in (self.python_src / "api" / "services").rglob("*.py"):
                if file.is_file():
                    service_files.append(file)
        
        # Extract services from each file
        for file_path in service_files:
            try:
                services.extend(self._extract_services_from_file(file_path))
            except Exception:
                continue
        
        return services
    
    def _extract_services_from_file(self, file_path: Path) -> List[PythonService]:
        """Extract Python services from a file."""
        services = []
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            # Extract service name from file name
            service_name = file_path.stem
            
            # Extract functions
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
            
            # Extract classes
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Extract endpoints (FastAPI routes)
            endpoints = self._extract_endpoints_from_file(file_path)
            
            services.append(PythonService(
                name=service_name,
                file_path=str(file_path.relative_to(self.project_root)),
                functions=functions,
                classes=classes,
                imports=imports,
                endpoints=endpoints
            ))
        except Exception:
            pass
        
        return services
    
    def _find_line_number(self, content: str, pattern: str) -> int:
        """Find line number of a pattern in content."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if pattern in line:
                return i + 1
        return 1
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def save_repo_map(self, repo_map: RepoMap, output_path: str = "data/repo_map.json") -> Path:
        """Save the repository map to a JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary
        def serialize(obj):
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif isinstance(obj, list):
                return [serialize(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: serialize(value) for key, value in obj.items()}
            else:
                return obj
        
        data = serialize(repo_map)
        output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_file


def create_repo_mapper(project_root: str = ".") -> RepoMapper:
    """Factory function to create a RepoMapper instance."""
    return RepoMapper(project_root)


# Example usage:
if __name__ == "__main__":
    # Create mapper
    mapper = create_repo_mapper("/Users/venom/Documents/analyse-financiere")
    
    # Generate repo map
    repo_map = mapper.generate_repo_map()
    
    # Save map
    output_file = mapper.save_repo_map(repo_map)
    print(f"Repository map saved to: {output_file}")
    
    # Print summary
    print(f"\nRepository Map Summary:")
    print(f"  API Endpoints: {len(repo_map.api_endpoints)}")
    print(f"  React Components: {len(repo_map.react_components)}")
    print(f"  Python Services: {len(repo_map.python_services)}")
    print(f"  Last Updated: {repo_map.last_updated}")