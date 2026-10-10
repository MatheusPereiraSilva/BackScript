# BackScript

Programming, but backwards.

BackScript v1.0.0 is a compiled language with postfix expressions, reverse blocks,
and `.wtf` source files. The syntax is intentionally wrong. The compiler is not.

## Requirements and installation

Python 3.10+ and GCC with GNU C11 support are required on a POSIX system. There
are no Python dependencies. Clone this repository, then run the included launcher:

```sh
chmod +x backscript
./backscript version
./backscript run examples/hello.wtf
```

To use `backscript` without `./`, add the repository directory to your `PATH`.
Keep `compiler/` and `runtime/` beside the launcher; it locates them automatically.

## Quick start

```wtf
"Hello, world!" print
30 age set

end
    "Access granted" print
else
    "Access denied" print
age 18 greater_equal if

end
    i print
0 10 2 i range

end
    a b add return
a b sum function

10 20 sum call print
```

Values precede operations. Block bodies begin with `end` and appear before their
bottom declaration. Execution proceeds from top to bottom; a block condition is
checked before its body runs.

## CLI

```sh
./backscript run examples/showcase.wtf
./backscript build examples/showcase.wtf -o showcase
./showcase
./backscript emit examples/showcase.wtf -o showcase.c
./backscript check examples/showcase.wtf
./backscript fmt examples/showcase.wtf
./backscript version
python3 tests/run_tests.py
```

`check` loads imports and validates names, operand counts, scopes, and control
flow without invoking GCC. Dynamic types and bounds are checked at runtime.
`fmt` validates first and normalizes reverse block indentation in place. `emit`
produces C that includes `backscript_runtime.h`:

```sh
gcc -std=gnu11 -Wall -Wextra -I runtime showcase.c -lm -o showcase
```

`build` writes the requested executable. `run` uses an automatically removed
temporary build directory and executes in the current working directory. Source
or runtime errors return 1; argument errors return 2; GCC and executed programs
propagate their exit status.

## Language features

- Numbers (double precision), UTF-8 strings, booleans, null, variables.
- Arithmetic, comparisons, eager boolean operations, and math builtins.
- Arrays with indexing, shared mutation, push, pop, and length.
- Objects with string keys, property lookup, mutation, existence, and key count.
- String concatenation, slicing, search, case conversion, trim, scalar conversion.
- Reverse `if`/`else`, `while`, and exclusive `range` with positive or negative steps.
- `break` and `continue` in loops, including nested conditionals.
- Local functions, forward calls, recursion, and mutual recursion.
- Relative file imports, duplicate suppression, and circular import diagnostics.
- Text file read, write, append, and existence checks.

```wtf
"name" "Matheus"
"age" 30
2 object user set
user "name" property print
user "age" 31 set_property
"Back" "Script" add uppercase print
"hello" 1 3 substring print
```

Functions have isolated local scope; pass global values as arguments. Imports
share function declarations and execute imported top-level statements once at
the import position. There are no namespaces in v1.0.

## Compiler pipeline and structure

```text
.wtf -> tokenizer / module loader -> reverse block tree
     -> validation and C generation -> GCC -> native executable
```

| Path | Purpose |
| --- | --- |
| `backscript` | Portable launcher |
| `compiler/frontend.py` | Source locations, tokenization, block parsing, imports |
| `compiler/codegen.py` | Scope validation and deterministic C generation |
| `compiler/backscript.py` | CLI, formatting, temporary builds |
| `runtime/backscript_runtime.h` | Dynamic values, allocation tracking, builtins |
| `examples/` | Runnable language examples and modules |
| `tests/run_tests.py` | End-to-end tests, errors, and warning-free C checks |
| `vscode/` | VS Code language support, snippets, and BackScript Neon theme |
| `docs/` | Language, grammar, runtime, modules, compiler, and bootstrap design |

Start with [the language guide](docs/LANGUAGE.md), [grammar](docs/GRAMMAR.md),
[standard library](docs/STDLIB.md), and [modules](docs/MODULES.md).
[Compiler internals](docs/COMPILER.md) describe validation and memory ownership.

## VS Code

The extension in [vscode/](vscode/README.md) provides `.wtf` syntax highlighting,
reverse block indentation, snippets, and the optional **BackScript Neon** theme.
Open `vscode/` as a VS Code folder and press **F5** to try it in an Extension
Development Host. See the extension README for local installation and packaging.

## Limitations and roadmap

Strings use byte offsets and lengths, with ASCII case conversion. Arrays and
objects use reference identity for equality. Memory is reclaimed on process
exit, so long-running allocation-heavy programs need a future collector. File
writes are synchronous and overwrite directly. Functions cannot capture globals
or define nested functions. Runtime failures terminate the program; exceptions
and recovery are future work.

Next steps include structured runtime diagnostics, indexed object lookup,
garbage collection, compiler data APIs, and a compiler written in BackScript.
See [self-hosting preparation](docs/SELF_HOSTING.md) for staged bootstrap goals.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md). Keep the language unusual and the
implementation maintainable. Run the full suite before submitting a change.

Released under the [MIT license](LICENSE).
