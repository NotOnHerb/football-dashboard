"""The build must give the same output on every machine.

numpy's default (quicksort) argsort picks a CPU-specific path (AVX2, AVX-512), and those order tied values
differently, so a pandas sort_values on a column with ties gave CI runners and laptops different data.json files
(different row order, and a different player kept by drop_duplicates). A stable sort keeps ties in input order on
every CPU. Sorts on two or more columns are lexsorts, which pandas always does stably.
"""
import ast, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNSTABLE = {'argsort', 'nlargest', 'nsmallest', 'sort_index', 'rank'}   # each orders ties per CPU, or needs a stable kind


def modules():
    """Every Python file outside tests/ (and the untracked .claude/ and .superpowers/ folders)."""
    for p in glob.glob(os.path.join(ROOT, '**', '*.py'), recursive=True):
        rel = os.path.relpath(p, ROOT).replace(os.sep, '/')
        if not rel.startswith(('tests/', '.claude/', '.superpowers/')): yield rel


def is_stable(call):
    kw = {k.arg: k.value for k in call.keywords}
    if isinstance(kw.get('kind'), ast.Constant) and kw['kind'].value == 'stable': return True
    by = kw.get('by', call.args[0] if call.args else None)
    return isinstance(by, (ast.List, ast.Tuple)) and len(by.elts) >= 2   # a lexsort


def is_loose(call):
    """True for a sort call that can order ties differently per CPU."""
    if not isinstance(call.func, ast.Attribute): return False
    name = call.func.attr
    if name == 'sort': return isinstance(call.func.value, ast.Name) and call.func.value.id == 'np'   # np.sort; list.sort is stable
    return name in UNSTABLE | {'sort_values'} and not is_stable(call)


def test_sorts_are_stable():
    loose = ['%s:%d %s' % (rel, node.lineno, node.func.attr) for rel in modules()
             for node in ast.walk(ast.parse(open(os.path.join(ROOT, rel), encoding='utf-8').read()))
             if isinstance(node, ast.Call) and is_loose(node)]
    assert not loose, "these sort ties differently per CPU; pass kind='stable' (or sort on 2+ columns): %s" % loose


def test_guard_catches_loose_sorts():
    bad = ["d.sort_values('k')", "d.sort_values(['week'])", "d.sort_values(\n  'k', ascending=False)", "v.argsort()", "np.sort(v)"]
    good = ["d.sort_values('k', kind='stable')", "d.sort_values(['a', 'b'])", "d.sort_values(by=['a', 'b'])", "xs.sort(key=len)"]
    call = lambda src: ast.parse(src).body[0].value
    assert all(is_loose(call(s)) for s in bad) and not any(is_loose(call(s)) for s in good)
