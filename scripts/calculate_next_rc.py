import os
import requests
import sys
import re
from urllib.parse import quote

def parse_version(tag):
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?$', tag)
    if match:
        major, minor, patch, rc = match.groups()
        major = int(major)
        minor = int(minor)
        patch = int(patch)
        rc = int(rc) if rc is not None else None
        return (major, minor, patch, rc)
    else:
        return None

def version_key(version_tuple):
    major, minor, patch, rc = version_tuple
    rc = rc if rc is not None else float('inf')  # Release versions come after RC versions
    return (major, minor, patch, rc)

def main():
    token = os.environ.get('GITHUB_TOKEN')
    org = os.environ.get("GHCR_ORG")
    user = os.environ.get("GHCR_USER")
    package_name = os.environ.get("GHCR_IMAGE_NAME")

    if not token:
        print("GITHUB_TOKEN environment variable is not set.")
        sys.exit(1)
    if not org and not user:
        print("GHCR_ORG and GHCR_USER environment variable is not set.")
        sys.exit(1)
    if not package_name:
        print("GHCR_IMAGE_NAME environment variable is not set.")
        sys.exit(1)

    # URL-encode the package name
    package_name_encoded = quote(package_name, safe='')

    if org:
        user_or_org = "org"
        owner = org
        api_url = f'https://api.github.com/org/{org}/packages/container/{package_name_encoded}/versions'
    else:
        user_or_org = "user"
        owner = user
        api_url = f'https://api.github.com/user/packages/container/{package_name_encoded}/versions'

    print(f"Using the {user_or_org} API ({api_url})")

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github+json'
    }

    response = requests.get(api_url, headers=headers)

    tags = []
    if response.status_code == 200:
        versions_data = response.json()

        for version in versions_data:
            # Each version may have multiple tags
            tags.extend(version.get('metadata', {}).get('container', {}).get('tags', []))
    else:
        if response.status_code == 404:
            print(f"GitHub Package owned by {owner} called {package_name} doesn't exist yet.")
        else:
            print(f"Failed to get package versions. Status code: {response.status_code}")
            print(response.text)
            sys.exit(1)

    if not tags:
        # No tags found
        next_tag = '1.0.0-rc.0'
        print(f"No tags found - next tag is {next_tag}")
    else:
        # Parse tags
        versions = []
        for tag in tags:
            parsed = parse_version(tag)
            if parsed:
                versions.append(parsed)

        if not versions:
            # No valid versions found
            next_tag = '1.0.0-rc.0'
            print(f"No valid versions found - next tag is {next_tag}")
        else:
            # Sort versions
            versions.sort(key=version_key)

            # Get the most recent version
            latest_version = versions[-1]
            print(f"Current latest version is {latest_version}")

            major, minor, patch, rc = latest_version

            if rc is None:
                # Latest version is x.y.z
                # Next tag is x.[y+1].0-rc.0
                next_major = major
                next_minor = minor + 1
                next_patch = 0
                next_rc = 0
            else:
                # Latest version is x.y.z-rc.n
                # Next tag is x.y.z-rc.[n+1]
                next_major = major
                next_minor = minor
                next_patch = patch
                next_rc = rc + 1

            next_tag = f"{next_major}.{next_minor}.{next_patch}-rc.{next_rc}"

    print(f"Next tag is: {next_tag}")

    # Set environment variable for use in subsequent steps
    with open(os.environ['GITHUB_ENV'], 'a') as fh:
        print(f"NEXT_TAG={next_tag}", file=fh)

if __name__ == "__main__":
    main()
