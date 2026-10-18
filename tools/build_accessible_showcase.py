"""Build the reproducible accessible-showcase source download."""
import argparse
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json
from zipfile import ZipFile, ZipInfo, ZIP_STORED

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/accessible-showcase'
ASSETS=ROOT/'docs/assets/accessible-showcase'

def main(channel='alpha4'):
    suffix='' if channel=='alpha4' else '-'+channel
    project=ROOT/('examples/accessible-showcase'+suffix)
    assets=ROOT/('docs/assets/accessible-showcase'+suffix)
    archive_root='fullbleed-accessible-showcase'+suffix
    manifest=json.loads((project/'SOURCE.json').read_text(encoding='utf-8'))
    names=sorted([*manifest['source_files'],'SOURCE.json'])
    contents={name:(project/name).read_bytes() for name in names}
    assert all(sha256(contents[name]).hexdigest()==digest for name,digest in manifest['source_files'].items())
    stream=BytesIO()
    with ZipFile(stream,'w',compression=ZIP_STORED) as archive:
        for name,data in contents.items():
            info=ZipInfo(archive_root+'/'+name,(2026,10,17,0,0,0))
            info.create_system=3
            info.external_attr=0o100644<<16
            archive.writestr(info,data)
    data=stream.getvalue()
    assets.mkdir(parents=True,exist_ok=True)
    (assets/'project.zip').write_bytes(data)
    record={**manifest,'zip_sha256':sha256(data).hexdigest(),'zip_bytes':len(data),
            'package_files':{name:sha256(value).hexdigest() for name,value in contents.items()}}
    (assets/'source.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'ok':True,'files':len(contents),'zip_sha256':record['zip_sha256']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel',choices=('alpha4','alpha5'),default='alpha4')
    main(parser.parse_args().channel)
