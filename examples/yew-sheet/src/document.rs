use serde::Deserialize;
use yew::prelude::*;

#[derive(Clone, PartialEq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SheetData {
    pub series: String,
    pub title: String,
    pub subtitle: String,
    pub starting_stack: String,
    pub table_size: String,
    pub registration: String,
    pub rows: Vec<ScheduleRow>,
    pub notes: Vec<String>,
}

#[derive(Clone, PartialEq, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum ScheduleRow {
    Level {
        number: u16,
        minutes: u16,
        game: String,
        stakes: String,
        ante: String,
    },
    Break {
        minutes: u16,
        label: String,
    },
}

#[derive(Clone, PartialEq, Properties)]
pub struct SheetProps {
    pub data: SheetData,
}

#[component]
pub fn StructureSheet(props: &SheetProps) -> Html {
    let data = &props.data;
    html! {
        <main class="sheet">
            <header class="masthead">
                <p class="eyebrow">{&data.series}</p>
                <h1>{&data.title}</h1>
                <p class="subtitle">{&data.subtitle}</p>
            </header>
            <dl class="facts">
                <div><dt>{"Starting stack"}</dt><dd>{&data.starting_stack}</dd></div>
                <div><dt>{"Table size"}</dt><dd>{&data.table_size}</dd></div>
                <div><dt>{"Registration"}</dt><dd>{&data.registration}</dd></div>
            </dl>
            <section aria-labelledby="schedule-title">
                <h2 id="schedule-title">{"The rotation"}</h2>
                <div class="table-scroll" tabindex="0" role="region" aria-label="Schedule table">
                    <table>
                        <caption>{"Levels, stakes and scheduled breaks"}</caption>
                        <thead><tr>
                            <th scope="col">{"Level"}</th>
                            <th scope="col">{"Minutes"}</th>
                            <th scope="col">{"Game"}</th>
                            <th scope="col">{"Blinds / bets"}</th>
                            <th scope="col">{"Ante"}</th>
                        </tr></thead>
                        <tbody>{for data.rows.iter().map(|row| match row {
                            ScheduleRow::Level {number, minutes, game, stakes, ante} => html! {
                                <tr class="level">
                                    <th scope="row">{number}</th><td>{minutes}</td>
                                    <td>{game}</td><td class="numeric">{stakes}</td><td class="numeric">{ante}</td>
                                </tr>
                            },
                            ScheduleRow::Break {minutes, label} => html! {
                                <tr class="break"><th colspan="5" scope="row">
                                    <span class="break-label">{label}</span>{" · "}{minutes}{" minute break"}
                                </th></tr>
                            },
                        })}</tbody>
                    </table>
                </div>
            </section>
            <section class="notes" aria-labelledby="notes-title">
                <h2 id="notes-title">{"Before you begin"}</h2>
                <ul>{for data.notes.iter().map(|note| html! { <li>{note}</li> })}</ul>
            </section>
            <footer><p>{"Illustrative structure · synthetic event data"}</p></footer>
        </main>
    }
}

#[derive(Clone, PartialEq, Properties)]
#[cfg(not(target_arch = "wasm32"))]
struct DocumentProps {
    data: SheetData,
    styled: bool,
}

#[cfg(not(target_arch = "wasm32"))]
#[component]
fn SheetDocument(props: &DocumentProps) -> Html {
    html! {
        <html lang="en">
            <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <title>{&props.data.title}</title>
                if props.styled { <link rel="stylesheet" href="style.css" /> }
            </head>
            <body><StructureSheet data={props.data.clone()} /></body>
        </html>
    }
}

#[cfg(not(target_arch = "wasm32"))]
pub async fn to_html(data: SheetData, styled: bool) -> String {
    let markup =
        yew::ServerRenderer::<SheetDocument>::with_props(move || DocumentProps { data, styled })
            .hydratable(false)
            .render()
            .await;
    format!("<!doctype html>\n{markup}\n")
}
