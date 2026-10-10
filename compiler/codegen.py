"""Validated postfix evaluation and deterministic C code generation."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math

from frontend import ARITIES, NUMBER, RESERVED, CompileError, valid_name

def c_string(data):
    escapes = {34: '\\"', 92: '\\\\', 10: '\\n', 13: '\\r', 9: '\\t', 63: '\\?'}
    encoded = []
    for byte in data:
        if byte in escapes:
            encoded.append(escapes[byte])
        elif 32 <= byte <= 126:
            encoded.append(chr(byte))
        else:
            encoded.append(f'\\{byte:03o}')
    return '"' + ''.join(encoded) + '"'


@dataclass
class Item:
    expression: str | None = None
    symbol: str | None = None


class Compiler:
    def __init__(self, program):
        self.program = program
        self.functions = {f.name: f for f in program.functions}
        self.counter = 0
        self.locals = set()
        self.line = None

    def temporary(self, prefix='value'):
        self.counter += 1
        return f'bs_{prefix}_{self.counter}'

    def fail(self, message):
        raise CompileError(message, self.line)

    def expression(self, item, known):
        if item.expression is not None:
            return item.expression
        if item.symbol in known:
            return f'bs_var_{item.symbol}'
        self.fail(f'unknown value {item.symbol!r}')

    def compile_tokens(self, tokens, known, stack, out, in_function):
        def pop():
            if not stack:
                self.fail('operation has too few operands')
            return stack.pop()

        def value(item):
            return self.expression(item, known)

        def produce(expression):
            name = self.temporary()
            out.append(f'BSValue {name} = {expression};')
            out.append(f'(void){name};')
            stack.append(Item(name))

        for token in tokens:
            if token.startswith('"'):
                # Non-ASCII UTF-8 bytes use fixed-width octal escapes in C literals.
                try:
                    data = json.loads(token).encode('utf-8')
                except UnicodeError:
                    self.fail('string contains an invalid Unicode surrogate')
                literal = c_string(data)
                produce(f'bs_string({literal})')
            elif NUMBER.fullmatch(token):
                number = float(token)
                if not math.isfinite(number):
                    self.fail('numeric literal is outside the finite numeric domain')
                produce(f'bs_number({number!r})')
            elif token in {'true', 'false', 'null'}:
                produce({'true': 'bs_bool(1)', 'false': 'bs_bool(0)', 'null': 'bs_null()'}[token])
            elif token in ARITIES:
                args = [value(pop()) for _ in range(ARITIES[token])][::-1]
                operation = 'string_convert' if token == 'string' else token
                produce(f'bs_{operation}({", ".join(args)})')
            elif token in {'array', 'object'}:
                if token == 'object':
                    count_item = pop()
                    count_expr = count_item.expression
                    count = self.literal_counts.get(count_expr)
                    if count is None or count < 0 or count != int(count):
                        self.fail('object expects a nonnegative integer literal pair count')
                    count = int(count)
                    if len(stack) < count * 2:
                        self.fail('object has too few key/value pairs')
                    items = stack[-count * 2:] if count else []
                    if count:
                        del stack[-count * 2:]
                else:
                    items = list(stack)
                    stack.clear()
                    count = len(items)
                expressions = [value(item) for item in items]
                array = self.temporary('items')
                if expressions:
                    out.append(f'BSValue {array}[] = {{{", ".join(expressions)}}};')
                produce(f'bs_{token}_from({count}, {array if expressions else "NULL"})')
            elif token == 'set':
                name, item = pop(), pop()
                if name.symbol is None:
                    self.fail('set expects a variable name')
                valid_name(name.symbol, self.line)
                expression = value(item)
                self.locals.add(name.symbol)
                known.add(name.symbol)
                out.append(f'bs_var_{name.symbol} = {expression};')
            elif token == 'call':
                name = pop().symbol
                if name not in self.functions:
                    self.fail(f'call expects a known function name, got {name!r}')
                count = len(self.functions[name].params)
                args = [value(pop()) for _ in range(count)][::-1]
                produce(f'bs_fn_{name}({", ".join(args)})')
            elif token in {'print', 'return'}:
                if token == 'return' and not in_function:
                    self.fail('return outside function')
                expression = value(pop())
                out.append(f'bs_println({expression});' if token == 'print' else f'return {expression};')
            elif token in {'write_file', 'append_file'}:
                path, content = value(pop()), value(pop())
                out.append(f'bs_{token}({content}, {path});')
            elif token in RESERVED:
                self.fail(f'{token} is not valid in an expression')
            else:
                valid_name(token, self.line)
                if token in known:
                    produce(f'bs_var_{token}')
                    # A known variable can also be an assignment target or function name.
                    stack[-1].symbol = token
                else:
                    stack.append(Item(symbol=token))
            if NUMBER.fullmatch(token):
                self.literal_counts[stack[-1].expression] = float(token)

    def tokens(self, tokens, known, in_function=False):
        out, stack = [], []
        self.compile_tokens(tokens, known, stack, out, in_function)
        if len(stack) != 1:
            self.fail('expression must produce exactly one value')
        return out, self.expression(stack[0], known)

    def compile_nodes(self, nodes, known, in_function=False, loops=0):
        out, stack = [], []
        for node in nodes:
            self.line = node.line
            tokens = node.line.tokens
            if node.kind == 'expression':
                if tokens in (['break'], ['continue']):
                    if not loops:
                        self.fail(f'{tokens[0]} outside loop')
                    if stack:
                        self.fail('unused operands before loop control')
                    out.append(f'{tokens[0]};')
                else:
                    self.compile_tokens(tokens, known, stack, out, in_function)
                    if tokens[-1] in {'setat', 'set_property', 'push'} and len(stack) == 1:
                        stack.clear()
                continue
            if stack:
                self.fail('unused operands before block')
            if node.kind == 'function':
                self.fail('functions must be declared at module level')
            if node.kind in {'if', 'while'}:
                prelude, condition = self.tokens(tokens[:-1], known, in_function)
                if node.kind == 'while':
                    out.append('while (1) {')
                    out.extend('    ' + line for line in prelude)
                    out.append(f'    if (!bs_truthy({condition})) break;')
                    body_known = set(known)
                    body = self.compile_nodes(node.body, body_known, in_function, loops + 1)
                    out.extend('    ' + line for line in body)
                    out.append('}')
                else:
                    out.extend(prelude)
                    out.append(f'if (bs_truthy({condition})) {{')
                    then_known = set(known)
                    body = self.compile_nodes(node.body, then_known, in_function, loops)
                    out.extend('    ' + line for line in body)
                    if node.otherwise is not None:
                        out.append('} else {')
                        else_known = set(known)
                        body = self.compile_nodes(node.otherwise, else_known, in_function, loops)
                        out.extend('    ' + line for line in body)
                        known.update(then_known & else_known)
                    out.append('}')
            elif node.kind == 'range':
                if len(tokens) < 4:
                    self.fail('range expects start stop [step] variable')
                variable = tokens[-2]
                valid_name(variable, self.line)
                values, operands = [], []
                self.compile_tokens(tokens[:-2], known, operands, values, in_function)
                if len(operands) not in {2, 3}:
                    self.fail('range expects start stop [step] variable')
                expressions = [self.expression(item, known) for item in operands]
                if len(expressions) == 2:
                    expressions.append('bs_number(1)')
                cursor, stop, step = [self.temporary(prefix) for prefix in ('cursor', 'stop', 'step')]
                out.extend(values)
                for name, expression in zip([cursor, stop, step], expressions):
                    out.append(f'double {name} = bs_num({expression});')
                    out.append(f'bs_finite({name});')
                out.append(f'if ({step} == 0) bs_error("range step must not be zero");')
                out.append(f'for (; {step} > 0 ? {cursor} < {stop} : {cursor} > {stop}; '
                           f'{cursor} = bs_range_next({cursor}, {step})) {{')
                self.locals.add(variable)
                out.append(f'    bs_var_{variable} = bs_number({cursor});')
                body_known = known | {variable}
                body = self.compile_nodes(node.body, body_known, in_function, loops + 1)
                out.extend('    ' + line for line in body)
                out.append('}')
        if stack:
            if len(stack) != 1:
                self.fail('unused values remain at end of block')
            out.append(f'(void){self.expression(stack[0], known)};')
        return out

    def scope(self, nodes, params=(), in_function=False):
        self.locals = set(params)
        self.literal_counts = {}
        body = self.compile_nodes(nodes, set(params), in_function)
        declarations = []
        for name in sorted(self.locals):
            if name not in params:
                declarations.append(f'BSValue bs_var_{name} = bs_null();')
            declarations.append(f'(void)bs_var_{name};')
        return declarations + body

    def compile(self):
        output = ['#include "backscript_runtime.h"', '']
        for function in self.program.functions:
            params = ', '.join(f'BSValue bs_var_{p}' for p in function.params) or 'void'
            output.append(f'BSValue bs_fn_{function.name}({params});')
        for function in self.program.functions:
            params = ', '.join(f'BSValue bs_var_{p}' for p in function.params) or 'void'
            output.extend(['', f'BSValue bs_fn_{function.name}({params}) {{'])
            output.extend('    ' + line for line in self.scope(function.node.body, function.params, True))
            output.extend(['    return bs_null();', '}'])
        output.extend(['', 'int main(void) {', '    bs_init();'])
        output.extend('    ' + line for line in self.scope(self.program.body))
        output.extend(['    return 0;', '}', ''])
        return '\n'.join(output)

