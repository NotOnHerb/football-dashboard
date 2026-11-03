"""The build must give the same output on every machine.

numpy's default (quicksort) argsort picks a CPU-specific path (AVX2, AVX-512), and those order tied values
differently, so a pandas sort_values on a column with ties gave CI runners and laptops different data.json files
(different row order, and a different player kept by drop_duplicates). A stable sort keeps ties in input order on
every CPU. Sorts on several columns are lexsorts, which pandas always does stably.
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ['build.py', 'model_fit.py', 'analyst/lab.py', 'analyst/snapshot.py', 'api_export.py', 'sources.py', 'cfb_fetch.py']


def test_single_column_sorts_are_stable():
    loose = []
    for f in FILES + ['engine/' + n for n in os.listdir(os.path.join(ROOT, 'engine')) if n.endswith('.py')]:
        for n, line in enumerate(open(os.path.join(ROOT, f), encoding='utf-8'), 1):
            for args in re.findall(r'sort_values\(([^()]*)\)', line):
                if not args.lstrip().startswith('[') and "kind='stable'" not in args: loose.append('%s:%d' % (f, n))
            if re.search(r'\bargsort\(|np\.sort\(|\.nlargest\(|\.nsmallest\(', line): loose.append('%s:%d' % (f, n))
    assert not loose, "sort ties differently per CPU; pass kind='stable': %s" % loose
