// SPDX-License-Identifier: MIT
// An optional website adapter around the unchanged published Rust crate.
use fullbleed::{Asset, AssetBundle, AssetKind, FullBleed};

fn render() -> Result<(), Box<dyn std::error::Error>> {
    let html = std::fs::read_to_string("input.html")?;
    let css = std::fs::read_to_string("style.css")?;
    if html.len() + css.len() > 200_000 {
        return Err("This playground accepts up to 200 KB of HTML and CSS combined.".into());
    }
    let mut builder = FullBleed::builder();
    for name in [
        "Inter-Variable.ttf",
        "DMSerifDisplay-Regular.ttf",
        "DMSerifDisplay-Italic.ttf",
        "BebasNeue-Regular.ttf",
    ] {
        builder = builder.register_font_file(name);
    }
    match std::fs::read_to_string("local-fonts.txt") {
        Ok(paths) => {
            let names: Vec<_> = paths.lines().collect();
            let mut local_fonts = AssetBundle::default();
            if names.len() > 16 {
                return Err("This playground accepts up to 16 local assets.".into());
            }
            for path in names {
                let name = path.strip_prefix("assets/").ok_or("Invalid local font path.")?;
                let lower = name.to_ascii_lowercase();
                if name.is_empty() || name.contains(['/', '\\', ':'])
                    || name.chars().any(char::is_control)
                    || !(lower.ends_with(".ttf") || lower.ends_with(".otf"))
                {
                    return Err("Invalid local font path.".into());
                }
                local_fonts.add(Asset::new(path.to_string(), AssetKind::Font,
                    std::fs::read(path)?, None, true));
            }
            builder = builder.register_bundle(local_fonts);
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(error) => return Err(error.into()),
    }
    let engine = builder.build()?;
    let (pdf, glyphs, document) = engine.render_with_glyph_report_and_document(&html, &css)?;
    if document.pages.is_empty() || document.pages.len() > 6 {
        return Err(
            "This playground supports 1 to 6 pages. Use Fullbleed locally for larger documents."
                .into(),
        );
    }
    std::fs::write("output.pdf", pdf)?;
    let pages = engine.render_finalized_pdf_image_pages("output.pdf", 96)?;
    if pages.len() != document.pages.len() {
        return Err("The PDF preview page count differs from the document.".into());
    }
    for (index, png) in pages.iter().enumerate() {
        std::fs::write(format!("page-{}.png", index + 1), png)?;
    }
    std::fs::write(
        "result.json",
        format!(
            "{{\"engine\":\"2.5.49\",\"pages\":{},\"missing_glyphs\":{}}}",
            pages.len(),
            glyphs.missing().len()
        ),
    )?;
    Ok(())
}

fn main() {
    if let Err(error) = render() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
