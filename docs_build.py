"""
Build script for Respectify Python library documentation.

This script:
1. Generates documentation using Sphinx 
2. Copies the generated docs to the docgen folder for Docusaurus integration
3. Matches the pattern used by the PHP library build system
"""

import subprocess
import shutil
import os
import sys
from pathlib import Path


def run_sphinx():
    """Generate documentation using Sphinx."""
    try:
        print("Generating Python documentation with Sphinx...")
        
        # Change to docs directory
        docs_dir = Path(__file__).parent / "docs"
        
        # Clean previous build
        build_dir = docs_dir / "_build"
        if build_dir.exists():
            shutil.rmtree(build_dir)
            print("Cleaned previous build directory")
        
        # Generate HTML docs
        subprocess.run([
            "sphinx-build",
            "-b", "html",  # HTML builder
            "-E",          # Don't use cached environment
            str(docs_dir), # Source directory
            str(build_dir / "html")  # Output directory
        ], check=True, cwd=docs_dir.parent)
        
        print("✅ Sphinx documentation generated successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Sphinx: {e}")
        return False
    except FileNotFoundError:
        print("❌ Error: sphinx-build command not found. Install with: pip install -e \".[docs]\"")
        return False


def copy_docs():
    """Copy generated docs to the docgen folder for Docusaurus integration."""
    try:
        print("Copying Python docs to docgen folder...")
        
        src_folder = Path(__file__).parent / "docs" / "_build" / "html"
        dest_folder = Path(__file__).parent.parent / "discussion-arena-docgen" / "respectify-docs" / "docs" / "Python"
        
        if not src_folder.exists():
            print(f"❌ Error: Source folder does not exist: {src_folder}")
            return False
            
        dest_folder_full_path = dest_folder.resolve()
        print(f"📁 Destination: {dest_folder_full_path}")
        
        # Remove existing Python docs
        if dest_folder.exists():
            shutil.rmtree(dest_folder)
            print("🧹 Removed existing Python docs")
        
        # Create destination directory
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Copy all generated HTML files as static content
        # For Docusaurus integration, we need to convert HTML to markdown or create index files
        
        # For now, let's copy the HTML and create an index.md that links to it
        shutil.copytree(src_folder, dest_folder / "html", dirs_exist_ok=True)
        
        # Create a main index.md for Docusaurus
        index_content = """# Python Library Documentation

The Respectify Python library provides both synchronous and asynchronous clients for the Respectify API.

## Quick Links

- [Full Documentation](./html/index.html) - Complete documentation with examples
- [API Reference](./html/api/clients.html) - Client classes and methods
- [Examples](./html/examples/basic_usage.html) - Usage examples and patterns

## Installation

```bash
pip install respectify
```

## Quick Start

```python
from respectify import RespectifyClient

client = RespectifyClient(
    email="your-email@example.com",
    api_key="your-api-key"
)

# Initialize a topic
topic = client.init_topic_from_text("This is my article content")

# Check if a comment is spam
result = client.check_spam("Great post!", topic.article_id)
print(f"Is spam: {result.is_spam}")
```

## Features

- 🔄 **Dual Interface**: Both synchronous and asynchronous clients
- 🛡️ **Type Safety**: Full type hints with Pydantic validation  
- 📊 **Comprehensive**: All Respectify API endpoints supported
- ⚡ **Efficient**: Megacall support for batch operations
- 🚨 **Error Handling**: Custom exceptions for different API conditions

## Repository

- [GitHub Repository](https://github.com/respectify/respectify-python)
- [PyPI Package](https://pypi.org/project/respectify/)
"""
        
        (dest_folder / "index.md").write_text(index_content)
        
        print("✅ Python docs copied successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error copying docs: {e}")
        return False


def main():
    """Main build function."""
    print("🐍 Building Respectify Python Library Documentation")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not (Path(__file__).parent / "respectify").exists():
        print("❌ Error: Must run from respectify-python root directory")
        sys.exit(1)
    
    # Generate documentation
    if not run_sphinx():
        sys.exit(1)
    
    # Copy to docgen folder
    if not copy_docs():
        sys.exit(1)
        
    print("=" * 60)
    print("🎉 Build completed successfully!")
    print()
    print("Next steps:")
    print("1. cd ../discussion-arena-docgen/respectify-docs")
    print("2. npm install  # (if needed)")
    print("3. npm start    # Preview the documentation")
    print("4. npm run build # Build for production")


if __name__ == "__main__":
    main()