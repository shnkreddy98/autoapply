import re

async def get_company_name(url: str) -> str:
    if url.startswith("https://jobs.ashbyhq.com") \
        or url.startswith("https://ats.rippling.com") \
            or url.startswith("https://jobs.lever.co") \
            or url.startswith("https://jobs-borads.greenhouse.io"):
        company_name = url.split("/")[3]
    elif url.startswith("https://careers"):
        company_name = url.split("/")[2].split(".")[1]
    elif "myworkdayjobs" in url:
        company_name = url.split("/")[2].split(".")[0]
    elif url.split("/")[3] == "careers":
        company_name = url.split("/")[2].split(".")[1]
    else:
        # remove https://
        # replace all special characters with space
        # split at space and remove generic words and keep non generic words only
        clean_url = "".join(url.split("/")[2:])
        clean_url = re.sub(r"[^a-zA-Z0-9]+", " ", clean_url).strip()
        clean_company_name = []
        for word in clean_url.split(" "):
            if word not in ["board", "us2", "com", "careers", "en", "sites", "Data", "Engineer"]:
                clean_company_name.append(word)

        company_name = "_".join(clean_company_name)
    return company_name
