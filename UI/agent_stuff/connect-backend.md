# Backend Integration Tracking

This file tracks all locations in the UI where dummy data is currently used. When moving to live endpoints, these sections should be updated to use the corresponding backend APIs.

## Current Dummy Data Points

| Component | Purpose | Status | Integration Note |
| :--- | :--- | :--- | :--- |
| `JobList.tsx` | Find Jobs section (discovery). | **Using Mock Data** | Uses `MOCK_AVAILABLE_JOBS` from `src/utils/mockData.ts`. Need endpoint for job search/discovery. |
| `Applications.tsx`| Tracking applied jobs. | **Using Mock Data (Fallback)** | Falls back to `MOCK_APPLIED_JOBS` if `/jobs` fails. |
| `Apply.tsx` | Resume selection list. | **Partially Live** | Currently hardcoded IDs in fallback. Update to fetch from `/list-resumes`. |
| `Profile.tsx` | User profile management. | **Using Mock Data** | Can use `MOCK_USER_PROFILE` for demo. Needs `/get-profile` and `/save-profile`. |
| `Onboarding.tsx`| Multi-step onboarding. | **Partially Live** | Submits to `/user-form`. Could fetch existing data for pre-fill. |

## Integration Steps for Live Backend
- [ ] Configure `API_BASE_URL` in `src/utils/api.ts`.
- [ ] Implement actual `fetch` or `axios` calls to replace hardcoded state initializations.
- [ ] Ensure all API responses match the TypeScript interfaces in `src/types.ts`.
