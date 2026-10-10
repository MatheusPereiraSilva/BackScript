# Builtin standard library

Builtins are linked through the C runtime; no imports are required. In this table,
`a`, `b`, `value`, `text`, and `path` represent previously evaluated operands.

| Syntax | Result / behavior |
| --- | --- |
| `a b add` | Numeric sum, or concatenation if either is a string |
| `a b subtract`, `multiply`, `divide`, `mod` | Numeric arithmetic |
| `a b equal`, `not_equal` | Scalar equality or collection identity |
| `a b greater`, `less`, `greater_equal`, `less_equal` | Numeric comparison |
| `a b and`, `or`; `value not` | Eager boolean operations |
| `value abs`, `floor`, `ceil`, `round` | Numeric unary operation; round halfway away from zero |
| `a b min`, `max`, `power` | Numeric binary operation |
| `value sqrt` | Square root; negative operand fails |
| `values... array` | New array from all pending operands (including empty) |
| `array index get` | Element at zero-based integer index |
| `array index value setat` | Mutates array and returns it |
| `array value push` | Appends value, mutates and returns array |
| `array pop` | Removes and returns final element |
| `collection length` | Array items, string bytes, or object keys |
| `key value ... count object` | New object from literal count of string-key pairs |
| `object key property` | Value at key; missing key fails |
| `object key value set_property` | Adds/replaces key, returns object |
| `object key has_property` | Boolean membership |
| `object keys_length` | Number of distinct keys |
| `text start count substring` | Byte slice with strict bounds; count is length |
| `text query contains` | Boolean substring match |
| `text prefix starts_with` | Boolean prefix match |
| `text suffix ends_with` | Boolean suffix match |
| `text uppercase`, `lowercase` | ASCII case conversion; creates string |
| `text trim` | Removes leading/trailing ASCII whitespace |
| `value string` | Converts number, boolean, null, or string to text |
| `path read_file` | Reads entire text file; rejects NUL bytes |
| `content path write_file` | Creates/truncates file; consumes both operands |
| `content path append_file` | Creates/appends file; consumes both operands |
| `path file_exists` | True for existing regular file; false for absent/nonregular path |
| `value print` | Prints value and newline; consumes operand |

Arrays and objects share storage on assignment and function calls. Mutating one
alias updates the others. Standalone mutation lines may discard their result.
Objects preserve insertion order for printing; replacing a key does not move it.
Arrays print `[1, 2]`, objects print `{name: Matheus}`. Printing recursive structures
stops after 32 nesting levels and emits `...`.

Numbers use C `double`. Nonfinite numeric literals are compile errors. Runtime
arithmetic follows floating-point behavior; domain-invalid square roots and
nonfinite power results fail. Scalar conversion/printing uses 15 significant
digits and is not a lossless numeric serialization API.

Strings and collection storage live until process exit. File operations are
synchronous and report operation, path, and system error on failure. Writes are
direct and non-atomic. No parent directories are created. File paths use the
current working directory. Empty files are valid. Runtime errors print to stderr
and exit with status 1; v1.0 has no exception recovery.
