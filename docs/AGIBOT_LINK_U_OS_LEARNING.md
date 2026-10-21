# GPT-Doug-LLM learns AGIBOT Link-U OS and X1 (2026-10-21)

**Status:** versioned, offline, provenance-backed **research reference**. This change does not retrain model weights, run robotic simulations, install AGIBOT code, connect a robot, configure AimRT, or deploy to XUNIA.

## What the supplied URL means

The user-supplied [AGIBOT Open Source Doc](https://www.agibot.com/DOCS/OS) currently shows the **AGIBOT X1 Development Guide** and links to the separate **Link-U-OS** page. Do not mistake X1 source assets for an installed Link-U OS image or treat Link-U OS as a phone operating system.

The official [Link-U OS Alpha page](https://www.agibot.com/filepage/282.html) describes an embodied robotics operating-system ecosystem, with hardware-side interfaces and higher-level intelligent-app integration. The open-source project has a separate [pinned main repository](https://github.com/Link-U-OS/Link-U-OS/tree/64ac7b08dd609dfb463310945856419be470315a).

## Confirmed Link-U OS Alpha features

| Feature | Public-source evidence | Engineering implication |
| --- | --- | --- |
| AimRT middleware with Channel/Topic and RPC; Protobuf and ROS2 Message | Link-U OS README | Future integration should use explicit, versioned message contracts; **no runtime connection included** |
| Hardware abstraction and northbound agent integration framework | AGIBOT Link-U official page and README | Treat LLM agent decisions as separate from safety-critical execution |
| Bazel builds across x86_64/aarch64, product packages | Link-U README and [English build guide](https://github.com/Link-U-OS/Link-U-OS/blob/64ac7b08dd609dfb463310945856419be470315a/document/en/build_package.md) | Requires target architecture, dependencies, and platform compatibility evaluation |
| Docker/VS Code devcontainer, setup-init | [English setup guide](https://github.com/Link-U-OS/Link-U-OS/blob/64ac7b08dd609dfb463310945856419be470315a/document/en/setup_environment.md) | A build environment is documented, but not installed by this record |
| AimStudio application/package deployment | [English deployment guide](https://github.com/Link-U-OS/Link-U-OS/blob/64ac7b08dd609dfb463310945856419be470315a/document/en/deploy_package.md) | Real package deployment is a separate authorization and validation activity |
| MuJoCo and Isaac Gym simulation; PPO-based bipedal locomotion | Link-U README | Simulation is the preferred place to test future high-level plans before hardware experiments |
| Expedition A2 Flagship robot target, Ubuntu 22.04 | Link-U deployment guide | A2 deployment documentation is **not** proof of X1, Mac or iOS deployment |
| Emergency-stop and supervised transitions | [Robot operation guide](https://github.com/Link-U-OS/Link-U-OS/blob/64ac7b08dd609dfb463310945856419be470315a/document/en/robot_operation.md) | Human-operated physical-safety supervision is mandatory before robot tests |

### Separate AGIBOT X1 research family

The X1 guide describes a 29-joint humanoid body, two grippers, and an optional head with three degrees of freedom. The [pinned X1 inference repo](https://github.com/AgibotTech/agibot_x1_infer/tree/9e0b818804d644fb9c9663e932dd33b03b24dfa4) describes AimRT-based inference, drivers, ROS 2 Humble and simulation. The [pinned X1 training repo](https://github.com/AgibotTech/agibot_x1_train/tree/e6651b9ab843fd1b1be70c087bfb7e8b28e44ccd) documents Isaac Gym reinforcement-learning training, MuJoCo sim2sim evaluation, and JIT/ONNX policy exports. These are separate repositories and targets; **do not infer that X1 is a plug-and-play Link-U OS A2 deployment**.

The Link-U OS root and X1 inference root declare **Mulan PSL v2**. This does not establish license status for the Link-U OS Git submodules, X1 training artifacts, trademarks, robot hardware, or model weights. Review source-specific terms before code reuse and preserve required notices.

## How GPT-Doug learns this

The authoritative local reference lives at [foundry/ontology/agibot-link-u-os-ontology.json](../foundry/ontology/agibot-link-u-os-ontology.json) and contains:
- 12 reviewed sources with official URLs or pinned GitHub commit paths
- 17 evidence-backed component and architecture nodes
- 16 typed source-supported relationships
- Link-U OS / A2 and AGIBOT X1 as distinct source families
- a clearly marked **design-only** GPT-Doug integration proposal
- fail-closed no-teleoperation/no-hardware/no-weapon and human-review gates

The implementation is deliberately **not** a crawler, agent runtime, ROS 2 node, telemetry bridge, model training job, or real robot controller. It performs no network access at runtime.

### Read-only commands

Run from the GPT-Doug repository root:

~~~sh
python3 scripts/agibot_os_knowledge.py doctor
python3 scripts/agibot_os_knowledge.py status --json
python3 scripts/agibot_os_knowledge.py search "AimRT ROS2 middleware" --json
python3 scripts/agibot_os_knowledge.py show x1-training
python3 scripts/agibot_os_knowledge.py graph --json
python3 -m pytest -q tests/test_agibot_os_knowledge.py
~~~

If those commands fail, the knowledge should **not** be promoted to default retrieval. A passing local knowledge test is not evidence of running or safe humanoid robotics software.

## Independent GPT-Doug architecture proposal (not source claim)

~~~text
AGIBOT / X1 / Link-U documentation and pinned open-source metadata
                       |
         Verified, versioned evidence references
                       |
       GPT-Doug ontology and read-only source search
                       |
     Human review of proposed ROS2/AimRT API contracts
                       |
   Future sandbox simulator adapter (NOT IMPLEMENTED)
                       |
 Independent robot safety / legal / license / CI gates
                       |
       Possible later hardware integration (NOT AUTHORIZED)
~~~

### Promotion gates

1. Complete separate licenses/terms review for each upstream module, assets, datasets, and weights.
2. Confirm supported platform and ROS/AimRT schemas against exact upstream versions.
3. Create an isolated, inspectable **simulation-only** adapter with no robot network or device control.
4. Test message validation, timeouts, negative inputs, provenance, reproducibility, and emergency-state handling.
5. Obtain human approval, manufacturer guidance, qualified safety review, and explicit legal authority **before** any physical robot deployment.

No affiliation with or endorsement by AGIBOT or Link-U OS is claimed.

**XUNIA Museum:** a draft catalog card is stored at [docs/museum/agibot-link-u-os-research.md](museum/agibot-link-u-os-research.md); not published to xunia.org.
