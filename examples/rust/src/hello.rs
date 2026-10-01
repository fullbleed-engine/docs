use fullbleed::FullBleed;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let html = "<h1>Invoice INV-1042</h1><p>Consulting: USD 1,200.00</p>";
    let css = "@page { size: A4; margin: 20mm; } h1 { color: #175c52; }";
    let engine = FullBleed::builder().build()?;
    let pdf = engine.render_to_buffer(html, css)?;
    std::fs::write("invoice.pdf", pdf)?;
    Ok(())
}
