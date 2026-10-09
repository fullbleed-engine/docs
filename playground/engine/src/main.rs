// SPDX-License-Identifier: MIT
// An optional website adapter around the unchanged published Rust crate.
use fullbleed::FullBleed;

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
            "{{\"engine\":\"2.5.22\",\"pages\":{},\"missing_glyphs\":{}}}",
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
