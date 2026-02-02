# Movies99 Frontend

This is the frontend application for the Movies99 ML-powered movie recommendation system.

## Table of Contents

- [Technologies Used](#technologies-used)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running Locally](#running-locally)
- [Project Structure](#project-structure)
- [Scripts](#scripts)
- [Testing](#testing)
- [Linting and Formatting](#linting-and-formatting)
- [Deployment (CI/CD)](#deployment-cicd)
- [Performance Optimizations](#performance-optimizations)
- [Design System](#design-system)
- [SEO and Accessibility](#seo-and-accessibility)

## Technologies Used

-   **Framework:** Next.js 16 (App Router)
-   **Language:** TypeScript
-   **Styling:** Tailwind CSS
-   **State Management:** Zustand, React Query
-   **UI Components:** Headless UI, Radix UI (via custom components in `components/ui`)
-   **Animations:** Framer Motion
-   **Icons:** Lucide React, Heroicons
-   **Bundler:** Webpack (for production build)
-   **Package Manager:** npm (or pnpm)
-   **Testing:** Jest, React Testing Library
-   **Linting:** ESLint
-   **Formatting:** Prettier

## Getting Started

### Prerequisites

-   Node.js (v18 or higher)
-   npm (or pnpm)
-   Access to the Movies99 backend API (running locally or deployed)

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-repo/movies99.git
    cd movies99/frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    # or pnpm install
    ```

### Running Locally

To run the frontend locally, you need to have the backend API running.

1.  **Start the Backend:**
    (Assuming your backend is in the `movies99/backend` directory)
    ```bash
    cd ../backend
    pip install -r requirements.txt # if not already installed
    uvicorn main:app --reload
    ```
    The backend should be running at `http://localhost:8000`.

2.  **Configure Frontend Environment:**
    Create a `.env.local` file in the `frontend` directory with the following content:
    ```
    NEXT_PUBLIC_API_BASE=http://localhost:8000
    ```

3.  **Start the Frontend Development Server:**
    ```bash
    cd frontend
    npm run dev
    ```
    The frontend application will be accessible at `http://localhost:3000`.

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router (pages, layouts, etc.)
│   ├── components/
│   │   ├── ui/              # Reusable UI primitives (Button, Modal, Card, etc.)
│   │   └── (feature)/       # Feature-specific components (e.g., movie, recommendation)
│   ├── features/            # Feature-sliced logic (hooks, state, types)
│   ├── lib/                 # Utility functions, API clients, shared types, Zustand stores
│   └── styles/              # Global styles
├── public/                  # Static assets
├── .env.local               # Local environment variables
├── .eslintrc.mjs            # ESLint configuration
├── .prettierrc              # Prettier configuration
├── next.config.ts           # Next.js configuration
├── package.json             # Project dependencies and scripts
├── tailwind.config.ts       # Tailwind CSS configuration
├── tsconfig.json            # TypeScript configuration
└── ...
```

## Scripts

-   `npm run dev`: Starts the development server.
-   `npm run build`: Creates an optimized production build.
-   `npm run start`: Starts the Next.js production server.
-   `npm run lint`: Runs ESLint for code quality checks.
-   `npm run test`: Runs Jest tests.
-   `npm run analyze`: Builds the application and generates a bundle analysis report (requires backend running during build for full data fetching).

## Testing

This project uses [Jest](https://jestjs.io/) and [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/) for unit and integration testing.

-   To run all tests: `npm test`
-   Test files are co-located with the components/modules they test (e.g., `Button.test.tsx` next to `Button.tsx`).

## Linting and Formatting

-   **ESLint:** Configured with `eslint-config-next` and `eslint-plugin-prettier` for code quality.
    -   Run `npm run lint` to check for issues.
-   **Prettier:** Integrated with ESLint for automatic code formatting.
    -   Formatting rules are defined in `.prettierrc`.

## Deployment (CI/CD)

A typical CI/CD pipeline for this application would involve the following steps:

1.  **Checkout Code:** Get the latest changes from your version control system.
2.  **Install Dependencies:** `npm install` (or `pnpm install`).
3.  **Run Linting:** `npm run lint`.
4.  **Run Tests:** `npm run test`.
5.  **Build Application:** `npm run build`.
    -   Ensure the backend API is accessible if prerendering/SSR requires data at build time. For cloud deployments, this might involve configuring build environments to point to a staging API.
6.  **Deploy:** Push the built artifacts to your hosting provider (e.g., Vercel, AWS S3/CloudFront, Netlify).

## Performance Optimizations

Several optimizations have been implemented:

-   **Image Optimization:** Uses `next/image` component with `priority` and `sizes` props.
-   **Lazy Loading:** Critical components (e.g., `RecommendationModal`) are dynamically imported.
-   **Code Splitting:** Next.js automatically handles page-level code splitting.
-   **Font Optimization:** Utilizes `next/font` for efficient loading of custom fonts (`Inter`, `Playfair Display`).
-   **API Call Optimization:** Employs `@tanstack/react-query` for data fetching, caching, and revalidation.
-   **Skeleton Loaders:** Implemented for a smoother user experience during data loading.

## Design System

The application follows a component-driven design system:

-   **`components/ui`:** A dedicated directory for highly reusable, generic UI primitives (e.g., `Button`, `Modal`, `Card`, `Input`).
-   **Centralized Styling:** Tailwind CSS is configured with a refined, Apple-like color palette, typography scale, and consistent spacing. All styles are driven from `tailwind.config.ts` and `globals.css` (for CSS variables).

## SEO and Accessibility

-   **SEO Metadata:** Enhanced metadata in `layout.tsx` including title, description, keywords, Open Graph, and Twitter card information.
-   **Accessibility Checks:** ESLint is configured with accessibility plugins to catch common issues during development. Semantic HTML and proper ARIA attributes are used where appropriate.