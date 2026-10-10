"""Validate default snippet expansions against the existing BackScript compiler."""
import json
from pathlib import Path
import re
import sys
import tempfile

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / 'compiler'))
from codegen import Compiler
from frontend import load_program

PLACEHOLDER = re.compile(r'\$\{(\d+)(?::([^}]*))?\}|\$(\d+)')


def expand(body):
    text = '\n'.join(body)
    defaults = {match[1]: match[2] for match in PLACEHOLDER.finditer(text) if match[2] is not None}
    return PLACEHOLDER.sub(lambda match: defaults.get(match[1] or match[3], ''), text) + '\n'


def main():
    snippets = json.loads((REPOSITORY / 'vscode/snippets/backscript.code-snippets').read_text())
    with tempfile.TemporaryDirectory(prefix='backscript-snippets-') as directory:
        work = Path(directory)
        (work / 'modules').mkdir()
        (work / 'modules/math.wtf').write_text((REPOSITORY / 'examples/modules/math.wtf').read_text())
        for name, snippet in snippets.items():
            source = work / 'snippet.wtf'
            source.write_text(expand(snippet['body']))
            Compiler(load_program(source)).compile()
            print(f'{name}: default expansion compiles')
    print(f'{len(snippets)} snippets validated.')


if __name__ == '__main__':
    main()
