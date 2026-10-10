# Self-hosting preparation

BackScript v1.0.0 is Stage 0. It does not implement or claim self-hosting.

| Stage | Artifact and verification |
| --- | --- |
| 0 | Python compiler emits C, GCC produces native executables |
| 1 | Implement the compiler in BackScript, matching Stage 0 semantics |
| 2 | Stage 0 compiles the Stage 1 source into a native compiler |
| 3 | That compiler compiles its own BackScript source |
| 4 | Compare emitted C and normalized artifacts, run cross-compiler conformance tests, repeat the bootstrap |

The frontend's source records, token lists, reverse block tree, module traversal,
symbol registry, scope sets, and code generation are separate concepts. A future
implementation can represent these with objects and arrays rather than depend
on Python-specific behavior. Deterministic ordered C emission, forward signature
registration, local function scope, and one specified standard library reduce
bootstrap ambiguity.

## Available foundations

V1 supports dynamic arrays, objects with string keys, strings, math, functions,
recursion, local variables, loops, file text input/output, and modules. These are
enough to prototype a tokenizer, parser, symbol registry, and C emitter. Stage 0
remains the reference implementation during that work.

## Work required before a practical bootstrap

- Command-line argument access and explicit process exit status in the language.
- Subprocess execution with argument arrays and captured status to invoke GCC.
- Directory/path operations and canonicalization for reliable module identity.
- String byte/codepoint access and lossless number serialization for tokenization
  and round-trip literal emission (byte substring is currently available).
- Object key enumeration for symbol tables, with specified ordering.
- Recoverable I/O errors and structured diagnostics for a compiler CLI.
- Efficient string builders, indexed object lookup, and garbage collection or
  arenas with explicit bounded lifetimes for large inputs.
- A standalone intermediate representation separating validation from emission,
  serializable token/AST records, and conformance fixtures shared by both compilers.
- Stable source maps, cross-platform generated output, bootstrap normalization,
  and reproducible builds across host compiler versions.

Stage 1 should first emit C using the same runtime and syntax specification.
Compare generated C rather than raw native binaries, whose bytes may differ due
to toolchain metadata and build paths. Verify runtime outputs, failures, import
resolution, and diagnostics on the same fixtures, then compile the compiler
again and check convergence. A passing factorial example establishes recursion;
it does not establish bootstrap readiness.
