# Modules

```wtf
"math.wtf" import
7 square call print
```

Imports are module-level statements with a literal `.wtf` path. Paths resolve
relative to the source containing the import, independent of the shell working
directory. Nested relative imports work the same way. Absolute paths are also
accepted. There is no remote loading or package registry.

The loader uses resolved canonical paths to suppress repeated imports, including
imports reached through different modules. A module's top-level statements are
inserted at its first import position and execute once. Imported functions join
the program's function registry before validation, so calls work regardless of
textual declaration order. Duplicate function names across modules are errors.
There are no namespaces, exports, or private function declarations.

Imported top-level variables join the executable's top-level scope in expansion
order. They are unavailable inside functions unless passed as arguments. Functions
have their own isolated local scopes.

An active-path stack detects circular dependencies and prints the import chain
and source location of the import that closes the cycle. Missing files, invalid
UTF-8, invalid syntax, and duplicate symbols report useful source diagnostics.
Modules are parsed once per compiler invocation.

Runnable example:

```sh
./backscript run examples/modules/main.wtf
```

Imports execute source code; review untrusted modules before running them, as
with other source files. `check` and `emit` only read and validate them.
