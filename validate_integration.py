#!/usr/bin/env python3
"""Validation script for the Multizone Heater integration."""
import json
import os
import sys
from pathlib import Path


def validate_integration():
    """Validate the integration structure and files."""
    print("Validating Multizone Heater integration...")
    
    base_dir = Path(__file__).parent / "custom_components" / "multizone_heater"
    
    # Check required files exist
    required_files = [
        "__init__.py",
        "manifest.json",
        "const.py",
        "config_flow.py",
        "strings.json",
        "translations/en.json",
    ]
    
    missing_files = []
    for file in required_files:
        file_path = base_dir / file
        if not file_path.exists():
            missing_files.append(file)
            print(f"❌ Missing file: {file}")
        else:
            print(f"✓ Found file: {file}")
    
    if missing_files:
        print(f"\n❌ Validation failed: {len(missing_files)} missing files")
        return False
    
    # Validate manifest.json
    print("\nValidating manifest.json...")
    manifest_path = base_dir / "manifest.json"
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        required_keys = ["domain", "name", "version", "documentation", "codeowners", "config_flow"]
        missing_keys = [key for key in required_keys if key not in manifest]
        
        if missing_keys:
            print(f"❌ Manifest missing keys: {missing_keys}")
            return False
        
        if manifest["domain"] != "multizone_heater":
            print(f"❌ Invalid domain in manifest: {manifest['domain']}")
            return False
        
        if not manifest["config_flow"]:
            print("❌ config_flow must be true")
            return False
        
        print("✓ Manifest is valid")
    except Exception as e:
        print(f"❌ Error validating manifest: {e}")
        return False
    
    # Validate strings.json
    print("\nValidating strings.json...")
    strings_path = base_dir / "strings.json"
    try:
        with open(strings_path) as f:
            strings = json.load(f)
        
        if "config" not in strings:
            print("❌ strings.json missing 'config' section")
            return False
        
        print("✓ Strings file is valid")
    except Exception as e:
        print(f"❌ Error validating strings: {e}")
        return False
    
    # Check Python files can be imported (syntax check)
    print("\nChecking Python syntax...")
    python_files = ["__init__.py", "const.py", "config_flow.py", "sensor.py", "coordinator.py", "core.py"]
    
    for py_file in python_files:
        file_path = base_dir / py_file
        try:
            with open(file_path) as f:
                compile(f.read(), py_file, "exec")
            print(f"✓ {py_file} syntax is valid")
        except SyntaxError as e:
            print(f"❌ Syntax error in {py_file}: {e}")
            return False
    
    print("\n✅ All validation checks passed!")
    print("\nIntegration features:")
    print("  • Async valve control for high performance")
    print("  • Multiple zone support with individual sensors and valves")
    print("  • Temperature aggregation (average, min, max)")
    print("  • Safety features (minimum valves open)")
    print("  • UI-based configuration flow")
    print("  • Optional main climate entity integration")
    
    return True


if __name__ == "__main__":
    if validate_integration():
        sys.exit(0)
    else:
        sys.exit(1)
