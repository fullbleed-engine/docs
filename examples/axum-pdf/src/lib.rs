use axum::{
    Json, Router,
    extract::{DefaultBodyLimit, State, rejection::JsonRejection},
    http::{HeaderValue, StatusCode, header},
    response::{Html, IntoResponse, Response},
    routing::{get, post},
};
use fullbleed::{Asset, AssetBundle, AssetKind, FullBleed};
use minijinja::{AutoEscape, Environment, UndefinedBehavior, value::Serde};
use serde::{Deserialize, Serialize};
use std::{fs, path::Path, sync::Arc};
use tokio::sync::Semaphore;

const MAX_BODY_BYTES: usize = 64 * 1024;
const MAX_ITEMS: usize = 200;
const RENDER_SLOTS: usize = 2;

#[derive(Clone)]
pub struct AppState {
    renderer: Arc<InvoiceRenderer>,
    slots: Arc<Semaphore>,
}

impl AppState {
    pub fn load(directory: &Path) -> Result<Self, Box<dyn std::error::Error>> {
        let mut assets = AssetBundle::default();
        for (family, file) in [
            ("Inter", "Inter-Variable.ttf"),
            ("DM Serif Display", "DMSerifDisplay-Regular.ttf"),
            ("Bebas Neue", "BebasNeue-Regular.ttf"),
        ] {
            assets.add(Asset::new(
                family.into(),
                AssetKind::Font,
                fs::read(directory.join("fonts").join(file))?,
                None,
                true,
            ));
        }
        let engine = FullBleed::builder().register_bundle(assets).build()?;
        let mut templates = Environment::new();
        templates.set_auto_escape_callback(|_| AutoEscape::Html);
        templates.set_undefined_behavior(UndefinedBehavior::Strict);
        templates.add_template_owned(
            "invoice.html",
            fs::read_to_string(directory.join("templates/invoice.html"))?,
        )?;
        let css = fs::read_to_string(directory.join("templates/invoice.css"))?;
        Ok(Self {
            renderer: Arc::new(InvoiceRenderer {
                engine,
                templates,
                css,
            }),
            slots: Arc::new(Semaphore::new(RENDER_SLOTS)),
        })
    }
}

pub fn app(state: AppState) -> Router {
    Router::new()
        .route(
            "/",
            get(|| async { Html(include_str!("../ui/index.html")) }),
        )
        .route(
            "/sample.json",
            get(|| async {
                (
                    [(header::CONTENT_TYPE, "application/json")],
                    include_str!("../sample.json"),
                )
            }),
        )
        .route("/health", get(|| async { "ok" }))
        .route("/invoices/pdf", post(invoice_pdf))
        .layer(DefaultBodyLimit::max(MAX_BODY_BYTES))
        .with_state(state)
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Invoice {
    invoice_number: String,
    issued: String,
    due: String,
    customer: Customer,
    items: Vec<Item>,
    #[serde(default)]
    note: String,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Customer {
    name: String,
    address_lines: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Item {
    description: String,
    quantity: u32,
    unit_price_cents: u64,
}

#[derive(Serialize)]
struct DisplayItem<'a> {
    description: &'a str,
    quantity: u32,
    unit_price: String,
    amount: String,
}

#[derive(Serialize)]
struct Document<'a> {
    invoice: &'a Invoice,
    items: Vec<DisplayItem<'a>>,
    total: String,
}

impl Invoice {
    fn validate(&self) -> Result<(), ApiError> {
        if self.invoice_number.is_empty()
            || self.invoice_number.len() > 32
            || !self
                .invoice_number
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || b"-_".contains(&byte))
        {
            return Err(ApiError::invalid(
                "invoice_number must contain 1–32 ASCII letters, digits, hyphens, or underscores.",
            ));
        }
        for (value, maximum, field) in [
            (self.issued.as_str(), 32, "issued"),
            (self.due.as_str(), 32, "due"),
            (self.customer.name.as_str(), 100, "customer.name"),
        ] {
            text_field(value, maximum, field, false)?;
        }
        text_field(&self.note, 600, "note", true)?;
        if self.customer.address_lines.is_empty() || self.customer.address_lines.len() > 4 {
            return Err(ApiError::invalid(
                "customer.address_lines must contain 1–4 lines.",
            ));
        }
        for line in &self.customer.address_lines {
            text_field(line, 100, "customer.address_lines", false)?;
        }
        if self.items.is_empty() || self.items.len() > MAX_ITEMS {
            return Err(ApiError::invalid("items must contain 1–200 line items."));
        }
        for item in &self.items {
            text_field(&item.description, 200, "items.description", false)?;
            if item.quantity == 0 || item.quantity > 10_000 || item.unit_price_cents > 100_000_000 {
                return Err(ApiError::invalid(
                    "Each quantity must be 1–10000 and unit_price_cents must be 0–100000000.",
                ));
            }
        }
        Ok(())
    }

    fn document(&self) -> Result<Document<'_>, ApiError> {
        let mut total = 0_u64;
        let mut items = Vec::with_capacity(self.items.len());
        for item in &self.items {
            let amount = item
                .unit_price_cents
                .checked_mul(u64::from(item.quantity))
                .ok_or_else(|| ApiError::invalid("Line amount is too large."))?;
            total = total
                .checked_add(amount)
                .ok_or_else(|| ApiError::invalid("Invoice total is too large."))?;
            items.push(DisplayItem {
                description: &item.description,
                quantity: item.quantity,
                unit_price: money(item.unit_price_cents),
                amount: money(amount),
            });
        }
        Ok(Document {
            invoice: self,
            items,
            total: money(total),
        })
    }
}

fn text_field(value: &str, maximum: usize, field: &str, allow_empty: bool) -> Result<(), ApiError> {
    if (!allow_empty && value.trim().is_empty())
        || value.chars().count() > maximum
        || value.chars().any(char::is_control)
    {
        return Err(ApiError::invalid(format!(
            "{field} must be printable text of at most {maximum} characters."
        )));
    }
    Ok(())
}

fn money(cents: u64) -> String {
    let digits = (cents / 100).to_string();
    let mut dollars = String::new();
    for (index, digit) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index) % 3 == 0 {
            dollars.push(',');
        }
        dollars.push(digit);
    }
    format!("{}{}.{:02}", "$", dollars, cents % 100)
}

struct InvoiceRenderer {
    engine: FullBleed,
    templates: Environment<'static>,
    css: String,
}

impl InvoiceRenderer {
    fn render(&self, invoice: &Invoice) -> Result<Vec<u8>, ApiError> {
        let document = invoice.document()?;
        let html = self
            .templates
            .get_template("invoice.html")
            .and_then(|template| template.render(Serde(document)))
            .map_err(|_| ApiError::internal())?;
        let (pdf, glyphs) = self
            .engine
            .render_with_glyph_report(&html, &self.css)
            .map_err(|_| ApiError::internal())?;
        if !glyphs.is_empty() {
            return Err(ApiError::invalid(
                "The configured fonts do not cover every character. Add the required fonts on the server.",
            ));
        }
        Ok(pdf)
    }
}

async fn invoice_pdf(
    State(state): State<AppState>,
    payload: Result<Json<Invoice>, JsonRejection>,
) -> Result<Response, ApiError> {
    let Json(invoice) = payload.map_err(|error| ApiError {
        status: error.status(),
        message: "Send a JSON invoice matching sample.json, within the 64 KiB request limit."
            .into(),
    })?;
    invoice.validate()?;
    let disposition = HeaderValue::from_str(&format!(
        "attachment; filename=\"invoice-{}.pdf\"",
        invoice.invoice_number
    ))
    .map_err(|_| ApiError::invalid("Invalid invoice_number."))?;
    let renderer = state.renderer.clone();
    let pdf = bounded_render(state.slots, move || renderer.render(&invoice)).await?;
    Ok((
        [
            (
                header::CONTENT_TYPE,
                HeaderValue::from_static("application/pdf"),
            ),
            (header::CONTENT_DISPOSITION, disposition),
            (
                header::CACHE_CONTROL,
                HeaderValue::from_static("private, no-store"),
            ),
            (
                header::X_CONTENT_TYPE_OPTIONS,
                HeaderValue::from_static("nosniff"),
            ),
        ],
        pdf,
    )
        .into_response())
}

async fn bounded_render<T: Send + 'static>(
    slots: Arc<Semaphore>,
    render: impl FnOnce() -> Result<T, ApiError> + Send + 'static,
) -> Result<T, ApiError> {
    let permit = slots.try_acquire_owned().map_err(|_| ApiError {
        status: StatusCode::SERVICE_UNAVAILABLE,
        message: "Both render slots are busy. Try again shortly.".into(),
    })?;
    tokio::task::spawn_blocking(move || {
        // A running blocking task cannot be aborted. Its permit stays with the
        // actual job, rather than the HTTP future that may be disconnected.
        let _permit = permit;
        render()
    })
    .await
    .map_err(|_| ApiError::internal())?
}

#[derive(Debug)]
struct ApiError {
    status: StatusCode,
    message: String,
}

impl ApiError {
    fn invalid(message: impl Into<String>) -> Self {
        Self {
            status: StatusCode::UNPROCESSABLE_ENTITY,
            message: message.into(),
        }
    }

    fn internal() -> Self {
        Self {
            status: StatusCode::INTERNAL_SERVER_ERROR,
            message: "The invoice could not be rendered. Check the server template and fonts."
                .into(),
        }
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let busy = self.status == StatusCode::SERVICE_UNAVAILABLE;
        let mut response = (
            self.status,
            Json(serde_json::json!({ "error": self.message })),
        )
            .into_response();
        response
            .headers_mut()
            .insert(header::CACHE_CONTROL, HeaderValue::from_static("no-store"));
        if busy {
            response
                .headers_mut()
                .insert(header::RETRY_AFTER, HeaderValue::from_static("1"));
        }
        response
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn invoice_validation_and_integer_money() {
        let mut invoice: Invoice = serde_json::from_str(include_str!("../sample.json")).unwrap();
        invoice.validate().unwrap();
        assert_eq!(invoice.document().unwrap().total, "$1,870.00");
        assert_eq!(money(1), "$0.01");
        assert_eq!(money(100_001), "$1,000.01");
        invoice.invoice_number = "bad\r\nheader".into();
        assert!(invoice.validate().is_err());
        invoice.invoice_number = "NS-1042".into();
        invoice.items[0].quantity = 0;
        assert!(invoice.validate().is_err());
        invoice.items[0].quantity = 8;
        invoice.items[0].unit_price_cents = u64::MAX;
        assert!(invoice.validate().is_err());
    }

    #[test]
    fn template_values_are_escaped_and_not_evaluated_as_templates() {
        let mut env = Environment::new();
        env.set_auto_escape_callback(|_| AutoEscape::Html);
        env.add_template("test.html", "<p>{{ value }}</p>").unwrap();
        let rendered = env
            .get_template("test.html")
            .unwrap()
            .render(minijinja::context! { value => "<b>A & B</b> {{ 7 * 7 }}" })
            .unwrap();
        assert!(rendered.contains("&lt;b&gt;"));
        assert!(rendered.contains("A &amp; B"));
        assert!(rendered.contains("{{ 7 * 7 }}"));
    }

    #[tokio::test]
    async fn busy_capacity_rejects_without_starting_another_job() {
        let slots = Arc::new(Semaphore::new(1));
        let held = slots.clone().acquire_owned().await.unwrap();
        let error = bounded_render::<()>(slots.clone(), || panic!("must not start"))
            .await
            .unwrap_err();
        assert_eq!(error.status, StatusCode::SERVICE_UNAVAILABLE);
        assert_eq!(error.into_response().headers()[header::RETRY_AFTER], "1");
        drop(held);
        assert_eq!(bounded_render(slots, || Ok(42)).await.unwrap(), 42);
    }

    #[tokio::test]
    async fn disconnected_request_keeps_its_slot_until_worker_finishes() {
        let slots = Arc::new(Semaphore::new(1));
        let (started_tx, started_rx) = tokio::sync::oneshot::channel();
        let (finish_tx, finish_rx) = std::sync::mpsc::channel();
        let request = tokio::spawn(bounded_render(slots.clone(), move || {
            started_tx.send(()).unwrap();
            finish_rx.recv_timeout(Duration::from_secs(5)).unwrap();
            Ok(())
        }));
        started_rx.await.unwrap();
        request.abort();
        assert!(request.await.unwrap_err().is_cancelled());
        assert_eq!(slots.available_permits(), 0);
        assert_eq!(
            bounded_render(slots.clone(), || Ok(()))
                .await
                .unwrap_err()
                .status,
            StatusCode::SERVICE_UNAVAILABLE
        );
        finish_tx.send(()).unwrap();
        let returned = tokio::time::timeout(Duration::from_secs(5), slots.acquire())
            .await
            .unwrap()
            .unwrap();
        drop(returned);
        assert_eq!(slots.available_permits(), 1);
    }

    #[tokio::test]
    async fn errors_and_panics_release_capacity() {
        let slots = Arc::new(Semaphore::new(1));
        let error = bounded_render::<()>(slots.clone(), || Err(ApiError::invalid("test")))
            .await
            .unwrap_err();
        assert_eq!(error.status, StatusCode::UNPROCESSABLE_ENTITY);
        assert_eq!(slots.available_permits(), 1);
        let error = bounded_render::<()>(slots.clone(), || panic!("controlled worker panic"))
            .await
            .unwrap_err();
        assert_eq!(error.status, StatusCode::INTERNAL_SERVER_ERROR);
        assert_eq!(slots.available_permits(), 1);
        assert!(bounded_render(slots, || Ok(())).await.is_ok());
    }
}
