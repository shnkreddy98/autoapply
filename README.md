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

## Testing

Tests run without the Docker stack — DB and browser are fully mocked.

### Setup (once)
```
uv sync --group dev
```

### Run
```
uv run pytest tests/test_db_fetched.py tests/test_api_fetched.py -v
```

- `test_db_fetched.py` — unit tests for `insert_fetched_urls` / `list_fetched_urls` (mocked cursor)
- `test_api_fetched.py` — functional tests for `/fetched-urls`, `/tailortojobs`, `/applytojobs` (TestClient, mocked DB + browser)


