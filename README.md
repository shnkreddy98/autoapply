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


### TODO
- complete apply endpoint
- add observability
    - usage metrics/cost
    - agent thoughts
    - browser streaming (ask inputs)
    - save state and notify user when agent is stuck
