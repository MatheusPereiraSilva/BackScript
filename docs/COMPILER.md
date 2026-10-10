# Compiler architecture

The Stage 0 compiler uses Python 3.10+ and emits GNU C11. Its modules have explicit
boundaries to support a later BackScript implementation:

1. `frontend.py` reads UTF-8 sources into physical source locations and tokenizes
   strings, identifiers, numbers, and comments.
2. The reverse block parser builds `Node` trees by pairing `end` with bottom
   declarations. It retains source file, line, and original text.
3. The module loader traverses canonical paths, detects cycles, suppresses repeated
   imports, expands top-level statements, and registers function signatures.
4. `codegen.py` validates postfix stack arities, reserved identifiers, scopes,
   definite assignment, loop control, and function calls while lowering to C.
5. `backscript.py` exposes the CLI and invokes GCC or formats a validated file.

Diagnostics show filename, physical line number, source line, and a caret at the
statement's first token. They identify the statement rather than an exact operand
column. Dynamic types, arithmetic domains, indexes, and I/O failures are checked
by the runtime. Runtime errors currently show the failed operation without a
BackScript stack trace.

## Evaluation and scopes

Every literal, variable read, operation, and call emits an ordered `BSValue`
temporary. C's unspecified argument evaluation order cannot reorder BackScript
side effects because call arguments are already materialized. Conditions emit
inside a `while` iteration and outside an `if`. Range bounds are captured once
in numeric cursor/stop/step locals. A C `for` increment ensures `continue` advances
the internal cursor.

Function prototypes precede definitions and use mangled `bs_fn_` names. Local
variables use `bs_var_` names. Temporaries have globally unique generated names.
Function parameters and assignments share one function scope; module-level
assignments share `main` scope. Declarations are hoisted, but the validator tracks
which variables are definitely assigned. Branch joins intersect known names;
possibly unexecuted loops do not introduce known names afterward. Each function
gets a fresh set, so no globals leak into its local scope. Every function has a
`null` fallthrough return, including functions with conditional returns.

Generated functions have external linkage so unused exported functions do not
trigger unused-static-function warnings. Explicit `(void)` references suppress
unused local warnings without changing evaluation. The runtime uses static
inline functions, allowing unused builtins without compiler warnings. The full
suite compiles generated C with `-std=gnu11 -O2 -Wall -Wextra -Werror`.

## Runtime ownership

`BSValue` is a tagged value. Strings, arrays, and objects own tracked allocations;
collection values are references to mutable storage. A process-wide allocation
list frees tracked storage via `atexit`, including runtime error exits. Collections
grow geometrically; resizing updates the tracked allocation and releases the
previous buffer. This simple
ownership model handles recursive graphs without reference-count cycles but does
not bound memory during long-running programs. Collection printing limits nesting
to handle cycles. File reading uses a separately managed growing buffer before
creating a tracked string, and all files are closed on success/error paths.

`run` and `build` create temporary C files; `run` also uses a temporary executable.
`emit` writes only the requested C output. There are no package dependencies or
persistent build caches. Formatter validation happens before an in-place edit.
