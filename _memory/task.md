ich hab auch die b haptics tactgloves2 und beim pinch sollen die auch in daumen und finger kurz vibrieren

und kannst du auch mal einfach die abstandänderung simulieren damit ich die dynamische vibration von den gloves testen kann?


===================================================================
HANDOFF / STAND 2026-06-25 — VOLLE PIPELINE AM ECHTEN GoFa LÄUFT
===================================================================
(Details + Recovery: Memory [[project_realrobot_pipeline_2026_06_25]] +
 [[project_quest_ondevice_deploy]] + [[project_psu_brownout_constraint]])

## END-TO-END VERIFIZIERT: Quest QR → Distanz → echtes GoFa-Tempo
- QR-Detection (MRUK), Achsen-Gizmo an QR-Pose, 5s-Drift-Re-Align (QrAnchorCalibrator.periodicReAlign).
- Distanz (Kopf→QR-Roboter) → distance_speed_scaler → live_speed → relay → EGM-Bridge → echter GoFa
  (näher=langsamer, 0.6m=0% / 2.0m=100%).
- Safety: Brille ab → App pausiert → Distanz STALE → Scaler PAUSIERT dpp_playback (Roboter stoppt);
  Brille auf → resume. (scaler-Param pause_playback_on_stale).
- HUD: AUTO/MANUELL + SPEED% LOKAL aus Distanz gerechnet (Quest-Abo auf /robot/speed_factor griff nicht).
- 2 In-VR-Poke-Buttons "Automatik"/"Manual control" (kopf-fixiert) → /quest/scaling_enabled.
- PC-Steuerkonsole: bridge/egm-bridge/relay_speed_console.py — 1-9=Tempo+Resume, 0/space=Freeze+Pause,
  H=Home([0,0,0,0,90,0])+park, ESC.

## REAL-ROBOT BRING-UP (was lief, was wichtig ist)
- PC-NIC "Ethernet"(Killer E3100G) = statisch 192.168.125.100/24 (Admin New-NetIPAddress). Controller-RWS=.1 (HTTPS!).
- RICHTIGES PROGRAMM: MetaMoveJointStream/MetaJointMain am PP (NICHT MainModule/main=Demo!). PP via Pendant
  "PP auf Routine" oder RWS-Rezept (mastership/edit/request → pcp/routine routine=MetaJointMain&userlevel=FALSE).
- EGM-Bridge Windows: egm_bridge_servo.py --host 192.168.125.100 --port 6515 --rosbridge-host 127.0.0.1
  (ROB_1 UDPUC = .100:6515, NICHT .99:6511! Bridge an .100 binden = Source-IP-Bug). Firewall UDP 6515.
- fake_jsp KILLEN sobald echte Bridge läuft (sonst /joint_states-Konflikt → "TCP too high"-Trip).
- SPEED: acceleration_scaling 0.10 (0.25+ trippt!), velocity 0.3-0.5, relay time_scale 2-3.
- Quest↔ROS: portproxy <PC-WLAN-IP>:10000→127.0.0.1:10000 (+ Firewall) — WSL bindet nur localhost.
- DEPLOY nur über USB-A→C-Kabel (USB-C adb crasht den Laptop, PD). adb: Unity-Hub .../platform-tools/adb.exe.

## LÄUFT GERADE (Container metamove-ros2-ros2-1, ROS_DOMAIN_ID=42)
Sim-Stack-Launch + dpp_playback (sequentiell, vel0.3/accel0.10) + jtc_servo_relay(time_scale3) +
distance_speed_scaler + EGM-Bridge(Windows, bg) + relay_speed_console(Fenster) + Quest-App(build/MetaMove.apk).
APK-Paket: com.DefaultCompany.MixedRealityTemplate.

## NOCH OFFEN (aus früher)
Planned-Path-Fade · Gloves(bHaptics Pinch-Vibration + Proximity) · QR-Gizmo-Feinschliff · Kokoro-TTS ·
Hand-Fliegen-Gag. Und: /robot/speed_factor-Abo der Quest sauber fixen (aktuell lokaler Fallback).

===================================================================
HANDOFF / STAND 2026-06-24 (für neuen Chat)
===================================================================

## LÄUFT & VERIFIZIERT (Szene: Scene_Robot.unity, GESPEICHERT)
- Unity <-> ROS MoveIt-KDL-IK funktioniert (Mode 2).
- Geteachte-Waypoint-Playback im Sim: dpp_playback -> MoveGroup -> jtc_servo_relay
  -> /servo_node/commands -> Unity. Joint-Replay, faehrt NICHT unter den Tisch.
  Waypoints: ros2/docker/metamove_bridge/dpp_waypoints.yaml (5 Stueck, 11.06.).
- Alle 6 Achsen verifiziert: JointAnglesSubscriber.joints[0..5].signFlip = TRUE
  (Unity-Modell dreht sonst andersrum als URDF). Per Achsen-Sweep bestaetigt.
- HUD (SafetyHud, programmatisch via Menue "MetaMove > Setup Virtual Pick&Place
  Demo"): CONNECTION (CONNECTED/NOT CONNECTED via ROSConnection) | DISTANCE | SPEED.
- RViz laeuft via WSLg (DISPLAY=:0). RobotModel aus /joint_states.

## ROS-STACK LAEUFT IM CONTAINER (metamove-ros2-ros2-1, ROS_DOMAIN_ID=42)
Launch: ros2 launch /opt/metamove_ws/src/metamove_bridge/launch/metamove_sim_playback.launch.py
  (move_group + jtc_servo_relay(node 'joint_trajectory_controller') + dpp_playback
   + ros_tcp_endpoint :10000 + rosbridge :9090 + fake_jsp). Ports 10000/9090 published.
Playback resume/pause: ros2 service call /dpp_playback/{resume,pause} std_srvs/srv/Trigger
RViz: ros2 launch .../metamove_rviz.launch.py  (mit -e DISPLAY=:0 -e LIBGL_ALWAYS_SOFTWARE=1)
Achsen-Test: python3 .../axis_test.py <joint 1-6> [amp] [secs]  (playback vorher pausieren)

## UNITY Scene_Robot WIRING
- ABB_CRB_15000: MoveItIkMode.useMoveIt=TRUE; JointAnglesSubscriber alle signFlip=TRUE;
  IKTargetPosePublisher.enabled=true.
- MetaMoveRosBridge: RosBridgeBootstrap.rosIPAddress = 127.0.0.1 (Editor; fuer Quest-Build
  = PC-LAN-IP). WelcomeAudio deaktiviert.
- VirtualDemo (synthetischer Loop) noch da, aber durch ROS-Playback ersetzt: PickPlaceLoop
  bewegt nur IKTarget (entkoppelt). WaypointPath (cyan, synthetisch) DEAKTIVIERT.
  RobotTcpTrail (TCP-Trail) = FALSCHER Ansatz, soll RAUS (war im Play-Mode nicht loeschbar).

## FERTIG & VERIFIZIERT 2026-06-24 (Feature "Waypoint-Bahn mit Progress-Fade")
- RobotTcpTrail GameObject geloescht; TcpTrail.cs in Trash (falscher Trail-Ansatz raus).
- dpp_playback.py: jetzt SEQUENTIELL (reshuffle_each_pass default=False, kein Initial-Shuffle)
  und published nach jedem erreichten Waypoint /dpp/wp_index (std_msgs/Int32) = Waypoint-Identitaet
  0..N-1 (cyclisch). Build ist symlink-install -> Source-Edit live, nur Node-Neustart noetig
  (Rebuild NICHT noetig). Verifiziert: echo /dpp/wp_index -> 0,1,2,3,4 sequentiell.
- Unity-Komponente PlannedPathFade.cs (Assets/MetaMove/Scripts/UI/Visualization/), Namespace
  MetaMove.UI.Visualization. Subscribt /dpp/wp_index, sampelt followTarget(=Joint_6)-Weltpos
  on-pass, baut im 1. Loop die 5-Punkt-Polyline (LineRenderer, world-space, URP Particles/Unlit),
  fadet abgefahrenen Prefix via colorGradient-Step auf traversedOpacity(0.5), Rest volle Opacity.
  KEIN wachsender Trail. Fade resettet pro Loop (Index wrappt 4->0).
- Scene_Robot WIRING: GameObject "PlannedPathFade" (root) mit LineRenderer + PlannedPathFade,
  followTarget = MountedRobotAnchor_DevStatic/.../Joint_6 (das AKTIVE, nicht MountedRobotAnchor).
  Szene gespeichert.
- E2E im Play-Mode getestet: positionCount=5, bounds 0.68x0.53x0.57m, alphaKeys 0.5->1.0 Step
  folgt currentIndex. Keine Exceptions. OK.
- HINWEIS: dpp_playback wurde standalone neugestartet (alter Launch-Node gekillt). Beim naechsten
  vollen Stack-Start via metamove_sim_playback.launch.py kommt der neue Code automatisch (symlink).

## OFFENE FEATURES (Reihenfolge offen)
- Milestone 2b: distance_speed_scaler -> jtc_servo_relay.live_speed (QR-Distanz steuert
  Tempo) + SafetyHud in ROS-Mode (publisht /quest/min_distance, liest /robot/speed_factor).
  Scaler+relay sind in setup.py registriert + gebaut.
- bHaptics Gloves: BHapticsAdapter.cs ist STUB -> an Bhaptics.SDK2 anbinden. PC-Player +
  pairen, kein Headset noetig. Proximity-Intensitaet (naeher=staerker) via ProximitySpeed-
  Controller.Distance. + Pinch -> Daumen/Finger kurz vibrieren (task.md).
- QR-Achsen-Gizmo (X rot raus/Z blau hoch/Y gruen, rechtshaendig) auf QR-Anchor.
- Roboter an QR ausrichten (AnchoredBaseBinder existiert).
- Distanz-Sim zum Gloves-Testen; Kokoro-TTS; Hand-Fliegen-Gag.

## GOTCHAS
- Unity-MCP Server = Port 8090 (nicht 8080!). ~/.claude.json "unity".url muss /8090/mcp.
- MCP set_property / gameobject modify gehen NICHT im Play-Mode (erst stop).
- WSL: distro Ubuntu-24.04; docker exec; bei nested quoting kein $loopvar (explizit aufrufen).
- Repo im Container unter /opt/metamove_ws/src (bind-mount von ros2/docker/...).
- Editor-Cam zeigt Roboter nicht ganz (Roboter NICHT bewegen, fuer Quest passt's) -> Scene-View
  oder DevEditorCamera nutzen.



