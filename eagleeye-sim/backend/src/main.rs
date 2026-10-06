use axum::{
    extract::ws::{Message, WebSocket, WebSocketUpgrade},
    response::IntoResponse,
    routing::get,
    Json, Router,
};
use chrono::Utc;
use rand::Rng;
use serde::Serialize;
use std::{net::SocketAddr, time::Duration};
use tower_http::cors::{Any, CorsLayer};
use uuid::Uuid;

#[derive(Serialize, Clone)]
struct Entity {
    id: Uuid,
    kind: &'static str,
    label: String,
    lat: f64,
    lon: f64,
    alt_m: f64,
    heading_deg: f64,
    confidence: f64,
    source: &'static str,
    classification: &'static str,
    ts: String,
}

#[derive(Serialize)]
struct Health {
    ok: bool,
    mode: &'static str,
    service: &'static str,
}

async fn health() -> Json<Health> {
    Json(Health { ok: true, mode: "SIMULATION", service: "GPT-DOUG EAGLEEYE" })
}

async fn entities() -> Json<Vec<Entity>> {
    Json(make_entities())
}

async fn ws(ws: WebSocketUpgrade) -> impl IntoResponse {
    ws.on_upgrade(stream)
}

async fn stream(mut socket: WebSocket) {
    loop {
        let payload = serde_json::json!({
            "type": "entity_batch",
            "simulation": true,
            "ts": Utc::now().to_rfc3339(),
            "entities": make_entities()
        });
        if socket.send(Message::Text(payload.to_string())).await.is_err() {
            break;
        }
        tokio::time::sleep(Duration::from_millis(900)).await;
    }
}

fn make_entities() -> Vec<Entity> {
    let mut rng = rand::thread_rng();
    let center_lat = 37.5407_f64;
    let center_lon = -77.4360_f64;
    let labels = [
        ("robot", "RPO-01", "roboparty"),
        ("sensor", "LIDAR-ALPHA", "sim"),
        ("vehicle", "SERVICE-UNIT-7", "public-demo"),
        ("hazard", "ROAD-OBSTRUCTION", "synthetic"),
        ("waypoint", "NAV-WP-03", "operator"),
    ];

    labels.into_iter().map(|(kind, label, source)| Entity {
        id: Uuid::new_v4(),
        kind,
        label: label.to_string(),
        lat: center_lat + rng.gen_range(-0.012..0.012),
        lon: center_lon + rng.gen_range(-0.018..0.018),
        alt_m: rng.gen_range(0.0..120.0),
        heading_deg: rng.gen_range(0.0..360.0),
        confidence: rng.gen_range(0.72..0.99),
        source,
        classification: "TRAINING",
        ts: Utc::now().to_rfc3339(),
    }).collect()
}

#[tokio::main]
async fn main() {
    let cors = CorsLayer::new().allow_origin(Any).allow_methods(Any).allow_headers(Any);
    let app = Router::new()
        .route("/health", get(health))
        .route("/api/entities", get(entities))
        .route("/ws", get(ws))
        .layer(cors);

    let addr: SocketAddr = "0.0.0.0:8787".parse().unwrap();
    println!("EAGLEEYE SIM API listening on {addr}");
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
