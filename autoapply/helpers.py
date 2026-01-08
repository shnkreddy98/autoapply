async def get_company_name(url: str) -> str:
    if url.startswith("https://jobs.ashbyhq.com") or url.startswith("https://ats.rippling.com") or url.startswith("https://jobs.lever.co"):
        company_name = url.split("/")[3]
    elif url.startswith("careers"):
        company_name = url.split("/")[2].split(".")[1]
    elif "myworkdayjobs" in url:
        company_name = url.split("/")[2].split(".")[0]
    else:
        company_name = url.split("/")[2]
    return company_name
