# TRON Python

Token Reduced Object Notation (TRON) - A serialization format optimized for LLM token efficiency.

## Installation

```bash
pip install tron-format
```

## Usage

```python
from tron import TRON

# Stringify Python objects to TRON format
data = [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
tron_str = TRON.stringify(data)
# Output:
# class A: x,y
#
# [A(1,2),A(3,4)]

# Parse TRON back to Python objects
parsed = TRON.parse(tron_str)
# [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
```

## Features

- Automatic schema detection for repeated object structures
- Class definitions reduce token count for LLM contexts
- Full round-trip support (stringify → parse preserves data)
- Compatible with JavaScript TRON implementation

## License

MIT
# tron
