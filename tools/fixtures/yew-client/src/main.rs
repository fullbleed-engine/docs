mod document;

use document::{SheetData, StructureSheet};
use yew::prelude::*;

#[component]
fn Preview() -> Html {
    let data: SheetData = serde_json::from_str(include_str!("../data.json")).unwrap();
    html! { <StructureSheet {data} /> }
}

fn main() {
    yew::Renderer::<Preview>::new().render();
}
