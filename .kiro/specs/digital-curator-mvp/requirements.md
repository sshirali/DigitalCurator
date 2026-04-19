# Requirements Document

## Introduction

Digital Curator MVP is a privacy-first, web-based photo organization tool designed for cross-device use. It helps users reclaim storage and mental space by identifying "digital junk" (duplicates, screenshots, and low-quality photos) through a local-first processing engine. A desktop Host performs all heavy scanning and indexing locally, while a lightweight Remote UI (tablet/mobile) loads only thumbnails for fast triage and decision-making. No original images are ever uploaded to the cloud.

## Glossary

- **System**: The Digital Curator MVP application as a whole.
- **Host**: The desktop process responsible for scanning, indexing, and serving the web interface.
- **Remote_UI**: The web-based interface accessed from a tablet or mobile device for triage.
- **Scanner**: The component that analyzes image files on the local filesystem.
- **Indexer**: The component that stores file paths, hashes, and metadata in the local database.
- **Duplicate_Detector**: The component that identifies identical and near-identical images.
- **Screenshot_Detector**: The component that identifies images likely to be screenshots.
- **Quality_Assessor**: The component that evaluates image sharpness and exposure.
- **Thumbnail_Generator**: The component that creates stripped, lightweight image previews.
- **Triage_UI**: The categorized interface for reviewing and acting on flagged images.
- **Decision_Sync**: The component that propagates Keep/Delete decisions across devices.
- **Trash_Manager**: The component that moves files to the system Trash/Recycle Bin.
- **Data_Manager**: The component responsible for clearing all local app data.
- **Perceptual_Hash**: A hash value representing the visual content of an image, used for near-duplicate detection.
- **Laplacian_Variance**: A numerical measure of image sharpness computed via the Laplacian operator.
- **EXIF**: Exchangeable Image File Format metadata embedded in image files, which may include GPS coordinates and device information.
- **Burst_Group**: A set of near-identical photos taken in rapid succession.
- **Winner**: The single image within a group selected as the best to keep.

---

## Requirements

### Requirement 1: Local File Scanning

**User Story:** As a user, I want the Host to scan a folder of photos on my local machine, so that the system can identify which files need review without sending any data to the cloud.

#### Acceptance Criteria

1. WHEN the user initiates a scan on a selected directory, THE Scanner SHALL traverse all image files (JPEG, PNG, HEIC, WEBP) within that directory and its subdirectories.
2. WHEN the Scanner encounters a file it cannot read, THE Scanner SHALL log the error with the file path and continue scanning remaining files.
3. WHILE a scan is in progress, THE System SHALL display the current scan progress as a percentage of files processed.
4. WHEN a scan completes, THE Indexer SHALL store each file's absolute path, file size, last-modified timestamp, SHA-256 hash, and Perceptual_Hash in the local SQLite database.
5. THE Scanner SHALL complete indexing of 1,000 image files in under 60 seconds on the Host machine.
6. THE Scanner SHALL process all image files exclusively on the Host machine's local hardware, transmitting no original image data to any external server.

---

### Requirement 2: Duplicate Detection

**User Story:** As a user, I want the system to identify duplicate and near-duplicate photos, so that I can delete redundant copies and free up storage.

#### Acceptance Criteria

1. WHEN the scan completes, THE Duplicate_Detector SHALL group files with identical SHA-256 hashes as exact duplicates.
2. WHEN the scan completes, THE Duplicate_Detector SHALL group files whose Perceptual_Hash values differ by a Hamming distance of 10 or fewer bits as near-duplicates (Burst_Groups).
3. THE Duplicate_Detector SHALL achieve a grouping precision of greater than 90% when identifying Burst_Groups.
4. WHEN a Burst_Group is identified, THE Duplicate_Detector SHALL designate the file with the highest pixel resolution as the candidate Winner.
5. IF two or more files in a Burst_Group share the highest resolution, THEN THE Duplicate_Detector SHALL designate the file with the highest Laplacian_Variance as the candidate Winner.
6. WHEN duplicate groups are identified, THE Indexer SHALL persist each group's membership and the candidate Winner to the local database.

---

### Requirement 3: Screenshot Identification

**User Story:** As a user, I want the system to automatically flag screenshots, so that I can quickly review and remove them without manually sorting through my library.

#### Acceptance Criteria

1. WHEN the Scanner processes an image file, THE Screenshot_Detector SHALL flag the file as a screenshot candidate IF the file lacks EXIF metadata AND the image aspect ratio matches a known device screen ratio (e.g., 9:19.5, 9:16, 2:3) within a tolerance of ±0.05.
2. WHEN the Scanner processes an image file, THE Screenshot_Detector SHALL flag the file as a screenshot candidate IF the filename contains the substring "screenshot" (case-insensitive).
3. WHEN the Scanner processes an image file, THE Screenshot_Detector SHALL flag the file as a screenshot candidate IF the file lacks EXIF capture date metadata.
4. WHEN a file matches two or more screenshot detection criteria, THE Screenshot_Detector SHALL assign it a higher confidence score than a file matching only one criterion.
5. THE Indexer SHALL store each file's screenshot flag status and confidence score in the local database.

---

### Requirement 4: Image Quality Assessment

**User Story:** As a user, I want the system to detect blurry or poorly lit photos, so that I can remove low-quality images that I would never use.

#### Acceptance Criteria

1. WHEN the Scanner processes an image file, THE Quality_Assessor SHALL compute the Laplacian_Variance of the image to measure sharpness.
2. WHEN the computed Laplacian_Variance of an image is below a configurable threshold (default: 100.0), THE Quality_Assessor SHALL flag the image as blurry.
3. WHEN the Scanner processes an image file, THE Quality_Assessor SHALL compute the mean luminance of the image.
4. WHEN the computed mean luminance of an image is below a configurable threshold (default: 30 on a 0–255 scale), THE Quality_Assessor SHALL flag the image as poorly lit.
5. THE Indexer SHALL store each file's Laplacian_Variance score, mean luminance score, and quality flags in the local database.

---

### Requirement 5: Thumbnail Generation

**User Story:** As a user, I want the Host to generate lightweight thumbnails for mobile triage, so that my tablet or phone can load previews quickly without accessing original files.

#### Acceptance Criteria

1. WHEN an image file is indexed, THE Thumbnail_Generator SHALL produce a JPEG thumbnail with a maximum dimension of 400 pixels on the longest side.
2. THE Thumbnail_Generator SHALL strip all EXIF metadata, including GPS coordinates and device identifiers, from every generated thumbnail.
3. THE Thumbnail_Generator SHALL store all thumbnails on the Host machine's local filesystem and SHALL NOT transmit original image data to any external server.
4. WHEN a thumbnail already exists for a file with an unchanged last-modified timestamp, THE Thumbnail_Generator SHALL reuse the existing thumbnail rather than regenerating it.
5. IF the Thumbnail_Generator fails to process an image file, THEN THE System SHALL log the error and mark that file's thumbnail status as unavailable in the database.

---

### Requirement 6: Triage UI — Categorized Review

**User Story:** As a user, I want a categorized interface with separate tabs for each type of clutter, so that I can focus my review on one category at a time.

#### Acceptance Criteria

1. THE Triage_UI SHALL present three distinct tabs: "Duplicates," "Screenshots," and "Blurry."
2. WHEN a tab is selected, THE Triage_UI SHALL display only the images flagged under that category.
3. THE Triage_UI SHALL display each image using its thumbnail rather than the original file.
4. THE Triage_UI SHALL enable a user to review and act on 50 items of clutter in under 60 seconds.
5. WHEN no flagged images exist in a category, THE Triage_UI SHALL display an empty-state message indicating the category is clean.

---

### Requirement 7: Side-by-Side Comparison

**User Story:** As a user, I want to compare similar photos side by side with quality indicators, so that I can make an informed decision about which photo to keep.

#### Acceptance Criteria

1. WHEN a user selects a Burst_Group in the Duplicates tab, THE Triage_UI SHALL display all images in the group in a dual-pane or multi-pane side-by-side view.
2. THE Triage_UI SHALL overlay a visual "Golden Star" indicator on the thumbnail of the candidate Winner within each Burst_Group.
3. THE Triage_UI SHALL display the resolution (width × height in pixels) and Laplacian_Variance score for each image in the comparison view.
4. WHEN a user taps the "Keep Best" button for a group, THE Triage_UI SHALL mark the candidate Winner as Keep and mark all other images in the group as Delete.
5. WHEN a user manually selects a different image as the Winner, THE Triage_UI SHALL update the Keep/Delete assignments for the group accordingly.

---

### Requirement 8: Keep/Delete Decision Management

**User Story:** As a user, I want my triage decisions to be recorded and synchronized across my devices, so that actions I take on my tablet are reflected when I return to my desktop.

#### Acceptance Criteria

1. WHEN a user marks an image as Keep or Delete, THE Decision_Sync component SHALL persist the decision to the local SQLite database immediately.
2. WHEN a Remote_UI session is active, THE Decision_Sync component SHALL propagate Keep/Delete state changes to the Remote_UI within 5 seconds of the decision being recorded.
3. WHEN a Remote_UI session is active, THE Decision_Sync component SHALL propagate Keep/Delete state changes from the Remote_UI back to the Host within 5 seconds.
4. THE Decision_Sync component SHALL synchronize Keep/Delete decisions without transmitting original image files to any external server.
5. WHEN a user has not yet made a decision on an image, THE Triage_UI SHALL display the image with a neutral (undecided) state indicator.

---

### Requirement 9: Non-Destructive File Deletion

**User Story:** As a user, I want deleted files to be moved to the system Trash rather than permanently erased, so that I can recover files if I change my mind.

#### Acceptance Criteria

1. WHEN a user confirms a deletion action, THE Trash_Manager SHALL move all files marked as Delete to the operating system's Trash or Recycle Bin.
2. THE Trash_Manager SHALL NOT permanently delete any file from the filesystem during normal operation.
3. WHEN the Trash_Manager successfully moves a file, THE Indexer SHALL update that file's status to "trashed" in the local database.
4. IF the Trash_Manager fails to move a file to the Trash, THEN THE System SHALL display an error message identifying the affected file and SHALL NOT alter the file's status in the database.
5. WHEN a deletion action is confirmed, THE Trash_Manager SHALL move all marked files before reporting the total count of successfully trashed files to the user.

---

### Requirement 10: App Data Wipe

**User Story:** As a user, I want a single action to clear all app data, so that I can remove all traces of the application from my machine at any time.

#### Acceptance Criteria

1. THE Triage_UI SHALL provide a clearly labeled "Wipe App Data" button accessible from the application settings.
2. WHEN the user activates the "Wipe App Data" button, THE System SHALL present a confirmation dialog before proceeding.
3. WHEN the user confirms the wipe action, THE Data_Manager SHALL delete the local SQLite database file.
4. WHEN the user confirms the wipe action, THE Data_Manager SHALL delete all cached thumbnail files from the local filesystem.
5. WHEN the Data_Manager completes the wipe, THE System SHALL display a confirmation message and return to the initial setup state.
6. THE Data_Manager SHALL NOT delete any original image files during the wipe operation.

---

### Requirement 11: Cross-Device Remote Triage

**User Story:** As a user, I want to access the triage interface from my tablet or phone over the local network, so that I can review photos on a more comfortable screen without moving files.

#### Acceptance Criteria

1. WHEN the Host is running, THE System SHALL expose the Remote_UI as a web application accessible via the Host machine's local network IP address and a configurable port.
2. THE Remote_UI SHALL load and display thumbnails for triage without requiring access to original image files.
3. WHEN a Remote_UI client connects, THE System SHALL display the current triage state, including all existing Keep/Delete decisions.
4. THE Remote_UI SHALL function on current versions of Safari (iOS), Chrome (Android), and Chrome (desktop) without requiring a native app installation.
5. WHILE the Remote_UI is in use, THE System SHALL restrict access to the local network and SHALL NOT expose the interface to the public internet by default.

---

### Requirement 12: Data Parsing and Serialization

**User Story:** As a developer, I want all image metadata and decision state to be reliably parsed and serialized, so that data integrity is maintained across sessions and devices.

#### Acceptance Criteria

1. WHEN the Indexer writes a record to the SQLite database, THE Indexer SHALL serialize all file metadata fields (path, size, timestamp, SHA-256 hash, Perceptual_Hash, flags, scores) into a defined schema without data loss.
2. WHEN the Indexer reads a record from the SQLite database, THE Indexer SHALL deserialize all fields back into the corresponding in-memory data structures without data loss.
3. FOR ALL valid file metadata records, serializing then deserializing SHALL produce a record equivalent to the original (round-trip property).
4. WHEN the Decision_Sync component serializes a Keep/Delete decision for transmission to the Remote_UI, THE Decision_Sync component SHALL produce a JSON payload containing the file identifier and decision value.
5. WHEN the Remote_UI receives a JSON decision payload, THE Decision_Sync component SHALL deserialize it and update the local state without data loss.
6. FOR ALL valid decision payloads, serializing then deserializing SHALL produce a payload equivalent to the original (round-trip property).
