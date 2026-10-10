"""End-to-end compiler and runtime tests; all generated artifacts live in temporary directories."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BS = ROOT / 'backscript'


class BackScriptTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='backscript-test-')
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)

    def source(self, text, name='main.wtf'):
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def cli(self, *args, success=True):
        result = subprocess.run([str(BS), *map(str, args)], cwd=self.work,
                                capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def execute(self, text, expected=None, success=True):
        path = self.source(text)
        generated = self.work / 'program.c'
        self.cli('emit', path, '-o', generated)
        executable = self.work / 'program'
        result = subprocess.run(['gcc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                                 '-I', str(ROOT / 'runtime'), str(generated), '-lm',
                                 '-o', str(executable)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([str(executable)], cwd=self.work, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        if expected is not None:
            self.assertEqual(result.stdout, expected)
        return result

    def invalid(self, text, message):
        path = self.source(text)
        result = self.cli('check', path, success=False)
        self.assertIn(message, result.stderr)
        self.assertRegex(result.stderr, r'\.wtf:\d+')
        self.assertIn('^', result.stderr)
        return result

    def test_arithmetic_and_booleans(self):
        self.execute('''2 3 add print
8 3 subtract print
4 5 multiply print
7 2 divide print
7 3 mod print
2 2 equal print
2 3 not_equal print
3 2 greater print
2 3 less print
2 2 greater_equal print
2 2 less_equal print
true false and print
true false or print
false not print
null print
''', '5\n5\n20\n3.5\n1\ntrue\ntrue\ntrue\ntrue\ntrue\ntrue\nfalse\ntrue\ntrue\nnull\n')

    def test_math(self):
        self.execute('''-3 abs print
1.8 floor print
1.2 ceil print
-1.5 round print
3 7 min print
3 7 max print
2 5 power print
9 sqrt print
''', '3\n1\n2\n-2\n3\n7\n32\n3\n')

    def test_strings(self):
        self.execute(r'''"Back" "Script" add print
"hello" uppercase print
"HELLO" lowercase print
" \thello\n" trim print
"BackScript" "Script" contains print
"BackScript" "Back" starts_with print
"BackScript" "Script" ends_with print
"hello" 1 3 substring print
"hello" 5 0 substring print
"hello" length print
42 string print
true string print
false string print
null string print
"x" false add print
"á" length print
"a\n\t\"b\"\\" print
''', 'BackScript\nHELLO\nhello\nhello\ntrue\ntrue\ntrue\nell\n\n5\n42\ntrue\nfalse\nnull\nxfalse\n2\na\n\t"b"\\\n')
        long = 'x' * 1000
        self.execute(f'"{long}" "{long}" add length print', '2000\n')

    def test_arrays_and_aliases(self):
        self.execute('''1 2 3 array a set
a b set
a 1 9 setat
a 4 push
b print
b pop print
a length print
a 0 get print
array empty set
empty length print
''', '[1, 9, 3, 4]\n4\n3\n1\n0\n')

    def test_collection_growth_and_cycles(self):
        self.execute('''array a set
0 object o set
end
    a i push
    o i string i set_property
0 2000 i range
a length print
a 1999 get print
o keys_length print
o "1999" property print
a a push
a 2000 get length print
o "self" o set_property
o "self" property keys_length print
''', '2000\n1999\n2000\n1999\n2001\n2001\n')

    def test_objects(self):
        self.execute('''"name" "Matheus"
"age" 30
2 object user set
user "name" property print
user "age" 31 set_property
user "active" true set_property
user "age" property print
user "active" has_property print
user "missing" has_property print
user keys_length print
user length print
0 object empty set
empty keys_length print
"x" 1 "x" 2 2 object duplicate set
duplicate keys_length print
duplicate "x" property print
''', 'Matheus\n31\ntrue\nfalse\n3\n3\n0\n1\n2\n')

    def test_if_else_and_definite_assignment(self):
        self.execute('''end
    "yes" print
true if
end
    10 result set
else
    20 result set
false if
result print
''', 'yes\n20\n')
        self.invalid('end\n  1 x set\ntrue if\nx print', 'unknown value')
        self.invalid('end\n  1 x set\nfalse while\nx print', 'unknown value')

    def test_while_break_continue(self):
        self.execute('''0 i set
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
''', '1\n2\n4\n5\n6\n7\n8\n')

    def test_range(self):
        self.execute('''end
    i print
0 5 i range
end
    i print
5 0 -2 i range
end
    i print
0 1 0.25 i range
end
    "unreachable" print
5 0 i range
''', '0\n1\n2\n3\n4\n5\n3\n1\n0\n0.25\n0.5\n0.75\n')

    def test_range_control_and_nested_loops(self):
        self.execute('''end
    end
        continue
    i 1 equal if
    end
        j print
        break
    0 3 j range
    i print
    end
        break
    i 3 equal if
0 6 i range
''', '0\n0\n0\n2\n0\n3\n')

    def test_range_evaluates_bounds_once(self):
        self.execute('''3 stop set
end
    0 stop set
    i print
0 stop i range
''', '0\n1\n2\n')

    def test_functions_recursion_and_forward_calls(self):
        self.execute('''5 factorial call print
end
    end
        1 return
    n 1 less_equal if
    n
    n 1 subtract factorial call
    multiply return
n factorial function
end
    x twice call return
x first function
end
    x 2 multiply return
x twice function
21 first call print
''', '120\n42\n')

    def test_mutual_recursion(self):
        self.execute('''end
    end
        true return
    n 0 equal if
    n 1 subtract odd call return
n even function
end
    end
        false return
    n 0 equal if
    n 1 subtract even call return
n odd function
10 even call print
9 odd call print
''', 'true\ntrue\n')

    def test_scope_and_fallthrough(self):
        self.execute('''99 value set
end
    x 1 add value set
    value return
x first function
end
    x 2 add value set
    value return
x second function
end
    end
        1 return
    x if
x maybe function
4 first call print
4 second call print
value print
false maybe call print
''', '5\n6\n99\nnull\n')
        self.invalid('end\n  1 private set\nlocal function\nprivate print', 'unknown value')
        self.invalid('1 global set\nend\n  global return\nf function', 'unknown value')

    def test_deterministic_evaluation(self):
        self.execute('''end
    a pop return
a take function
1 2 3 array a set
a take call a take call subtract print
a print
''', '1\n[1]\n')

    def test_imports(self):
        self.source('end\n x x multiply return\nx square function', 'lib/math.wtf')
        self.source('"math.wtf" import\nend\n x square call return\nx via function', 'lib/wrapper.wtf')
        path = self.source('"lib/wrapper.wtf" import\n"lib/math.wtf" import\n7 via call print')
        self.assertEqual(self.cli('run', path).stdout, '49\n')
        self.execute('"lib/wrapper.wtf" import\n"lib/math.wtf" import\n7 via call print', '49\n')

    def test_import_errors(self):
        self.source('"main.wtf" import', 'other.wtf')
        self.invalid('"other.wtf" import', 'circular import')
        self.invalid('"missing.wtf" import', 'cannot read')
        self.invalid('"bad.txt" import', '.wtf')
        self.invalid('end\n "other.wtf" import\nf function', 'not valid in an expression')

    def test_imported_source_diagnostics(self):
        imported = self.source('# module\n\nend\n  missing return\nf function', 'lib/bad.wtf')
        path = self.source('"lib/bad.wtf" import\nf call print')
        result = self.cli('check', path, success=False)
        self.assertIn(str(imported) + ':4', result.stderr)
        self.assertIn('missing return', result.stderr)

    def test_files(self):
        self.execute(r'''"hello\n" "output.txt" write_file
"world" "output.txt" append_file
"output.txt" read_file print
"output.txt" file_exists print
"missing.txt" file_exists print
"" "empty.txt" write_file
"empty.txt" read_file length print
''', 'hello\nworld\ntrue\nfalse\n0\n')
        self.assertEqual((self.work / 'output.txt').read_text(), 'hello\nworld')
        self.execute('"' + 'a' * 9000 + '" "large.txt" write_file\n"large.txt" read_file length print', '9000\n')

    def test_runtime_errors(self):
        cases = [
            ('1 0 divide print', 'division by zero'),
            ('1 0 mod print', 'modulo by zero'),
            ('array a set\na pop print', 'empty array'),
            ('1 array a set\na -1 get print', 'index'),
            ('1 array a set\na 0.5 get print', 'index'),
            ('"hello" 4 2 substring print', 'index'),
            ('0 object a set\na "x" property print', 'property'),
            ('1 length print', 'length expects'),
            ('1 uppercase print', 'expected string'),
            ('"x" 2 subtract print', 'expected number'),
            ('-1 sqrt print', 'sqrt expects'),
            ('end\n i print\n0 2 0 i range', 'step must not be zero'),
            ('end\n i print\n1e20 1e21 1 i range', 'cannot advance'),
            ('"missing.txt" read_file print', 'cannot read'),
            ('"hello" "missing/dir/file" write_file', 'cannot write'),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                self.assertIn(message, self.execute(source, success=False).stderr)
        (self.work / 'binary.txt').write_bytes(b'hello\0world')
        self.assertIn('NUL', self.execute('"binary.txt" read_file print', success=False).stderr)

    def test_compile_errors(self):
        cases = [
            ('break', 'outside loop'), ('continue', 'outside loop'),
            ('1 return', 'outside function'), ('add print', 'too few operands'),
            ('unknown print', 'unknown value'), ('"unterminated', 'unterminated string'),
            (r'"bad\q" print', 'invalid string escape'), (r'"bad\u0000" print', 'NUL'),
            ('true if', "expected 'end'"), ('end\n1 print', 'no declaration'),
            ('else', "expected 'end'"), ('1 2', 'unused values'),
            ('end\n1 print\nx x f function', 'duplicate function parameter'),
            ('end\n1 return\nf function\nend\n2 return\nf function', 'duplicate function'),
            ('end\n x return\nx f function\nf call', 'too few operands'),
            ('bad call', 'known function'), ('1 2 object a set', 'too few key/value'),
            ('2 n set\nn object a set', 'literal pair count'),
            ('1 if set', 'not valid in an expression'),
            ('1e999 print', 'finite numeric domain'),
            (r'"\ud800" print', 'invalid Unicode surrogate'),
            ('end\n1 print\n0 i range', 'range expects'),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                self.invalid(source, message)

    def test_cli_and_formatter(self):
        self.assertEqual(self.cli('version').stdout, 'BackScript 1.0.0\n')
        self.assertEqual(self.cli('--version').stdout, 'BackScript 1.0.0\n')
        path = self.source('end\nend\n"yes" print\ntrue if\nelse\n"no" print\nfalse if\n')
        self.cli('check', path)
        self.cli('check', path, '--unknown', success=False)
        self.cli('fmt', path)
        expected = 'end\n    end\n        "yes" print\n    true if\nelse\n    "no" print\nfalse if\n'
        self.assertEqual(path.read_text(), expected)
        self.cli('fmt', path)
        self.assertEqual(path.read_text(), expected)
        executable = self.work / 'native'
        self.cli('build', path, '-o', executable)
        self.assertEqual(subprocess.check_output([str(executable)], text=True), 'no\n')
        self.assertEqual(self.cli('run', path).stdout, 'no\n')
        self.cli('check', self.work / 'nonexistent.wtf', success=False)
        self.cli('build', path, '-o', executable, '--cc', 'missing-compiler', success=False)

    def test_all_examples(self):
        for example in sorted((ROOT / 'examples').rglob('*.wtf')):
            with self.subTest(example=example.name):
                self.cli('check', example)
                generated = self.work / 'example.c'
                self.cli('emit', example, '-o', generated)
                executable = self.work / 'example'
                result = subprocess.run(['gcc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                                         '-I', str(ROOT / 'runtime'), str(generated), '-lm',
                                         '-o', str(executable)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                result = subprocess.run([str(executable)], cwd=self.work, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                if example.name == 'recursion.wtf':
                    self.assertEqual(result.stdout, '120\n')
                if example.name == 'hello.wtf':
                    self.assertEqual(result.stdout, 'Hello, world!\n')
                if example.name == 'showcase.wtf':
                    self.assertEqual(result.stdout, 'BackScript\nPROGRAMMING BACKWARDS\n[10, 25, 30, 40]\n40\n3\nMatheus\ntrue\n3\nAccess granted\n0\n1\n9\n16\n1\n3\n120\n3\n256\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
