import os
import requests
import sys
import re
from urllib.parse import quote

def parse_version(tag, x, y):
    match = re.match(rf'^{x}\.{y}\.(\d+)$', tag)
    if match:
        n = int(match.group(1))
        return n
    else:
        return None

def parse_rc_version(tag, x, y):
    match = re.match(rf'^{x}\.{y}\.0-rc\.(\d+)$', tag)
    if match:
        rc_n = int(match.group(1))
        return rc_n
    else:
        return None

def main():
    token = os.environ.get('GITHUB_TOKEN')
    owner = os.environ.get("GHCR_ORG")
    package_name = os.environ.get("GHCR_IMAGE_NAME")
    github_ref_name = os.environ.get('BASE_REF_NAME')  # e.g., 'release-1.2'

    if not token:
        print("GITHUB_TOKEN environment variable is not set.")
        sys.exit(1)
    if not owner:
        print("GHCR_ORG environment variable is not set.")
        sys.exit(1)
    if not package_name:
        print("GHCR_IMAGE_NAME environment variable is not set.")
        sys.exit(1)
    if not github_ref_name:
        print("BASE_REF_NAME environment variable is not set.")
        sys.exit(1)

    # Extract x and y from branch name 'release-x.y'
    match = re.match(r'release-(\d+)\.(\d+)', github_ref_name)
    if not match:
        print(f"Branch name {github_ref_name} does not match pattern 'release-x.y'")
        sys.exit(1)

    x = int(match.group(1))
    y = int(match.group(2))

    # URL-encode the package name
    package_name_encoded = quote(package_name, safe='')
    api_url = f'https://api.github.com/orgs/{owner}/packages/container/{package_name_encoded}/versions?per_page=100'

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github+json'
    }

    versions_data = []
    page = 1
    while True:
        response = requests.get(f"{api_url}&page={page}", headers=headers)

        if response.status_code != 200:
            print(f"Failed to get package versions. Status code: {response.status_code}")
            print(response.text)
            sys.exit(1)

        data = response.json()
        if not data:
            break
        versions_data.extend(data)
        page += 1

    tags = []
    for version in versions_data:
        # Each version may have multiple tags
        tags.extend(version.get('metadata', {}).get('container', {}).get('tags', []))

    # Find existing tags matching x.y.*
    existing_ns = []
    for tag in tags:
        n = parse_version(tag, x, y)
        if n is not None:
            existing_ns.append(n)

    if existing_ns:
        max_n = max(existing_ns)
        next_n = max_n + 1
        next_tag = f"{x}.{y}.{next_n}"
    else:
        # No existing tags matching x.y.*
        next_tag = f"{x}.{y}.0"

    # Determine whether to retag or build
    if next_tag == f"{x}.{y}.0":
        # Need to retag x.y.0-rc.n as x.y.0 where n is the latest RC
        # Find latest RC tag x.y.0-rc.n
        rc_ns = []
        for tag in tags:
            rc_n = parse_rc_version(tag, x, y)
            if rc_n is not None:
                rc_ns.append(rc_n)
        if not rc_ns:
            # TODO this should instead opt to blindly return next release
            # Then, it should tell gh actions to build the container instead of retagging it.
            print(f"No RC tags found for {x}.{y}.0-rc.n")
            sys.exit(1)
        max_rc_n = max(rc_ns)
        source_tag = f"{x}.{y}.0-rc.{max_rc_n}"
        # Output env variables
        build_image = 'false'
        retag_image = 'true'
    else:
        # Need to build image off release-x.y
        build_image = 'true'
        retag_image = 'false'
        source_tag = ''

    # Set environment variables
    with open(os.environ['GITHUB_ENV'], 'a') as fh:
        print(f"NEXT_TAG={next_tag}", file=fh)
        print(f"BUILD_IMAGE={build_image}", file=fh)
        print(f"RETAG_IMAGE={retag_image}", file=fh)
        if source_tag:
            print(f"SOURCE_TAG={source_tag}", file=fh)

    print(f"Next tag is: {next_tag}")
    print(f"Build image: {build_image}")
    print(f"Retag image: {retag_image}")
    if source_tag:
        print(f"Source tag: {source_tag}")

if __name__ == "__main__":
    main()
