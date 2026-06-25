# Architecture Audit — Drift & Cleanup Inventory

Snapshot of inconsistencies, stale docs, and pattern violations discovered while writing `ARCHITECTURE.md`. Each entry has a severity tag and a concrete location so it's pickup-able as a 10-minute fix later.

Generated 2026-05-14. Re-verify any entry's claim against current code before acting on it — this list ages.

---

## Severity scale

- **HIGH** — actively misleading or blocks a documented goal
- **MED** — adds friction or causes confusion for new contributors
- **LOW** — code-hygiene nits, can sit in a backlog

---

## Findings

### 1. `unity-quest/Assets/MetaMove/SETUP.md` is stale [HIGH]

Document references the **GoHolo** predecessor project — wrong folder paths (`Assets/GoHolo/...`), wrong Unity project name (`ABBGoFa_Quest3`), wrong scripts (`PinchDragSceneSetup` only, missing the entire MetaMove namespace).

**Impact:** A new contributor opening `SETUP.md` learns about a project that doesn't exist anymore.

**Fix:** Either rewrite as MetaMove-flavored quickstart, or delete and replace with a 5-line pointer to `docs/ARCHITECTURE.md` + `WIRING_UI.md`.

Location: `unity-quest/Assets/MetaMove/SETUP.md`

---

### 2. `IRobotCommandSink` lies about `RwsRobotSink` [HIGH]

Comment in [Robot/IRobotCommandSink.cs:5-7](../unity-quest/Assets/MetaMove/Scripts/Robot/IRobotCommandSink.cs#L5-L7) lists `RwsRobotSink` as an implementation. It doesn't exist (`Glob unity-quest/**/RwsRobotSink*.cs` returns nothing). Only `EgmRobotSink` and `MockRobotSink` are checked in.

**Impact:** The dual-path architecture ([[project_architecture_dual_path]]) says RWS should handle VC-Sim. With no sink in code, you cannot exercise the VC-Sim path through the same gesture pipeline. Lab-test [[project_lab_test_2026_05_15]] can't compare RWS vs EGM cleanly until this exists.

**Fix:** Either implement `RwsRobotSink` (HTTP POST to RAPID via RWS variables), or update the interface doc-comment to reflect reality. Recommend implementing it — it unblocks VC-Sim testing.

---

### 3. `AnchorDriftHud` uses `OnGUI` — wrong for VR [MED]

[Safety/AnchorDriftHud.cs:46-74](../unity-quest/Assets/MetaMove/Scripts/Safety/AnchorDriftHud.cs#L46-L74) renders via legacy IMGUI `OnGUI`. That draws to the 2D screen overlay, which in VR/passthrough either disappears entirely or appears as a flat sprite stuck to the headset display.

**Impact:** The drift HUD is *the* tool for measuring spatial-anchor stability during a session. Currently it's unreadable in headset, which defeats its purpose.

**Fix:** Port to the lazy-follow world-space pattern established in [UI/Hud/StatusHud.cs](../unity-quest/Assets/MetaMove/Scripts/UI/Hud/StatusHud.cs). One TMP world panel that follows the head, shows live + max drift in mm.

---

### 4. `QuestDepthPublisher` disabled pending Meta v85 API rewire [MED — HIGH for octomap]

[Robot/Ros/QuestDepthPublisher.cs:86](../unity-quest/Assets/MetaMove/Scripts/Robot/Ros/QuestDepthPublisher.cs#L86) is gated behind `METAMOVE_QUEST_DEPTH_ENABLED` scripting define (not currently set). Three accessors broke in Meta XR SDK v85.

**Concrete fix path** ([[project_meta_xr_v85_depth_api]]):
- Depth texture: `Shader.GetGlobalTexture("_EnvironmentDepthTexture") as RenderTexture` (Tex2DArray, slice 0 = left).
- FoV: derive from `Camera.main.projectionMatrix` (`vfov = 2*atan(1/p.m11)`).
- Near/far: rewrite linearization to use shader global `_EnvironmentDepthZBufferParams` directly — avoids reflection.

**Impact:** [[project_octomap_hybrid_pipeline]] (planned MoveIt collision world) cannot consume Quest depth until this is fixed. `octomap_test.launch.py` exists ready to receive data.

---

### 5. No top-level `README.md` at repo root [MED]

Repo has `docs/` with several MDs but nothing at `c:\git\MetaMove\README.md`. New contributors (or future-you returning after a break) land in a directory with `ai-services/`, `unity-quest/`, `ros2/`, `robotstudio/` etc. and no orientation.

Recent commit `d4edbac docs: add project README` looks like it added a README somewhere but not at root (Glob didn't surface one).

**Fix:** A 30-line README.md at repo root pointing to `docs/ARCHITECTURE.md`, `docs/ui-panels.md`, and per-subfolder entry points.

---

### 6. `RosBridgeBootstrap` default IP is the *alternate* [LOW]

[Robot/Ros/RosBridgeBootstrap.cs:21](../unity-quest/Assets/MetaMove/Scripts/Robot/Ros/RosBridgeBootstrap.cs#L21) defaults to `192.168.125.99`. Memory [[project_gofa_ip_alt]] documents `.99` as the *alternative* IP — not the canonical lab address.

**Impact:** Builds inherit the alt IP by default. Probably intentional (WSL2 mirrored bridge is at .99 — [[project_egm_joint_via_sm_working]]), but the field tooltip just says "Lab LAN" without explaining why .99 and not .1.

**Fix:** Either expand the tooltip to explain (WSL2 mirror necessity), or move the value into `RobotConnectionConfig` so it's discoverable in one place with other endpoints.

---

### 7. Legacy `FindObjectOfType` in older author scripts [LOW]

[Editor/TelemetryPanelAuthor.cs:88-99](../unity-quest/Assets/MetaMove/Editor/TelemetryPanelAuthor.cs#L88-L99) uses `Object.FindObjectOfType<T>()` — deprecated in Unity 6. New scripts (StatusHud, StatusHudAuthor) use `FindFirstObjectByType<T>()`. Mixed style.

**Fix:** Sweep old author scripts to the new API on next touch. Pure deprecation-warning cleanup, no functional change.

---

### 8. Hand-rolled EGM protobuf [LOW]

[Robot/EGM/EgmMessages.cs](../unity-quest/Assets/MetaMove/Scripts/Robot/EGM/EgmMessages.cs) + `ProtoReader.cs` hand-implement the ABB EGM wire format instead of using `Google.Protobuf`. Pragmatic (the rparak reference used the legacy 2.4 plugin which doesn't ship on Quest), but brittle if ABB ever extends the schema.

**Fix:** Acceptable as-is for now. Add a comment cross-referencing `egm.proto` in `robotstudio/` so the next person knows where the source-of-truth schema lives.

---

### 9. `_Recovery/0*.unity` scenes show up in git status [LOW]

Per `git status` snapshot: `unity-quest/Assets/_Recovery/0.unity` through `0 (7).unity` are untracked. These are Unity's crash-recovery scenes, regenerated each crash.

**Fix:** Add `unity-quest/Assets/_Recovery/` to `.gitignore`.

---

### 10. UI panels read from telemetry — but no enforcement [LOW]

`RobotTelemetry` is the documented single read-point ([RobotTelemetry.cs:6-8](../unity-quest/Assets/MetaMove/Scripts/Robot/RobotTelemetry.cs#L6-L8) "Single pull-point for live robot state. Overlays + HUD subscribe here instead of poking EgmClient directly"). The pattern is established, but nothing prevents a panel from grabbing `EgmClient` directly.

**Impact:** If a panel ever bypasses, swapping sources (mock ↔ EGM ↔ ROS) breaks at unexpected places.

**Fix:** Grep for direct `EgmClient` references in `UI/` and `Interaction/` folders — should be zero. (Note: `EgmKeyboardTester` is allowed; it's a tester, not UI.) Document this rule in `WIRING_UI.md`.

---

### 11. Two scenes overlap in scope: `Scene_Robot` and `Scene_EGM_KeyboardTest` [LOW]

`Scene_EGM_KeyboardTest.unity` is for low-level EGM debug (testing keystrokes → joint commands). `Scene_Robot.unity` is the production scene. Both reference `EgmClient`.

**Impact:** Risk of double-binding ports or duplicating UI assets if you accidentally additive-load both.

**Fix:** Document in a scene-header note that the keyboard-test scene is exclusive (don't combine). Or rename to `Sandbox_EGM_Keyboard.unity` to make the role obvious.

---

### 12. `StatusHud.IsPassthroughOn` uses runtime reflection [LOW]

[UI/Hud/StatusHud.cs:176-194](../unity-quest/Assets/MetaMove/Scripts/UI/Hud/StatusHud.cs#L176-L194) reflects `OVRManager.isInsightPassthroughEnabled` to avoid a hard Oculus.VR dependency. Fine, but if Meta ever changes the assembly name from `Oculus.VR`, the fallback to camera-clearflag is the only signal left.

**Fix:** Acceptable for now (gracefully degrades). On next touch, cross-reference the actual assembly name from `Library/PackageCache/com.meta.xr.sdk.core@*/Runtime/...` — currently still `Oculus.VR`.

---

## What's NOT a problem (clarifications)

These looked like issues at first glance but are intentional:

- **`SystemInfo.batteryLevel` in StatusHud returns −1 in Editor on PC** — by design; only Android (Quest 3) reports real battery. HUD shows `--%` in Editor.
- **`#if METAMOVE_QUEST_DEPTH_ENABLED` gates an entire method body** — intentional kill-switch until the Meta v85 API is reconnected. The `BuildAndPublish` helper is unused-but-defined; that's a warning, not an error.
- **`autoDetectRemote = true` in EgmClient** — looks risky but is correct for the lab where the controller's UDP source-IP varies (WSL mirroring quirks). Documented in [[project_egm_joint_via_sm_working]].

---

## Suggested order of attack

If you want to chip through these in a session:

1. **#5** (root README, ~10min) — biggest contributor-onboarding win for least effort
2. **#1** (SETUP.md rewrite, ~15min) — pairs with #5
3. **#9** (.gitignore, ~2min) — trivial, do whenever
4. **#3** (AnchorDriftHud port to lazy-follow, ~30min) — uses the StatusHud pattern, mostly mechanical
5. **#2** (implement `RwsRobotSink`, ~1-2h) — unblocks dual-path lab test
6. **#4** (re-enable QuestDepthPublisher, ~1h) — concrete fix path already documented in [[project_meta_xr_v85_depth_api]]

The rest can ride along on a future touch of the affected files.
