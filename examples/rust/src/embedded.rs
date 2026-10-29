use fullbleed::{Asset, AssetBundle, AssetKind, FullBleed};
use std::{fs, path::Path};

const FONTS: [(&str, &[u8]); 4] = [
    ("Inter", include_bytes!("../fonts/Inter-Variable.ttf")),
    (
        "DMSerifDisplay-Regular",
        include_bytes!("../fonts/DMSerifDisplay-Regular.ttf"),
    ),
    (
        "DMSerifDisplay-Italic",
        include_bytes!("../fonts/DMSerifDisplay-Italic.ttf"),
    ),
    (
        "BebasNeue",
        include_bytes!("../fonts/BebasNeue-Regular.ttf"),
    ),
];

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    let [document, output_dir] = args.as_slice() else {
        return Err("Usage: embedded invoice|report OUTPUT_DIR".into());
    };
    let (html, css) = match document.to_str() {
        Some("invoice") => (
            include_str!("../templates/invoice.html"),
            include_str!("../templates/invoice.css"),
        ),
        Some("report") => (
            include_str!("../templates/report.html"),
            include_str!("../templates/report.css"),
        ),
        _ => return Err("Choose invoice or report.".into()),
    };
    let output_dir = Path::new(output_dir);
    if output_dir.exists() {
        return Err("OUTPUT_DIR already exists. Choose a new directory.".into());
    }

    let mut assets = AssetBundle::default();
    for (name, bytes) in FONTS {
        assets.add(Asset::new(
            name.into(),
            AssetKind::Font,
            bytes.to_vec(),
            None,
            true,
        ));
    }
    let engine = FullBleed::builder().register_bundle(assets).build()?;
    let (pdf, glyphs) = engine.render_with_glyph_report(html, css)?;
    if !glyphs.missing().is_empty() {
        return Err("The bundled fonts do not cover all document characters.".into());
    }

    if let Some(parent) = output_dir.parent().filter(|p| !p.as_os_str().is_empty()) {
        fs::create_dir_all(parent)?;
    }
    fs::create_dir(output_dir)?;
    fs::write(output_dir.join("document.pdf"), pdf)?;
    let pages = engine.render_finalized_pdf_image_pages(output_dir.join("document.pdf"), 96)?;
    for (index, png) in pages.iter().enumerate() {
        fs::write(output_dir.join(format!("page-{}.png", index + 1)), png)?;
    }
    println!(
        "Rendered {} page(s) to {}",
        pages.len(),
        output_dir.display()
    );
    Ok(())
}
