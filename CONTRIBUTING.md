# Contributing

Use Python 3.10+ and GCC. Run `python3 tests/run_tests.py` before submitting a
change; it validates examples and compiles generated C with warnings as errors.
Tests must use temporary directories for build artifacts and file operations.

Keep syntax consistent: values before operations, block bodies before declarations.
Document semantic changes in `docs/LANGUAGE.md`, `docs/GRAMMAR.md`, and relevant
standard library or module documentation. Include executable examples and tests
for new behavior and meaningful error cases. Keep implementation code direct,
readable, and free of joke comments or unnecessary logging.

Report bugs with the source, command, compiler version, and expected/actual output.
Changes to runtime ownership or evaluation order need explicit regression coverage.
The project uses the MIT license; contributions are made under that license.
