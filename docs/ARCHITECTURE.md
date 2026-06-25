# MetaMove Architecture

Single source of truth for the data flow between Quest 3, the ROS2 bridge, and the ABB GoFa controller. Last verified against the codebase on 2026-05-14.

---

## Goal

Telemanipulate an ABB GoFa CRB 15000 from a Quest 3 in mixed-reality passthrough, with the Unity scene acting as a colocated digital twin. Two paths exist depending on whether the target is the **real robot** or a **RobotStudio Virtual Controller** simulation.

---

## Dual-Path Overview

```
                    ┌─────────────────────────────────────────────┐
                    │              Quest 3 (Unity)                │
                    │  Gestures · IK target · Ghost robot · HUD   │
                    └────────────┬───────────────────┬────────────┘
                                 │                   │
                  ROS-TCP-Connector   ←─── only EGM path uses ROS today
                                 │
                ┌────────────────┴──────────────────┐
                │   ros2_jazzy Docker (WSL2 / Win)  │
                │   bridge_node + MoveIt Servo      │
                │   rosbridge_websocket : 10000     │
                └────────────────┬──────────────────┘
                                 │
                            /servo_node/commands (Float64MultiArray, 50 Hz, rad)
                                 │
                                 ▼
                ┌────────────────────────────────────┐
                │  Unity ServoCommandSubscriber      │   real-robot path
                │  rad→deg, resend @ 250 Hz          │
                └────────────────┬───────────────────┘
                                 │
                            EgmClient.SendJoints
                                 │   UDP :6511
                                 ▼
                ┌────────────────────────────────────┐
                │  ABB GoFa controller (SM Add-In)   │
                │  UDPUC ROB_1, EGMRunJoint loop     │
                └────────────────────────────────────┘
```

**Path A — Real robot (validated 2026-05-08, EGM Joint via SM Add-In):**
Quest → ROS-TCP → ros2 docker → MoveIt Servo → `/servo_node/commands` → Unity `ServoCommandSubscriber` → `EgmClient.SendJoints` → controller.
Telemetry flows back the opposite way: controller → `EgmClient.RxLoop` (250 Hz) → `RobotTelemetry` → UI.

**Path B — RobotStudio Virtual Controller (RWS, pivot 2026-05-14):**
Unity → RWS HTTP/HTTPS → VC. No ROS, no EGM. EGM same-host is impossible with RS 2025 sandbox isolation ([[project_vc_egm_isolated_rs2025]]).
**Status:** not yet implemented in code. `IRobotCommandSink` claims an `RwsRobotSink` exists; only `EgmRobotSink` and `MockRobotSink` are checked in.

---

## Component Inventory

### Unity side — `unity-quest/Assets/MetaMove/Scripts/`

| Concern | File | Role |
|---|---|---|
| Network EGM | `Robot/EGM/EgmClient.cs` | UDP :6511 client. BG thread RX, main-thread TX. Sole holder of socket state. |
| EGM messages | `Robot/EGM/EgmMessages.cs`, `ProtoReader.cs` | Hand-rolled wire format for ABB EGM (no Google.Protobuf dep). |
| EGM sink | `Robot/EGM/EgmRobotSink.cs` | Adapts `IRobotCommandSink` to `EgmClient.SendPose`. Continuous streamer @ 250 Hz. |
| Robot abstraction | `Robot/IRobotCommandSink.cs` | Interface: `SendTcpTarget` + `Stop`. Gesture code targets this, not EgmClient. |
| Mock sink | `Robot/MockRobotSink.cs` | Editor-only, logs to Console. Use before EGM is wired. |
| Telemetry pull-point | `Robot/RobotTelemetry.cs` | Reads `EgmClient.TryGetLatest`, exposes joint deg + TCP pose + Hz + motorsOn. UI must read here, **not** `EgmClient` directly. |
| ROS bootstrap | `Robot/Ros/RosBridgeBootstrap.cs` | Configures `ROSConnection` singleton with endpoint. `DefaultExecutionOrder(-100)` so it runs before publishers. |
| ROS in | `Robot/Ros/ServoCommandSubscriber.cs` | `/servo_node/commands` → `EgmClient.SendJoints`. Falls back to echoing current joints if no command for 0.5s (hold pose, keep EGM alive). |
| ROS out (joints) | `Robot/Ros/JointStatePublisher.cs` | Publishes Unity-side joint state to ROS for MoveIt awareness. |
| ROS out (head) | `Robot/Ros/QuestHeadPosePublisher.cs` | Quest headset pose → ROS, frame `quest_world`. |
| ROS out (depth) | `Robot/Ros/QuestDepthPublisher.cs` | Quest environment depth → PointCloud2. **DISABLED** pending Meta XR v85 API rewire (see FIXME). |
| UI HUD | `UI/Hud/StatusHud.cs` | Lazy-follow curved status HUD. Reads `SystemInfo.batteryLevel` + `RobotTelemetry`. |
| UI HUD bootstrap | `UI/Hud/PassthroughEnabler.cs` | Idempotent AR-mode boot: OVRManager flag + underlay + transparent camera. |
| UI panels | `UI/Panels/*.cs` | `WorldPanelBase` is the lifecycle base; concrete panels are derived prefab-variants. See `WIRING_UI.md`. |

### ROS2 side — `ros2/docker/`

| Concern | Path | Role |
|---|---|---|
| Container | `Dockerfile` + `docker-compose.yml` | ROS2 Jazzy image with MoveIt2 + rosbridge + ros-tcp-endpoint. |
| Bridge node | `metamove_bridge/metamove_bridge/bridge_node.py` | Glue between Quest pose/commands and MoveIt Servo. |
| ABB driver | `abb_gofa_custom/` | abb_driver + abb_crb15000_moveit forks (SM Add-In incompatibility issues — see [[project_ros2_abb_driver_state]]). |
| Launch | `metamove_bridge/launch/sim_servo.launch.py`, `octomap_test.launch.py` | Servo + (planned) octomap launchers. |

### Controller side — `robotstudio/`

| Concern | Path | Role |
|---|---|---|
| RAPID code | `rapid/MetaMoveCorePers.mod` | EGM session module (UDPUC ROB_1, EGMRunJoint). |
| Snapshots | `gofa_snapshot_*/`, `gofa_dump_*.json` | Backup + dump tooling for the real controller. |
| TCP bridge test | `tcp_bridge_test/` | RAPID-side TCP socket experiment, alternative to EGM for VC-Sim ([[project_tcp_bridge_workaround]]). |

---

## Frame Conventions

Two conversion boundaries exist; mistakes here are the single most common bug source.

| Frame | Convention | Used by |
|---|---|---|
| **Unity world** | Left-handed, **+Y up**, +Z forward, meters | Everything inside the Unity scene |
| **ROS REP-103** | Right-handed, **+Z up**, +X forward, meters | All ROS topics (`/quest/head_pose`, `/quest/depth_points`, `/joint_states`) |
| **ABB base** | Right-handed, +Z up, +X forward, **mm**, Euler ZYX deg | EGM wire format on UDP :6511 |

**Conversions:**
- Unity → ROS: `pos.To<FLU>()` from `Unity.Robotics.ROSGeometry`. Always per-point inside publishers.
- Unity → EGM Pose: `pos * 1000.0` (meter → mm) and `rot.eulerAngles` (degrees). Done inside `EgmClient.SendPose`.
- Unity → EGM Joint: degrees, in URDF joint order. Done inside `ServoCommandSubscriber` (rad→deg) and `EgmClient.SendJoints`.

**Tracking origin:** Unity world ↔ GoFa base is calibrated via a QR marker (see `Safety/QrSafetyVisualizer.cs` + `gofa_base_link → quest_world` TF published by the QR calibrator).

---

## Execution Order

Two `DefaultExecutionOrder` overrides matter:

- `RosBridgeBootstrap` = **−100** — runs before any publisher/subscriber.
- `QuestDepthPublisher` = **−40** — runs before publishers that depend on depth.

Everything else uses default order; if a script needs deterministic init relative to telemetry, set its order between −40 and 0.

---

## Settings Surface

All tunables live in `ScriptableObject` assets under `unity-quest/Assets/MetaMove/Settings/`:

- `UiThemeConfig` — colors, spacing, typography (mm-world)
- `RobotConnectionConfig` — preset endpoints (.1 main, .99 alt, VC)
- `SafetyConfig` — zone tolerances, ISO mode
- `HapticsConfig` — bHaptics adapter config
- `GestureConfig` — pinch/swipe thresholds
- `JointLimits` (per robot) — `JointLimits_GoFa5_95.asset`

Panels read from these; never hardcode tunables in scripts.

---

## What's Not Here Yet

Cross-reference for planned-but-unimplemented surfaces (see also `ARCHITECTURE_AUDIT.md`):

- **`RwsRobotSink`** — the RWS-HTTPS path for VC-Sim. Interface comment in `IRobotCommandSink.cs` lists it as if it exists; it doesn't.
- **Octomap pipeline** — `QuestDepthPublisher` is disabled (Meta SDK v85 API broke 3 accessors). `octomap_test.launch.py` exists but cannot ingest data until the publisher is fixed.
- **Body tracking** — `com.meta.xr.sdk.movement` not yet imported (Step 19 in WIRING_UI).
- **Curved scroll lists, voice, demo panels** — see WIRING_UI § "What's NOT yet wired".

---

## Cross-References

- `docs/ui-panels.md` — UI panel catalog + Meta asset inventory
- `unity-quest/Assets/MetaMove/WIRING_UI.md` — Editor wiring checklist for UI panels
- `docs/gesture-vocabulary.md` — hand-pose taxonomy used by `Interaction/Gestures/`
- `docs/safety-anchor-test.md` — anchor drift measurement protocol
- `ros2/docker/metamove_bridge/SIM_SERVO_README.md` — bringing up the ros2 stack
