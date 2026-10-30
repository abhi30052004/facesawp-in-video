# BollySwap AI - Phase 1 Studio Web Application

**BollySwap AI** is a premium, cinematic AI video face-swapping web application crafted specifically for Indian cinema workflows, digital filmmakers, VFX supervisors, and creative storytellers.

---

## 🎬 Design Identity & Palette
- **Background**: Near-black obsidian `#09090B`
- **Studio Cards**: Elevated slate `#17171C` (with `#202027` hover)
- **Primary Accent**: Muted Bollywood Gold `#D6AD65` / `#F3DC9B`
- **Secondary Accent**: Cinematic Velvet Burgundy `#8E3048` / `#FFA8BD`
- **Typography**: `Cinzel` (cinematic serif headings) + `Plus Jakarta Sans` (interface body) + `Space Grotesk` (timecode & frame metrics)
- **Visuals**: Ambient studio backlighting, glassmorphic panels, filmstrip borders, subtle restrained microinteractions via Framer Motion.

---

## 🚀 Key Modules Built in Phase 1

### 1. Navigation & Studio Layout
- **Collapsible Sidebar**: Smoothly expands and collapses (`Dashboard`, `Create Project`, `My Projects`, `Settings`).
- **Live Status Header**: Displays real-time API connection mode (`Frontend Demo Mode` vs `FastAPI Connected`), quick "+ New Face Swap" CTA, and director avatar.
- **Demo Transparency Banner**: Honestly identifies Phase 1 interactive simulation mode, clearly labeling demo data and simulated states without deceptive spoofing.
- **Studio Status Footer**: Highlights active GPU worker availability, storage meter, and C2PA provenance compliance.

### 2. Directorial Dashboard (`/`)
- **Quick Action Hero Banner**: Features prominent "Start New Face Swap" CTA and active model versioning (`BollyMesh-v2.4`).
- **Usage & Compute Statistics**:
  - Render Credits remaining (`420 / 500`)
  - Swaps Rendered (`38 master sequences`)
  - Footage Processed (`18.5 mins`)
  - Cloud Storage Quota (`3.2 GB / 25 GB`)
- **Recent Projects Roster**: Quick inspection cards with status badges and resolution indicators.
- **How It Works Guide**: 4-stage visual journey (Footage Ingestion → Target Identity → Consent & Synthesis → Synchronized Master Review).

### 3. Multi-Step Create Project Wizard (`/create`)
- **Step 1: Footage Ingestion**:
  - Drag-and-drop zone supporting `.mp4`, `.mov`, `.webm`.
  - Client-side validation: Max 100MB and Max 60 seconds duration check.
  - Video preview player with timecodes, aspect ratio, and resolution detection.
  - Instant pre-packaged Bollywood demo clips for immediate testing without personal media.
- **Step 2: Target Actor Identity Selection**:
  - **Bollywood Actor Roster (Demo Presets)**: Curated archetypes (*The Eternal Romantic Hero*, *Golden Age Matinee Idol*, *Royal Period Sovereign*, *High-Octane Action Star*, *Dramatic Powerhouse*, *Contemporary Glamour Lead*) labeled with demo tags and suitability scores.
  - **Custom Face Photo Upload**: Supports JPG and PNG (up to 10MB) with simulated 468 landmark alignment inspection.
- **Step 3: Ethical AI Likeness Consent Gate**:
  - Strict compliance check requiring explicit affirmations of likeness ownership/authorization, creative anti-deepfake policy, and synthetic media watermarking acknowledgment before render activation.
- **Step 4: Multi-Stage Processing Screen**:
  - Honest simulation state with live progress bar (0% - 100%), elapsed counter, and remaining ETA.
  - 4 distinct pipeline stages:
    1. *Footage Ingestion & Frame Extraction*
    2. *3D Facial Mesh & Landmark Tracking*
    3. *Neural Latent Swapping & Lighting Blending*
    4. *Temporal Consistency & Audio Remuxing*
  - Real-time terminal console streaming timestamped frame analysis logs.
  - Optional "Fast-Forward Simulation" button for swift evaluation.
- **Step 5: Results & Master Comparison**:
  - **Synchronized Master Comparison**: Dual players running simultaneously with unified play/pause and time scrub controls.
  - **Side-by-Side Mode** and **Interactive Split Slider Mode** to inspect hairline blending and skin texture.
  - **Export Action**: Triggers genuine browser download of the preview stream with honest Phase 1 notice.
  - **Save to Projects**: Stores rendered output directly into local storage.

### 4. Studio Film Roster & Archive (`/projects`)
- Search by project title or actor name.
- Status filters (`All`, `Completed`, `Processing`).
- Grid view and List view switcher.
- Project Detail Modal with interactive playback, technical specs, provenance checksums, and delete actions.
- Empty states with call-to-actions.

### 5. Studio Settings & API Bridge (`/settings`)
- **Directorial Profile**: Editable name, email, studio affiliation, and role.
- **AI & Pipeline Defaults**: Default resolution (`720p`, `1080p`, `4k`), color grading presets (*Authentic*, *Warm Vintage*, *Vibrant Masala*, *Moody Noir*), and watermark preferences.
- **FastAPI Integration Bridge**:
  - Typed API configuration for future FastAPI integration (`backendUrl`, `apiKey`, `useLiveBackend`).
  - "Test Endpoint Ping" action with latency measurement.
- **Reset Demo Data**: One-click restoration of factory demo projects and default stats.

---

## 🛠️ Architecture & Tech Stack
- **Framework**: React 19, TypeScript
- **Bundler**: Vite 6
- **Styling**: Tailwind CSS v4 with custom cinematic utility layers
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Routing**: React Router DOM v7
- **API Architecture**: Typed API abstraction layer (`src/services/api.ts`) ready for Phase 2 FastAPI endpoints.

---

## 💻 Running the Application

### Prerequisites
- Node.js (v18+)
- npm

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Run Development Server
```bash
cd frontend
npm run dev
```
Open your browser at `http://localhost:5173`.

### 3. Production Build
```bash
cd frontend
npm run build
```
Verify the production build locally:
```bash
npm run preview
```

