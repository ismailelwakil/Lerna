# Academic OS — Manual Student Acceptance Test Plan

**Target Audience:** Non-technical manual testers, product managers, and educational evaluators.  
**Live UI Host:** `http://localhost:8501` (Active in the browser preview environment)  
**Test Data Directory:** `/home/user/academic-os/data/manual_test/sample_manual_lecture.txt`  
**Test Student ID:** `manual_student_01`  
**Test Course:** `CS101 Algorithms`  

---

## Part 1: Primary End-to-End Student Journey

Follow these sequential steps in the browser to verify the complete learning cycle.

### Step 1: Open the Academic OS UI
- **Action:** Navigate to `http://localhost:8501` in your browser.
- **Expected Result:** The Academic OS "AI Tutor" application loads immediately. You see the header banner with course chips, theme switch (`☀️ Light` / `🌙 Dark`), and four main tabs: `Tutor`, `My Learning`, `Course Materials`, and `Study Tools`.

---

### Step 2: Configure Course & Preferences
- **Page/Location:** Click the `👤 Student Profile & Preferences` expander at the top.
- **Fields & Values:**
  - **Course:** Type `CS101 Algorithms`
  - **Language:** Select `English`
  - **Learning preference:** Select `step-by-step`
- **Button:** Click `Save preferences`
- **Expected Result:** A green toast displays "Preferences updated!". The header chip updates to display `CS101 Algorithms`, `English`, and `step-by-step`.

---

### Step 3: Upload Course Lecture Material
- **Page/Location:** Click on the **Course Materials** tab.
- **Action:** In the file uploader labeled "Upload course material", drag and drop or browse to select the prepared file:  
  `/home/user/academic-os/data/manual_test/sample_manual_lecture.txt`
- **Button:** Click **Add material** (primary blue button).
- **Expected Result:** A spinner indicates indexing. Upon completion, a green message displays:  
  `sample_manual_lecture.txt is ready for AI Tutor.`  
  Under "Available materials", a card appears displaying `sample_manual_lecture.txt` with a green `Ready` badge.

---

### Step 4: Ask a Course-Constrained Question
- **Page/Location:** Click on the **Tutor** tab.
- **Field:** In the multi-select dropdown `Use materials`, select `sample_manual_lecture.txt`.
- **Field:** In the chat input box at the bottom, enter:  
  `According to our lecture notes, what was the exact latency of the cryogenic array benchmark and what is the unique proof token?`
- **Action:** Press Enter or submit.
- **Expected Result:**
  - The Tutor responds: "According to the lecture notes, the cryogenic array benchmark achieved an exact latency of **4.81 microseconds** (UniqueManualProofToken#9824) [1]."
  - Below the response, a small caption appears: `Grounded in selected/uploaded course material`.
  - A source citation card displays `[1] sample_manual_lecture.txt`.
  - Proves that RAG strictly used the uploaded synthetic fact rather than generic pre-trained memory.

---

### Step 5: Start a Knowledge Diagnostic
- **Page/Location:** Click on the **My Learning** tab.
- **Field:** Under "Start a knowledge check", enter topic: `Binary Search`.
- **Button:** Click **Start knowledge check**.
- **Expected Result:** The diagnostic questions generate and appear under "Knowledge check". Each question displays its concept target and provides answer choices, including an explicit `I don't know` option.

---

### Step 6: Submit Diagnostic with a Misconception
- **Page/Location:** Under the generated diagnostic in **My Learning**:
- **Action:** For the first question (concept: Binary Search), purposefully select the option indicating:  
  `binary search works on completely unsorted collections` or type an answer stating that sorting is not required.
- **Button:** Click **Submit knowledge check**.
- **Expected Result:**
  - The assessment score calculates (e.g. score < 0.60).
  - The concept is flagged under "Focus areas".
  - Under "Concepts to revisit", an active warning banner appears highlighting the detected misconception:  
    `⚠️ Student believes binary search can operate on unsorted sequences.`
  - The "Next Best Action" card dynamically recommends:  
    **Action:** `Correct Misconception`  
    **Reason:** `A misconception was detected in assessment evidence.`  
    **Strategy:** `Misconception-Correction`

---

### Step 7: Personalized Tutor Intervention
- **Page/Location:** Switch back to the **Tutor** tab.
- **Field:** In the chat input box, ask:  
  `Why did my diagnostic say I had a misconception about binary search requirements?`
- **Action:** Submit.
- **Expected Result:** The Tutor provides a targeted contrastive explanation directly refuting the misconception: it clarifies that binary search relies on ordering to eliminate half of the elements; without sorted data, division in half could discard the target element.

---

### Step 8: Review Study Planner & Spaced Repetition Queue
- **Page/Location:** Click on the **My Learning** tab.
- **Expected Result:**
  - Under **Reactive Study Plan**, prioritized cards appear:  
    `🔴 High: Resolve Misconception on Binary Search` with recommended steps.
  - Under **Spaced Repetition (Due for Review)**, the weak concept `binary search` is listed with its current mastery and two buttons: `Remembered ✓` and `Forgot ✗`.
- **Action:** Click `Remembered ✓` next to `binary search`.
- **Expected Result:** The page refreshes; mastery increases and the scheduled interval is updated.

---

### Step 9: Reassessment & Misconception Clearance
- **Page/Location:** In **My Learning**, scroll to "Start a knowledge check".
- **Field:** Enter `Binary Search` and click **Start knowledge check**.
- **Action:** Answer all questions correctly (e.g. selecting that input must be strictly sorted and time complexity is O(log n)).
- **Button:** Click **Submit knowledge check**.
- **Expected Result:**
  - Score updates to 100% / 0.8+.
  - The misconception warning is removed.
  - Under **Resolved Misconceptions**, a green success banner appears:  
    `✓ Cleared: Student understands input array must be sorted.`
  - Under **Next Best Action**, the recommendation changes to **Progress** or **Targeted Practice**.

---

### Step 10: Generate Learning Resources (All Formats)
- **Page/Location:** Click on the **Study Tools** tab.
- **Field:** Enter Topic: `Binary Search`.
- **Action:** Under "Choose resources", check all options (or select `Architecture Diagram`, `Presentation Deck`, `Study Notes`, `Formal Exam`).
- **Button:** Click **Generate resources**.
- **Expected Result:**
  - A spinner runs.
  - Formatted text cards render the Notes, Exam, and Questions.
  - For `Architecture Diagram`: An SVG diagram preview renders visually in the browser, accompanied by a `Download Diagram` button.
  - For `Presentation Deck`: A PowerPoint `.pptx` download button appears.
  - Click `Download Diagram` or `Download Presentation` to confirm file delivery.

---

### Step 11: Saved Resources History
- **Page/Location:** In **Study Tools**, scroll to **Saved Study Resources**.
- **Action:** Click the expander `📚 View previously generated study resources`.
- **Expected Result:** Your previous generation session appears with timestamp, topic (`Binary Search`), and download links.

---

### Step 12: Voice Push-to-Talk Interaction
- **Page/Location:** Click on the **Tutor** tab.
- **Action:** Click the `🎙️ Voice Question` expander.
- **Action:** Upload an audio question file (WAV or MP3) or a sample recorded file.
- **Button:** Click **Process voice query**.
- **Expected Result:**
  - The voice tutor transcribes the question and feeds it into the **same** tutor learning brain and profile.
  - The user message appears with a `🎙️` icon.
  - The grounded tutor answer appears with source citations.
  - An embedded audio player (`st.audio`) allows playing the synthesized tutor response.

---

### Step 13: Persistence Across Restart
- **Action:** Refresh your browser window completely (Ctrl+R / Cmd+R).
- **Expected Result:**
  - Profile preferences, uploaded course materials, mastery scores, resolved misconceptions, and conversation history persist.
  - No data is lost upon refresh.

---

## Part 2: Independent Capability Tests

### Test A: Trusted External Web Discovery (Binary Search Historical Failure Test)
- **Location:** **Tutor** tab.
- **Control:** Deselect all materials in `Use materials` (leave empty for trusted general discovery).
- **Prompt:**  
  `What is binary search? Explain how it works, state its time complexity, and mention the main requirement that must be satisfied before using it.`
- **Verification Criteria:**
  - Coherent direct definition of binary search.
  - Explanation of the repeated-halving mechanism.
  - State time complexity is O(log n).
  - Explicit statement that input must be sorted.
  - Inline bracketed citations `[1]`.
  - **Zero contamination**: Must NOT dump raw text about Treap, Heap Sort, or Red-Black Trees.

### Test B: Instruction Following & One-Sentence Constraint
- **Location:** **Tutor** tab (unselected materials).
- **Prompt:**  
  `What is the capital of France? Answer in one sentence only.`
- **Verification Criteria:**
  - Answer is exactly one sentence: `The capital of France is Paris [1].`
  - No irrelevant retrieval text.

### Test C: High-Stakes Clinical Knowledge & Wikipedia Exclusion
- **Location:** **Tutor** tab.
- **Prompt:**  
  `What is the mechanism of action of penicillin on bacterial cell wall synthesis?`
- **Verification Criteria:**
  - Explains inhibition of bacterial transpeptidase enzymes and peptidoglycan cross-linking.
  - Evidence citations cite authoritative medical sources (e.g. StatPearls, NCBI, WHO).
  - **Wikipedia is strictly excluded** from clinical citations.

### Test D: Multilingual Arabic & Egyptian Dialect
- **Location:** **Tutor** tab.
- **Prompt (Egyptian Dialect):**  
  `اشرحلي ازاي بيشتغل البحث الثنائي binary search وايه التعقيد بتاعه`
- **Verification Criteria:**
  - Tutor responds in Arabic with technical terms preserved (`Binary Search`, `O(log n)`).
  - Uses natural explanatory terminology (`البحث الثنائي`, `مصفوفة مرتبة`, `نصف`).

### Test E: Socratic Guidance vs Direct Mode
- **Location:** **Tutor** tab.
- **Control:** In `Tutoring style`, select **Socratic Guidance**.
- **Prompt:**  
  `How do I invert a binary tree in Python?`
- **Verification Criteria:**
  - The Tutor guides you with questions about base cases and recursive swaps rather than immediately dumping the entire solution.

---

## Part 3: Acceptance Checklist for Evaluators

| Verification Check | Pass | Notes |
| :--- | :---: | :--- |
| 1. Streamlit loads on port 8501 without errors | [ ] | |
| 2. Course and preferences sync and persist | [ ] | |
| 3. Material RAG retrieves unique synthetic fact (4.81 microseconds) | [ ] | |
| 4. Knowledge diagnostic generates with explicit "I don't know" | [ ] | |
| 5. Misconception correctly flagged and updates Next Best Action | [ ] | |
| 6. Reassessment clears misconception and updates mastery | [ ] | |
| 7. Spaced repetition queue and study plan react dynamically | [ ] | |
| 8. All 14 content types generate valid text, SVG, or PPTX | [ ] | |
| 9. Voice interaction routes through the same unified student brain | [ ] | |
| 10. Trusted general search passes binary search regression without noise | [ ] | |
| 11. Clinical questions exclude Wikipedia from evidence | [ ] | |
| 12. Multilingual queries preserve Arabic concept integrity | [ ] | |
