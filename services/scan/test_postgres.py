import os
from dotenv import load_dotenv
load_dotenv('../../.env')

from models import get_engine, init_db, get_session
from clone_manager import clone_repository, cleanup_repository
from semgrep_runner import run_semgrep
from gitleaks_runner import run_gitleaks
from checkov_runner import run_checkov
from trivy_runner import run_trivy
from risk_engine import assess_risk
from persistence import save_scan_result

engine = get_engine(os.environ['DATABASE_URL'])
init_db(engine)
session = get_session(engine)

repo_url = 'https://github.com/pallets/flask.git'
print(f'Clonage de {repo_url}...')
clone_result = clone_repository(repo_url)

if clone_result.success:
    semgrep_result = run_semgrep(clone_result.local_path)
    if not semgrep_result.success:
        semgrep_result = None
    gitleaks_result = run_gitleaks(clone_result.local_path)
    if not gitleaks_result.success:
        gitleaks_result = None
    checkov_result = run_checkov(clone_result.local_path)
    if not checkov_result.success:
        checkov_result = None
    trivy_result = run_trivy(clone_result.local_path)
    if not trivy_result.success:
        trivy_result = None

    assessment = assess_risk(semgrep_result, gitleaks_result, checkov_result, trivy_result)
    saved_scan = save_scan_result(session, repo_url, assessment, semgrep_result, gitleaks_result, checkov_result, trivy_result)
    print(f'✅ Scan sauvegardé en PostgreSQL avec id={saved_scan.id}')
    print(f'   score={saved_scan.score}, findings={len(saved_scan.findings)}')

    from collections import Counter
    sources = Counter(f.source for f in saved_scan.findings)
    for source, count in sources.items():
        print(f'   - {source}: {count}')

    cleanup_repository(clone_result.local_path)

session.close()
