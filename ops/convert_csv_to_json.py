#!/usr/bin/env python3
"""CSV to JSON Converter for NFA Batch Processing
Converts CSV file with LOJA, Texto, CPF format to JSON format expected by nfa_batch_processor.py
"""

import json
import re
import sys
from pathlib import Path


def fix_cpf(cpf: str) -> str:
    """Fix malformed CPF values.

    Handles:
    - Removes spaces
    - Fixes pattern XXX.XXX.XXX.XX -> XXX.XXX.XXX-XX (point before last 2 digits)
    - Fixes pattern XXX.XXX.XXX- XX -> XXX.XXX.XXX-XX (space after hyphen)

    Args:
        cpf: CPF string that may have formatting issues

    Returns:
        CPF string in correct format XXX.XXX.XXX-XX
    """
    # Remove all spaces
    cpf = cpf.strip().replace(" ", "")

    # Fix pattern: XXX.XXX.XXX.XX -> XXX.XXX.XXX-XX
    # Example: "008.772.790.04" -> "008.772.790-04"
    # Example: "113.684.248.99" -> "113.684.248-99"
    cpf = re.sub(r"(\d{3}\.\d{3}\.\d{3})\.(\d{2})", r"\1-\2", cpf)

    # Fix pattern: XXX.XXX.XXX- XX -> XXX.XXX.XXX-XX
    # Example: "228.953.718- 73" -> "228.953.718-73"
    cpf = re.sub(r"(\d{3}\.\d{3}\.\d{3})-(\d{2})", r"\1-\2", cpf)

    return cpf


def convert_csv_to_json(csv_path: str, output_path: str) -> int:
    """Convert CSV file to JSON format for NFA batch processing.

    Args:
        csv_path: Path to input CSV file
        output_path: Path to output JSON file

    Returns:
        Number of items converted
    """
    items = []

    # Read CSV file
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"❌ Error: CSV file not found: {csv_path}", file=sys.stderr)
        return 0

    with open(csv_file, encoding="utf-8") as f:
        lines = f.readlines()

    # Skip header row (line 1)
    data_lines = lines[1:] if len(lines) > 1 else []

    for line_num, line in enumerate(
        data_lines, start=2
    ):  # Start at 2 because we skipped header
        line = line.strip()
        if not line:
            continue

        # Split by comma
        parts = line.split(",")
        if len(parts) < 3:
            print(
                f"⚠️  Warning: Line {line_num} has less than 3 columns, skipping",
                file=sys.stderr,
            )
            continue

        loja = parts[0].strip()
        texto = parts[1].strip()
        cpf_raw = parts[2].strip()

        # Fix CPF formatting
        cpf = fix_cpf(cpf_raw)

        # Build JSON object
        item = {"loja": f"{loja}- {texto}", "cpf": cpf, "test": texto}

        items.append(item)

    # Write JSON file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    return len(items)


def validate_json(json_path: str) -> tuple[bool, int, list[str]]:
    """Validate the generated JSON file.

    Args:
        json_path: Path to JSON file

    Returns:
        Tuple of (is_valid, item_count, list_of_errors)
    """
    errors = []
    json_file = Path(json_path)

    if not json_file.exists():
        return False, 0, [f"JSON file not found: {json_path}"]

    try:
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, 0, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, 0, [f"Error reading JSON: {e}"]

    if not isinstance(data, list):
        return False, 0, ["JSON root must be an array"]

    item_count = len(data)

    # Validate each item
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"Item {i+1} is not an object")
            continue

        # Check required fields
        required_fields = ["loja", "cpf"]
        for field in required_fields:
            if field not in item:
                errors.append(f"Item {i+1} missing required field: {field}")

        # Validate CPF format (basic check: XXX.XXX.XXX-XX)
        if "cpf" in item:
            cpf = item["cpf"]
            if not re.match(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$", cpf):
                errors.append(f"Item {i+1} has invalid CPF format: {cpf}")

    is_valid = len(errors) == 0
    return is_valid, item_count, errors


def main():
    """Main entry point."""
    # Default paths
    project_root = Path(__file__).parent.parent
    csv_path = "/Volumes/MICRO/downloads_MICRO/227_CPF.csv"
    output_path = project_root / "data_input_final"

    # Allow command line arguments to override defaults
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])

    print("Converting CSV to JSON...")
    print(f"  Input:  {csv_path}")
    print(f"  Output: {output_path}")
    print()

    # Convert
    count = convert_csv_to_json(csv_path, str(output_path))

    if count == 0:
        print("❌ Conversion failed or no items found", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Converted {count} items to JSON")
    print(f"✓ Saved to {output_path}")
    print()

    # Validate
    print("Validating JSON...")
    is_valid, item_count, errors = validate_json(str(output_path))

    if is_valid:
        print(f"✓ JSON válido - {item_count} itens confirmados")
        print("✓ All CPFs are properly formatted")
        sys.exit(0)
    else:
        print("❌ Validation failed:")
        print(f"  Items found: {item_count}")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
