"""Read-only retention audit against the verified migration archives."""
from collections import Counter
from contextlib import closing
from datetime import datetime
from pathlib import Path
import hashlib, json, sqlite3, tempfile, zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    marker = json.loads((ROOT/'LOCAL_EDITION.json').read_text(encoding='utf-8'))
    archive = Path(marker['source_root'])
    manifest = json.loads((archive/'manifest.json').read_text(encoding='utf-8'))
    result = {'checked_at':datetime.now().astimezone().isoformat(), 'root':str(ROOT),
              'archive':str(archive), 'json_differences':[], 'tables':{},
              'note':'A later intentional edit or deletion may differ from migration; never automatically restore data.'}
    for rel, expected in manifest['files']['redesigned'].items():
        if Path(rel).parent.as_posix() == 'data' and rel.endswith('.json'):
            actual = hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
            if actual != expected:
                result['json_differences'].append(rel)
    with closing(sqlite3.connect((ROOT/'data/portfolio.db').as_uri()+'?mode=ro',uri=True)) as current:
        result['sqlite_integrity'] = current.execute('pragma integrity_check').fetchone()[0]
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime',prefix='migration-audit-') as tmp:
            for version in ('original','redesigned'):
                with zipfile.ZipFile(archive/(version+'.zip')) as z:
                    dbpath = Path(tmp)/(version+'.db')
                    dbpath.write_bytes(z.read('data/portfolio.db'))
                with closing(sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)) as baseline:
                    for (table,) in baseline.execute("select name from sqlite_master where type='table'"):
                        query = 'select * from "'+table.replace('"','""')+'"'
                        before, after = baseline.execute(query).fetchall(), current.execute(query).fetchall()
                        result['tables'][version+'/'+table] = {'before':len(before),'current':len(after),
                            'missing_or_changed':sum((Counter(before)-Counter(after)).values())}
    result['status'] = 'PASS' if result['sqlite_integrity']=='ok' and not result['json_differences'] and not any(v['missing_or_changed'] for v in result['tables'].values()) else 'REVIEW_CHANGES'
    (ROOT/'docs/verification/canonical-migration-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result['status'] != 'PASS'

if __name__ == '__main__':
    raise SystemExit(main())
