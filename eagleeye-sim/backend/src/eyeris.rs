use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EyerisLayerKind {
    Weather,
    Hazard,
    Navigation,
    RobotTelemetry,
    PublicTraffic,
    PublicAviation,
    PublicMaritime,
    UserAuthorizedSensor,
    SyntheticTraining,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EyerisLayer {
    pub id: String,
    pub label: String,
    pub kind: EyerisLayerKind,
    pub enabled: bool,
    pub source: String,
    pub provenance: String,
    pub freshness_seconds: u64,
    pub public_or_authorized: bool,
    pub privacy_mode: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArAnnotation {
    pub id: String,
    pub label: String,
    pub category: String,
    pub lat: Option<f64>,
    pub lon: Option<f64>,
    pub altitude_m: Option<f64>,
    pub bearing_deg: Option<f64>,
    pub distance_m: Option<f64>,
    pub confidence: Option<f64>,
    pub source: String,
    pub privacy_safe: bool,
}

// Intentionally excluded from the schema:
// weapon aimpoints, ballistic solutions, target priorities,
// hostile-person labels, autonomous engagement commands.
