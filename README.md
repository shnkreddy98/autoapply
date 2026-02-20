# AutoApply

Automated job application tool that tailors your resume to job descriptions using LLMs.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)

## Getting Started

### Add Gemini API key

```
cp .env.example dev.env
```
Add gemini api key to the dev.env

### Just Run
```
docker compose up -d
```

### How to use it

- Go to localhost:5173 once the docker contianer is ready
- Go to `Profile` to upload your first resume
- Go to `Home` page and select the resume of your choice and paste the job links 
- Go to data/applications/<todays-date>/<company-name>/<resumename> to access tailored resume


#### TODO
  Next Steps (Setup)

  Before running the application:

  1. Get Google OAuth Client ID:
    - Go to Google Cloud Console
    - Create OAuth 2.0 Client ID (Web Application)
    - Add authorized origins: http://localhost:5173 (dev)
    - Copy Client ID
  2. Generate JWT Secret:
  # Generate a random 32-character secret
  openssl rand -hex 16
  3. Update environment files:
  # Backend (autoapply/dev.env)
  GOOGLE_CLIENT_ID=<your-client-id>
  JWT_SECRET=<your-32-char-secret>

  # Frontend (UI/.env)
  VITE_GOOGLE_CLIENT_ID=<your-client-id>
  4. Run migrations:
  docker exec <postgres-container> psql -U admin -d jobs-db -f /init/schema.sql
  5. Install dependencies:
  # Backend
  pip install -e .

  # Frontend
  cd UI
  npm install

  The implementation is production-ready with proper error handling, security headers, and data isolation!