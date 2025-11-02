from __future__ import annotations
import ast
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ReactComponentInfo:
    """Information about a React component."""
    name: str
    file_path: str
    props: List[str]
    hooks: List[str]
    imports: List[str]
    component_type: str  # 'page', 'component', 'layout'


@dataclass
class PythonServiceInfo:
    """Information about a Python service."""
    name: str
    file_path: str
    functions: List[str]
    classes: List[str]
    imports: List[str]
    endpoints: List[str]


@dataclass
class APISchemaInfo:
    """Information about API schemas."""
    name: str
    file_path: str
    fields: List[str]
    base_classes: List[str]


@dataclass
class RepoMap:
    """Repository map containing all structural information."""
    react_components: List[ReactComponentInfo]
    python_services: List[PythonServiceInfo]
    api_schemas: List[APISchemaInfo]
    api_endpoints: List[Dict[str, Any]]
    file_structure: Dict[str, Any]
    last_updated: str


class RepoMapper:
    """Maps repository structure for intelligent agent navigation."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.webapp_src = self.project_root / "webapp" / "src"
        self.python_src = self.project_root / "src"
    
    def generate_repo_map(self) -> RepoMap:
        """Generate a complete map of the repository structure."""
        react_components = self._map_react_components()
        python_services = self._map_python_services()
        api_schemas = self._map_api_schemas()
        api_endpoints = self._extract_api_endpoints()
        file_structure = self._map_file_structure()
        
        return RepoMap(
            react_components=react_components,
            python_services=python_services,
            api_schemas=api_schemas,
            api_endpoints=api_endpoints,
            file_structure=file_structure,
            last_updated=self._get_current_timestamp()
        )
    
    def _map_react_components(self) -> List[ReactComponentInfo]:
        """Map React components in the webapp/src directory."""
        components = []
        
        # Find all .tsx and .ts files in webapp/src
        for file_path in self.webapp_src.rglob("*.tsx"):
            if file_path.is_file():
                try:
                    component_info = self._analyze_react_file(file_path)
                    if component_info:
                        components.append(component_info)
                except Exception:
                    continue
        
        for file_path in self.webapp_src.rglob("*.ts"):
            if file_path.is_file() and not file_path.name.endswith(".d.ts"):
                try:
                    component_info = self._analyze_react_file(file_path)
                    if component_info:
                        components.append(component_info)
                except Exception:
                    continue
        
        return components
    
    def _analyze_react_file(self, file_path: Path) -> Optional[ReactComponentInfo]:
        """Analyze a React file to extract component information."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Determine component type based on path
            component_type = "component"
            if "pages" in str(file_path):
                component_type = "page"
            elif "layout" in str(file_path):
                component_type = "layout"
            
            # Extract component name from filename
            name = file_path.stem
            
            # Extract imports
            imports = self._extract_js_imports(content)
            
            # Extract props and hooks (basic analysis)
            props = self._extract_react_props(content)
            hooks = self._extract_react_hooks(content)
            
            return ReactComponentInfo(
                name=name,
                file_path=str(file_path.relative_to(self.project_root)),
                props=props,
                hooks=hooks,
                imports=imports,
                component_type=component_type
            )
        except Exception:
            return None
    
    def _extract_js_imports(self, content: str) -> List[str]:
        """Extract import statements from JavaScript/TypeScript content."""
        imports = []
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                # Extract module names
                if 'from ' in line:
                    parts = line.split('from ')
                    if len(parts) > 1:
                        module = parts[1].strip().strip(';"\'')
                        if module and not module.startswith('.'):
                            imports.append(module)
        return list(set(imports))
    
    def _extract_react_props(self, content: str) -> List[str]:
        """Extract React props from content (basic implementation)."""
        props = []
        # Look for common prop patterns
        if 'props:' in content or '{' in content and '}' in content:
            # Very basic prop detection
            lines = content.split('\n')
            for line in lines:
                if ':' in line and ('const ' in line or 'interface ' in line or 'type ' in line):
                    prop_name = line.split(':')[0].strip()
                    if prop_name and (' ' not in prop_name) and prop_name.isidentifier():
                        props.append(prop_name)
        return list(set(props))[:10]  # Limit to 10 props
    
    def _extract_react_hooks(self, content: str) -> List[str]:
        """Extract React hooks used in the component."""
        hooks = []
        common_hooks = [
            'useState', 'useEffect', 'useContext', 'useReducer', 'useCallback', 
            'useMemo', 'useRef', 'useImperativeHandle', 'useLayoutEffect', 'useDebugValue',
            'useQuery', 'useMutation', 'useForm', 'useRouter'
        ]
        
        for hook in common_hooks:
            if hook in content:
                hooks.append(hook)
        
        return list(set(hooks))
    
    def _map_python_services(self) -> List[PythonServiceInfo]:
        """Map Python services in the src directory."""
        services = []
        
        # Find all .py files in src excluding __pycache__ and test files
        for file_path in self.python_src.rglob("*.py"):
            if (file_path.is_file() and 
                "__pycache__" not in str(file_path) and 
                not file_path.name.startswith("test_") and
                not file_path.name.endswith("_test.py")):
                try:
                    service_info = self._analyze_python_file(file_path)
                    if service_info:
                        services.append(service_info)
                except Exception:
                    continue
        
        return services
    
    def _analyze_python_file(self, file_path: Path) -> Optional[PythonServiceInfo]:
        """Analyze a Python file to extract service information."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Parse the Python AST
            tree = ast.parse(content)
            
            # Extract service name from filename
            name = file_path.stem
            
            # Extract functions and classes
            functions = []
            classes = []
            imports = []
            endpoints = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                    # Check if it's an API endpoint (decorated with @app.get, @app.post, etc.)
                    if any(isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr') and 
                           decorator.func.attr in ['get', 'post', 'put', 'delete'] 
                           for decorator in node.decorator_list if isinstance(decorator, ast.Call)):
                        endpoints.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
            
            return PythonServiceInfo(
                name=name,
                file_path=str(file_path.relative_to(self.project_root)),
                functions=functions[:20],  # Limit to 20 functions
                classes=classes,
                imports=list(set(imports)),
                endpoints=endpoints
            )
        except Exception:
            return None
    
    def _map_api_schemas(self) -> List[APISchemaInfo]:
        """Map API schemas from the codebase."""
        schemas = []
        
        # Look for schema files
        schema_files = list(self.python_src.rglob("schema*.py")) + \
                       list(self.python_src.rglob("*schema*.py")) + \
                       list(self.python_src.rglob("schemas.py"))
        
        for file_path in schema_files:
            if file_path.is_file():
                try:
                    schema_info = self._analyze_schema_file(file_path)
                    if schema_info:
                        schemas.append(schema_info)
                except Exception:
                    continue
        
        return schemas
    
    def _analyze_schema_file(self, file_path: Path) -> Optional[APISchemaInfo]:
        """Analyze a schema file to extract schema information."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Parse the Python AST
            tree = ast.parse(content)
            
            # Extract schema name from filename
            name = file_path.stem
            
            # Extract fields and base classes
            fields = []
            base_classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    base_classes.extend([base.id for base in node.bases if isinstance(base, ast.Name)])
                    # Extract fields from class attributes
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            fields.append(item.target.id)
                        elif isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    fields.append(target.id)
            
            return APISchemaInfo(
                name=name,
                file_path=str(file_path.relative_to(self.project_root)),
                fields=list(set(fields))[:20],  # Limit to 20 fields
                base_classes=list(set(base_classes))
            )
        except Exception:
            return None
    
    def _extract_api_endpoints(self) -> List[Dict[str, Any]]:
        """Extract API endpoints from the FastAPI application."""
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
            
            # Look for common FastAPI endpoint patterns
            lines = content.split('\n')
            current_endpoint = None
            
            for i, line in enumerate(lines):
                # Look for endpoint decorators
                if '@app.' in line and ('get(' in line or 'post(' in line or 'put(' in line or 'delete(' in line):
                    method = line.split('@app.')[1].split('(')[0]
                    path_start = line.find('"')
                    if path_start != -1:
                        path_end = line.find('"', path_start + 1)
                        if path_end != -1:
                            path = line[path_start+1:path_end]
                            
                            # Look for the function name
                            func_name = "unknown"
                            for j in range(i+1, min(i+5, len(lines))):
                                func_line = lines[j]
                                if 'def ' in func_line:
                                    func_parts = func_line.split('def ')
                                    if len(func_parts) > 1:
                                        func_name = func_parts[1].split('(')[0].strip()
                                    break
                            
                            endpoints.append({
                                "method": method.upper(),
                                "path": path,
                                "function": func_name,
                                "file": str(file_path.relative_to(self.project_root)),
                                "line": i + 1
                            })
        except Exception:
            pass
        
        return endpoints
    
    def _map_file_structure(self) -> Dict[str, Any]:
        """Create a hierarchical map of the file structure."""
        def _build_tree(path: Path) -> Dict[str, Any]:
            if path.is_file():
                return {"type": "file", "name": path.name}
            elif path.is_dir():
                children = {}
                try:
                    for item in path.iterdir():
                        if not item.name.startswith('.'):
                            children[item.name] = _build_tree(item)
                except PermissionError:
                    pass
                return {"type": "directory", "name": path.name, "children": children}
            return {"type": "unknown", "name": path.name}
        
        return _build_tree(self.project_root)
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def save_repo_map(self, repo_map: RepoMap, output_path: str = "data/repo_map.json") -> Path:
        """Save the repository map to a JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclass to dictionary
        def _serialize(obj):
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif isinstance(obj, list):
                return [_serialize(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: _serialize(value) for key, value in obj.items()}
            else:
                return obj
        
        data = _serialize(repo_map)
        output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_file
    
    def load_repo_map(self, input_path: str = "data/repo_map.json") -> Optional[RepoMap]:
        """Load a repository map from a JSON file."""
        input_file = Path(input_path)
        if not input_file.exists():
            return None
        
        try:
            data = json.loads(input_file.read_text(encoding="utf-8"))
            # Convert dictionary back to dataclass (simplified)
            return RepoMap(**data)
        except Exception:
            return None


def create_repo_mapper(project_root: str = ".") -> RepoMapper:
    """Factory function to create a RepoMapper instance."""
    return RepoMapper(project_root)


# Example usage:
if __name__ == "__main__":
    # Create mapper and generate repo map
    mapper = create_repo_mapper("/Users/venom/Documents/analyse-financiere")
    repo_map = mapper.generate_repo_map()
    
    # Save the map
    output_file = mapper.save_repo_map(repo_map)
    print(f"Repository map saved to: {output_file}")
    
    # Print summary
    print(f"\nRepository Map Summary:")
    print(f"  React Components: {len(repo_map.react_components)}")
    print(f"  Python Services: {len(repo_map.python_services)}")
    print(f"  API Schemas: {len(repo_map.api_schemas)}")
    print(f"  API Endpoints: {len(repo_map.api_endpoints)}")
    print(f"  Last Updated: {repo_map.last_updated}")