"""
Sphinx documentation build script for Python API reference generation.

This generates comprehensive API reference documentation from Python source code
and copies it to the main documentation site under /reference/api/python/.

This complements the feature-centric docs which explain concepts with examples.
"""

import subprocess
import shutil
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
    """Copy generated docs to the Docusaurus API reference folder."""
    try:
        print("Copying Python docs to API reference folder...")

        src_folder = Path(__file__).parent / "docs" / "_build" / "html"
        dest_folder = Path(__file__).parent.parent / "discussion-arena-docgen" / "respectify-docs" / "docs" / "reference" / "api" / "python"

        if not src_folder.exists():
            print(f"❌ Error: Source folder does not exist: {src_folder}")
            return False

        dest_folder_full_path = dest_folder.resolve()
        print(f"📁 Copying to: {dest_folder_full_path}")

        # Remove existing Python docs
        if dest_folder.exists():
            shutil.rmtree(dest_folder)
            print("🧹 Removed existing Python API docs")

        # Create destination directory
        dest_folder.mkdir(parents=True, exist_ok=True)

        # Copy all generated HTML files
        shutil.copytree(src_folder, dest_folder / "html", dirs_exist_ok=True)

        # Create a main index.md for Docusaurus navigation
        index_content = """---
sidebar_position: 1
---

# Python API Reference

Complete API reference for the Respectify Python library, auto-generated from source code.

## Browse API Documentation

- [**Full API Documentation**](./html/index.html) - Complete documentation with all modules
- [**Client Classes**](./html/api/clients.html) - RespectifyClient and RespectifyClientAsync
- [**Schemas**](./html/api/schemas.html) - All response and request models
- [**Exceptions**](./html/api/exceptions.html) - Error types and handling

## Quick Links

For feature-focused documentation with examples, see:
- [Getting Started](/docs/getting-started/installation)
- [Features](/docs/features/spam-detection)
- [Schema Reference](/docs/reference/schemas/) (field-by-field with language tabs)
"""

        (dest_folder / "index.md").write_text(index_content)

        print("✅ Python API reference docs copied successfully.")
        return True

    except Exception as e:
        print(f"❌ Error copying docs: {e}")
        return False


def main():
    """Main build function."""
    print("🔨 Building Python API Reference Documentation")
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
    print("✅ Build completed successfully!")
    print()
    print("API reference available at: /docs/reference/api/python/")


if __name__ == "__main__":
    main()