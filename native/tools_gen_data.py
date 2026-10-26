# يولّد بيانات الترتيب (الأجزاء وأحكام التجويد) من app.js حتى تبقى النسختان متطابقتين
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE.parent / 'app.js').read_text(encoding='utf-8')

m = re.search(r'const JUZ_START = \[(.*?)\];', src, re.S)
juz = [[int(a), int(b)] for a, b in re.findall(r'\[(\d+),\s*(\d+)\]', m.group(1))]
assert len(juz) == 30, len(juz)

m = re.search(r'const TJ_RULES = \{(.*?)\n  \};', src, re.S)
rules = {}
for key, name, desc in re.findall(r"(\w+):\s*\['([^']*)',\s*'([^']*)'\]", m.group(1)):
    rules[key] = [name, desc]
assert rules, 'no tajweed rules'

(HERE / 'data' / 'juz.json').write_text(json.dumps(juz, ensure_ascii=False), encoding='utf-8')
(HERE / 'data' / 'tajweed.json').write_text(json.dumps(rules, ensure_ascii=False, indent=1), encoding='utf-8')
print('juz', len(juz), 'rules', len(rules))
