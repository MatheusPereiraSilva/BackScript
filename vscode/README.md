# BackScript for VS Code

Declarative editor support for BackScript v1.0.0: `.wtf` language detection,
TextMate highlighting, reverse block indentation, snippets, and the optional
**BackScript Neon** dark theme. There is no extension runtime, language server,
telemetry, or build step. Any VS Code theme can use the standard token scopes.

## Try it locally

1. Open this repository's `vscode/` directory as the VS Code folder:
   `code vscode` from the repository root.
2. Press **F5**, or select **Run BackScript Extension** in Run and Debug and
   start debugging. The included `.vscode/launch.json` opens an Extension
   Development Host with `examples/showcase.wtf`.
3. In that host, open any `.wtf` file. The status bar should show **BackScript**.
   Use **Developer: Inspect Editor Tokens and Scopes** to inspect highlighting.

The development extension is loaded only in the host window. No `npm install`
is required. After changing contributions, restart the debug session.

## Theme and snippets

In the development host or a window with the installed extension, run
**Preferences: Color Theme** from the Command Palette and select
**BackScript Neon**. The theme is optional and applies to the whole window.

| Category | Neon color |
| --- | --- |
| Control and execution keywords | Magenta |
| Declared and called function names | Cyan |
| Strings and module paths | Lime |
| Numbers | Warm yellow |
| Booleans and null | Blue |
| Arithmetic, comparisons, boolean operators | Violet |
| Collection, string, file, and math builtins | Teal |
| Variables | Near white |
| Comments | Muted gray |
| Invalid escapes and errors | Red |

In a BackScript file, type a prefix and choose its completion (or use
**Insert Snippet**):

| Prefix | Expansion |
| --- | --- |
| `bshello` | Hello world |
| `bsif` | Reverse conditional |
| `bsifelse` | Reverse conditional with else |
| `bswhile` | Counted reverse while loop |
| `bsfunc` | Function body followed by its declaration |
| `bsrange` | Exclusive range loop with step |
| `bsarray` | Array assignment |
| `bsobject` | Object assignment |
| `bsimport` | Relative module import |

Tab moves between placeholders. Defaults follow the compiler's syntax; import
paths must name a file available relative to your source.

## Editor behavior

`.wtf` is registered under language id `backscript` and scope `source.backscript`.
`#` is the line comment prefix. Only double quotes auto-close; parentheses and
square brackets are not BackScript grouping syntax.

`end` indents the following body. `else` and bottom `if`, `while`, `range`, and
`function` declarations outdent; the body after `else` indents again. Comments
and strings containing those words do not trigger indentation. Four spaces and
full auto-indentation are language defaults and can be overridden in settings.

These rules assist typing; they do not parse block nesting or provide Format
Document. For authoritative formatting, use the existing compiler from the
repository root:

```sh
./backscript fmt examples/showcase.wtf
```

## Package and install locally

With Node.js and npm installed, run from `vscode/`:

```sh
npx @vscode/vsce package --allow-missing-repository
code --install-extension ./backscript-1.0.0.vsix
```

Alternatively, use **Extensions: Install from VSIX...**. Reload VS Code if prompted.
The packaging tool is development tooling, not an extension runtime dependency.
No account is needed to package or install locally. The manifest's `backscript`
publisher is a local identifier; publishing to the Marketplace requires your own
registered publisher and appropriate repository metadata.

`.vscodeignore` excludes development configuration and validation scripts from
the package. The extension includes its MIT license. Generated `.vsix` files are
ignored by the root repository.

## Validate changes

Validate every JSON contribution, manifest paths, indentation rules, all builtin
scopes, function names, import paths, escapes, and showcase tokenization using
`tests/validate.cjs`. This script needs TextMate and Oniguruma **only for testing**.
On Linux with VS Code installed in `/usr/share/code`, use its bundled engines:

```sh
BACKSCRIPT_VSCODE_MODULES=/usr/share/code/resources/app/node_modules.asar \
ELECTRON_RUN_AS_NODE=1 /usr/share/code/code tests/validate.cjs
python3 tests/validate_snippets.py
```

On other installations, adjust the application/module paths. Alternatively,
install the two test engines into a temporary directory and point the validator
at its `node_modules`:

```sh
npm install --prefix /tmp/backscript-vscode-tests --no-save vscode-textmate vscode-oniguruma
BACKSCRIPT_VSCODE_MODULES=/tmp/backscript-vscode-tests/node_modules node tests/validate.cjs
python3 tests/validate_snippets.py
```

The Python validator expands snippet defaults and validates them with the existing
compiler, using a temporary example module. Run the main language suite from the
repository root with `python3 tests/run_tests.py` when integration changes affect
compiler behavior.

Highlighting is lexical: function names are detected immediately before `function`
or `call`; it does not resolve symbols or report compiler diagnostics. No
completion engine, debugger, or language server is provided. Run the development
host to check the visual result and interactive indentation before releasing.

Reference: VS Code's [syntax highlighting](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide),
[language configuration](https://code.visualstudio.com/api/language-extensions/language-configuration-guide),
and [extension packaging](https://code.visualstudio.com/api/working-with-extensions/publishing-extension) guides.
