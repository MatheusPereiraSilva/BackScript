# BackScript v1.0 language guide

## Values and execution

Source is UTF-8. `#` starts a comment outside a string. Whitespace separates
operands and operations; indentation is for humans. Numbers are finite decimal
literals, optionally signed and with exponents (`-1.5`, `.5`, `1e3`). Values are
numbers, strings, `true`, `false`, `null`, arrays, and objects.

Expressions are postfix, evaluated left to right. Each evaluated operand is
captured in a generated temporary before the next operation, including calls and
collection mutations. `and` and `or` evaluate both operands. False values are
`false`, `null`, zero, and empty strings or collections.

Operand stacks can span lines inside a block:

```wtf
"name" "Matheus"
"age" 30
2 object user set
```

`print`, `set`, `return`, and file writes consume operands. `array` consumes all
pending operands to make an array. `object` consumes a literal pair count and
that many key/value pairs, leaving earlier operands intact. Standalone `push`,
`setat`, and `set_property` lines discard their one remaining result; they mutate
the underlying collection. Other expression results remain on the operand stack.
One unused result at the end of a block is discarded; multiple leftovers are a
compile error. The stack must be empty before a nested block or loop control.

## Variables and scope

```wtf
30 age set
age 1 add age set
age print
```

Names use ASCII letters, digits, and underscores, starting with a letter or
underscore. Operation names and literal keywords are reserved. Variables are
local to their top-level program or function. Parameters belong to function
scope, and `set` updates or creates a variable in that scope. Functions cannot
read top-level variables; pass them as parameters. Arrays and objects passed as
arguments share mutable storage. Scalars are passed by value.

Variables must be assigned before use. An assignment in both `if` branches is
available afterward; assignment in one branch or a possibly unexecuted loop is
not. Existing variables retain assignments made inside blocks. A new range
variable is available inside its body; it becomes available afterward only if it
was already assigned before the loop. Block-local declarations are hoisted in C
but compile-time validation prevents reading a value that might be uninitialized.

## Operators

`add`, `subtract`, `multiply`, `divide`, `mod` take two operands. `add` concatenates
when either operand is a string, converting the other scalar to text. Other
arithmetic operations require numbers. Division and modulo by zero fail.

`equal`, `not_equal`, `greater`, `less`, `greater_equal`, `less_equal` take two
operands. Ordering requires numbers. Equality compares scalar values; collections
compare identity. `and`, `or`, and unary `not` use truthiness.

## Reverse blocks

```wtf
end
    "Adult" print
else
    "Minor" print
age 18 greater_equal if
```

`end` begins the body. A bottom declaration closes it. An optional `else` divides
the true and false bodies. Conditions must produce one value. Nested blocks
follow the same rule. There is no implicit reversal of statement execution.

```wtf
0 i set
end
    i 1 add i set
    end
        continue
    i 3 equal if
    i print
    end
        break
    i 8 greater_equal if
i 10 less while
```

`while` evaluates its condition before every iteration. `break` exits the nearest
loop; `continue` begins its next iteration. Both are compile errors outside loops.

```wtf
end
    i print
0 10 2 i range
```

`start stop [step] variable range` evaluates numeric bounds and step once. The
stop bound is exclusive. Default step is 1. A positive step runs while the cursor
is less than stop; a negative step runs while it is greater. A zero or nonfinite
step/bound fails. `continue` advances the cursor. Assigning the body variable does
not change the internal cursor. A step that cannot advance floating-point state
fails rather than looping forever.

## Functions

```wtf
end
    end
        1 return
    n 1 less_equal if
    n n 1 subtract factorial call multiply return
n factorial function

5 factorial call print
```

`parameters name function` declares a module-level function after its body.
`arguments name call` invokes it. All signatures are registered before body
validation, so forward calls, recursion, and mutual recursion work. Parameter
counts are exact for a call (earlier pending operands may belong to a surrounding
expression). Falling through returns `null`. `return` requires one value and is
valid only in a function. Nested functions and duplicate declarations are errors.

## Collections, strings, files, and modules

```wtf
10 20 30 array numbers set
numbers 0 get print
numbers 1 99 setat
numbers 40 push
numbers pop print

"name" "Matheus" "age" 30 2 object user set
user "name" property print
user "active" true set_property
user "active" has_property print
user keys_length print
```

Object keys must be strings; duplicate keys use the last value. Missing
properties, fractional/out-of-range indexes, and popping empty arrays fail.

Strings use JSON escapes (`\n`, `\r`, `\t`, `\b`, `\f`, `\"`, `\\`, `\/`,
`\uXXXX`). NUL bytes and invalid surrogate sequences are rejected. Lengths and
substring indexes count UTF-8 bytes, so slicing can split a multibyte character.
Case conversion and whitespace trimming use the C locale (ASCII behavior).
`substring` takes start and length, both nonnegative integers within the string.

```wtf
"Back" "Script" add print
"hello" 1 3 substring print
42 string print
"hello" "output.txt" write_file
"output.txt" read_file print
"modules/math.wtf" import
```

File paths resolve from the executable's working directory; import paths resolve
from the importing source file. Imports accept only literal `.wtf` paths at
module level. See [STDLIB.md](STDLIB.md) and [MODULES.md](MODULES.md).
