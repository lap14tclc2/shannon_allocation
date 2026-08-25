#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import yaml

VALID_STATUS = {"draft", "inferred", "verified", "conflicted", "stale", "deprecated"}
VALID_NOTE_TYPES = {
    "principle", "decision", "contract", "rule", "reference", "runbook",
    "observation", "plan", "checklist", "question",
}
VALID_RELATIONSHIPS = {
    "requires", "supports", "contradicts", "supersedes", "extends",
    "derived-from", "applies-to", "example-of",
}
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RELATION_RE = re.compile(r"^- ([a-z-]+): \[([^\]]+)\]\(([^)]+)\)$")


def parse_frontmatter(text: str) -> dict[str, object]:
    normalized = text.replace("\r\n", "\n").lstrip("\ufeff")
    if not normalized.startswith("---\n"):
        return {}
    end = normalized.find("\n---\n", 4)
    if end < 0:
        return {}
    loaded = yaml.safe_load(normalized[4:end])
    return loaded if isinstance(loaded, dict) else {}


def extract_links(path: Path, text: str) -> list[tuple[str, Path]]:
    links: list[tuple[str, Path]] = []
    for target in LINK_RE.findall(text.replace("\r\n", "\n").lstrip("\ufeff")):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        clean_target = target.split("#", 1)[0]
        links.append((target, (path.parent / clean_target).resolve()))
    return links


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$\n([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def normalise_claim(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def main() -> int:
    skill_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    references_dir = skill_dir / "references"
    maps_dir = references_dir / "maps"
    notes_dir = references_dir / "notes"
    sources_dir = references_dir / "sources"

    errors: list[str] = []
    all_md = sorted(references_dir.rglob("*.md"))
    note_files = sorted(notes_dir.glob("*.md"))
    source_files = sorted(sources_dir.glob("*.md"))
    map_files = sorted(maps_dir.glob("*.md"))

    if not map_files:
        errors.append("No map files found.")
    if not note_files:
        errors.append("No permanent notes found.")
    if not source_files:
        errors.append("No source notes found.")

    ids: Counter[str] = Counter()
    filenames: Counter[str] = Counter(path.name for path in all_md)
    link_graph: dict[Path, list[Path]] = defaultdict(list)
    id_by_path: dict[Path, str] = {}

    for path in note_files + source_files:
        text = path.read_text(encoding="utf-8")
        try:
            fm = parse_frontmatter(text)
        except yaml.YAMLError as exc:
            errors.append(f"{path.name}: invalid YAML frontmatter: {exc}.")
            continue

        is_note = path.parent == notes_dir
        file_type = "permanent note" if is_note else "source note"
        required = ["id", "title", "type", "status", "created", "updated", "sources"] if is_note else [
            "id", "title", "type", "status", "accessed",
        ]
        for field in required:
            if field not in fm:
                errors.append(f"{path.name}: missing required field '{field}' for {file_type}.")

        status = fm.get("status")
        if status and status not in VALID_STATUS:
            errors.append(f"{path.name}: invalid status '{status}'.")
        note_id = fm.get("id")
        if isinstance(note_id, str):
            ids[note_id] += 1
            id_by_path[path.resolve()] = note_id

        if is_note:
            if fm.get("type") not in VALID_NOTE_TYPES:
                errors.append(f"{path.name}: invalid permanent note type '{fm.get('type')}'.")
            claim = section(text, "Claim")
            if not claim:
                errors.append(f"{path.name}: missing primary claim content.")

            sources = fm.get("sources")
            if not isinstance(sources, list) or not sources:
                errors.append(f"{path.name}: permanent note must have a non-empty sources list.")
            else:
                for source_target in sources:
                    if not isinstance(source_target, str):
                        errors.append(f"{path.name}: source target must be a string.")
                        continue
                    resolved = (path.parent / source_target).resolve()
                    link_graph[path.resolve()].append(resolved)
                    if not resolved.exists():
                        errors.append(f"{path.name}: missing source reference '{source_target}'.")
                    elif resolved.parent != sources_dir.resolve():
                        errors.append(f"{path.name}: source reference is outside references/sources/.")

            relationship_block = section(text, "Relationships")
            if not relationship_block:
                errors.append(f"{path.name}: missing Relationships section.")
            for line in [item.strip() for item in relationship_block.splitlines() if item.strip()]:
                match = RELATION_RE.match(line)
                if not match:
                    errors.append(f"{path.name}: malformed relationship line '{line}'.")
                    continue
                label, linked_id, target = match.groups()
                if label not in VALID_RELATIONSHIPS:
                    errors.append(f"{path.name}: invalid relationship label '{label}'.")
                resolved = (path.parent / target).resolve()
                if not resolved.exists():
                    errors.append(f"{path.name}: missing relationship target '{target}'.")
                elif linked_id.startswith("QFD-") and id_by_path.get(resolved) not in (None, linked_id):
                    errors.append(f"{path.name}: relationship label '{linked_id}' does not match target note ID.")

        for target, resolved in extract_links(path, text):
            link_graph[path.resolve()].append(resolved)
            if not resolved.exists():
                errors.append(f"{path.name}: broken relative link '{target}'.")

    # Re-check relationship labels after every note ID has been indexed.
    for path in note_files:
        for line in [item.strip() for item in section(path.read_text(encoding="utf-8"), "Relationships").splitlines() if item.strip()]:
            match = RELATION_RE.match(line)
            if not match:
                continue
            _, linked_id, target = match.groups()
            resolved = (path.parent / target).resolve()
            if resolved.exists() and linked_id.startswith("QFD-") and id_by_path.get(resolved) != linked_id:
                errors.append(f"{path.name}: relationship ID '{linked_id}' does not match '{target}'.")

    for path in map_files:
        text = path.read_text(encoding="utf-8")
        note_links = 0
        for target, resolved in extract_links(path, text):
            link_graph[path.resolve()].append(resolved)
            if not resolved.exists():
                errors.append(f"{path.name}: broken relative link target '{target}'.")
                continue
            if notes_dir.resolve() in resolved.parents:
                note_links += 1
        if path.name != "index.md" and note_links == 0:
            errors.append(f"{path.name}: map does not point to any permanent notes.")

    for note_id, count in ids.items():
        if count > 1:
            errors.append(f"Duplicate note ID '{note_id}' appears {count} times.")
    for filename, count in filenames.items():
        if count > 1:
            errors.append(f"Duplicate filename '{filename}' appears {count} times under references/.")

    claims_to_files: dict[str, list[str]] = defaultdict(list)
    for path in note_files:
        claim = normalise_claim(section(path.read_text(encoding="utf-8"), "Claim"))
        if claim:
            claims_to_files[claim].append(path.name)
    for files in claims_to_files.values():
        if len(files) > 1:
            errors.append(f"Potential duplicate knowledge across notes: {', '.join(files)}.")

    root = (maps_dir / "index.md").resolve()
    if root.exists():
        reachable: set[Path] = set()
        queue: deque[Path] = deque([root])
        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            for next_path in link_graph.get(current, []):
                if next_path not in reachable and references_dir.resolve() in next_path.parents:
                    queue.append(next_path)
        for path in all_md:
            if path.resolve() not in reachable:
                errors.append(f"{path.relative_to(skill_dir)} is not reachable from references/maps/index.md.")
    else:
        errors.append("references/maps/index.md is missing.")

    if errors:
        print("VALIDATION FAILED")
        for item in sorted(set(errors)):
            print(f"- {item}")
        return 1

    print("VALIDATION PASSED")
    print(f"Maps: {len(map_files)}")
    print(f"Permanent notes: {len(note_files)}")
    print(f"Source notes: {len(source_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
