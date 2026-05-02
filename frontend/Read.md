## Architecture decisions
for the frontend of this project Pages Router is selected as architecture .

** Pages Router (not App Router)— uses pages/ directory which is simpler better, documented, and works cleanly with _app.tsx for global providers.App Router adds complexity that isn't needed for this project scope **

## Folder Structure of the frontend
frontend/
├── package.json
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── postcss.config.js
│
├── src/
│   ├── styles/globals.css
│   │
│   ├── services/
│   │   ├── api.ts
│   │   ├── authService.ts
│   │   ├── imageService.ts
│   │   ├── compareService.ts
│   │   ├── reportService.ts
│   │   └── feedbackService.ts
│   │
│   ├── context/AuthContext.tsx
│   ├── hooks/useAuth.ts
│   │
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Spinner.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Modal.tsx
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Navbar.tsx
│   │   │   └── AppLayout.tsx
│   │   └── forensic/
│   │       ├── EvidenceTypeSelector.tsx
│   │       ├── ImageUploader.tsx
│   │       ├── SimilarityResultCard.tsx
│   │       ├── ReportViewer.tsx
│   │       └── FeedbackForm.tsx
│   │
│   └── pages/
│       ├── _app.tsx
│       ├── index.tsx
│       ├── login.tsx
│       ├── dashboard.tsx
│       ├── upload.tsx
│       ├── compare.tsx
│       ├── reports.tsx
│       ├── logs.tsx
│       ├── feedback.tsx
│       ├── admin.tsx
│       └── change-password.tsx
|       └──cases.tsx


## Run with

cd frontend
npm install
npm run dev
