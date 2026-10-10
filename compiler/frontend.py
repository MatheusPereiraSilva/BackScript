#!/usr/bin/env python3
"""Source locations, tokenizer, reverse block parser, and module loader."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z_0-9]*\Z')
NUMBER = re.compile(r'-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z')
BLOCKS = {'if', 'while', 'range', 'function'}
ARITIES = {
    **dict.fromkeys(['add', 'subtract', 'multiply', 'divide', 'mod', 'equal',
                     'not_equal', 'greater', 'less', 'greater_equal', 'less_equal',
                     'and', 'or', 'get', 'push', 'property', 'has_property',
                     'contains', 'starts_with', 'ends_with', 'min', 'max', 'power'], 2),
    **dict.fromkeys(['not', 'length', 'pop', 'keys_length', 'uppercase', 'lowercase',
                     'trim', 'string', 'abs', 'floor', 'ceil', 'round', 'sqrt',
                     'read_file', 'file_exists'], 1),
    **dict.fromkeys(['setat', 'set_property', 'substring'], 3),
}
STATEMENTS = {'set', 'print', 'return', 'call', 'array', 'object', 'write_file',
              'append_file', 'break', 'continue', 'import', 'else', 'end'}
RESERVED = set(ARITIES) | STATEMENTS | BLOCKS | {'true', 'false', 'null'}


class CompileError(Exception):
    def __init__(self, message, line=None):
        self.message, self.line = message, line
        super().__init__(message)

    def __str__(self):
        if self.line is None:
            return f'BackScript compile error: {self.message}'
        return (f'{self.line.path}:{self.line.number}\n    {self.line.text}\n'
                f'    {" " * (len(self.line.text) - len(self.line.text.lstrip()))}^\n'
                f'BackScript compile error: {self.message}')


@dataclass
class Line:
    path: Path
    number: int
    text: str
    tokens: list[str]


@dataclass
class Node:
    line: Line
    kind: str = 'expression'
    body: list[Node] | None = None
    otherwise: list[Node] | None = None


@dataclass
class Function:
    name: str
    params: list[str]
    node: Node


@dataclass
class Program:
    functions: list[Function]
    body: list[Node]


def tokenize(text):
    tokens = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
        elif text[i] == '#':
            break
        elif text[i] == '"':
            start = i
            i += 1
            while i < len(text):
                if text[i] == '\\':
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise CompileError('unterminated string')
            token = text[start:i]
            try:
                value = json.loads(token)
            except ValueError:
                raise CompileError('invalid string escape (use JSON escapes)') from None
            if '\0' in value:
                raise CompileError('strings cannot contain NUL bytes')
            tokens.append(token)
        else:
            start = i
            while i < len(text) and not text[i].isspace() and text[i] != '#':
                i += 1
            tokens.append(text[start:i])
    return tokens


def read_lines(path):
    try:
        source = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        raise CompileError(f'cannot read {path}: {error}') from None
    result = []
    for number, text in enumerate(source.splitlines(), 1):
        line = Line(path, number, text, [])
        try:
            line.tokens = tokenize(text)
        except CompileError as error:
            error.line = line
            raise
        if line.tokens:
            result.append(line)
    return result


def parse_lines(lines):
    index = 0

    def sequence(in_block=False):
        nonlocal index
        nodes = []
        while index < len(lines):
            line = lines[index]
            tokens = line.tokens
            if tokens == ['else'] or tokens[-1] in BLOCKS:
                if in_block:
                    return nodes
                raise CompileError("expected 'end' before reverse block declaration", line)
            index += 1
            if tokens == ['end']:
                body = sequence(True)
                otherwise = None
                if index < len(lines) and lines[index].tokens == ['else']:
                    index += 1
                    otherwise = sequence(True)
                if index == len(lines):
                    raise CompileError('reverse block has no declaration', line)
                terminal = lines[index]
                if terminal.tokens[-1] not in BLOCKS:
                    raise CompileError('expected reverse block declaration', terminal)
                if otherwise is not None and terminal.tokens[-1] != 'if':
                    raise CompileError('else requires an if block', terminal)
                index += 1
                nodes.append(Node(terminal, terminal.tokens[-1], body, otherwise))
            else:
                nodes.append(Node(line))
        return nodes

    return sequence()


def valid_name(name, line):
    if not IDENTIFIER.fullmatch(name) or name in RESERVED:
        raise CompileError(f'invalid or reserved identifier {name!r}', line)


def load_program(path):
    visited, active, functions, body = set(), [], [], []

    def load(file, import_line=None):
        file = file.resolve()
        if file in active:
            chain = ' -> '.join(str(p) for p in [*active, file])
            raise CompileError(f'circular import: {chain}', import_line)
        if file in visited:
            return
        active.append(file)
        try:
            nodes = parse_lines(read_lines(file))
        except CompileError as error:
            if error.line is None:
                error.line = import_line
            raise
        for node in nodes:
            tokens = node.line.tokens
            if tokens[-1] == 'import':
                if len(tokens) != 2 or not tokens[0].startswith('"'):
                    raise CompileError('import expects a literal .wtf path', node.line)
                relative = json.loads(tokens[0])
                if Path(relative).suffix != '.wtf':
                    raise CompileError('imports must reference .wtf files', node.line)
                load(file.parent / relative, node.line)
            elif node.kind == 'function':
                if len(tokens) < 2:
                    raise CompileError('function expects a name', node.line)
                name, params = tokens[-2], tokens[:-2]
                for identifier in [name, *params]:
                    valid_name(identifier, node.line)
                if len(set(params)) != len(params):
                    raise CompileError('duplicate function parameter', node.line)
                functions.append(Function(name, params, node))
            else:
                body.append(node)
        active.pop()
        visited.add(file)

    load(Path(path))
    names = set()
    for function in functions:
        if function.name in names:
            raise CompileError(f'duplicate function {function.name!r}', function.node.line)
        names.add(function.name)
    return Program(functions, body)


