#!/usr/bin/env python3
"""
Convert Infracost Go resource definitions to Python pricing calculator classes.
This script parses Go structs and generates equivalent Python classes with pricing logic.
"""

import os
import re
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

class GoToPythonConverter:
    def __init__(self, infracost_aws_path: str):
        self.infracost_path = infracost_aws_path
        self.go_to_python_types = {
            'string': 'str',
            'int64': 'int',
            'float64': 'float',
            'bool': 'bool',
            '*string': 'Optional[str]',
            '*int64': 'Optional[int]',
            '*float64': 'Optional[float]',
            '*bool': 'Optional[bool]',
            '[]string': 'List[str]',
            'decimal.Decimal': 'Decimal',
        }
        
    def convert_all_resources(self) -> Dict[str, str]:
        """Convert all Go resource files to Python classes"""
        go_files = list(Path(self.infracost_path).glob("*.go"))
        go_files = [f for f in go_files if not f.name.endswith('_test.go')]
        
        converted = {}
        for go_file in go_files:
            try:
                python_code = self.convert_go_file(go_file)
                if python_code:
                    converted[go_file.stem] = python_code
            except Exception as e:
                print(f"Error converting {go_file.name}: {e}")
                
        return converted
    
    def convert_go_file(self, go_file_path: Path) -> Optional[str]:
        """Convert a single Go file to Python"""
        with open(go_file_path, 'r') as f:
            content = f.read()
        
        # Skip files without struct definitions
        if 'type ' not in content or 'struct {' not in content:
            return None
            
        # Extract struct definitions
        structs = self.extract_structs(content)
        if not structs:
            return None
            
        # Generate Python code
        python_code = self.generate_python_code(structs, go_file_path.stem)
        return python_code
    
    def extract_structs(self, content: str) -> List[Dict]:
        """Extract Go struct definitions from file content"""
        structs = []
        
        # Find all struct definitions
        struct_pattern = r'type\s+(\w+)\s+struct\s*\{([^}]+)\}'
        matches = re.finditer(struct_pattern, content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            struct_name = match.group(1)
            struct_body = match.group(2)
            
            # Parse struct fields
            fields = self.parse_struct_fields(struct_body)
            
            # Extract methods (simplified)
            methods = self.extract_methods(content, struct_name)
            
            structs.append({
                'name': struct_name,
                'fields': fields,
                'methods': methods
            })
            
        return structs
    
    def parse_struct_fields(self, struct_body: str) -> List[Dict]:
        """Parse struct fields from struct body"""
        fields = []
        lines = struct_body.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
                
            # Parse field: Name Type `tags`
            field_match = re.match(r'(\w+)\s+([*\[\]\w.]+)(?:\s+`([^`]*)`)?', line)
            if field_match:
                field_name = field_match.group(1)
                field_type = field_match.group(2)
                tags = field_match.group(3) or ''
                
                # Extract infracost_usage tag
                usage_key = None
                if 'infracost_usage:' in tags:
                    usage_match = re.search(r'infracost_usage:"([^"]*)"', tags)
                    if usage_match:
                        usage_key = usage_match.group(1)
                
                fields.append({
                    'name': field_name,
                    'type': field_type,
                    'usage_key': usage_key,
                    'python_type': self.convert_go_type(field_type)
                })
                
        return fields
    
    def convert_go_type(self, go_type: str) -> str:
        """Convert Go type to Python type annotation"""
        return self.go_to_python_types.get(go_type, 'Any')
    
    def extract_methods(self, content: str, struct_name: str) -> List[Dict]:
        """Extract method signatures for the struct"""
        methods = []
        
        # Find methods for this struct
        method_pattern = rf'func\s+\([^)]*\*?{struct_name}\)\s+(\w+)\([^)]*\)\s*([^{{]*)\s*\{{'
        matches = re.finditer(method_pattern, content)
        
        for match in matches:
            method_name = match.group(1)
            return_type = match.group(2).strip()
            
            methods.append({
                'name': method_name,
                'return_type': return_type
            })
            
        return methods
    
    def generate_python_code(self, structs: List[Dict], file_name: str) -> str:
        """Generate Python code from parsed structs"""
        imports = [
            "from typing import Dict, List, Any, Optional",
            "from decimal import Decimal",
            "from dataclasses import dataclass",
            ""
        ]
        
        classes = []
        
        for struct in structs:
            class_code = self.generate_class(struct)
            classes.append(class_code)
        
        # Generate usage schema mappings
        usage_schemas = self.generate_usage_schemas(structs)
        
        python_code = '\n'.join(imports) + '\n'.join(classes) + '\n' + usage_schemas
        return python_code
    
    def generate_class(self, struct: Dict) -> str:
        """Generate Python class from struct definition"""
        class_name = struct['name']
        fields = struct['fields']
        
        # Generate dataclass fields
        field_lines = []
        for field in fields:
            python_name = self.snake_case(field['name'])
            python_type = field['python_type']
            
            # Add default values for optional fields
            if python_type.startswith('Optional'):
                field_lines.append(f"    {python_name}: {python_type} = None")
            elif python_type in ['int', 'float']:
                field_lines.append(f"    {python_name}: {python_type} = 0")
            elif python_type == 'bool':
                field_lines.append(f"    {python_name}: {python_type} = False")
            elif python_type == 'str':
                field_lines.append(f"    {python_name}: {python_type} = ''")
            else:
                field_lines.append(f"    {python_name}: {python_type}")
        
        # Generate methods
        method_lines = []
        
        # Core type method
        method_lines.append(f"""
    def core_type(self) -> str:
        return "{class_name}"
""")
        
        # Usage schema method
        usage_fields = [f for f in fields if f['usage_key']]
        if usage_fields:
            usage_items = []
            for field in usage_fields:
                usage_items.append(f'        {{key: "{field["usage_key"]}", default_value: 0}}')
            
            method_lines.append(f"""
    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
{chr(10).join(usage_items)}
        ]
""")
        else:
            method_lines.append("""
    def usage_schema(self) -> List[Dict[str, Any]]:
        return []
""")
        
        # Build resource method (simplified)
        method_lines.append("""
    def build_resource(self) -> Dict[str, Any]:
        # TODO: Implement pricing logic based on Infracost patterns
        return {
            'name': getattr(self, 'address', self.core_type()),
            'cost_components': self._build_cost_components(),
            'usage_schema': self.usage_schema()
        }
    
    def _build_cost_components(self) -> List[Dict[str, Any]]:
        # TODO: Extract cost component logic from Go implementation
        return []
""")
        
        class_code = f"""
@dataclass
class {class_name}:
    \"\"\"
    Python equivalent of Infracost {class_name} resource.
    Auto-generated from Go struct definition.
    \"\"\"
{chr(10).join(field_lines)}
{''.join(method_lines)}
"""
        
        return class_code
    
    def generate_usage_schemas(self, structs: List[Dict]) -> str:
        """Generate usage schema mappings"""
        schemas = {}
        
        for struct in structs:
            usage_fields = [f for f in struct['fields'] if f['usage_key']]
            if usage_fields:
                schema_items = []
                for field in usage_fields:
                    schema_items.append({
                        'key': field['usage_key'],
                        'type': field['python_type'],
                        'default_value': 0
                    })
                schemas[struct['name']] = schema_items
        
        if not schemas:
            return ""
            
        return f"""
# Usage schema mappings extracted from Go structs
USAGE_SCHEMAS = {json.dumps(schemas, indent=2)}
"""
    
    def snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def main():
    """Convert all Infracost AWS resources to Python"""
    infracost_path = "/Users/suhaibchisti/Downloads/infracost/internal/resources/aws"
    
    if not os.path.exists(infracost_path):
        print(f"Infracost path not found: {infracost_path}")
        return
    
    converter = GoToPythonConverter(infracost_path)
    converted_resources = converter.convert_all_resources()
    
    # Create output directory
    output_dir = Path("./aws_resources")
    output_dir.mkdir(exist_ok=True)
    
    # Write converted files
    for resource_name, python_code in converted_resources.items():
        output_file = output_dir / f"{resource_name}.py"
        with open(output_file, 'w') as f:
            f.write(python_code)
        print(f"Generated: {output_file}")
    
    # Generate __init__.py
    init_content = "# Auto-generated AWS resource classes from Infracost\n\n"
    for resource_name in converted_resources.keys():
        init_content += f"from .{resource_name} import *\n"
    
    with open(output_dir / "__init__.py", 'w') as f:
        f.write(init_content)
    
    print(f"\nConverted {len(converted_resources)} AWS resources to Python!")
    print(f"Total Infracost resources available: 113")
    print(f"Successfully converted: {len(converted_resources)}")

if __name__ == "__main__":
    main()
