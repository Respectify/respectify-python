#!/usr/bin/env python3
"""
Generate PHP classes and markdown documentation from Python Pydantic schemas.

This script parses schemas.py and generates:
1. PHP class files with proper camelCase properties
2. Markdown documentation with Python/PHP/JSON examples
3. Maintains the Python schemas as the single source of truth

Usage:
    python schema_generator.py
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FieldInfo:
    """Information about a schema field."""
    name: str  # Python snake_case name
    type_hint: str  # Python type hint
    description: str
    default: Optional[str] = None
    constraints: Dict[str, str] = None  # e.g., ge=1, le=5

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}

    @property
    def php_name(self) -> str:
        """Convert snake_case to camelCase for PHP."""
        # Convert snake_case to camelCase - NO SPECIAL MAPPINGS
        # Python is the source of truth, PHP matches it exactly
        parts = self.name.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])

    @property
    def php_type(self) -> str:
        """Convert Python type to PHP type."""
        # Handle List[X]
        if 'List[' in self.type_hint:
            return 'array'

        # Check if it's optional
        is_optional = 'Optional[' in self.type_hint

        # Handle Optional[X]
        type_clean = self.type_hint.replace('Optional[', '').replace(']', '')

        type_map = {
            'str': 'string',
            'int': 'int',
            'float': 'float',
            'bool': 'bool',
            'UUID': 'string',  # UUIDs are strings in PHP
        }

        # Check for custom classes
        php_base_type = None
        for py_type, php_type in type_map.items():
            if py_type in type_clean:
                php_base_type = php_type
                break

        # If not found in map, it's a class name
        if php_base_type is None:
            php_base_type = type_clean

        # Add ? for nullable types
        if is_optional:
            return f"?{php_base_type}"

        return php_base_type

    @property
    def json_name(self) -> str:
        """JSON uses snake_case like Python."""
        return self.name


@dataclass
class SchemaInfo:
    """Information about a schema class."""
    name: str
    docstring: str
    fields: List[FieldInfo]
    is_frozen: bool = True
    has_properties: bool = False  # For MegaCallResult aliases


class SchemaParser:
    """Parse Python schemas.py file to extract schema information."""

    def __init__(self, schema_file: Path):
        self.schema_file = schema_file
        with open(schema_file, 'r') as f:
            self.tree = ast.parse(f.read())

    def parse_schemas(self) -> List[SchemaInfo]:
        """Parse all schema classes from the file."""
        schemas = []

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                # Only process BaseModel subclasses
                if any(base.id == 'BaseModel' for base in node.bases if isinstance(base, ast.Name)):
                    schema = self._parse_class(node)
                    schemas.append(schema)

        return schemas

    def _parse_class(self, node: ast.ClassDef) -> SchemaInfo:
        """Parse a single class definition."""
        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Check if frozen
        is_frozen = True
        has_properties = False

        for item in node.body:
            # Check model_config
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == 'model_config':
                        # Look for frozen=True in the config
                        if 'frozen' in ast.unparse(item.value):
                            is_frozen = 'frozen=True' in ast.unparse(item.value) or 'frozen = True' in ast.unparse(item.value)

            # Check for @property decorators
            if isinstance(item, ast.FunctionDef):
                for decorator in item.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'property':
                        has_properties = True

        # Parse fields
        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field = self._parse_field(item)
                if field:
                    fields.append(field)

        return SchemaInfo(
            name=node.name,
            docstring=docstring,
            fields=fields,
            is_frozen=is_frozen,
            has_properties=has_properties
        )

    def _parse_field(self, node: ast.AnnAssign) -> Optional[FieldInfo]:
        """Parse a field definition."""
        field_name = node.target.id

        # Skip if not a schema field (like model_config)
        if field_name == 'model_config':
            return None

        # Get type hint
        type_hint = ast.unparse(node.annotation)

        # Parse Field() call if present
        description = ""
        default = None
        constraints = {}

        if node.value and isinstance(node.value, ast.Call):
            # Check if it's a Field() call
            if isinstance(node.value.func, ast.Name) and node.value.func.id == 'Field':
                # Parse arguments
                for keyword in node.value.keywords:
                    if keyword.arg == 'description':
                        if isinstance(keyword.value, ast.Constant):
                            description = keyword.value.value
                    elif keyword.arg in ('ge', 'le', 'min_length', 'max_length'):
                        constraints[keyword.arg] = ast.unparse(keyword.value)
                    elif keyword.arg == 'default_factory':
                        default = 'default_factory'

                # Check for default value (first positional arg)
                if node.value.args:
                    first_arg = ast.unparse(node.value.args[0])
                    if first_arg != '...':
                        default = first_arg

        return FieldInfo(
            name=field_name,
            type_hint=type_hint,
            description=description,
            default=default,
            constraints=constraints
        )


class PHPGenerator:
    """Generate PHP class code from schema information."""

    def __init__(self, schemas: List[SchemaInfo]):
        self.schemas = schemas
        self.schema_map = {s.name: s for s in schemas}

    def generate_class(self, schema: SchemaInfo) -> str:
        """Generate PHP class code for a schema."""
        # Build class definition
        lines = [
            "<?php",
            "",
            "/*",
            " * ===============================================================================",
            " * WARNING: AUTO-GENERATED FILE - DO NOT EDIT MANUALLY!",
            " * ===============================================================================",
            " * ",
            " * This file is automatically generated from Python schemas in:",
            " * respectify-python/respectify/schemas.py",
            " * ",
            " * To make changes:",
            " * 1. Edit the Python schema file",
            " * 2. Run: python schema_generator.py",
            " * 3. All PHP classes and documentation will be regenerated",
            " * ",
            " * Any manual edits to this file WILL BE OVERWRITTEN!",
            " * ===============================================================================",
            " */",
            "",
            "namespace Respectify\\Schemas;",
            "",
            "/**",
            f" * {schema.docstring}",
            " */",
            f"class {schema.name} {{",
        ]

        # Add properties
        for field in schema.fields:
            lines.append("")
            lines.append("    /**")
            lines.append(f"     * {field.description}")

            # Add type constraints as documentation
            if field.constraints:
                constraint_doc = ", ".join(f"{k}={v}" for k, v in field.constraints.items())
                lines.append(f"     * Constraints: {constraint_doc}")

            lines.append("     */")
            lines.append(f"    public {field.php_type} ${field.php_name};")

        # Add constructor
        lines.append("")
        lines.append("    /**")
        lines.append(f"     * {schema.name} constructor.")
        lines.append("     * @param array $data The JSON data from the API")
        lines.append("     */")
        lines.append("    public function __construct(array $data) {")

        for field in schema.fields:
            # Determine how to parse this field
            if field.php_type == 'array':
                # Check if it's an array of objects
                if 'List[' in field.type_hint:
                    # Extract the type inside List[]
                    inner_type = re.search(r'List\[(\w+)\]', field.type_hint)
                    if inner_type:
                        inner_class = inner_type.group(1)
                        # Check if this is a known schema class
                        if inner_class in self.schema_map:
                            lines.append(f"        $this->{field.php_name} = array_map(fn($item) => new {inner_class}($item), $data['{field.json_name}'] ?? []);")
                        else:
                            # Plain array
                            lines.append(f"        $this->{field.php_name} = $data['{field.json_name}'] ?? [];")
                else:
                    lines.append(f"        $this->{field.php_name} = $data['{field.json_name}'] ?? [];")
            elif field.php_type in ('int', 'float', 'bool', 'string'):
                # Scalar types
                if field.php_type == 'bool':
                    default = 'false'
                elif field.php_type in ('int', 'float'):
                    default = '0' if field.php_type == 'int' else '0.0'
                    # Add type casting for float
                    if field.php_type == 'float':
                        lines.append(f"        $this->{field.php_name} = floatval($data['{field.json_name}'] ?? {default});")
                        continue
                else:
                    default = "''"
                lines.append(f"        $this->{field.php_name} = $data['{field.json_name}'] ?? {default};")
            elif 'Optional[' in field.type_hint:
                # Optional nested object
                inner_type = re.search(r'Optional\[(\w+)\]', field.type_hint)
                if inner_type:
                    inner_class = inner_type.group(1)
                    if inner_class in self.schema_map:
                        lines.append(f"        $this->{field.php_name} = isset($data['{field.json_name}']) ? new {inner_class}($data['{field.json_name}']) : null;")
                    else:
                        lines.append(f"        $this->{field.php_name} = $data['{field.json_name}'] ?? null;")
            else:
                # Required nested object
                if field.php_type in self.schema_map:
                    lines.append(f"        $this->{field.php_name} = new {field.php_type}($data['{field.json_name}']);")
                else:
                    lines.append(f"        $this->{field.php_name} = $data['{field.json_name}'];")

        lines.append("    }")
        lines.append("}")
        lines.append("")

        return "\n".join(lines)


class MarkdownGenerator:
    """Generate markdown documentation from schema information."""

    def __init__(self, schemas: List[SchemaInfo]):
        self.schemas = schemas
        self.schema_map = {s.name: s for s in schemas}

    def generate_doc(self, schema: SchemaInfo) -> str:
        """Generate markdown documentation for a schema."""
        lines = [
            "---",
            "sidebar_position: 1",
            "---",
            "",
            f"# {schema.name}",
            "",
            schema.docstring,
            "",
            ":::danger[AUTO-GENERATED - DO NOT EDIT]",
            "This documentation is automatically generated from `respectify-python/respectify/schemas.py`.",
            "",
            "To make changes, edit the Python schema file and run `python schema_generator.py`.",
            ":::",
            "",
            "## Fields",
            "",
        ]

        for field in schema.fields:
            # Field heading
            lines.append(f"### {field.name}")
            lines.append("")

            # Description
            lines.append(field.description)
            lines.append("")

            # Type information
            lines.append(f"**Type:** {self._format_type(field)}")
            lines.append("")

            # Constraints
            if field.constraints:
                constraint_str = ", ".join(f"{k}={v}" for k, v in field.constraints.items())
                lines.append(f"**Constraints:** {constraint_str}")
                lines.append("")

            # Language-specific access
            lines.append("import Tabs from '@theme/Tabs';")
            lines.append("import TabItem from '@theme/TabItem';")
            lines.append("")
            lines.append('<Tabs groupId="language">')
            lines.append('  <TabItem value="python" label="Python">')
            lines.append("")
            lines.append(f"`result.{field.name}`")
            lines.append("")
            lines.append("  </TabItem>")
            lines.append('  <TabItem value="php" label="PHP">')
            lines.append("")
            lines.append(f"`$result->{field.php_name}`")
            lines.append("")
            lines.append("  </TabItem>")
            lines.append('  <TabItem value="rest" label="JSON">')
            lines.append("")
            lines.append(f'`"{field.json_name}"`')
            lines.append("")
            lines.append("  </TabItem>")
            lines.append("</Tabs>")
            lines.append("")

        return "\n".join(lines)

    def _format_type(self, field: FieldInfo) -> str:
        """Format type information for display."""
        type_str = field.type_hint

        # Make it more readable
        type_str = type_str.replace('Optional[', '').replace(']', ' (optional)')

        # Add constraint hints
        if 'ge' in field.constraints and 'le' in field.constraints:
            type_str += f" ({field.constraints['ge']}-{field.constraints['le']})"

        return type_str


def main():
    """Main entry point."""
    # Paths
    script_dir = Path(__file__).parent
    schema_file = script_dir / 'respectify' / 'schemas.py'
    php_output_dir = script_dir.parent / 'respectify-php' / 'src' / 'Schemas'
    docs_output_dir = script_dir.parent / 'discussion-arena-docgen' / 'respectify-docs' / 'docs' / 'reference' / 'schemas'

    print(f"Parsing schemas from: {schema_file}")

    # Parse schemas
    parser = SchemaParser(schema_file)
    schemas = parser.parse_schemas()

    print(f"Found {len(schemas)} schemas")

    # Filter to only the main result schemas we want to document
    doc_schemas = [
        'CommentScore', 'SpamDetectionResult', 'CommentRelevanceResult',
        'DogwhistleResult', 'MegaCallResult', 'InitTopicResponse'
    ]

    # Generate PHP classes
    php_output_dir.mkdir(parents=True, exist_ok=True)
    php_gen = PHPGenerator(schemas)

    for schema in schemas:
        php_code = php_gen.generate_class(schema)
        output_file = php_output_dir / f"{schema.name}.php"

        with open(output_file, 'w') as f:
            f.write(php_code)

        print(f"Generated PHP: {output_file}")

    # Generate markdown docs (only for main schemas)
    docs_output_dir.mkdir(parents=True, exist_ok=True)
    md_gen = MarkdownGenerator(schemas)

    for schema in schemas:
        if schema.name in doc_schemas:
            md_content = md_gen.generate_doc(schema)
            output_file = docs_output_dir / f"{schema.name}.md"

            with open(output_file, 'w') as f:
                f.write(md_content)

            print(f"Generated docs: {output_file}")

    print("\nDone! Remember to:")
    print("1. Review generated PHP classes")
    print("2. Run PHP tests to verify")
    print("3. Rebuild documentation: cd respectify-docs && npm run build")


if __name__ == '__main__':
    main()
