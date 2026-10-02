use fullbleed::FullBleed;
use std::{fs, path::PathBuf};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    let [html_path, css_path, fonts_dir, output_dir] = args.as_slice() else {
        return Err("Usage: from-files HTML CSS FONTS_DIR OUTPUT_DIR".into());
    };
    let html = fs::read_to_string(html_path)?;
    let css = fs::read_to_string(css_path)?;
    let mut builder = FullBleed::builder();
    for name in [
        "Inter-Variable.ttf",
        "DMSerifDisplay-Regular.ttf",
        "DMSerifDisplay-Italic.ttf",
        "BebasNeue-Regular.ttf",
    ] {
        let font = fonts_dir.join(name);
        fs::metadata(&font)?;
        builder = builder.register_font_file(font);
    }
    let engine = builder.build()?;
    let (pdf, glyphs) = engine.render_with_glyph_report(&html, &css)?;
    if !glyphs.missing().is_empty() {
        return Err("The supplied fonts do not cover all document characters.".into());
    }
    fs::create_dir_all(output_dir)?;
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
