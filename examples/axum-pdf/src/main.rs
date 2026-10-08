use fullbleed_axum_starter::{AppState, app};
use std::{io::Write, net::SocketAddr, path::Path};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Loopback by default. Add your application's authentication and deployment
    // controls before exposing this example beyond your own machine.
    let address: SocketAddr = std::env::var("PDF_BIND")
        .unwrap_or_else(|_| "127.0.0.1:3000".into())
        .parse()?;
    let state = AppState::load(Path::new("."))?;
    let listener = tokio::net::TcpListener::bind(address).await?;
    println!("Listening on http://{}", listener.local_addr()?);
    std::io::stdout().flush()?;
    axum::serve(listener, app(state))
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
