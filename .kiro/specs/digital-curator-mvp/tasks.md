# Implementation Plan: Digital Curator MVP

## Overview

Implement a local-first photo triage application with a Python/FastAPI Host backend and a React/TypeScript frontend. The Host performs all scanning, detection, and indexing locally; the Remote UI (browser) loads only thumbnails and JSON payloads over the local network.

Implementation proceeds bottom-up: data layer → core detectors → scan pipeline → API → frontend.

## Tasks

- [x] 1. Set up project structure, dependencies, and database schema
  - Create directory layout: `host/` (Python package), `frontend/` (Vite/React/TS), `tests/unit/`, `tests/property/`
  - Add `pyproject.toml` (or `requirements.txt`) with: fastapi, uvicorn, sqlalchemy, pillow, opencv-python, imagehash, send2trash, hypothesis, pytest, pytest-asyncio
  - Add `frontend/package.json` with: react, react-dom, typescript, vite, @vitejs/plugin-react
  - Create `host/db/schema.py` with SQLAlchemy ORM models matching the SQLite schema (`files`, `duplicate_groups`, `group_members` tables)
  - Create `host/db/init.py` to initialize the DB at `~/.digital-curator/curator.db`
  - _Requirements: 1.4, 2.6, 3.5, 4.5, 8.1, 12.1_

- [x] 2. Implement the Indexer
  - [x] 2.1 Implement `host/indexer.py` with `Indexer` class
    - Implement `upsert_file(record: FileRecord)`, `upsert_group(group: DuplicateGroup)`, `set_decision(file_id, decision)`, `set_trashed(file_id)`, `get_flagged(category)`, `get_group(group_id)`, and `get_file(abs_path)` methods
    - Use SQLAlchemy sessions; raise on write failure (do not swallow errors)
    - _Requirements: 1.4, 2.6, 3.5, 4.5, 8.1, 12.1, 12.2_

  - [ ]* 2.2 Write property test for FileRecord persistence round-trip
    - **Property 4: FileRecord persistence round-trip**
    - **Validates: Requirements 1.4, 2.6, 3.5, 4.5, 8.1, 12.1, 12.2, 12.3**
    - File: `tests/property/test_prop_persistence.py`
    - Tag: `# Feature: digital-curator-mvp, Property 4: FileRecord persistence round-trip`

  - [ ]* 2.3 Write property test for new files defaulting to undecided
    - **Property 18: New files default to undecided**
    - **Validates: Requirements 8.5**
    - File: `tests/property/test_prop_persistence.py`
    - Tag: `# Feature: digital-curator-mvp, Property 18: New files default to undecided`

  - [ ]* 2.4 Write unit tests for Indexer
    - Happy-path upsert, read-back, set_decision, set_trashed
    - Error injection: DB write failure
    - File: `tests/unit/test_indexer.py`
    - _Requirements: 1.4, 8.1, 12.1, 12.2_

- [x] 3. Implement core data models and Python dataclasses
  - Create `host/models.py` with `FileRecord`, `DuplicateGroup`, `DecisionPayload`, `QualityConfig`, `ScanResult`, `TrashResult`, `FailedFile`, `ScreenshotResult`, `QualityResult`, `ImageMetadata`, `Category` (enum: duplicates/screenshots/blurry), `Decision` (enum: undecided/keep/delete)
  - _Requirements: 1.4, 2.6, 3.5, 4.5, 8.1, 12.1_

- [x] 4. Implement ScreenshotDetector
  - [x] 4.1 Implement `host/screenshot_detector.py` with `ScreenshotDetector.classify(path, metadata) -> ScreenshotResult`
    - Criterion 1: no EXIF metadata AND aspect ratio matches known screen ratios (9:19.5, 9:16, 2:3) within ±0.05
    - Criterion 2: filename contains "screenshot" (case-insensitive)
    - Criterion 3: no EXIF capture date
    - Confidence score = number of matching criteria (0–3); `is_candidate = confidence >= 1`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 4.2 Write property test for screenshot detection criteria correctness
    - **Property 8: Screenshot detection criteria correctness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    - File: `tests/property/test_prop_screenshot.py`
    - Tag: `# Feature: digital-curator-mvp, Property 8: Screenshot detection criteria correctness`

  - [ ]* 4.3 Write unit tests for ScreenshotDetector
    - Test each criterion independently and in combination
    - Edge cases: no EXIF + non-screen ratio, filename "SCREENSHOT.PNG"
    - File: `tests/unit/test_screenshot_detector.py`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 5. Implement QualityAssessor
  - [x] 5.1 Implement `host/quality_assessor.py` with `QualityAssessor.assess(path, config) -> QualityResult`
    - Compute Laplacian variance on grayscale image via `cv2.Laplacian`
    - Compute mean luminance as mean of L channel in LAB colorspace
    - Set `is_blurry = laplacian_var < config.blur_threshold`
    - Set `is_dark = mean_luminance < config.dark_threshold`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 5.2 Write property test for quality threshold flags
    - **Property 9: Quality threshold flags**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    - File: `tests/property/test_prop_quality.py`
    - Tag: `# Feature: digital-curator-mvp, Property 9: Quality threshold flags`

  - [ ]* 5.3 Write unit tests for QualityAssessor
    - Happy path with known blurry/sharp/dark/bright images
    - Edge case: zero-byte or corrupt image
    - File: `tests/unit/test_quality_assessor.py`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 6. Implement ThumbnailGenerator
  - [x] 6.1 Implement `host/thumbnail_generator.py` with `ThumbnailGenerator.generate(source, dest) -> bool` and `get_or_create(record) -> Optional[Path]`
    - Resize to max 400px on longest side, output JPEG
    - Strip all EXIF by clearing `image.info` before save
    - Cache key: `{sha256[:16]}.jpg` in `~/.digital-curator/thumbs/`
    - Reuse existing thumbnail if `last_modified` unchanged
    - On failure: log WARNING, set `thumb_status = 'unavailable'`, remove partial file
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 6.2 Write property test for thumbnail dimension constraint
    - **Property 10: Thumbnail dimension constraint**
    - **Validates: Requirements 5.1**
    - File: `tests/property/test_prop_thumbnails.py`
    - Tag: `# Feature: digital-curator-mvp, Property 10: Thumbnail dimension constraint`

  - [ ]* 6.3 Write property test for thumbnail EXIF stripping
    - **Property 11: Thumbnail EXIF stripping**
    - **Validates: Requirements 5.2**
    - File: `tests/property/test_prop_thumbnails.py`
    - Tag: `# Feature: digital-curator-mvp, Property 11: Thumbnail EXIF stripping`

  - [ ]* 6.4 Write property test for thumbnail generation idempotence
    - **Property 12: Thumbnail generation idempotence**
    - **Validates: Requirements 5.4**
    - File: `tests/property/test_prop_thumbnails.py`
    - Tag: `# Feature: digital-curator-mvp, Property 12: Thumbnail generation idempotence`

  - [ ]* 6.5 Write property test for thumbnail failure marking status unavailable
    - **Property 13: Thumbnail failure marks status unavailable**
    - **Validates: Requirements 5.5**
    - File: `tests/property/test_prop_thumbnails.py`
    - Tag: `# Feature: digital-curator-mvp, Property 13: Thumbnail failure marks status unavailable`

  - [ ]* 6.6 Write unit tests for ThumbnailGenerator
    - Happy path, cache hit, corrupt image, disk-full simulation
    - File: `tests/unit/test_thumbnail_generator.py`
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

- [x] 7. Implement DuplicateDetector
  - [x] 7.1 Implement `host/duplicate_detector.py` with `DuplicateDetector.detect(records) -> list[DuplicateGroup]` and `_select_winner(group) -> FileRecord`
    - Group by identical SHA-256 → exact duplicates
    - Cluster remaining by pHash Hamming distance ≤ 10 → near-duplicates (Burst_Groups)
    - Winner: highest pixel count; tiebreak by highest Laplacian variance
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

  - [ ]* 7.2 Write property test for exact duplicate grouping by SHA-256
    - **Property 5: Exact duplicate grouping by SHA-256**
    - **Validates: Requirements 2.1**
    - File: `tests/property/test_prop_duplicates.py`
    - Tag: `# Feature: digital-curator-mvp, Property 5: Exact duplicate grouping by SHA-256`

  - [ ]* 7.3 Write property test for near-duplicate grouping by pHash Hamming distance
    - **Property 6: Near-duplicate grouping by pHash Hamming distance**
    - **Validates: Requirements 2.2**
    - File: `tests/property/test_prop_duplicates.py`
    - Tag: `# Feature: digital-curator-mvp, Property 6: Near-duplicate grouping by pHash Hamming distance`

  - [ ]* 7.4 Write property test for winner selection correctness
    - **Property 7: Winner selection correctness**
    - **Validates: Requirements 2.4, 2.5**
    - File: `tests/property/test_prop_duplicates.py`
    - Tag: `# Feature: digital-curator-mvp, Property 7: Winner selection correctness`

  - [ ]* 7.5 Write unit tests for DuplicateDetector
    - Exact duplicates, near-duplicates, single-file group, all files in one group
    - Winner tiebreak by Laplacian variance
    - File: `tests/unit/test_duplicate_detector.py`
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

- [x] 8. Implement Scanner and wire sub-detectors
  - [x] 8.1 Implement `host/scanner.py` with `Scanner.scan(directory, progress_callback) -> ScanResult`
    - Traverse directory tree, filter by supported extensions (`.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`)
    - For each file: compute SHA-256 + pHash, run ScreenshotDetector, run QualityAssessor, run ThumbnailGenerator, call `Indexer.upsert_file`
    - Emit progress as `files_processed / total_files * 100` via callback
    - Skip unreadable files: log WARNING with path, continue
    - After all files indexed: run DuplicateDetector, persist groups via `Indexer.upsert_group`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [ ]* 8.2 Write property test for scanner discovering all image files
    - **Property 1: Scanner discovers all image files**
    - **Validates: Requirements 1.1**
    - File: `tests/property/test_prop_scanner.py`
    - Tag: `# Feature: digital-curator-mvp, Property 1: Scanner discovers all image files`

  - [ ]* 8.3 Write property test for scanner resilience to unreadable files
    - **Property 2: Scanner resilience to unreadable files**
    - **Validates: Requirements 1.2**
    - File: `tests/property/test_prop_scanner.py`
    - Tag: `# Feature: digital-curator-mvp, Property 2: Scanner resilience to unreadable files`

  - [ ]* 8.4 Write property test for scan progress monotonically increasing and bounded
    - **Property 3: Scan progress is monotonically increasing and bounded**
    - **Validates: Requirements 1.3**
    - File: `tests/property/test_prop_scanner.py`
    - Tag: `# Feature: digital-curator-mvp, Property 3: Scan progress is monotonically increasing and bounded`

  - [ ]* 8.5 Write unit tests for Scanner
    - Empty directory, mixed readable/unreadable files, progress callback sequence
    - File: `tests/unit/test_scanner.py`
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 9. Checkpoint — Ensure all backend unit and property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement TrashManager and DataManager
  - [x] 10.1 Implement `host/trash_manager.py` with `TrashManager.trash_files(file_ids) -> TrashResult`
    - Use `send2trash.send2trash()` per file
    - On success: call `Indexer.set_trashed(file_id)`
    - On failure: log ERROR, do NOT update DB, add to `failed` list
    - Return `TrashResult(trashed, failed)`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 10.2 Write property test for trash operation correctness and safety
    - **Property 19: Trash operation correctness and safety**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**
    - File: `tests/property/test_prop_trash.py`
    - Tag: `# Feature: digital-curator-mvp, Property 19: Trash operation correctness and safety`

  - [ ]* 10.3 Write unit tests for TrashManager
    - Happy path, partial failure (some files fail), `send2trash` exception injection
    - File: `tests/unit/test_trash_manager.py`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 10.4 Implement `host/data_manager.py` with `DataManager.wipe() -> None`
    - Delete SQLite DB file (idempotent if absent)
    - Delete entire thumbnail cache directory (idempotent if absent)
    - Do NOT touch original image files
    - _Requirements: 10.3, 10.4, 10.6_

  - [ ]* 10.5 Write property test for wipe removing app data but not originals
    - **Property 20: Wipe removes app data but not originals**
    - **Validates: Requirements 10.3, 10.4, 10.6**
    - File: `tests/property/test_prop_wipe.py`
    - Tag: `# Feature: digital-curator-mvp, Property 20: Wipe removes app data but not originals`

  - [ ]* 10.6 Write unit tests for DataManager
    - Wipe with existing DB + thumbs, wipe when already absent (idempotent)
    - File: `tests/unit/test_data_manager.py`
    - _Requirements: 10.3, 10.4, 10.6_

- [x] 11. Implement DecisionSync (WebSocket broadcast)
  - [x] 11.1 Implement `host/decision_sync.py` with `DecisionSync` class
    - `record_decision(file_id, decision)`: persist to DB via Indexer, then broadcast
    - `broadcast(payload: DecisionPayload)`: send JSON to all connected WebSocket clients
    - `handle_remote_decision(payload)`: deserialize, validate, call `record_decision`
    - Maintain a connection pool; remove disconnected clients on send failure
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 11.3_

  - [ ]* 11.2 Write property test for new client receiving complete decision state
    - **Property 21: New client receives complete decision state**
    - **Validates: Requirements 11.3**
    - File: `tests/property/test_prop_sync.py`
    - Tag: `# Feature: digital-curator-mvp, Property 21: New client receives complete decision state`

  - [ ]* 11.3 Write property test for decision payload serialization round-trip
    - **Property 22: Decision payload serialization round-trip**
    - **Validates: Requirements 12.4, 12.5, 12.6**
    - File: `tests/property/test_prop_sync.py`
    - Tag: `# Feature: digital-curator-mvp, Property 22: Decision payload serialization round-trip`

  - [ ]* 11.4 Write unit tests for DecisionSync
    - Client connects and receives initial state, broadcast on decision, malformed JSON handling, client disconnect
    - File: `tests/unit/test_decision_sync.py`
    - _Requirements: 8.1, 8.2, 8.3, 11.3_

- [x] 12. Implement FastAPI routes and wire all backend components
  - [x] 12.1 Create `host/api.py` with FastAPI app and all routes
    - `POST /scan` — start scan, return 202 with scan job id
    - `GET /scan/progress` — SSE stream of progress percentage
    - `GET /triage/{category}` — return flagged files for category (duplicates/screenshots/blurry)
    - `GET /groups/{group_id}` — return group detail with member metadata (width, height, laplacian_var)
    - `GET /thumbs/{file_id}` — serve thumbnail JPEG from cache
    - `POST /decisions` — record Keep/Delete decision via DecisionSync
    - `GET /decisions` — return all current decisions
    - `WS /ws` — WebSocket endpoint; send full decision state on connect, relay broadcasts
    - `POST /trash` — call TrashManager with list of file_ids
    - `POST /wipe` — call DataManager.wipe() after validating confirmation token
    - Return `{"error": ..., "detail": ...}` for all 4xx/5xx responses
    - _Requirements: 6.1, 6.2, 7.3, 8.1, 8.2, 8.3, 9.1, 10.1, 10.2, 11.1, 11.2, 11.4, 11.5_

  - [ ]* 12.2 Write property test for category filter correctness
    - **Property 14: Category filter correctness**
    - **Validates: Requirements 6.2**
    - File: `tests/property/test_prop_triage.py`
    - Tag: `# Feature: digital-curator-mvp, Property 14: Category filter correctness`

  - [ ]* 12.3 Write property test for group detail including quality metadata
    - **Property 15: Group detail includes quality metadata**
    - **Validates: Requirements 7.3**
    - File: `tests/property/test_prop_triage.py`
    - Tag: `# Feature: digital-curator-mvp, Property 15: Group detail includes quality metadata`

  - [ ]* 12.4 Write property test for "Keep Best" assigning correct decisions
    - **Property 16: "Keep Best" assigns correct decisions**
    - **Validates: Requirements 7.4**
    - File: `tests/property/test_prop_triage.py`
    - Tag: `# Feature: digital-curator-mvp, Property 16: Keep Best assigns correct decisions`

  - [ ]* 12.5 Write property test for manual winner reassignment
    - **Property 17: Manual winner reassignment**
    - **Validates: Requirements 7.5**
    - File: `tests/property/test_prop_triage.py`
    - Tag: `# Feature: digital-curator-mvp, Property 17: Manual winner reassignment`

  - [ ]* 12.6 Write unit tests for API routes
    - Each route: correct status codes and response shapes
    - Error cases: unknown file_id (404), conflicting decision (409), internal error (500)
    - WebSocket: connect, receive initial state, receive broadcast
    - File: `tests/unit/test_api.py`
    - _Requirements: 6.1, 6.2, 7.3, 8.2, 8.3, 11.1_

- [x] 13. Checkpoint — Ensure all backend tests pass including API tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Implement React frontend — core layout and triage tabs
  - [x] 14.1 Create `frontend/src/App.tsx` with three-tab layout: "Duplicates", "Screenshots", "Blurry"
    - Each tab fetches `GET /triage/{category}` and renders a thumbnail grid
    - Display empty-state message when no flagged images exist in a category
    - Show each image using `<img src="/thumbs/{file_id}">` (thumbnail only, never original)
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

  - [x] 14.2 Implement undecided/keep/delete state indicator per thumbnail
    - Neutral indicator for undecided, visual keep/delete badges
    - _Requirements: 8.5_

  - [ ]* 14.3 Write component tests for triage tab rendering
    - Test tab switching, empty state, thumbnail display, decision badges
    - Use React Testing Library
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x] 15. Implement side-by-side comparison view for duplicate groups
  - [x] 15.1 Create `frontend/src/ComparisonView.tsx` for Burst_Group detail
    - Fetch `GET /groups/{group_id}` and render multi-pane view
    - Overlay "Golden Star" indicator on candidate winner thumbnail
    - Display resolution (W×H) and Laplacian variance score per image
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 15.2 Implement "Keep Best" button and manual winner selection
    - "Keep Best": POST decision keep for winner + delete for all others
    - Manual tap on image: reassign keep to tapped image, delete to all others
    - _Requirements: 7.4, 7.5_

  - [ ]* 15.3 Write component tests for ComparisonView
    - Golden star on winner, resolution/laplacian display, Keep Best action, manual reassignment
    - Use React Testing Library
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 16. Implement real-time decision sync in the frontend
  - [x] 16.1 Create `frontend/src/hooks/useDecisionSync.ts`
    - Open WebSocket to `ws://{host}/ws` on mount
    - Load initial state from `GET /decisions` on connect
    - Apply incoming decision broadcasts to local React state
    - Expose `recordDecision(file_id, decision)` which POSTs to `/decisions`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 11.3_

  - [ ]* 16.2 Write unit tests for useDecisionSync hook
    - Initial state load, incoming broadcast updates state, recordDecision sends POST
    - _Requirements: 8.2, 8.3, 11.3_

- [x] 17. Implement settings panel with Wipe App Data
  - Create `frontend/src/SettingsPanel.tsx` with clearly labeled "Wipe App Data" button
  - Show confirmation dialog before proceeding
  - On confirm: POST `/wipe` with confirmation token; on success display confirmation message and reset to initial state
  - _Requirements: 10.1, 10.2, 10.5_

- [x] 18. Final checkpoint — Ensure all tests pass end-to-end
  - Ensure all unit tests, property tests, and component tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use the `hypothesis` library with minimum 100 examples per test
- Tag format for property tests: `# Feature: digital-curator-mvp, Property {N}: {description}`
- Checkpoints ensure incremental validation at meaningful milestones
- The frontend never accesses original image files — only `/thumbs/{file_id}` endpoints
