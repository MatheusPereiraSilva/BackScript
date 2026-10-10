#!/usr/bin/env python3
"""BackScript command line interface."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

from codegen import Compiler
from frontend import BLOCKS, CompileError, load_program, tokenize

VERSION = '1.0.0'


def format_file(path):
    # Validate first; block delimiters are balanced before any file is changed.
    Compiler(load_program(path)).compile()
    source = path.read_text(encoding='utf-8')
    depth, formatted = 0, []
    for text in source.splitlines():
        tokens = tokenize(text)
        if tokens and tokens[-1] in BLOCKS:
            depth -= 1
        indentation = depth - 1 if tokens == ['else'] else depth
        formatted.append('    ' * max(0, indentation) + text.strip() if text.strip() else '')
        if tokens == ['end']:
            depth += 1
    path.write_text('\n'.join(formatted) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='backscript')
    parser.add_argument('--version', action='version', version=f'BackScript {VERSION}')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('version')
    for command in ['run', 'build', 'emit', 'check', 'fmt']:
        sub = commands.add_parser(command)
        sub.add_argument('source', type=Path)
        if command in {'build', 'emit'}:
            sub.add_argument('-o', '--output', type=Path, required=True)
        if command in {'run', 'build'}:
            sub.add_argument('--cc', default='gcc')
    args = parser.parse_args(argv)
    try:
        if args.command == 'version':
            print(f'BackScript {VERSION}')
            return 0
        if args.command == 'fmt':
            format_file(args.source)
            return 0
        generated = Compiler(load_program(args.source)).compile()
        if args.command == 'check':
            return 0
        if args.command == 'emit':
            args.output.write_text(generated, encoding='utf-8')
            return 0
        runtime = Path(__file__).resolve().parent.parent / 'runtime'
        with tempfile.TemporaryDirectory(prefix='backscript-') as directory:
            c_path = Path(directory) / 'program.c'
            c_path.write_text(generated, encoding='utf-8')
            executable = args.output.resolve() if args.command == 'build' else Path(directory) / 'program'
            subprocess.run([args.cc, '-std=gnu11', '-O2', '-Wall', '-Wextra', '-I', str(runtime),
                            str(c_path), '-lm', '-o', str(executable)], check=True)
            if args.command == 'run':
                return subprocess.run([str(executable)]).returncode
        return 0
    except CompileError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as error:
        print(f'BackScript error: {error}', file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        return error.returncode


if __name__ == '__main__':
    raise SystemExit(main())
