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

    # Sub-types that should be documented inline with their parent
    INLINE_SUBTYPES = {
        'CommentScore': ['LogicalFallacy', 'ObjectionablePhrase', 'NegativeTonePhrase'],
        'CommentRelevanceResult': ['OnTopicResult', 'BannedTopicsResult'],
        'DogwhistleResult': ['DogwhistleDetection', 'DogwhistleDetails'],
    }

    # Main schemas that have their own documentation pages
    MAIN_SCHEMAS = [
        'CommentScore', 'SpamDetectionResult', 'CommentRelevanceResult',
        'DogwhistleResult', 'MegaCallResult', 'InitTopicResponse'
    ]

    def __init__(self, schemas: List[SchemaInfo]):
        self.schemas = schemas
        self.schema_map = {s.name: s for s in schemas}
        # Build reverse map: which parent has which inline subtypes
        self.subtype_parent = {}
        for parent, subtypes in self.INLINE_SUBTYPES.items():
            for subtype in subtypes:
                self.subtype_parent[subtype] = parent

    def generate_doc(self, schema: SchemaInfo, sidebar_position: int = 1) -> str:
        """Generate markdown documentation for a schema."""
        lines = [
            "---",
            f"sidebar_position: {sidebar_position}",
            "---",
            "",
            "import Tabs from '@theme/Tabs';",
            "import TabItem from '@theme/TabItem';",
            "",
            f"# {schema.name}",
            "",
            schema.docstring,
            "",
            "## Fields",
            "",
        ]

        # Collect all types needed for imports
        python_imports = {schema.name}
        php_imports = {schema.name}

        for field in schema.fields:
            inner_type = self._get_inner_type(field.type_hint)
            if inner_type and inner_type in self.schema_map:
                python_imports.add(inner_type)
                php_imports.add(inner_type)

        # Add import info at the top
        lines.insert(len(lines) - 2, self._generate_imports_section(schema.name, python_imports, php_imports))
        lines.insert(len(lines) - 2, "")

        for field in schema.fields:
            lines.extend(self._generate_field_doc(field, schema.name))

        # Add inline sub-type documentation
        if schema.name in self.INLINE_SUBTYPES:
            lines.append("## Sub-types")
            lines.append("")
            for subtype_name in self.INLINE_SUBTYPES[schema.name]:
                if subtype_name in self.schema_map:
                    subtype = self.schema_map[subtype_name]
                    lines.extend(self._generate_subtype_doc(subtype))

        return "\n".join(lines)

    def _generate_imports_section(self, schema_name: str, python_imports: set, php_imports: set) -> str:
        """Generate the imports section showing how to import in each language."""
        python_import_list = ', '.join(sorted(python_imports))
        php_use_statements = '\n'.join(f"use Respectify\\Schemas\\{name};" for name in sorted(php_imports))

        return f"""<Tabs groupId="language">
<TabItem value="python" label="Python">

```python
from respectify.schemas import {python_import_list}
```

</TabItem>
<TabItem value="php" label="PHP">

```php
{php_use_statements}
```

</TabItem>
<TabItem value="rest" label="JSON">

Types are returned as JSON objects in API responses.

</TabItem>
</Tabs>"""

    def _generate_field_doc(self, field: FieldInfo, current_schema: str = "") -> List[str]:
        """Generate documentation for a single field."""
        lines = []

        # Field heading
        lines.append(f"### {field.name}")
        lines.append("")

        # Description
        lines.append(field.description)
        lines.append("")

        # Constraints (if any)
        if field.constraints:
            constraint_str = ", ".join(f"{k}={v}" for k, v in field.constraints.items())
            lines.append(f"**Constraints:** {constraint_str}")
            lines.append("")

        # Type and access per language
        py_display = self._format_python_field_display(field, current_schema)
        php_display = self._format_php_field_display(field, current_schema)
        json_display = self._format_json_field_display(field, current_schema)

        lines.append('<Tabs groupId="language">')
        lines.append('<TabItem value="python" label="Python">')
        lines.append("")
        lines.append(py_display)
        lines.append("")
        lines.append("</TabItem>")
        lines.append('<TabItem value="php" label="PHP">')
        lines.append("")
        lines.append(php_display)
        lines.append("")
        lines.append("</TabItem>")
        lines.append('<TabItem value="rest" label="JSON">')
        lines.append("")
        lines.append(json_display)
        lines.append("")
        lines.append("</TabItem>")
        lines.append("</Tabs>")
        lines.append("")

        return lines

    def _generate_subtype_doc(self, schema: SchemaInfo) -> List[str]:
        """Generate inline documentation for a sub-type with Python/PHP/JSON tabs."""
        lines = []
        lines.append(f"### {schema.name}")
        lines.append("")
        lines.append(schema.docstring)
        lines.append("")
        lines.append('<Tabs groupId="language">')
        lines.append('<TabItem value="python" label="Python">')
        lines.append("")
        lines.append("| Field | Type | Description |")
        lines.append("|-------|------|-------------|")
        for field in schema.fields:
            py_type = self._format_python_type(field)
            lines.append(f"| `{field.name}` | `{py_type}` | {field.description} |")
        lines.append("")
        lines.append("</TabItem>")
        lines.append('<TabItem value="php" label="PHP">')
        lines.append("")
        lines.append("| Field | Type | Description |")
        lines.append("|-------|------|-------------|")
        for field in schema.fields:
            php_type = self._format_php_type(field)
            lines.append(f"| `{field.php_name}` | `{php_type}` | {field.description} |")
        lines.append("")
        lines.append("</TabItem>")
        lines.append('<TabItem value="rest" label="JSON">')
        lines.append("")
        lines.append("```json")
        lines.append("{")
        field_lines = []
        for field in schema.fields:
            json_example = self._get_json_example_value(field)
            field_lines.append(f'  "{field.name}": {json_example}')
        lines.append(",\n".join(field_lines))
        lines.append("}")
        lines.append("```")
        lines.append("")
        lines.append("</TabItem>")
        lines.append("</Tabs>")
        lines.append("")

        return lines

    def _get_json_example_value(self, field: FieldInfo) -> str:
        """Get an example JSON value for a field (for sub-type documentation)."""
        type_hint = field.type_hint

        # Handle List[X]
        if 'List[' in type_hint:
            inner = self._get_inner_type(type_hint)
            if inner == 'str':
                return '["...", "..."]'
            elif inner == 'int':
                return '[1, 2]'
            elif inner == 'float':
                return '[0.5, 0.8]'
            return '[]'

        # Handle Optional[X]
        if 'Optional[' in type_hint:
            inner = self._get_inner_type(type_hint)
            # Return example of the inner type (not null)
            return self._get_json_example(inner or 'str')

        return self._get_json_example(type_hint)

    def _format_json_type(self, field: FieldInfo) -> str:
        """Format type for JSON schema display."""
        type_hint = field.type_hint

        # Map Python types to JSON types
        type_map = {
            'str': 'string',
            'int': 'integer',
            'float': 'number',
            'bool': 'boolean',
        }

        # Handle List[X]
        if 'List[' in type_hint:
            inner = self._get_inner_type(type_hint)
            if inner:
                inner_json = type_map.get(inner, inner)
                return f"array[{inner_json}]"
            return "array"

        # Handle Optional[X]
        if 'Optional[' in type_hint:
            inner = self._get_inner_type(type_hint)
            if inner:
                inner_json = type_map.get(inner, inner)
                return f"{inner_json} | null"
            return "null"

        return type_map.get(type_hint, type_hint)

    def _get_inner_type(self, type_hint: str) -> Optional[str]:
        """Extract the inner type from List[X] or Optional[X]."""
        import re
        match = re.search(r'(?:List|Optional)\[(\w+)\]', type_hint)
        return match.group(1) if match else None

    def _format_python_type(self, field: FieldInfo) -> str:
        """Format type for Python display."""
        type_str = field.type_hint

        # Add range info for constrained numbers
        if 'ge' in field.constraints and 'le' in field.constraints:
            base_type = type_str.replace('Optional[', '').replace(']', '')
            return f"{base_type}  # {field.constraints['ge']}-{field.constraints['le']}"

        return type_str

    def _format_php_type(self, field: FieldInfo) -> str:
        """Format type for PHP display."""
        type_hint = field.type_hint

        # Handle List[X] -> X[]
        if 'List[' in type_hint:
            inner = self._get_inner_type(type_hint)
            if inner:
                return f"{inner}[]"
            return "array"

        # Handle Optional[X] -> ?X
        if 'Optional[' in type_hint:
            inner = self._get_inner_type(type_hint)
            if inner:
                # Map Python types to PHP
                type_map = {'str': 'string', 'int': 'int', 'float': 'float', 'bool': 'bool'}
                php_type = type_map.get(inner, inner)
                return f"?{php_type}"

        # Simple types
        type_map = {'str': 'string', 'int': 'int', 'float': 'float', 'bool': 'bool'}
        return type_map.get(type_hint, type_hint)

    def _get_type_link(self, type_name: str, current_schema: str) -> Optional[str]:
        """Get the appropriate link for a type reference.

        Returns:
            - Anchor link (#typename) if it's an inline subtype of current schema
            - Relative page link (./TypeName) if it's a main schema on separate page
            - None if no link needed
        """
        if type_name not in self.schema_map:
            return None

        # Check if this is an inline subtype of the current schema
        if current_schema in self.INLINE_SUBTYPES:
            if type_name in self.INLINE_SUBTYPES[current_schema]:
                return f"#{type_name.lower()}"

        # Check if this is a main schema (separate page)
        if type_name in self.MAIN_SCHEMAS:
            return f"./{type_name}"

        # Check if it's a subtype documented on another page
        if type_name in self.subtype_parent:
            parent = self.subtype_parent[type_name]
            return f"./{parent}#{type_name.lower()}"

        return None

    def _format_python_field_display(self, field: FieldInfo, current_schema: str = "") -> str:
        """Format Python field display with inline type link."""
        type_hint = field.type_hint
        inner = self._get_inner_type(type_hint)

        # Add range for constrained numbers
        if 'ge' in field.constraints and 'le' in field.constraints:
            range_comment = f"  # {field.constraints['ge']}-{field.constraints['le']}"
        else:
            range_comment = ""

        # Check if inner type needs a link (for List/Optional wrappers)
        link_target = self._get_type_link(inner, current_schema) if inner else None

        if link_target:
            # Build type with inline link for wrapped types
            # Use HTML <code> tags to ensure space is also code-formatted
            if 'List[' in type_hint:
                return f"<code>result.{field.name}: List[</code>[`{inner}`]({link_target})<code>]</code>{range_comment}"
            elif 'Optional[' in type_hint:
                return f"<code>result.{field.name}: Optional[</code>[`{inner}`]({link_target})<code>]</code>{range_comment}"

        # Check if the type itself is a schema (direct reference, not wrapped)
        direct_link = self._get_type_link(type_hint, current_schema)
        if direct_link:
            return f"<code>result.{field.name}: </code>[`{type_hint}`]({direct_link}){range_comment}"

        return f"`result.{field.name}: {type_hint}{range_comment}`"

    def _format_php_field_display(self, field: FieldInfo, current_schema: str = "") -> str:
        """Format PHP field display with inline type link."""
        type_hint = field.type_hint
        inner = self._get_inner_type(type_hint)

        # Check if inner type needs a link (for List/Optional wrappers)
        link_target = self._get_type_link(inner, current_schema) if inner else None

        if link_target:
            # Build type with inline link for wrapped types
            # Use HTML <code> tags to ensure space is also code-formatted
            if 'List[' in type_hint:
                return f"<code>$result->{field.php_name}: </code>[`{inner}`]({link_target})<code>[]</code>"
            elif 'Optional[' in type_hint:
                return f"<code>$result->{field.php_name}: ?</code>[`{inner}`]({link_target})"

        # Check if the type itself is a schema (direct reference, not wrapped)
        direct_link = self._get_type_link(type_hint, current_schema)
        if direct_link:
            return f"<code>$result->{field.php_name}: </code>[`{type_hint}`]({direct_link})"

        php_type = self._format_php_type(field)
        return f"`$result->{field.php_name}: {php_type}`"

    def _format_json_field_display(self, field: FieldInfo, current_schema: str = "") -> str:
        """Format JSON field display with full inline structure for nested types."""
        type_hint = field.type_hint
        inner = self._get_inner_type(type_hint)

        # Check if this is a nested schema type (wrapped in List/Optional)
        if inner and inner in self.schema_map:
            subtype = self.schema_map[inner]
            link_target = self._get_type_link(inner, current_schema)

            # Build inline JSON structure
            inline_obj = self._build_json_object_example(subtype)

            if 'List[' in type_hint:
                json_code = f'```json\n"{field.json_name}": [{inline_obj}, ...]\n```'
                if link_target:
                    return f"{json_code}\n\nEach element is a [`{inner}`]({link_target}) object."
                return json_code
            elif 'Optional[' in type_hint:
                json_code = f'```json\n"{field.json_name}": {inline_obj}  // or null\n```'
                if link_target:
                    return f"{json_code}\n\nThis is a [`{inner}`]({link_target}) object (or null)."
                return json_code
            else:
                json_code = f'```json\n"{field.json_name}": {inline_obj}\n```'
                if link_target:
                    return f"{json_code}\n\nThis is a [`{inner}`]({link_target}) object."
                return json_code

        # Check if the type itself is a schema (direct reference, not wrapped)
        if type_hint in self.schema_map:
            subtype = self.schema_map[type_hint]
            link_target = self._get_type_link(type_hint, current_schema)
            inline_obj = self._build_json_object_example(subtype)
            json_code = f'```json\n"{field.json_name}": {inline_obj}\n```'
            if link_target:
                return f"{json_code}\n\nThis is a [`{type_hint}`]({link_target}) object."
            return json_code

        # Simple types
        if 'List[' in type_hint:
            if inner == 'str':
                return f'```json\n"{field.json_name}": ["...", "..."]\n```'
            return f'```json\n"{field.json_name}": []\n```'
        elif 'Optional[' in type_hint:
            example = self._get_json_example(inner or 'str')
            return f'```json\n"{field.json_name}": {example}  // or null\n```'
        else:
            example = self._get_json_example(type_hint)
            return f'```json\n"{field.json_name}": {example}\n```'

    def _build_json_object_example(self, schema: SchemaInfo) -> str:
        """Build a JSON object example for a schema type."""
        json_lines = []
        for f in schema.fields:
            example = self._get_json_field_example(f)
            json_lines.append(f'  "{f.name}": {example}')
        return "{\n" + ",\n".join(json_lines) + "\n}"

    def _get_json_field_example(self, field: FieldInfo) -> str:
        """Get a JSON example value for a field, handling List[str] etc."""
        type_hint = field.type_hint

        if 'List[' in type_hint:
            inner = self._get_inner_type(type_hint)
            if inner == 'str':
                return '["...", "..."]'
            elif inner == 'int':
                return '[1, 2]'
            elif inner == 'float':
                return '[0.5, 0.8]'
            elif inner in self.schema_map:
                return f'[{inner}, ...]'
            return '[]'

        if 'Optional[' in type_hint:
            inner = self._get_inner_type(type_hint)
            if inner in self.schema_map:
                return inner
            return self._get_json_example(inner or 'str')

        # Handle direct schema references (not wrapped)
        if type_hint in self.schema_map:
            return type_hint

        return self._get_json_example(type_hint)

    def _format_json_schema_and_link(self, field: FieldInfo, current_schema: str = "") -> Tuple[str, Optional[str]]:
        """Format JSON schema representation and optional link for a field."""
        type_hint = field.type_hint
        inner = self._get_inner_type(type_hint)

        # Build JSON example based on type
        if 'List[' in type_hint:
            if inner and inner in self.schema_map:
                # Reference the type by name instead of showing confusing inline object
                json_code = f'```json\n"{field.json_name}": [{inner}, ...]\n```'
                link_target = self._get_type_link(inner, current_schema)
                if link_target:
                    if link_target.startswith('#'):
                        link = f"See [{inner}]({link_target}) below."
                    else:
                        link = f"See [{inner}]({link_target})."
                    return json_code, link
                return json_code, None
            elif inner == 'str':
                return f'```json\n"{field.json_name}": ["...", "..."]\n```', None
            else:
                return f'```json\n"{field.json_name}": []\n```', None

        elif 'Optional[' in type_hint:
            if inner and inner in self.schema_map:
                # Reference the type by name
                json_code = f'```json\n"{field.json_name}": {inner} | null\n```'
                link_target = self._get_type_link(inner, current_schema)
                if link_target:
                    if link_target.startswith('#'):
                        link = f"See [{inner}]({link_target}) below."
                    else:
                        link = f"See [{inner}]({link_target})."
                    return json_code, link
                return json_code, None
            else:
                json_type = self._get_json_example(inner or type_hint)
                return f'```json\n"{field.json_name}": {json_type}\n```', None

        else:
            json_example = self._get_json_example(type_hint)
            return f'```json\n"{field.json_name}": {json_example}\n```', None

    def _get_json_example(self, type_hint: str) -> str:
        """Get a JSON example value for a type."""
        examples = {
            'str': '"string"',
            'int': '1',
            'float': '0.5',
            'bool': 'true',
            'UUID': '"550e8400-e29b-41d4-a716-446655440000"',
        }
        return examples.get(type_hint, '{}')

    def _format_json_type(self, field: FieldInfo) -> str:
        """Format type for JSON display (legacy, kept for compatibility)."""
        type_hint = field.type_hint

        # Handle List[X]
        if 'List[' in type_hint:
            inner = self._get_inner_type(type_hint)
            if inner:
                if inner in self.schema_map:
                    return f"array of {inner} objects"
                elif inner == 'str':
                    return "array of strings"
                return f"array of {inner}"
            return "array"

        # Handle Optional[X]
        is_optional = 'Optional[' in type_hint
        clean_type = type_hint.replace('Optional[', '').replace(']', '')

        type_map = {
            'str': 'string',
            'int': 'integer',
            'float': 'number',
            'bool': 'boolean',
            'UUID': 'string (UUID format)',
        }

        json_type = type_map.get(clean_type, f"{clean_type} object")

        if is_optional:
            return f"{json_type} or null"

        return json_type


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
