"""Package source and evidence only; exclude credentials, caches and the virtual environment."""
import sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.kb import ROOT

allowed_dirs={'core','web','scripts','tests','data','evidence'}
allowed_files={'README.md','requirements.txt','.env.example','.gitignore','app.py','ANSWERS.txt','ANSWERS.pdf','WALKTHROUGH_SCRIPT.txt','START_HERE.txt'}
target=ROOT/'submission.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    candidates=[ROOT/name for name in allowed_files]
    candidates += [p for name in allowed_dirs for p in (ROOT/name).rglob('*')]
    for p in sorted(candidates):
        if not p.is_file():continue
        relative=p.relative_to(ROOT)
        if any(x in {'__pycache__','.env','.venv','.git','.pytest_cache','runtime'} for x in relative.parts):continue
        if relative.parts[0] in allowed_dirs or str(relative) in allowed_files:z.write(p,'Darwix/'+relative.as_posix())
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert not any('/.env' in n and not n.endswith('.env.example') for n in z.namelist())
    print('Files:',len(z.namelist()),'Size:',round(target.stat().st_size/1e6,2),'MB')
