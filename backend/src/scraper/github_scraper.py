import os
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv("../../.env")


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DB_URL        = os.getenv("DATABASE_URL")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

MAX_MEMBERS_PER_ORG  = 10
MAX_USERS_FALLBACK   = 8
MAX_REPOS_PER_USER   = 3 
MIN_STARS            = 5  # Having 5 stars can mean project is impactful allowing more accurate data


## utilizing company repos to scan verified members so we know the projects of those users are accurate

COMPANY_GITHUB_ORGS = {
    "Google":         ["google", "googleapis", "googlecloudplatform", "google-deepmind"],
    "Meta":           ["facebook", "facebookresearch", "facebookincubator"],
    "Apple":          ["apple"],
    "Amazon":         ["aws", "amzn", "awslabs"],
    "Netflix":        ["netflix"],
    "Microsoft":      ["microsoft", "azure", "dotnet", "aspnet"],
    "OpenAI":         ["openai"],
    "Anthropic":      ["anthropic"],
    "NVIDIA":         ["nvidia"],
    "DeepMind":       ["google-deepmind"],
    "Stripe":         ["stripe"],
    "Airbnb":         ["airbnb"],
    "Uber":           ["uber", "uber-go", "uber-web"],
    "Lyft":           ["lyft"],
    "Twitter":        ["twitter", "twitterdev"],
    "LinkedIn":       ["linkedin"],
    "Salesforce":     ["salesforce", "forcedotcom"],
    "Palantir":       ["palantir"],
    "Snowflake":      ["snowflakedb"],
    "Databricks":     ["databricks"],
    "Figma":          ["figma"],
    "Notion":         ["makenotion"],
    "Canva":          ["canva"],
    "Vercel":         ["vercel"],
    "Netlify":        ["netlify"],
    "Cloudflare":     ["cloudflare"],
    "Twilio":         ["twilio"],
    "Coinbase":       ["coinbase"],
    "Shopify":        ["shopify"],
    "Atlassian":      ["atlassian"],
    "Dropbox":        ["dropbox"],
    "GitHub":         ["github"],
    "GitLab":         ["gitlab-org"],
    "MongoDB":        ["mongodb"],
    "Elastic":        ["elastic"],
    "Grafana":        ["grafana"],
    "DataDog":        ["datadog"],
    "HashiCorp":      ["hashicorp"],
    "Confluent":      ["confluentinc"],
    "Hugging Face":   ["huggingface"],
    "Weights & Biases": ["wandb"],
    "Pinecone":       ["pinecone-io"],
    "LangChain":      ["langchain-ai"],
    "Scale AI":       ["scaleapi"],
    "DigitalOcean":   ["digitalocean"],
    "Supabase":       ["supabase"],
    "PlanetScale":    ["planetscale"],
    "Replit":         ["replit"],
    "Postman":        ["postmanlabs"],
    "Sentry":         ["getsentry"],
    "Asana":          ["asana"],
    "HubSpot":        ["hubspot"],
    "Zendesk":        ["zendesk"],
    "Intercom":       ["intercom"],
    "Mixpanel":       ["mixpanel"],
    "Amplitude":      ["amplitude"],
    "CircleCI":       ["circleci"],
    "Buildkite":      ["buildkite"],
    "LaunchDarkly":   ["launchdarkly"],
    "Okta":           ["okta"],
    "Auth0":          ["auth0"],
    "CrowdStrike":    ["crowdstrike"],
    "Palo Alto Networks": ["PaloAltoNetworks"],
    "Splunk":         ["splunk"],
    "New Relic":      ["newrelic"],
    "Freshworks":     ["freshworks"],
    "Zoho":           ["zoho"],
    "Razorpay":       ["razorpay"],
    "Zerodha":        ["zerodha"],
    "Flipkart":       ["flipkart"],
    "Adobe":          ["adobe"],
    "Intel":          ["intel"],
    "Samsung":        ["Samsung"],
    "Spotify":        ["spotify"],
    "Discord":        ["discord"],
    "Slack":          ["slackhq"],
    "Zoom":           ["zoom"],
    "Pinterest":      ["pinterest"],
    "DoorDash":       ["doordash"],
    "Grab":           ["grab"],
    "Duolingo":       ["duolingo"],
    "Coursera":       ["coursera"],
    "Temporal":       ["temporalio"],
    "Retool":         ["tryretool"],
    "Linear":         ["linear"],
    "Webflow":        ["webflow"],
    "Docusign":       ["docusign"],
    "SAP":            ["SAP"],
    "Oracle":         ["oracle"],
    "IBM":            ["IBM"],
}


def get_db():
    return psycopg2.connect(DB_URL)

def get_companies(cursor):
    cursor.execute("SELECT id, name FROM companies ORDER BY tier ASC")
    return cursor.fetchall()

def insert_resume(cursor, company_id, source_url, person_name):
    cursor.execute(
        """
        INSERT INTO resumes (company_id, source_url, person_name)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (company_id, source_url, person_name),
    )
    row = cursor.fetchone()
    return row[0] if row else None

def insert_project(cursor, resume_id, title, description, tech_stack, source_url):
    cursor.execute(
        """
        INSERT INTO projects (resume_id, title, description, tech_stack, source_url)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (resume_id, title, description, tech_stack, source_url),
    )


## To stay within rate limits add a delay between API calls
## Imp to make sure we don't get rate limited
def handle_rate_limit(resp):
    if resp.status_code == 403:
        print("    Rate limited — sleeping 60s")
        time.sleep(60)
        return True
    return False

def get_org_members(org_name, max_members=MAX_MEMBERS_PER_ORG):
    """Verified employees — strongest signal."""
    url    = f"https://api.github.com/orgs/{org_name}/public_members"
    params = {"per_page": max_members}
    resp   = requests.get(url, headers=HEADERS, params=params)
    if handle_rate_limit(resp):
        resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code == 404:
        print(f"    Org '{org_name}' not found")
        return []
    if resp.status_code != 200:
        print(f"    Failed {org_name}: {resp.status_code}")
        return []
    members = [m["login"] for m in resp.json()]
    print(f"    Org '{org_name}' → {len(members)} public members")
    return members

def search_users_by_company_field(company_name, max_users=MAX_USERS_FALLBACK):
    """Fallback: self-reported company field on GitHub profiles."""
    url    = "https://api.github.com/search/users"
    params = {"q": f'company:"{company_name}"', "per_page": max_users, "sort": "followers"}
    resp   = requests.get(url, headers=HEADERS, params=params)
    if handle_rate_limit(resp):
        resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code != 200:
        print(f"    Fallback search failed for {company_name}: {resp.status_code}")
        return []
    users = [u["login"] for u in resp.json().get("items", [])]
    print(f"    Fallback → {len(users)} users for '{company_name}'")
    return users

def get_user_repos(username):
    url    = f"https://api.github.com/users/{username}/repos"
    params = {"per_page": 50, "sort": "stars", "direction": "desc", "type": "owner"}
    resp   = requests.get(url, headers=HEADERS, params=params)
    if handle_rate_limit(resp):
        resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code != 200:
        return []
    repos = [
        r for r in resp.json()
        if not r.get("fork")
        and r.get("stargazers_count", 0) >= MIN_STARS
        and r.get("description")
        and not r.get("archived")
    ]
    return repos[:MAX_REPOS_PER_USER]

def extract_tech_stack(repo):
    stack = []
    if repo.get("language"):
        stack.append(repo["language"])
    stack += repo.get("topics", [])
    seen, result = set(), []
    for item in stack:
        if item.lower() not in seen:
            seen.add(item.lower())
            result.append(item)
    return result[:8]

def get_users_for_company(company_name):
    """
    Strategy:
    1. Known GitHub org → use public org members (verified)
    2. No org → fall back to company field search (self-reported)
    """
    orgs = COMPANY_GITHUB_ORGS.get(company_name)
    if orgs:
        print(f"  Org membership strategy ({len(orgs)} org(s))")
        users, seen = [], set()
        for org in orgs:
            for u in get_org_members(org):
                if u not in seen:
                    seen.add(u)
                    users.append(u)
            time.sleep(1)
        return users
    else:
        print(f"  No org mapped, we will be using company field fallback")
        time.sleep(6)
        return search_users_by_company_field(company_name)

def scrape():
    conn   = get_db()
    cursor = conn.cursor()
    companies = get_companies(cursor)
    print(f"Starting scrape for {len(companies)} companies...\n")

    for company_id, company_name in companies:
        print(f"\n[{company_name}]")
        users = get_users_for_company(company_name)

        if not users:
            print(f"  No users found — skipping")
            continue

        for username in users:
            profile_url = f"https://github.com/{username}"
            print(f"  → {username}")
            repos = get_user_repos(username)

            if not repos:
                print(f"    No qualifying repos")
                time.sleep(1)
                continue

            resume_id = insert_resume(cursor, company_id, profile_url, username)
            if not resume_id:
                print(f"    Already in DB")
                time.sleep(1)
                continue

            for repo in repos:
                tech_stack = extract_tech_stack(repo)
                insert_project(
                    cursor,
                    resume_id,
                    repo["name"],
                    repo.get("description", ""),
                    tech_stack,
                    repo["html_url"]
                )
                print(f"    + {repo['name']} [{', '.join(tech_stack[:3])}] Stars: {repo['stargazers_count']}")

            conn.commit()
            time.sleep(1.5)

        print(f"  Done with {company_name}")

    cursor.close()
    conn.close()
    print("\nScrape complete.")


if __name__ == "__main__":
    scrape()