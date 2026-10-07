// Adapter contracts for future integrations.
// Deliberately data-only: these interfaces ingest observations and state;
// they do not expose weapon or payload-control commands.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Observation {
    pub source: String,
    pub object_type: String,
    pub label: String,
    pub lat: Option<f64>,
    pub lon: Option<f64>,
    pub altitude_m: Option<f64>,
    pub confidence: Option<f64>,
    pub provenance: String,
}

pub trait ObservationSource {
    fn source_name(&self) -> &'static str;
    fn is_simulation(&self) -> bool;
}
