# Mental Training System: Architecture & Enhancement Plan

## 1. Multimodal Sensor Fusion
- **Biometric Inputs**: Smartwatch telemetry including continuous HR, HRV (time-domain rMSSD/SDNN), Photoplethysmography (PPG), Skin Temperature, and Electrodermal Activity (EDA/GSR where available).
- **Physical Exertion Gating (False-Positive Suppression)**:
  - Integration of continuous 3-axis accelerometer and vector magnitude data.
  - Stress alert suppression when physical motion / metabolic demand exceeds threshold ($>1.2\text{ METs}$), preventing false alarms during walking or exercise.
- **Dynamic Circadian Baseline**:
  - Baseline metrics calculated via rolling 7-day percentile windows rather than fixed, static thresholds.
  - Automatically accounts for circadian fluctuations, sleep deficit, and recovery status.

## 2. Tiered Audio Inference & Privacy Protection
- **Edge Gated Ring-Buffer**:
  - Microphone operates in a dormant, rolling local ring-buffer state without continuous recording or transmission.
  - 5–10s audio capture activates **strictly** when an acute sympathetic surge is detected (e.g., HRV drop $>20\%$ below baseline coinciding with elevated autonomic arousal).
- **On-Device Feature Extraction**:
  - Immediate local extraction of speech metrics (jitter, pitch variability/$F_0$ shifts, volume envelope, speech rate).
  - Raw audio buffers are purged from memory immediately post-extraction.
- **Affective State Classification**:
  - Differentiates between passive withdrawal/insult response (low speech volume, flattened affect) and outward verbal escalation.

## 3. Real-Time Intervention Hierarchy
- **Level 1 — Somatic Grounding (Micro-Haptics)**:
  - **Trigger**: Early physiological drift or mild stress threshold breach.
  - **Action**: Discreet haptic pattern on smartwatch (e.g., subtle double-pulse) anchoring body awareness ("release tension / exhale"). Operates with zero visual or cognitive distraction.
- **Level 2 — Contextual Micro-Prompt (Audio/Visual)**:
  - **Trigger**: Sustained sympathetic arousal during verbal confrontation.
  - **Action**: Minimalist text chip on screen or single-phrase audio cue via earpiece timed during conversational pauses.
- **Level 3 — Post-Event Recovery & Debrief**:
  - **Trigger**: 3–5 minutes post-incident, once autonomic baseline recovery begins.
  - **Action**: Prompt for a brief structured cognitive check-in.

## 4. Closed-Loop Biofeedback Simulation & Guided Imagery
- **Biometric-Coupled Scenario Training**:
  - LLM-powered dynamic roleplay simulating interpersonal conflict, social friction, and boundary negotiation.
  - Dynamic Difficulty Adjustment (DDA): Scenario pressure and adversary aggression scale up or down based on user's live physiological stability.
- **Physiologically Calibrated Guided Imagery**:
  - Guided pacing synchronized with Respiratory Sinus Arrhythmia (RSA) to steer heart rate rhythms toward the resonance frequency (~0.1 Hz / 6 breaths per minute).
  - Quantified autonomic recovery scoring tracking time-to-equilibrium.
