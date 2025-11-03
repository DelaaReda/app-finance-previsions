from __future__ import annotations
import ast
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class PatchResult:
    """Result of a patch operation."""
    success: bool
    file_path: str
    changes_made: bool
    original_content: str
    patched_content: str
    backup_path: Optional[str]
    error_message: Optional[str]
    line_changes: List[Dict[str, Any]]


@dataclass
class ASTDiff:
    """Represents changes in AST structure."""
    type: str  # 'insert', 'modify', 'delete'
    node_type: str  # 'function', 'class', 'import', etc.
    location: Dict[str, Any]  # line, column, path
    before: Optional[str]
    after: Optional[str]


class ASTPatcher:
    """Patches code files using AST transformations with rollback safety."""
    
    def __init__(self, project_root: str = ".", backup_dir: str = "data/backups"):
        self.project_root = Path(project_root)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def patch_file(self, file_path: str, patch_operations: List[Dict[str, Any]], 
                   dry_run: bool = False) -> PatchResult:
        """
        Apply AST-based patches to a file.
        
        Args:
            file_path: Path to the file to patch
            patch_operations: List of patch operations to apply
            dry_run: If True, don't actually apply changes
            
        Returns:
            PatchResult with details of the operation
        """
        full_path = self.project_root / file_path
        
        # Validate file exists
        if not full_path.exists():
            return PatchResult(
                success=False,
                file_path=file_path,
                changes_made=False,
                original_content="",
                patched_content="",
                backup_path=None,
                error_message=f"File not found: {file_path}",
                line_changes=[]
            )
        
        # Read original content
        try:
            original_content = full_path.read_text(encoding="utf-8")
        except Exception as e:
            return PatchResult(
                success=False,
                file_path=file_path,
                changes_made=False,
                original_content="",
                patched_content="",
                backup_path=None,
                error_message=f"Failed to read file: {str(e)}",
                line_changes=[]
            )
        
        # Backup original file
        backup_path = self._create_backup(full_path, original_content)
        
        # Apply patches based on file type
        if file_path.endswith(('.py',)):
            result = self._patch_python_file(full_path, original_content, patch_operations, dry_run)
        elif file_path.endswith(('.ts', '.tsx')):
            result = self._patch_typescript_file(full_path, original_content, patch_operations, dry_run)
        else:
            result = PatchResult(
                success=False,
                file_path=file_path,
                changes_made=False,
                original_content=original_content,
                patched_content=original_content,
                backup_path=str(backup_path),
                error_message=f"Unsupported file type: {file_path}",
                line_changes=[]
            )
        
        # If not successful and we have a backup, restore it
        if not result.success and not dry_run:
            self._restore_backup(full_path, backup_path)
        
        return result
    
    def _create_backup(self, file_path: Path, content: str) -> Path:
        """Create a backup of the original file."""
        backup_name = f"{file_path.name}.backup.{self._get_timestamp()}"
        backup_path = self.backup_dir / backup_name
        backup_path.write_text(content, encoding="utf-8")
        return backup_path
    
    def _restore_backup(self, file_path: Path, backup_path: Path) -> bool:
        """Restore file from backup."""
        try:
            if backup_path.exists():
                content = backup_path.read_text(encoding="utf-8")
                file_path.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False
    
    def _patch_python_file(self, file_path: Path, content: str, 
                          patch_operations: List[Dict[str, Any]], dry_run: bool) -> PatchResult:
        """Apply patches to a Python file using AST."""
        try:
            # Parse AST
            tree = ast.parse(content)
            
            # Apply transformations
            transformer = self._create_python_transformer(patch_operations)
            new_tree = transformer.visit(tree)
            ast.fix_missing_locations(new_tree)
            
            # Convert back to source
            import astor
            patched_content = astor.to_source(new_tree)
            
            # Check if changes were made
            changes_made = patched_content != content
            
            # Write changes if not dry run
            if changes_made and not dry_run:
                file_path.write_text(patched_content, encoding="utf-8")
            
            return PatchResult(
                success=True,
                file_path=str(file_path.relative_to(self.project_root)),
                changes_made=changes_made,
                original_content=content,
                patched_content=patched_content,
                backup_path=str(self.backup_dir / f"{file_path.name}.backup.{self._get_timestamp()}"),
                error_message=None,
                line_changes=self._calculate_line_changes(content, patched_content)
            )
            
        except Exception as e:
            return PatchResult(
                success=False,
                file_path=str(file_path.relative_to(self.project_root)),
                changes_made=False,
                original_content=content,
                patched_content=content,
                backup_path=None,
                error_message=f"AST transformation failed: {str(e)}",
                line_changes=[]
            )
    
    def _create_python_transformer(self, patch_operations: List[Dict[str, Any]]) -> ast.NodeTransformer:
        """Create a Python AST transformer for the given operations."""
        class PythonTransformer(ast.NodeTransformer):
            def __init__(self, operations: List[Dict[str, Any]]):
                self.operations = operations
            
            def visit_FunctionDef(self, node):
                # Apply function-specific operations
                for op in self.operations:
                    if op.get("type") == "add_parameter" and op.get("target_function") == node.name:
                        # Add parameter to function
                        param_name = op.get("parameter_name")
                        default_value = op.get("default_value")
                        if param_name:
                            # Add parameter to args
                            arg = ast.arg(arg=param_name, annotation=None)
                            node.args.args.append(arg)
                            if default_value is not None:
                                # Add default value
                                node.args.defaults.append(ast.Constant(value=default_value))
                
                return self.generic_visit(node)
            
            def visit_Import(self, node):
                # Apply import operations
                for op in self.operations:
                    if op.get("type") == "add_import":
                        module = op.get("module")
                        if module:
                            # Add new import
                            pass  # Complex to implement without breaking existing structure
                
                return self.generic_visit(node)
        
        return PythonTransformer(patch_operations)
    
    def _patch_typescript_file(self, file_path: Path, content: str,
                              patch_operations: List[Dict[str, Any]], dry_run: bool) -> PatchResult:
        """Apply patches to a TypeScript file using ts-morph."""
        try:
            # For now, use simple text-based patching for TypeScript
            # In a real implementation, we would use ts-morph via Node.js
            
            patched_content = content
            changes_made = False
            
            # Apply simple text-based operations
            for op in patch_operations:
                op_type = op.get("type")
                if op_type == "add_import":
                    module = op.get("module")
                    if module and f"from '{module}'" not in patched_content:
                        # Add import at the top
                        lines = patched_content.split('\n')
                        lines.insert(0, f"import {{ }} from '{module}';")
                        patched_content = '\n'.join(lines)
                        changes_made = True
                elif op_type == "add_function":
                    function_name = op.get("function_name")
                    if function_name and f"function {function_name}" not in patched_content:
                        # Add function at the end
                        function_body = op.get("body", "// TODO: Implement function")
                        patched_content += f"\n\nfunction {function_name}() {{\n{function_body}\n}}\n"
                        changes_made = True
            
            # Check if changes were made
            changes_made = changes_made or (patched_content != content)
            
            # Write changes if not dry run
            if changes_made and not dry_run:
                file_path.write_text(patched_content, encoding="utf-8")
            
            return PatchResult(
                success=True,
                file_path=str(file_path.relative_to(self.project_root)),
                changes_made=changes_made,
                original_content=content,
                patched_content=patched_content,
                backup_path=str(self.backup_dir / f"{file_path.name}.backup.{self._get_timestamp()}"),
                error_message=None,
                line_changes=self._calculate_line_changes(content, patched_content)
            )
            
        except Exception as e:
            return PatchResult(
                success=False,
                file_path=str(file_path.relative_to(self.project_root)),
                changes_made=False,
                original_content=content,
                patched_content=content,
                backup_path=None,
                error_message=f"TypeScript transformation failed: {str(e)}",
                line_changes=[]
            )
    
    def _calculate_line_changes(self, original: str, patched: str) -> List[Dict[str, Any]]:
        """Calculate line-by-line changes between original and patched content."""
        original_lines = original.split('\n')
        patched_lines = patched.split('\n')
        
        changes = []
        
        # Simple diff algorithm
        max_len = max(len(original_lines), len(patched_lines))
        for i in range(max_len):
            orig_line = original_lines[i] if i < len(original_lines) else None
            patch_line = patched_lines[i] if i < len(patched_lines) else None
            
            if orig_line != patch_line:
                change_type = "modified"
                if orig_line is None:
                    change_type = "added"
                elif patch_line is None:
                    change_type = "deleted"
                
                changes.append({
                    "line_number": i + 1,
                    "type": change_type,
                    "original": orig_line,
                    "patched": patch_line
                })
        
        return changes
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    def rollback_last_patch(self, backup_path: str) -> bool:
        """Rollback the last patch using the backup."""
        try:
            backup_file = Path(backup_path)
            if backup_file.exists():
                # Extract original file path from backup name
                backup_name = backup_file.name
                if ".backup." in backup_name:
                    original_file_name = backup_name.split(".backup.")[0]
                    original_file = self.project_root / original_file_name
                    
                    # Restore content
                    content = backup_file.read_text(encoding="utf-8")
                    original_file.write_text(content, encoding="utf-8")
                    
                    return True
            return False
        except Exception:
            return False


def create_ast_patcher(project_root: str = ".", backup_dir: str = "data/backups") -> ASTPatcher:
    """Factory function to create an ASTPatcher instance."""
    return ASTPatcher(project_root, backup_dir)


# Example usage:
if __name__ == "__main__":
    # Create patcher
    patcher = create_ast_patcher("/Users/venom/Documents/analyse-financiere")
    
    # Example patch operations
    patch_ops = [
        {
            "type": "add_import",
            "module": "logging"
        },
        {
            "type": "add_function",
            "function_name": "new_helper_function",
            "body": "    console.log('New helper function');\n    return true;"
        }
    ]
    
    # Apply patch (dry run)
    result = patcher.patch_file("webapp/src/App.tsx", patch_ops, dry_run=True)
    
    if result.success:
        print(f"Patching successful (dry run): {result.file_path}")
        print(f"Changes made: {result.changes_made}")
        if result.line_changes:
            print(f"Lines changed: {len(result.line_changes)}")
    else:
        print(f"Patching failed: {result.error_message}")