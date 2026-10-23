mod document;

use document::{SheetData, to_html};
use fullbleed::{Asset, AssetBundle, AssetKind, FullBleed};
use std::{error::Error, fs, path::PathBuf};

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    let [input, output] = args.as_slice() else {
        return Err("Usage: fullbleed-yew-sheet INPUT.json NEW_OUTPUT_DIRECTORY".into());
    };
    if output.exists() {
        return Err(
            "Choose a new output directory so an older document cannot be overwritten.".into(),
        );
    }
    let data: SheetData = serde_json::from_slice(&fs::read(input)?)?;
    if data.rows.is_empty() || data.rows.len() > 200 {
        return Err("Supply between 1 and 200 schedule rows.".into());
    }
    let html = to_html(data.clone(), true).await;
    let unstyled = to_html(data, false).await;
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let css = fs::read_to_string(root.join("style.css"))?;
    let font_files = [
        ("Inter", "Inter-Variable.ttf"),
        ("DM Serif Display", "DMSerifDisplay-Regular.ttf"),
    ];
    let mut fonts = AssetBundle::default();
    for (family, filename) in font_files {
        fonts.add(Asset::new(
            family.into(),
            AssetKind::Font,
            fs::read(root.join("fonts").join(filename))?,
            None,
            true,
        ));
    }
    let engine = FullBleed::builder().register_bundle(fonts).build()?;
    let (pdf, glyphs) = engine.render_with_glyph_report(&unstyled, &css)?;
    if !glyphs.missing().is_empty() {
        return Err("The bundled fonts do not cover all document characters.".into());
    }
    fs::create_dir_all(output.join("fonts"))?;
    fs::write(output.join("document.html"), html)?;
    fs::write(output.join("unstyled.html"), unstyled)?;
    fs::write(output.join("style.css"), css)?;
    fs::write(output.join("document.pdf"), pdf)?;
    for (_, filename) in font_files {
        fs::copy(
            root.join("fonts").join(filename),
            output.join("fonts").join(filename),
        )?;
    }
    for notice in ["Inter-OFL.txt", "DMSerifDisplay-OFL.txt"] {
        fs::copy(
            root.join("fonts").join(notice),
            output.join("fonts").join(notice),
        )?;
    }
    let pages = engine.render_finalized_pdf_image_pages(output.join("document.pdf"), 96)?;
    for (index, png) in pages.iter().enumerate() {
        fs::write(output.join(format!("page-{}.png", index + 1)), png)?;
    }
    println!(
        "{} PDF page(s), styled HTML and unstyled HTML written to {}",
        pages.len(),
        output.display()
    );
    Ok(())
}
