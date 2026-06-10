"""Stringify (encoder) for TRON format."""

import json
import math
import re
from dataclasses import dataclass
from typing import Any

# Pattern for valid identifiers
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@dataclass
class ClassDef:
    """Internal class definition for stringify."""

    name: str
    keys: list[str]


def _generate_class_name(index: int) -> str:
    """
    Generate a class name for the given index.

    Index 0-25: A-Z
    Index 26-51: A1-Z1
    Index 52-77: A2-Z2
    etc.
    """
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    cycle = index // 26
    position = index % 26

    if cycle == 0:
        return letters[position]
    else:
        return letters[position] + str(cycle)


def stringify(value: Any) -> str:
    """
    Convert a Python object to TRON format.

    Args:
        value: The Python object to serialize.

    Returns:
        The TRON string representation.

    Raises:
        TypeError: If the value contains circular references or unsupported types.
    """
    if value is None:
        return "null"

    # 1. DFS to discover classes (outer objects are defined before inner objects)
    classes: list[ClassDef] = []
    schema_to_class: dict[str, ClassDef] = {}
    schema_counts: dict[str, int] = {}
    class_counter = 0

    visited: set[int] = set()

    def dfs_discover(current: Any) -> None:
        nonlocal class_counter

        if current is None:
            return

        # Check for bool BEFORE int (bool is subclass of int in Python)
        if isinstance(current, bool):
            return

        if not isinstance(current, (dict, list)):
            return

        # Use id() for visited check (handles mutable objects)
        obj_id = id(current)
        if obj_id in visited:
            return
        visited.add(obj_id)

        if isinstance(current, list):
            for item in current:
                dfs_discover(item)
        else:
            # Plain dict
            keys = [k for k in current if current[k] is not None]
            if keys:
                # Use sorted keys for signature to ensure consistent schema
                sorted_keys = sorted(keys)
                schema_signature = ",".join(sorted_keys)

                # Track occurrence count
                schema_counts[schema_signature] = schema_counts.get(schema_signature, 0) + 1

                if schema_signature not in schema_to_class:
                    class_name = _generate_class_name(class_counter)
                    class_counter += 1
                    # Use original keys order from first occurrence
                    class_def = ClassDef(name=class_name, keys=list(keys))
                    classes.append(class_def)
                    schema_to_class[schema_signature] = class_def

                # Recursively visit children (DFS)
                for key in keys:
                    dfs_discover(current[key])

    dfs_discover(value)

    # Filter classes based on property count and occurrence:
    # - 1 property or 1 occurrence: never define class (use JSON)
    # - 2+ properties and 2+ occurrences: define class
    filtered_schema_to_class: dict[str, ClassDef] = {}
    filtered_classes: list[ClassDef] = []
    filtered_class_counter = 0

    for schema_signature, class_def in schema_to_class.items():
        property_count = len(class_def.keys)
        occurrence_count = schema_counts.get(schema_signature, 0)

        should_define_class = property_count > 1 and occurrence_count > 1
        if should_define_class:
            # Reassign class names sequentially for filtered classes
            new_class_name = _generate_class_name(filtered_class_counter)
            filtered_class_counter += 1
            new_class_def = ClassDef(name=new_class_name, keys=class_def.keys)
            filtered_schema_to_class[schema_signature] = new_class_def
            filtered_classes.append(new_class_def)

    # 2. Generate Header
    output = ""
    for cls in filtered_classes:
        # "class ClassName: prop1,prop2"
        keys_str = []
        for key in cls.keys:
            if IDENTIFIER_PATTERN.match(key):
                keys_str.append(key)
            else:
                keys_str.append(json.dumps(key))
        output += f"class {cls.name}: {','.join(keys_str)}\n"

    if output:
        output += "\n"

    # 3. Generate Data
    output += _serialize(value, filtered_schema_to_class, set())

    return output


def _serialize(value: Any, schema_to_class: dict[str, ClassDef], stack: set[int]) -> str:
    """Serialize a value to TRON format."""
    if value is None:
        return "null"

    # Check bool BEFORE int (bool is subclass of int in Python)
    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, str):
        return json.dumps(value)

    if isinstance(value, (int, float)):
        # Handle special float values
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return "null"
        return str(value)

    if isinstance(value, list):
        obj_id = id(value)
        if obj_id in stack:
            raise TypeError("Converting circular structure to TRON")
        stack.add(obj_id)
        try:
            items = [_serialize(v, schema_to_class, stack) for v in value]
            return f"[{','.join(items)}]"
        finally:
            stack.discard(obj_id)

    if isinstance(value, dict):
        obj_id = id(value)
        if obj_id in stack:
            raise TypeError("Converting circular structure to TRON")
        stack.add(obj_id)

        try:
            keys = [k for k in value if value[k] is not None]
            if not keys:
                return "{}"

            sorted_keys = sorted(keys)
            schema_signature = ",".join(sorted_keys)
            class_def = schema_to_class.get(schema_signature)

            if class_def:
                # Use class instantiation
                args = [_serialize(value[key], schema_to_class, stack) for key in class_def.keys]
                return f"{class_def.name}({','.join(args)})"
            else:
                # Use JSON object syntax
                pairs = []
                for key in keys:
                    key_str = json.dumps(key)
                    val_str = _serialize(value[key], schema_to_class, stack)
                    pairs.append(f"{key_str}:{val_str}")
                return "{" + ",".join(pairs) + "}"
        finally:
            stack.discard(obj_id)

    raise TypeError(f"Unsupported type: {type(value).__name__}")


# Export for unit testing
exported_for_unit_testing = {
    "generate_class_name": _generate_class_name,
}
