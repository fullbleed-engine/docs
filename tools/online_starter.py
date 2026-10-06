"""Create an online editor launch form from an already verified starter ZIP."""
from html import escape
import re


STARTERS = {
    'browser': {'name': 'JavaScript', 'stack': 'JavaScript + Vite', 'entry': 'src%2Fmain.js', 'run': 'run-the-starter'},
    'react': {'name': 'React', 'stack': 'React + TypeScript', 'entry': 'src%2FApp.tsx', 'run': 'run-the-project'},
}


def check_online_links(root, flavor):
    for page, expected in [('docs/index.md', f'assets/{flavor}-starter/edit-online.html'),
                           (f'docs/guides/{flavor}-pdf.md', f'../assets/{flavor}-starter/edit-online.html')]:
        links = re.findall(r'\]\(([^)]+)\)', (root / page).read_text(encoding='utf-8'))
        assert links.count(expected) == 1 and not any('stackblitz.com/github/' in link for link in links), (
            f'{page}: online editor must use the launcher built from the downloadable {flavor} starter')


def write_online_launcher(root, flavor, manifest, project_files):
    starter = STARTERS[flavor]
    fields = {'project[title]': f'Fullbleed {starter["name"]} PDF starter',
        'project[description]': 'Editable HTML/CSS templates and local PDF previews. MIT licensed; fictional sample data.',
        'project[template]': 'node', 'project[dependencies]': '{}'}
    fields.update({f'project[files][{name}]': value for name, value in sorted(project_files.items())})
    inputs = '\n'.join(f'<input type="hidden" name="{escape(name, quote=True)}" value="{escape(value, quote=True)}">'
        for name, value in fields.items())
    launcher = (root / 'tools/online_starter.html').read_text(encoding='utf-8')
    # Insert project text last so placeholder-like strings inside source files stay intact.
    for token, value in {'__FLAVOR__': flavor, '__STARTER_NAME__': starter['name'],
        '__STACK__': starter['stack'], '__ENTRY_FILE__': starter['entry'], '__RUN_SECTION__': starter['run'],
        '__PACKAGE_VERSION__': manifest['package_version'], '__ENGINE_VERSION__': manifest['engine_version']}.items():
        assert token in launcher
        launcher = launcher.replace(token, escape(value, quote=True))
    assert launcher.count('__PROJECT_FIELDS__') == 1
    launcher = launcher.replace('__PROJECT_FIELDS__', inputs)
    path = root / f'docs/assets/{flavor}-starter/edit-online.html'
    path.write_text(launcher, encoding='utf-8', newline='\n')
    return path
