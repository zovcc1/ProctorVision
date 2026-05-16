# Focus Loss Detection: Issue Analysis and Resolution Report

## 1. Overview
This document outlines the problems identified in the initial implementation of the Focus Loss Detection feature (branch `feat/focus-loss-detection-13445228947159134448`, commit `c1cb604`) and details the fixes implemented to ensure a robust, secure, and user-friendly system.

## 2. Identified Problems ("The Problem")

The initial implementation contained several critical flaws that compromised the security and usability of the proctoring system:

### A. Lack of Backend Enforcement (Security Vulnerability)
*   **The Issue:** The `auto_terminate_on_focus_loss` configuration setting was present in `config.json` but was never actually read or used by the backend.
*   **The Risk:** Termination logic was entirely client-side (JavaScript). A savvy user could bypass the security by disabling JavaScript, modifying the frontend code, or blocking specific API calls, allowing them to switch tabs indefinitely without the session ever stopping.

### B. Hardcoded UI Thresholds
*   **The Issue:** The "CHEATING DETECTED" overlay had the text "more than 2 seconds" hardcoded.
*   **The Risk:** Even if an administrator increased the threshold to 10 seconds in the backend configuration, the user would still see a confusing and inaccurate message about a 2-second limit.

### C. Race Condition on Window Closure
*   **The Issue:** The `beforeunload` event handler fired two asynchronous requests simultaneously: `reportExternalEvent('window_closed')` and `session/stop`.
*   **The Risk:** The backend often processed the "stop" request first. Once a session is stopped, the backend ignores further events. This resulted in "Window Closed" incidents frequently missing from final proctoring reports.

### D. UI/UX Gaps
*   **Settings Access:** Users had no way to configure the new focus loss settings through the UI.
*   **Alert Metadata:** Focus-related events (`focus_loss`, `window_closed`) appeared in the Live Alerts panel with raw internal names and generic warning icons, making them look unpolished and difficult to interpret quickly.
*   **Termination Feedback:** If the backend did stop the session, the frontend simply returned to the "Start" state without showing the "CHEATING DETECTED" warning, leaving the student confused about why their session ended.

### E. Technical Debt & Logic Errors
*   **Unimplemented Parameters:** The `stopSession` function was updated to accept a `reason` parameter, but it was marked as unused (`_reason`) and never sent to the server.
*   **Orphan Branch:** The feature branch had no common ancestor with `master`, containing a duplicate of the entire codebase, which would cause severe merge conflicts.

---

## 3. Implemented Solutions

The following changes were implemented to resolve the issues above:

### 1. Robust Backend-Side Enforcement
*   **State Tracking:** `SessionManager` now tracks `_focus_lost_at` on the server.
*   **Autonomous Monitoring:** The backend `_stream_loop` independently calculates the elapsed time since the last blur event. If it exceeds the threshold, the backend calls `stop_session()` autonomously.
*   **Reset Logic:** Added a `focus` event report from the frontend to the backend to reset the server-side timer if the student returns to the window within the allowed time.

### 2. Dynamic UI & Messaging
*   The "CHEATING DETECTED" overlay now pulls the threshold value directly from the active configuration: `settings?.security?.focus_loss_threshold_seconds`.
*   The `AlertsPanel` was updated with human-readable labels (e.g., "Tab/Window Blurred") and specific icons for all focus-related events.

### 3. Reliable Event Sequencing
*   Used `await` in the `beforeunload` handler to ensure the `window_closed` event is successfully recorded before the session stop request is dispatched.
*   Implemented the `keepalive: true` flag in fetch calls to ensure requests complete even after the page is closed.

### 4. Enhanced Reporting
*   Modified the `Session` class to store a `termination_reason`.
*   Updated the `ReportGenerator` to include this reason in the "Session Summary" section of the PDF report (e.g., "Term. Reason: Cheating Detected: Focus Loss (Backend Enforcement)").

### 5. Settings Integration
*   Added the "Focus Loss Threshold (s)" field to the `SettingsModal`, allowing real-time adjustment of the security parameters.

## 4. Architectural Summary

| Component | Responsibility |
| :--- | :--- |
| **Frontend (React)** | Detects blur/focus events, manages local grace-period timer, displays warning overlays. |
| **Backend (Flask)** | Receives blur/focus signals, independently enforces timeout in the processing loop, notifies UI via SocketIO if termination occurs. |
| **Storage (PDF)** | Captures snapshots of focus violations and logs the specific reason for session termination. |
