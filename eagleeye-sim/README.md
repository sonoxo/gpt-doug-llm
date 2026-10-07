# GPT-DOUG // EAGLEEYE SIM

A safe mixed-reality robotics and public-data simulation stack.

## What it is
- Browser helmet HUD with synthetic/public-data overlays
- Rust gateway shaped around the Lattice SDK event model
- ROS2/robotics adapter boundary for RoboParty digital-twin data
- Internet connector registry for public APIs and user-authorized services
- Human-first policy gates and audit events
- No weapon firing, target selection, strike planning, or autonomous engagement

## Architecture
```
Public APIs / Authorized services / ROS2 sim
                |
                v
          Connector Gateway
                |
                v
        Ontology + Event Bus
   Entity / Sensor / Track / Alert
                |
         +------+------+
         |             |
         v             v
   EagleEye HUD   Robot Digital Twin
```

## Quick start
```bash
cd eagleeye-sim
cp .env.example .env
docker compose up --build
```

Frontend: http://localhost:4173
Backend API: http://localhost:8787
Health: http://localhost:8787/health

## Data boundary
This project supports synthetic feeds, public internet sources, and user-authorized connectors. It deliberately excludes real weapon-control paths and real-person targeting.
