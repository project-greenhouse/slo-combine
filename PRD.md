# Product Requirements Document (PRD) & Development Plan
## Code 8 Performance App (Vue + Firebase Migration)

### 1. Executive Summary
**Objective:** Transition the existing Python Streamlit dashboard to a robust, scalable, and modern Vue 3 application using TypeScript and Firebase, incorporating role-based experiences for administrators, coaches, and athletes. Leveraging Firebase Cloud Functions (Gen 2 Python) allows us to reuse existing data processing logic while delivering a highly performant frontend.

### 2. System Architecture
*   **Frontend:** Vue 3 (Composition API), TypeScript, Vite.
*   **Styling:** Tailwind CSS (deep grays, crisp whites, and Code 8 gold/amber).
*   **State Management:** Pinia.
*   **Database & Auth:** Firebase Auth, Firestore (Database).
*   **Backend API & Compute:** Firebase Cloud Functions (Python Gen 2) on the Blaze Plan.
    *   Provides secure environment for Hawking Dynamics and Valor API keys.
    *   Executes complex `pandas` operations (percentile interpolations, merging, etc.) and returns clean JSON to the Vue frontend.

### 3. Core Features & Role Experiences

#### 3.1 Role-Based Access Control (RBAC)
*   **Routing guards** in Vue Router based on user role (Admin, Coach, Athlete).
*   **Firestore Security Rules** locking down write-access (e.g., commentaries) to Admins and Coaches.
*   **Admin/Owner:** Full read/write access to all data, configuration, user management, and roles.
*   **Coach:** Access to the "Coach's Evaluation Hub" for their assigned athletes or the full roster, allowing rapid input of commentary.
*   **Athlete:** Strictly read-only access. When they log in, they bypass roster selection and are routed directly to their personalized presentation dashboard.

#### 3.2 Coach's Evaluation Hub (Admin / Coach View)
*   A condensed, data-dense interface prioritizing raw metrics, cross-test percentiles, and historical benchmarks.
*   Optimized for rapid context-switching between athletes.
*   Side-by-side or persistent Rich Text Editor (VueQuill or Tiptap) for drafting strategy and commentary directly tied to the currently selected athlete.
*   Instant auto-save to Firestore (`/summaries/{athleteId}`).

#### 3.3 Athlete Presentation Dashboard (Athlete / Shared View)
*   Highly visual UI built with Chart.js or ECharts.
*   **Movement Data (Valor API):** Visualized Shoulder, Ankle, and Hip scores.
*   **Speed Data (Swift) & Power Data (Hawking Dynamics):** Percentile strip plots and bar charts.
*   Displays the Coach's rich-text summary seamlessly integrated into the UI as read-only actionable advice.

#### 3.4 Report Generation Engine
*   1-click PDF exports generated via dedicated `@media print` CSS routes.

---

### 4. Development & Execution Plan

#### Phase 1: Project Foundation & Security Setup (Week 1)
1. **Repository & Tooling:** Scaffold the Vue 3 + TypeScript + Vite project. Install Tailwind CSS.
2. **Firebase Setup & RBAC:**
   * Link to `code8-perofrmance` (Project Number: `457977335218`).
   * Setup Firebase Auth.
   * Create a `users` collection in Firestore to assign `role: 'admin' | 'coach' | 'athlete'`.
   * Configure Vue Router guards to redirect users based on their role upon login.

#### Phase 2: Python Cloud Functions Data Pipeline (Weeks 2-3)
*Reusing legacy Streamlit Python logic safely in the Cloud.*
1. **Setup Firebase Functions (Python Gen 2):** Initialize the functions directory.
2. **Migrate Logic:** 
   * Move `functions/data.py`, `func_swift.py`, and `func_player_info.py` logic into callable HTTP Cloud Functions.
   * Utilize existing `pandas` transformations for percentile calculations (`swiftSprint`, `proAgility`, `AthleteCMJ`).
   * Securely store Valor and HD API tokens using Firebase Secret Manager or environment variables.
3. **Firestore Seeding:** Migrate the static `ForcePlatePercentiles` and `CombinePercentiles` data from Supabase to Firestore.

#### Phase 3: The Coach's Evaluation Hub (Week 4)
*Focusing on the internal administrative experience.*
1. **Roster Navigation:** Build a lightning-fast, searchable data table or list for selecting athletes.
2. **Data-Dense UI:** Create the condensed metric view showing Sprint, Pro Agility, Vertical, Broad Jump, and Force Plate summaries in a tight, spreadsheet-like grid.
3. **Commentary Integration:** Embed the rich-text editor (VueQuill) directly alongside the data grid, auto-saving drafts to Firestore as the coach types.

#### Phase 4: Athlete Presentation Dashboard (Week 5-6)
*Focusing on the end-user visual experience.*
1. **State Management:** Connect Pinia to the new Firebase Python Cloud Functions to fetch the processed JSON data.
2. **Visual Component Development:**
   * Build the ECharts/SVG components for Shoulder/Ankle/Hip scores (replacing Matplotlib radial gauges).
   * Build the horizontal percentile strip plots for Speed & Power data.
3. **Commentary Display:** Pull the HTML commentary generated in Phase 3 from Firestore and render it cleanly inside the athlete's visual dashboard.
4. **PDF Export:** Implement the print-stylesheet logic for perfect 1-page athlete reports.

#### Phase 5: QA, Testing, & Deployment (Week 7)
1. **Integration Testing:** Verify that the Vue app seamlessly interacts with the Python Cloud Functions and properly displays data states (Loading, Error, Success).
2. **Security Rules Validation:** Ensure Athletes cannot read other athletes' data or write to the commentary collections.
3. **Deployment:** Deploy the Vue frontend to Firebase Hosting and the Python API to Firebase Functions.