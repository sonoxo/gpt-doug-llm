use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EyeFamily {
    Environment,
    Mobility,
    Robotics,
    Infrastructure,
    CyberDefense,
    DataIntegrity,
    Operations,
    Safety,
    Provenance,
    Simulation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TechnicalEye {
    pub id: u16,
    pub name: String,
    pub family: EyeFamily,
    pub enabled: bool,
    pub source_scope: String,
    pub max_age_seconds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardianFinding {
    pub id: String,
    pub eye_id: u16,
    pub title: String,
    pub category: String,
    pub severity: u8,
    pub confidence: f32,
    pub horizon_seconds: u64,
    pub evidence_count: u32,
    pub provenance_quality: f32,
    pub freshness_penalty: f32,
    pub summary: String,
    pub recommendation: GuardianRecommendation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardianRecommendation {
    pub action: String,
    pub rationale: String,
    pub reversible: bool,
    pub human_approval_required: bool,
    pub escalation: String,
}

pub fn default_eyes() -> Vec<TechnicalEye> {
    let families = [
        EyeFamily::Environment,
        EyeFamily::Mobility,
        EyeFamily::Robotics,
        EyeFamily::Infrastructure,
        EyeFamily::CyberDefense,
        EyeFamily::DataIntegrity,
        EyeFamily::Operations,
        EyeFamily::Safety,
        EyeFamily::Provenance,
        EyeFamily::Simulation,
    ];

    (0..100).map(|i| {
        let family = families[(i as usize) % families.len()].clone();
        TechnicalEye {
            id: i + 1,
            name: format!("GUARDIAN-EYE-{:03}", i + 1),
            family,
            enabled: true,
            source_scope: "public/synthetic/user-authorized".to_string(),
            max_age_seconds: 300,
        }
    }).collect()
}

pub fn score(severity: u8, confidence: f32, provenance_quality: f32, freshness_penalty: f32) -> f32 {
    let sev = severity as f32 / 100.0;
    (sev * confidence * provenance_quality * (1.0 - freshness_penalty.clamp(0.0, 0.9))).clamp(0.0, 1.0)
}
