"""Exercise the actual chart-report download and inspect its final PDF objects."""
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import pypdfium2 as pdfium
from pypdf import PdfReader
from pypdf.generic import ContentStream

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/matplotlib-report"


def verify(args):
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    extracted = out / "project with spaces"
    extracted.mkdir(exist_ok=False)
    checks, commands = [], []
    report = {"schema":"fullbleed.matplotlib-starter-verification.v1", "ok":False,
              "platform":platform.system(), "python":platform.python_version(),
              "versions":{name:version(name) for name in ("fullbleed","matplotlib","numpy","pypdf","pypdfium2")},
              "checks":checks, "commands":commands}

    def check(name, value):
        checks.append({"name":name, "passed":bool(value)})
        if not value:
            raise AssertionError(name)

    def run(label, arguments, expected=0):
        result = subprocess.run([sys.executable,"-I",*map(str,arguments)],cwd=project,
            env={**os.environ,"PYTHONUTF8":"1","PYTHONPATH":"","MPLCONFIGDIR":str(out/"matplotlib-cache")},
            capture_output=True,text=True,encoding="utf-8",timeout=120)
        (out/(label+".stdout.txt")).write_text(result.stdout,encoding="utf-8")
        (out/(label+".stderr.txt")).write_text(result.stderr,encoding="utf-8")
        commands.append({"label":label,"exit":result.returncode})
        check(label+" command exit",result.returncode==expected)
        return result

    def inspect_pdf(path, label, expected_pages=None):
        reader=PdfReader(path)
        check(label+" expected page count",len(reader.pages)==expected_pages if expected_pages else bool(reader.pages))
        check(label+" has no raster image objects",all(len(page.images)==0 for page in reader.pages))
        form_paths=[]
        visited=set()
        def visit(resources):
            for reference in resources.get("/XObject",{}).values():
                obj=reference.get_object()
                identity=(getattr(reference,"idnum",None),getattr(reference,"generation",None)) if hasattr(reference,"idnum") else id(obj)
                if identity in visited:
                    continue
                visited.add(identity)
                if obj.get("/Subtype")=="/Form":
                    operators=[op for _,op in ContentStream(obj,reader).operations]
                    bounds=obj.get("/BBox",[0,0,0,0])
                    if float(bounds[2])-float(bounds[0])>100 and float(bounds[3])-float(bounds[1])>100:
                        form_paths.append(sum(op in {b"m",b"l",b"c",b"re"} for op in operators))
                    visit(obj.get("/Resources",{}))
        for page in reader.pages:
            visit(page["/Resources"])
        check(label+" contains both charts as vector forms",len([n for n in form_paths if n>100])>=2 if expected_pages==2 else any(n>100 for n in form_paths))
        text="\n".join(page.extract_text() for page in reader.pages)
        (out/(label+"-pypdf.txt")).write_text(text,encoding="utf-8")
        with pdfium.PdfDocument(str(path)) as document:
            other=[]
            for index in range(len(document)):
                page=document[index]
                textpage=page.get_textpage()
                other.append(textpage.get_text_range())
                boxes=[textpage.get_charbox(i) for i in range(textpage.count_chars())]
                painted=[(l,b,r,t) for l,b,r,t in boxes if r>l and t>b]
                check(f"{label} page {index+1} text stays inside the page",bool(painted) and all(l>=0 and b>=0 and r<=page.get_width()+.2 and t<=page.get_height()+.2 for l,b,r,t in painted))
                page.render(scale=110/72).to_pil().save(out/f"{label}-pdfium-{index+1}.png")
                textpage.close()
                page.close()
        other="\n".join(other)
        (out/(label+"-pdfium.txt")).write_text(other,encoding="utf-8")
        check(label+" text has no replacement glyph", "\ufffd" not in text+other)
        return reader,text,other,form_paths

    try:
        manifest=json.loads((ASSETS/"source.json").read_text(encoding="utf-8"))
        archive_path=args.zip or ASSETS/"project.zip"
        check("ZIP hash matches source manifest",sha256(archive_path.read_bytes()).hexdigest()==manifest["zip_sha256"])
        with zipfile.ZipFile(archive_path) as archive:
            expected={"matplotlib-report/"+item["path"] for item in manifest["files"]}
            check("exact ZIP file set",set(archive.namelist())==expected)
            check("ZIP paths stay within project",all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in expected))
            for item in manifest["files"]:
                data=archive.read("matplotlib-report/"+item["path"])
                check("source bytes: "+item["path"],data==(ROOT/"examples/matplotlib-report"/item["path"]).read_bytes() and sha256(data).hexdigest()==item["sha256"])
            archive.extractall(extracted)
        project=extracted/"matplotlib-report"
        for line in (project/"requirements.txt").read_text().splitlines():
            name,pin=line.split("==")
            check("installed dependency: "+name,version(name)==pin)
        run("render",["report.py","--out",out/"render"])
        run("replay",["report.py","--out",out/"replay"])
        for name in ("volume.svg","regions.svg","report.pdf","preview/report_page1.png","preview/report_page2.png"):
            check("repeated bytes: "+name,(out/"render"/name).read_bytes()==(out/"replay"/name).read_bytes())
        for name in ("volume","regions"):
            svg=ET.parse(out/"render"/(name+".svg"))
            tags=[element.tag.split("}")[-1] for element in svg.iter()]
            check(name+" SVG has paths without raster images or text-font dependencies",tags.count("path")>20 and "image" not in tags and "text" not in tags)
        check("document font covers the sample",json.loads((out/"render/glyph-report.json").read_text())==[])
        reader,text,other,paths=inspect_pdf(out/"render/report.pdf","report",2)
        compact=lambda value:"".join(value.split())
        for phrase in ("FIELDNOTE LOGISTICS","261,400","+91.3%","+5.9%","61,400","58,000","34,000","32,100","35,400","39,000","31,200","46,000","48,200","52,000","53,100","North: 15,300","South: 18,700","East: 12,100","West: 15,300","1 / 2","2 / 2"):
            check("selectable data in both readers: "+phrase,compact(phrase) in compact(text) and compact(phrase) in compact(other))
        check("A4 pages",all(abs(float(p.mediabox.width)-595.276)<.2 and abs(float(p.mediabox.height)-841.89)<.2 for p in reader.pages))
        check("rendered total is calculated from data",json.loads((out/"render/render.json").read_text())["total_deliveries"]==261400)

        snippets=re.findall(r"```python\n(.*?)```",(ROOT/"docs/guides/matplotlib-pdf.md").read_text(encoding="utf-8"),re.S)
        check("one executable guide snippet",len(snippets)==1)
        (project/"guide.py").write_text(snippets[0],encoding="utf-8")
        run("guide",["guide.py"])
        _,guide_text,guide_other,_=inspect_pdf(project/"chart-report.pdf","guide",1)
        check("guide PDF includes selectable chart values",all(value in guide_text and value in guide_other for value in ("32,000","35,000","41,000")))

        data=json.loads((project/"data.json").read_text())
        data["organization"]="Mira & Co <Research>"
        data["months"]=[{"label":"First","planned":0,"delivered":0},{"label":"Final","planned":100,"delivered":125}]
        data["regions"]=[{"label":"A & B","delivered":75},{"label":"C < D","delivered":50}]
        edited=project/"edited.json"
        edited.write_text(json.dumps(data),encoding="utf-8")
        css=project/"report.css"
        css.write_text(css.read_text().replace("#d7f266","#f7d3b5"),encoding="utf-8")
        run("edited",["report.py","--data",edited,"--out",out/"edited"])
        _,edited_text,edited_other,_=inspect_pdf(out/"edited/report.pdf","edited",2)
        for phrase in ("Mira & Co <Research>","A & B: 75","C < D: 50","+25.0%","n/a"):
            check("customized PDF data: "+phrase,compact(phrase) in compact(edited_text) and compact(phrase) in compact(edited_other))
        check("changed data and styling change PDF",(out/"edited/report.pdf").read_bytes()!=(out/"render/report.pdf").read_bytes())
        for label,value,message in (("negative-count",-1,"nonnegative integer"),("boolean-count",True,"nonnegative integer"),("inconsistent-total",126,"Regional deliveries must sum")):
            data["months"][-1]["delivered"]=value
            edited.write_text(json.dumps(data),encoding="utf-8")
            result=run(label,["report.py","--data",edited,"--out",out/label],expected=1)
            check(label+" rejected before PDF creation",message in result.stderr and not (out/label/"report.pdf").exists())
        report.update(zip_sha256=manifest["zip_sha256"],pdf_sha256=sha256((out/"render/report.pdf").read_bytes()).hexdigest(),
                      pages=2,raster_image_objects=0,chart_form_path_operators=paths,
                      svg_sha256={name:sha256((out/"render"/(name+".svg")).read_bytes()).hexdigest() for name in ("volume","regions")},
                      scope="The actual ZIP and guide snippet with fictional data: vector chart objects, selectable values in two readers, repeated bytes, customization and invalid-data failures. No arbitrary Matplotlib feature, PDF conformance or cross-version equivalence claim.")
        if args.update_assets:
            shutil.copyfile(out/"render/report.pdf",ASSETS/"report.pdf")
            for index in (1,2):
                shutil.copyfile(out/f"render/preview/report_page{index}.png",ASSETS/f"report-{index}.png")
        else:
            check("published PDF matches this render",(ASSETS/"report.pdf").read_bytes()==(out/"render/report.pdf").read_bytes())
        report["ok"]=True
        if args.update_assets:
            (ASSETS/"verification.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8",newline="\n")
        return report
    finally:
        (out/"verification.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=ROOT/"output/matplotlib-verification")
    parser.add_argument("--zip",type=Path)
    parser.add_argument("--update-assets",action="store_true")
    result=verify(parser.parse_args())
    print(json.dumps({"ok":result["ok"],"checks":len(result["checks"]),"pdf_sha256":result["pdf_sha256"]}))
