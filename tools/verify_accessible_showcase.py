"""Execute the exact source ZIP and compare its PDF with the validated specimen."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import runpy
import subprocess
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'docs/assets/accessible-showcase'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'target/accessible-showcase')
    parser.add_argument('--channel',choices=('alpha4','alpha5'),default='alpha4')
    args=parser.parse_args()
    suffix='' if args.channel=='alpha4' else '-'+args.channel
    assets=ROOT/('docs/assets/accessible-showcase'+suffix)
    archive_root='fullbleed-accessible-showcase'+suffix
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((assets/'source.json').read_text(encoding='utf-8'))
    archive=assets/'project.zip'
    assert sha256(archive.read_bytes()).hexdigest()==manifest['zip_sha256']
    project=out/archive_root
    with ZipFile(archive) as package:
        expected={archive_root+'/'+name for name in manifest['package_files']}
        assert set(package.namelist())==expected
        for name,digest in manifest['package_files'].items():
            data=package.read(archive_root+'/'+name)
            assert sha256(data).hexdigest()==digest,name
            path=(project/name).resolve()
            assert path.is_relative_to(project.resolve())
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    output=out/'rendered'
    for script in ('render.py','verify.py'):
        subprocess.run([sys.executable,str(project/script),'--out',str(output)],cwd=project,check=True)
    structure=json.loads((output/'structure.json').read_text(encoding='utf-8'))
    assert structure['marked_content_nesting_valid']
    # This is the real pre-refinement PDF that passed the profile boolean but
    # emitted nested-MCID warnings. The source kit must reject it independently.
    negative=ROOT/'tools/fixtures/accessible-showcase/nested-table-mcid.pdf'
    negative_manifest=json.loads(negative.with_suffix('.json').read_text(encoding='utf-8'))
    assert sha256(negative.read_bytes()).hexdigest()==negative_manifest['sha256']
    sys.path.insert(0,str(project))
    inspect=runpy.run_path(str(project/'verify.py'))['inspect_structure']
    try:
        inspect(negative)
    except AssertionError as error:
        rejection=str(error)
        assert rejection.startswith('Nested MCID on page 2:'),rejection
    else:
        raise AssertionError('The source kit accepted the known nested-MCID PDF')
    actual=sha256((output/'common-ground-guide.pdf').read_bytes()).hexdigest()
    validated=json.loads((assets/'validation.json').read_text(encoding='utf-8'))
    assert validated['external_validation']['compliant']
    assert validated['external_validation']['stderr_bytes']==0
    assert actual==validated['pdf_sha256']==sha256((assets/'common-ground-guide.pdf').read_bytes()).hexdigest()
    report={'ok':True,'source_files':len(manifest['source_files']),'pdf_sha256':actual,
            'matches_externally_validated_pdf':True,'external_validator_rerun':False,
            'marked_content_nesting_valid':True,'negative_control_rejection':rejection}
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':
    main()
