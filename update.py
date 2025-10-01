#!/usr/bin/env python3
import sys
import re
import xml.etree.ElementTree as ET
from urllib.request import urlopen
from datetime import date
from pathlib import Path


def parse_version(version_str):
    """Parse version string into major, minor, patch components."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}. Expected MAJOR.MINOR.PATCH (e.g., 5.2.6)")

    major, minor, patch = match.groups()
    return major, minor, patch


def get_metainfo_path(major, minor):
    """Construct path to metainfo.xml file."""
    majorminor = f"{major}{minor}"
    filename = f"com.netxms.NetXMSClient{majorminor}.metainfo.xml"
    path = Path(f"{major}.{minor}") / filename

    if not path.exists():
        raise FileNotFoundError(f"Metainfo file not found: {path}")

    return path


def fetch_changelog():
    """Fetch changelog from GitHub."""
    url = "https://raw.githubusercontent.com/netxms/changelog/master/ChangeLog.md"
    try:
        with urlopen(url) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Failed to fetch changelog: {e}")


def extract_release_notes(changelog_text, version):
    """Extract release notes for a specific version from the changelog."""
    version_pattern = rf'^#\s+{re.escape(version)}\s*$'

    lines = changelog_text.split('\n')
    start_idx = None

    for i, line in enumerate(lines):
        if re.match(version_pattern, line):
            start_idx = i + 1
            break

    if start_idx is None:
        raise ValueError(f"Version {version} not found in changelog")

    notes = []
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()

        if re.match(r'^#\s+\d+\.\d+', line):
            break

        if not line or re.match(r'^#{2,}', line):
            continue

        if line.startswith('*') or line.startswith('-'):
            note = line[1:].strip()
            if note:
                notes.append(note)

    if not notes:
        raise ValueError(f"No release notes found for version {version}")

    return notes


def create_release_element(version, notes):
    """Create a new release XML element."""
    anchor = version.replace('.', '')

    today = date.today().isoformat()

    release = ET.Element('release', version=version, date=today)

    url = ET.SubElement(release, 'url')
    url.text = f"https://github.com/netxms/changelog/blob/master/ChangeLog.md#{anchor}"

    description = ET.SubElement(release, 'description')
    ul = ET.SubElement(description, 'ul')

    for note in notes:
        li = ET.SubElement(ul, 'li')
        li.text = note

    return release


def indent_xml(elem, level=0, indent_str="   "):
    """Add proper indentation to XML elements."""
    i = "\n" + level * indent_str
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + indent_str
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent_xml(child, level + 1, indent_str)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def update_metainfo(metainfo_path, version, notes):
    """Update the metainfo.xml file with new release information."""
    tree = ET.parse(metainfo_path)
    root = tree.getroot()

    releases = root.find('releases')
    if releases is None:
        raise ValueError("No <releases> element found in metainfo.xml")

    new_release = create_release_element(version, notes)

    releases.insert(0, new_release)

    indent_xml(root)

    tree.write(metainfo_path, encoding='UTF-8', xml_declaration=True)

    print(f"✓ Updated {metainfo_path}")
    print(f"✓ Added release {version} with {len(notes)} release notes")


def main():
    if len(sys.argv) != 2:
        print("Usage: ./update.py <version>")
        sys.exit(1)

    version = sys.argv[1]

    try:
        major, minor, patch = parse_version(version)
        print(f"Processing version {version} (Major: {major}, Minor: {minor}, Patch: {patch})")

        metainfo_path = get_metainfo_path(major, minor)
        print(f"Target file: {metainfo_path}")

        print("Fetching changelog from GitHub...")
        changelog = fetch_changelog()

        print(f"Extracting release notes for version {version}...")
        notes = extract_release_notes(changelog, version)
        print(f"Found {len(notes)} release notes")

        update_metainfo(metainfo_path, version, notes)

        print("✓ Update completed successfully!")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
