import requests
import json
import re
import time
import random

query_url = "https://hackerone.com/programs/search?query=type:hackerone&sort=published_at:descending&page={page}"

headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

policy_scope_query = """
query PolicySearchStructuredScopesQuery($handle: String!) {
  team(handle: $handle) {
    structured_scopes_search {
      nodes {
        ... on StructuredScopeDocument {
          identifier
          eligible_for_bounty
          eligible_for_submission
          display_name
        }
      }
    }
  }
}
"""

scope_query = """
query TeamAssets($handle: String!) {
  team(handle: $handle) {
    in_scope_assets: structured_scopes(
      archived: false
      eligible_for_submission: true
    ) {
      edges {
        node {
          asset_identifier
          asset_type
          eligible_for_bounty
        }
      }
    }
  }
}
"""

def safe_request(session, method, url, **kwargs):
    for attempt in range(3):
        try:
            r = session.request(method, url, timeout=10, **kwargs)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 ** attempt)  # exponential backoff
    return None

def hackerone_android_list():
    targets = {"android_apps": [], "android_with_bounty": []}
    csv_android = [["handle", "android_app", "eligible_for_bounty"]]

    page = 1
    with requests.Session() as session:
        while True:
            r = safe_request(session, "GET", query_url.format(page=page))
            if not r:
                break
            page += 1
            if r.status_code != 200:
                break
            resp = json.loads(r.text)

            for program in resp["results"]:
                custom_headers = headers.copy()
                custom_headers.update({"Accept": "application/json"})
                r = safe_request(
                    session, "GET",
                    f"https://hackerone.com{program['url']}",
                    headers=custom_headers
                )
                if r.status_code != 200:
                    continue
                resp = json.loads(r.text)

                # new scope
                query = json.dumps({
                    "query": policy_scope_query,
                    "variables": {"handle": program["handle"]},
                })
                custom_headers = headers.copy()
                custom_headers.update({"Content-Type": "application/json"})
                r = safe_request(
                    session, "POST",
                    "https://hackerone.com/graphql",
                    data=query,
                    headers=custom_headers
                )
                policy_scope_resp = json.loads(r.text)

                for e in policy_scope_resp["data"]["team"]["structured_scopes_search"]["nodes"]:
                    if (
                        e["eligible_for_submission"]
                        and (
                            "play.google.com/store/apps" in e["identifier"].lower()
                            or "android" in e["display_name"].lower()
                        )
                    ):
                        app = e["identifier"]
                        if app not in targets["android_apps"]:
                            if not app.startswith("https://play.google.com") and re.match(r"^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+(\.\*)?$", app):
                                app = f"https://play.google.com/store/apps/details?id={app}"
                            targets["android_apps"].append(app)
                            bounty = e["eligible_for_bounty"] or False
                            if bounty:
                                targets["android_with_bounty"].append(app)
                            csv_android.append([program["handle"], app, str(bounty)])

                # old scope
                query = json.dumps({
                    "query": scope_query,
                    "variables": {"handle": program["handle"]},
                })
                custom_headers = headers.copy()
                custom_headers.update({"Content-Type": "application/json"})
                r = safe_request(
                    session, "POST",
                    "https://hackerone.com/graphql",
                    data=query,
                    headers=custom_headers
                )
                scope_resp = json.loads(r.text)

                for e in scope_resp["data"]["team"]["in_scope_assets"]["edges"]:
                    node = e["node"]
                    if (
                        node["asset_type"] in ["GOOGLE_PLAY", "ANDROID_APP"]
                        or "play.google.com/store/apps" in node["asset_identifier"].lower()
                    ):
                        app = node["asset_identifier"]
                        if not app.startswith("https://play.google.com") and re.match(r"^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+(\.\*)?$", app):
                            app = f"https://play.google.com/store/apps/details?id={app}"
                        if app not in targets["android_apps"]:
                            targets["android_apps"].append(app)
                            bounty = node["eligible_for_bounty"] or False
                            if bounty:
                                targets["android_with_bounty"].append(app)
                            csv_android.append([program["handle"], app, str(bounty)])
            
                time.sleep(random.uniform(0.5, 0.5))
            time.sleep(random.uniform(1.5, 2.5))

    # dedupe
    targets["android_apps"] = list(set(targets["android_apps"]))
    targets["android_with_bounty"] = list(set(targets["android_with_bounty"]))

    return targets, csv_android

if __name__ == "__main__":
    targets, csv_android = hackerone_android_list()
    with open("android_apps.txt", "w") as f:
        f.write("\n".join(targets["android_apps"]))
    with open("android_apps_with_bounties.txt", "w") as f:
        f.write("\n".join(targets["android_with_bounty"]))
    with open("android_apps.csv", "w") as f:
        f.write("\n".join([",".join(e) for e in csv_android]))
