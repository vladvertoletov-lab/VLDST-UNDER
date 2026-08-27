from pathlib import Path
import ast, re, sys
root=Path(__file__).resolve().parents[1]
errors=[]
for p in list((root/'backend').rglob('*.py'))+list((root/'bot').rglob('*.py'))+list((root/'tests').rglob('*.py')):
    try: ast.parse(p.read_text(encoding='utf-8'))
    except Exception as e: errors.append(f'{p}: {e}')
for forbidden in ['.env','.git','node_modules','__pycache__']:
    if any(x.name==forbidden for x in root.rglob('*')): errors.append(f'forbidden artifact: {forbidden}')
print('Python AST: PASS' if not errors else '\n'.join(errors))
sys.exit(1 if errors else 0)
