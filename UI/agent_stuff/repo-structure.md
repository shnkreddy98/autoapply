# AutoApply UI - Repository Structure

This repository contains the UI layer for the **AutoApply** application, an automated job application system. It is built with **React**, **TypeScript**, and **Material-UI (MUI)**.

## Core Purpose
The application enables users to:
1.  **Sign In/Up**: Simple contact info collection (not a full OAuth/password-based auth yet).
2.  **Onboarding**: Multi-step form to collect personal details, work eligibility, and EEO information for automated applications.
3.  **Application Management**: Track the progress of automated applications via a history list (`JobList.tsx`).
4.  **Find & Apply**: Trigger new automated application runs (`Apply.tsx`) using specified job URLs and uploaded resumes.

## Directory Structure
- `src/`: Root directory for the React application.
  - `pages/`: Contains the main page components:
    - `Login.tsx`: Initial entry point for user contact info.
    - `Onboarding.tsx`: 6-step form for user profile data.
    - `Apply.tsx`: Trigger the backend to apply to specific job URLs.
    - `JobList.tsx`: Displays application history (currently titled "Application History").
    - `JobDetails.tsx`: Details for a specific application.
    - `JobMonitor.tsx`: Real-time monitoring of application processes.
    - `Profile.tsx`: User profile management.
    - `JobChat.tsx`: Interface for AI-driven job-related chats.
    - `Tailor.tsx`: Resume tailoring interface.
  - `utils/`:
    - `api.ts`: Centralized backend configuration and URL helper.
    - `dateUtils.ts`: Utility for date formatting.
  - `types.ts`: TypeScript interfaces for shared data models (Job, Profile, etc.).

## Backend Integration
- API endpoints are prefixed with a base URL defined in `src/utils/api.ts`.
- Key endpoints identified:
  - `POST /save-user`: Stores basic user info from the Login page.
  - `POST /user-form`: Submits the 6-step onboarding form.
  - `GET /jobs`: Retrieves application history.
  - `POST /applytojobs`: Triggers the automated application engine.
  - `GET /list-resumes`: Fetches available resumes for the user.
