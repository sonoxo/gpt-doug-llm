# Architecture

## 1. Helmet frontend
React/Vite HUD with WebSocket streaming, compass, ontology graph, entity overlays, and device/system status.

## 2. Rust event gateway
Axum service normalizing all incoming events into a small ontology:
- Entity
- Sensor
- Observation
- Track
- Robot
- Waypoint
- Alert

The existing `sonoxo/lattice-sdk-rust` repository can be used behind an optional adapter when the operator has legitimate API access. Its README documents entity-event polling, custom base URLs, retry controls, timeouts, and custom HTTP clients.

## 3. RoboParty adapter
Recommended integration surfaces discovered in RoboParty:
- `roboto_origin`: aggregate platform
- `rpo_description`: URDF/MJCF digital-twin assets
- `roboparty_navigation`: ROS2 Humble + Nav2 + localization
- `roboparty_deploy`: deployment/middleware
- `roboparty_firmware`: embedded edge boundary
- `gpt-6-astra-real2sim-workflow`: real-to-sim scene generation

Connect ROS2 via rosbridge or a dedicated gRPC/WebSocket relay. By default the web stack consumes simulated robot state only.

## 4. Internet connector policy
The gateway may ingest:
- public weather/disaster APIs
- public geospatial datasets
- user-authorized SaaS/API connections
- local sensors and robot simulators

Every connector must declare provenance, rate limit, auth scope, freshness, and whether the feed is simulated/public/private.

## 5. Hard safety boundary
Never route these categories to hardware:
- weapon firing
- payload release
- autonomous target selection
- strike planning
- lethal engagement
- real-person hostile classification

For training, map detections to neutral classes such as UNKNOWN, VEHICLE, ROBOT, HAZARD, WAYPOINT, or TRAINING OBJECT.
