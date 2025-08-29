import requests
import json
import re

query_url = "https://hackerone.com/programs/search?query=type:hackerone&sort=published_at:descending&page={page}"

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

def hackerone_android_list():
    targets = {"android_apps": [], "android_with_bounty": []}
    csv_android = [["handle", "android_app", "eligible_for_bounty"]]

    page = 1
    with requests.Session() as session:
        while True:
            r = session.get(query_url.format(page=page))
            page += 1
            if r.status_code != 200:
                break
            resp = json.loads(r.text)

            for program in resp["results"]:
                r = session.get(
                    f"https://hackerone.com{program['url']}",
                    headers={"Accept": "application/json"},
                )
                if r.status_code != 200:
                    continue
                resp = json.loads(r.text)

                # new scope
                query = json.dumps({
                    "query": policy_scope_query,
                    "variables": {"handle": resp["handle"]},
                })
                r = session.post(
                    "https://hackerone.com/graphql",
                    data=query,
                    headers={"content-type": "application/json"},
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
                            targets["android_apps"].append(app)
                            bounty = e["eligible_for_bounty"] or False
                            if bounty:
                                targets["android_with_bounty"].append(app)
                            csv_android.append([resp["handle"], app, str(bounty)])

                # old scope
                query = json.dumps({
                    "query": scope_query,
                    "variables": {"handle": resp["handle"]},
                })
                r = session.post(
                    "https://hackerone.com/graphql",
                    data=query,
                    headers={"content-type": "application/json"},
                )
                scope_resp = json.loads(r.text)

                for e in scope_resp["data"]["team"]["in_scope_assets"]["edges"]:
                    node = e["node"]
                    if (
                        node["asset_type"] in ["GOOGLE_PLAY", "ANDROID_APP"]
                        or "play.google.com/store/apps" in node["asset_identifier"].lower()
                    ):
                        app = node["asset_identifier"]
                        if app not in targets["android_apps"]:
                            targets["android_apps"].append(app)
                            bounty = node["eligible_for_bounty"] or False
                            if bounty:
                                targets["android_with_bounty"].append(app)
                            csv_android.append([resp["handle"], app, str(bounty)])

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
