/* Run with VS Code's bundled TextMate/Oniguruma modules or an isolated test install. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const repository = path.dirname(root);
const read = file => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
let assertions = 0;
function verify(condition, message) {
    assert.ok(condition, message);
    assertions++;
}
function jsonFiles(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
        const file = path.join(directory, entry.name);
        if (entry.isDirectory()) jsonFiles(file);
        else if (file.endsWith('.json') || file.endsWith('.code-snippets')) {
            JSON.parse(fs.readFileSync(file, 'utf8'));
            assertions++;
        }
    }
}

async function main() {
    jsonFiles(root);
    const manifest = read('package.json');
    verify(manifest.name === 'backscript' && manifest.version === '1.0.0', 'extension identity');
    verify(!manifest.main && !manifest.dependencies && !manifest.activationEvents, 'declarative extension');
    const language = manifest.contributes.languages[0];
    verify(language.id === 'backscript' && language.aliases.includes('BackScript'), 'language registration');
    verify(language.extensions.includes('.wtf'), '.wtf association');
    for (const contribution of [
        language.configuration,
        ...manifest.contributes.grammars.map(item => item.path),
        ...manifest.contributes.snippets.map(item => item.path),
        ...manifest.contributes.themes.map(item => item.path),
    ]) verify(fs.existsSync(path.join(root, contribution)), `missing contribution ${contribution}`);

    const config = read(language.configuration);
    verify(config.comments.lineComment === '#', 'line comments');
    verify(config.brackets.length === 0, 'unsupported bracket syntax');
    verify(config.autoClosingPairs.length === 1 && config.autoClosingPairs[0].open === '"', 'quote-only closing');
    const increase = new RegExp(config.indentationRules.increaseIndentPattern);
    const decrease = new RegExp(config.indentationRules.decreaseIndentPattern);
    for (const text of ['end', '    end # body', 'else', '    else # fallback']) {
        verify(increase.test(text), `indent after ${text}`);
    }
    for (const text of ['true if', 'i 5 less while # loop', '0 10 2 i range', 'a b sum function', 'else']) {
        verify(decrease.test(text), `outdent ${text}`);
    }
    for (const text of ['"range" print', '"if" print', '# else', '"while # function" print', 'if_count print']) {
        verify(!increase.test(text) && !decrease.test(text), `false indentation on ${text}`);
    }
    verify(config.onEnterRules[0].action.indent === 'indent', 'enter behavior');
    const launch = read('.vscode/launch.json').configurations[0];
    verify(launch.type === 'extensionHost' && launch.args.includes('--extensionDevelopmentPath=${workspaceFolder}'), 'F5 launch');

    const snippets = read('snippets/backscript.code-snippets');
    const prefixes = new Set(Object.values(snippets).map(item => item.prefix));
    for (const prefix of ['bshello', 'bsif', 'bsifelse', 'bswhile', 'bsfunc', 'bsrange', 'bsarray', 'bsobject', 'bsimport']) {
        verify(prefixes.has(prefix), `missing snippet ${prefix}`);
    }
    const theme = read('themes/backscript-neon-color-theme.json');
    verify(theme.name === 'BackScript Neon' && theme.type === 'dark', 'theme registration');
    for (const value of Object.values(theme.colors)) verify(/^#[0-9a-f]{6}(?:[0-9a-f]{2})?$/i.test(value), `theme color ${value}`);

    function luminance(color) {
        const rgb = color.slice(1).match(/../g).map(channel => parseInt(channel, 16) / 255)
            .map(channel => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4);
        return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
    }
    const background = luminance(theme.colors['editor.background']);
    for (const rule of theme.tokenColors) {
        const foreground = luminance(rule.settings.foreground);
        const contrast = (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
        verify(contrast >= 4.5, `token contrast for ${rule.name}: ${contrast}`);
    }

    const moduleRoot = process.env.BACKSCRIPT_VSCODE_MODULES;
    const modulePath = name => moduleRoot ? path.join(moduleRoot, name) : name;
    const textmate = require(modulePath('vscode-textmate'));
    const oniguruma = require(modulePath('vscode-oniguruma'));
    const wasm = fs.readFileSync(require.resolve(modulePath('vscode-oniguruma/release/onig.wasm')));
    await oniguruma.loadWASM(wasm.buffer.slice(wasm.byteOffset, wasm.byteOffset + wasm.byteLength));
    const grammarContribution = manifest.contributes.grammars[0];
    verify(grammarContribution.scopeName === 'source.backscript', 'TextMate registration');
    const grammarData = read(grammarContribution.path);
    const registry = new textmate.Registry({
        onigLib: Promise.resolve({
            createOnigScanner: patterns => new oniguruma.OnigScanner(patterns),
            createOnigString: text => new oniguruma.OnigString(text),
        }),
        loadGrammar: async scope => scope === 'source.backscript' ? grammarData : null,
    });
    const grammar = await registry.loadGrammar('source.backscript');
    verify(Boolean(grammar), 'TextMate grammar loads');
    function tokens(line, state = textmate.INITIAL) {
        const result = grammar.tokenizeLine(line, state);
        verify(!result.stoppedEarly, `tokenization stopped: ${line}`);
        return { ...result, pieces: result.tokens.map(token => ({
            text: line.slice(token.startIndex, token.endIndex), scopes: token.scopes,
        })) };
    }
    function hasScope(line, text, scope) {
        verify(tokens(line).pieces.some(token => token.text === text && token.scopes.includes(scope)),
            `missing ${scope} for ${JSON.stringify(text)} in ${JSON.stringify(line)}`);
    }
    const categories = {
        'keyword.control.backscript': 'end if else while range function return break continue import',
        'keyword.other.backscript': 'print set call',
        'keyword.operator.arithmetic.backscript': 'add subtract multiply divide mod',
        'keyword.operator.comparison.backscript': 'equal not_equal greater less greater_equal less_equal',
        'keyword.operator.logical.backscript': 'and or not',
        'support.function.collection.backscript': 'array object get setat property set_property has_property keys_length length push pop',
        'support.function.string.backscript': 'string substring contains starts_with ends_with uppercase lowercase trim',
        'support.function.file.backscript': 'read_file write_file append_file file_exists',
        'support.function.math.backscript': 'abs floor ceil round min max power sqrt',
        'constant.language.backscript': 'true false null',
    };
    const frontend = fs.readFileSync(path.join(repository, 'compiler/frontend.py'), 'utf8').split('class CompileError')[0];
    const reserved = [...new Set([...frontend.matchAll(/'([a-z_]+)'/g)].map(match => match[1]))].sort();
    const covered = Object.values(categories).flatMap(words => words.split(' '));
    verify(JSON.stringify([...covered].sort()) === JSON.stringify(reserved), 'grammar vocabulary matches compiler');
    for (const [scope, words] of Object.entries(categories)) {
        for (const word of words.split(' ')) hasScope(word, word, scope);
    }
    for (const number of ['0', '42', '-3', '-1.5', '.5', '-.5', '1.', '1e3', '-1.2E-3']) {
        hasScope(`${number} print`, number, 'constant.numeric.backscript');
    }
    hasScope('a b sum function', 'sum', 'entity.name.function.backscript');
    hasScope('10 20 sum call print', 'sum', 'entity.name.function.backscript');
    hasScope('numbers 0 get print', 'numbers', 'variable.other.backscript');
    hasScope('call_count print', 'call_count', 'variable.other.backscript');
    hasScope('"modules/math.wtf" import # module', 'modules/math.wtf', 'entity.name.filename.backscript');
    hasScope('"Hello from BackScript" uppercase print', 'Hello from BackScript', 'string.quoted.double.backscript');
    hasScope('"# end if 42" print', '# end if 42', 'string.quoted.double.backscript');
    hasScope('# "end" if 42', ' "end" if 42', 'comment.line.number-sign.backscript');
    for (const escape of ['\\n', '\\t', '\\r', '\\b', '\\f', '\\"', '\\\\', '\\/', '\\u0041']) {
        hasScope(`"a${escape}b" print`, escape, 'constant.character.escape.backscript');
    }
    hasScope('"bad\\q" print', '\\q', 'invalid.illegal.escape.backscript');
    const unterminated = tokens('"unterminated');
    verify(tokens('42 print', unterminated.ruleStack).pieces.some(token => token.text === '42' &&
        token.scopes.includes('constant.numeric.backscript')), 'unterminated strings do not consume next line');

    const example = fs.readFileSync(path.join(repository, 'examples/showcase.wtf'), 'utf8');
    let state = textmate.INITIAL;
    const seen = new Set();
    for (const line of example.split(/\r?\n/)) {
        const result = tokens(line, state);
        state = result.ruleStack;
        for (const token of result.pieces) for (const scope of token.scopes) seen.add(scope);
    }
    for (const scope of ['keyword.control.backscript', 'keyword.other.backscript', 'entity.name.function.backscript',
        'constant.numeric.backscript', 'constant.language.backscript', 'string.quoted.double.backscript',
        'support.function.collection.backscript', 'support.function.string.backscript', 'support.function.math.backscript']) {
        verify(seen.has(scope), `showcase category ${scope}`);
    }
    registry.dispose();
    console.log(`BackScript extension validation passed (${assertions} checks).`);
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
