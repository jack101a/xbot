# OCR-Enhanced Tracking & Solving Plan

This plan implements an active OCR-based solver that not only identifies the correct answer but also tracks game state (Score, Question Number, Time) directly from screenshots. This is necessary because the Parivahan portal renders critical information as images.

## User Review Required

> [!IMPORTANT]
> - **Performance Overhead**: OCR processing on a CPU takes ~2-5 seconds. We will optimize this by using a singleton OCR engine to avoid reloading weights.
> - **Spatial Assumptions**: The logic assumes a standard vertical layout as seen in the portal screenshots. If the UI changes (e.g., mobile view), the coordinate mapping might need adjustment.
> - **PaddleOCR Installation**: Initial run will download ~200MB of Hindi models.

## Proposed Changes

---

### Backend Components

#### [MODIFY] `ocr_engine.py`
- Refine the text extraction logic to use bounding boxes for spatial grouping.
- **Metadata Extraction**:
    - Extract "Score" (स्कोर), "Question No" (प्रश्न), and "Time Remaining" (शेष सेकंड).
- **Question Isolation**:
    - Track text blocks in the middle Y-range to form the vector search query.
- **Option Mapping**:
    - Group the 4 bottom-most text regions into Options 1-4.
    - Perform fuzzy similarity matching between these regions and the Vector DB target result.

#### [MODIFY] `main.py`
- Update the `/ocr-solve` endpoint to return the tracked metadata (Score, QNo, Time) alongside the chosen answer.

---

### Extension Update

#### [MODIFY] `content.js`
- Update the UI Overlay to display the tracked "Live Stats" returned from the backend OCR.
- Replace the current DOM-based score scraper with the OCR-derived values for better accuracy.

---

### Verification Plan

#### Automated Verification
- Run `test_ocr.py` on existing logged screenshots to verify correct Score/QNo/Option extraction.
- Validate that the fuzzy matching logic identifies the correct option even with minor OCR noise.

#### Manual Verification
- Test on a live Parivahan exam page.
- Verify that the overlay correctly mirrors the "Score" and "Question No" shown on the page.
- Confirm the solver clicks the correct radio button regardless of random option rotation.
