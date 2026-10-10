# BackScript v1.0 grammar

The following EBNF describes structure. Expressions also obey compile-time
postfix operand counts and name/scope validation.

```ebnf
program          = { statement | import | function } ;
body             = { statement } ;
statement        = expression-line | conditional | while-loop | range-loop
                 | "break" newline | "continue" newline ;
conditional      = "end" newline body [ "else" newline body ] expression "if" newline ;
while-loop       = "end" newline body expression "while" newline ;
range-loop       = "end" newline body range-operands identifier "range" newline ;
range-operands   = expression ; (* produces start, stop, optional step *)
function         = "end" newline body { identifier } identifier "function" newline ;
import           = string-literal "import" newline ;
expression-line  = expression newline ;
expression       = { literal | identifier | operation } ;
literal          = number | string-literal | "true" | "false" | "null" ;
identifier       = (letter | "_") { letter | digit | "_" } ;
number           = [ "-" ] (digits [ "." [digits] ] | "." digits)
                   [ ("e" | "E") ["+" | "-"] digits ] ;
```

Blank lines and comments are ignored. String literals are JSON-compatible quoted
strings, without literal newlines, NUL, or invalid Unicode surrogates. Identifiers
are ASCII and cannot use reserved operation or structural names. Imports and
functions are restricted to module level. `else` is restricted to `if`.

A reverse block pairs its opening `end` with the next unpaired bottom declaration;
nested blocks must close first. A declaration without `end` is an error. The
parser tracks physical source lines rather than indentation.

Postfix operations consume their documented arity. `set` consumes value and
identifier, `call` consumes a function identifier and its parameter count,
`array` consumes all pending operands, and `object` consumes a nonnegative literal
pair count and twice that many operands. [STDLIB.md](STDLIB.md) specifies builtin
arities and results. Operand stacks span lines but not nested block boundaries.
