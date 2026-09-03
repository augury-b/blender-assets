import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

POSSIBLE_BLENDER_PATHS = [
    r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender\blender.exe",
]

CATALOG_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

CATALOG_DEFINITIONS = {
    "Augury Assets": "Augury Assets",
    # 1. Models
    "Augury Assets/Models": "Models",
    # 2. Geometry Nodes
    "Augury Assets/Geometry Nodes": "Geometry Nodes",
    "Augury Assets/Geometry Nodes/Selectors": "Selectors",
    "Augury Assets/Geometry Nodes/Generators": "Generators",
    "Augury Assets/Geometry Nodes/Deformers": "Deformers",
    # 3. Shaders
    "Augury Assets/Shaders": "Shaders",
    "Augury Assets/Shaders/Materials": "Materials",
    "Augury Assets/Shaders/Materials/Stylized": "Stylized",
    "Augury Assets/Shaders/Materials/Photoreal": "Photoreal",
    "Augury Assets/Shaders/Node Groups": "Node Groups",
    # 4. Compositor
    "Augury Assets/Compositor": "Compositor",
    "Augury Assets/Compositor/Node Groups": "Node Groups",
    # Fallback Catchment
    "Augury Assets/Other": "Other",
}


def get_blender_binary():
    if shutil.which("blender"):
        return "blender"
    for path in POSSIBLE_BLENDER_PATHS:
        if os.path.isfile(path):
            return path
    return None


def run_cmd(cmd, desc):
    print(f"\n[+] {desc}...")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"[-] Command failed during: {desc}")
        sys.exit(res.returncode)


def sync_catalog_file(root_dir: Path) -> dict[str, str]:
    """Generates a valid blender_assets.cats.txt with the mandatory VERSION 1 header."""
    print("\n[+] Synchronizing blender_assets.cats.txt...")
    cats_file = root_dir / "blender_assets.cats.txt"
    path_to_uuid = {
        cat_path: str(uuid.uuid5(CATALOG_NAMESPACE, cat_path))
        for cat_path in CATALOG_DEFINITIONS.keys()
    }

    header = (
        "# This is an Asset Catalog Definition file for Blender.\n"
        "# Empty lines and lines starting with '#' will be ignored.\n"
        "# The first non-comment line must be 'VERSION <number>'.\n"
        "\n"
        "VERSION 1\n"
        "\n"
    )

    # Rebuild file completely to guarantee valid structure and UUID mappings
    with open(cats_file, "w", encoding="utf-8") as f:
        f.write(header)
        for cat_path, display_name in CATALOG_DEFINITIONS.items():
            f.write(f"{path_to_uuid[cat_path]}:{cat_path}:{display_name}\n")

    print(f"[✓] Wrote {len(CATALOG_DEFINITIONS)} catalogs with valid header to {cats_file.name}")
    return path_to_uuid


def consolidate_and_tag_assets(blender_bin: str, root_dir: Path, path_to_uuid: dict[str, str]):
    """Headless Blender pass: categorizes assets and standardizes tags."""
    print("\n[+] Consolidating asset categories and normalizing tags...")

    worker_template = """
import bpy
import re

CAT_MAP = __CAT_MAP_JSON__

def normalize_tags(asset_data, extra_tags=None):
    raw_tags = [t.name.strip() for t in asset_data.tags if t.name.strip()]
    cleaned_tags = {t.title() for t in raw_tags}
    
    if extra_tags:
        for t in extra_tags:
            cleaned_tags.add(t.title())
    cleaned_tags.add("Augury")

    # Safe removal via list copy
    for old_tag in list(asset_data.tags):
        asset_data.tags.remove(old_tag)
        
    for tag in sorted(cleaned_tags):
        asset_data.tags.new(tag)

def get_search_context(item):
    name_lower = item.name.lower()
    raw_tag_names = [t.name.lower().strip() for t in item.asset_data.tags]
    search_blob = name_lower + " " + " ".join(raw_tag_names)
    tokens = set(re.findall(r'[a-zA-Z0-9]+', search_blob))
    return search_blob, tokens

def route_material(mat):
    if not mat.asset_data:
        return False
        
    blob, tokens = get_search_context(mat)
    extra_tags = ["Material", "Shader"]

    if any(k in blob for k in ["stylized", "toon", "npr", "anime"]):
        chosen_cat = "Augury Assets/Shaders/Materials/Stylized"
        extra_tags.append("Stylized")
    elif any(k in blob for k in ["photoreal", "photo-real", "realistic", "pbr", "real"]):
        chosen_cat = "Augury Assets/Shaders/Materials/Photoreal"
        extra_tags.append("Photoreal")
    else:
        chosen_cat = "Augury Assets/Shaders/Materials"

    if "procedural" in blob or "proc" in tokens or "voronoi" in blob:
        extra_tags.append("Procedural")

    mat.asset_data.catalog_id = CAT_MAP.get(chosen_cat, CAT_MAP.get("Augury Assets/Other"))
    normalize_tags(mat.asset_data, extra_tags)
    return True

def route_node_group(ng):
    if not ng.asset_data:
        return False
        
    blob, tokens = get_search_context(ng)
    
    if ng.type == 'GEOMETRY':
        extra_tags = ["Geometry Nodes"]
        if any(k in blob for k in ["selector", "select"]):
            chosen_cat = "Augury Assets/Geometry Nodes/Selectors"
            extra_tags.append("Selector")
        elif any(k in blob for k in ["generator", "generate"]) or "gen" in tokens:
            chosen_cat = "Augury Assets/Geometry Nodes/Generators"
            extra_tags.append("Generator")
        elif "deform" in blob:
            chosen_cat = "Augury Assets/Geometry Nodes/Deformers"
            extra_tags.append("Deformer")
        else:
            chosen_cat = "Augury Assets/Geometry Nodes"

    elif ng.type == 'SHADER':
        chosen_cat = "Augury Assets/Shaders/Node Groups"
        extra_tags = ["Shader", "Node Group"]

    elif ng.type == 'COMPOSITING':
        chosen_cat = "Augury Assets/Compositor/Node Groups"
        extra_tags = ["Compositor", "Node Group"]

    else:
        chosen_cat = "Augury Assets/Other"
        extra_tags = ["Other"]

    ng.asset_data.catalog_id = CAT_MAP.get(chosen_cat, CAT_MAP.get("Augury Assets/Other"))
    normalize_tags(ng.asset_data, extra_tags)
    return True

def route_model(item):
    if not item.asset_data:
        return False
        
    blob, tokens = get_search_context(item)
    extra_tags = ["Model"]

    if any(k in blob for k in ["other", "misc", "rig", "camera", "light"]):
        chosen_cat = "Augury Assets/Other"
        extra_tags = ["Other"]
    else:
        chosen_cat = "Augury Assets/Models"

    item.asset_data.catalog_id = CAT_MAP.get(chosen_cat, CAT_MAP.get("Augury Assets/Other"))
    normalize_tags(item.asset_data, extra_tags)
    return True

def route_generic(item, fallback_tag="Other"):
    if not item.asset_data:
        return False
    item.asset_data.catalog_id = CAT_MAP.get("Augury Assets/Other")
    normalize_tags(item.asset_data, [fallback_tag])
    return True

modified = False

for mat in bpy.data.materials:
    if route_material(mat):
        modified = True

for ng in bpy.data.node_groups:
    if route_node_group(ng):
        modified = True

for obj in bpy.data.objects:
    if route_model(obj):
        modified = True
for col in bpy.data.collections:
    if route_model(col):
        modified = True

for act in bpy.data.actions:
    if route_generic(act, "Animation"):
        modified = True
for wrd in bpy.data.worlds:
    if route_generic(wrd, "World"):
        modified = True

if modified:
    bpy.ops.wm.save_mainfile()
"""

    worker_script = worker_template.replace(
        "__CAT_MAP_JSON__", json.dumps(path_to_uuid)
    )
    temp_script = root_dir / "_temp_consolidate.py"
    temp_script.write_text(worker_script, encoding="utf-8")

    blend_files = [
        p
        for p in root_dir.rglob("*.blend")
        if not p.name.startswith((".", "#")) and not p.name.endswith("@")
    ]

    try:
        for blend in blend_files:
            res = subprocess.run(
                [blender_bin, "-b", str(blend), "-P", str(temp_script)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                print(f"[-] Error processing {blend.name}:\n{res.stderr}")
    finally:
        if temp_script.exists():
            temp_script.unlink()

    print("[✓] All assets unified under 'Augury Assets' hierarchy.")


def main():
    repo_root = Path(__file__).resolve().parent

    blender = get_blender_binary()
    if not blender:
        print("[-] Blender executable not found. Check system PATH or publish.py.")
        sys.exit(1)

    print(f"[+] Using Blender binary: {blender}")

    # 1. Write the catalog file with valid VERSION 1 header
    path_to_uuid = sync_catalog_file(repo_root)

    # 2. Tag assets and assign catalog IDs
    consolidate_and_tag_assets(blender, repo_root, path_to_uuid)

    # 3. Generate native Blender preview listing
    run_cmd(
        f'"{blender}" -b -c asset_listing generate .',
        "Generating Asset Listing & Previews",
    )

    # 4. Check Git status
    status = (
        subprocess.check_output("git status --porcelain", shell=True)
        .decode("utf-8")
        .strip()
    )
    if not status:
        print("\n[✓] Everything is up to date. Nothing to push.")
        return

    # 5. Commit & Push
    commit_msg = input("\nEnter commit summary (or press Enter for default): ").strip()
    if not commit_msg:
        commit_msg = "Update remote asset library"

    run_cmd("git add .", "Staging files")
    run_cmd(f'git commit -m "{commit_msg}"', "Committing changes")
    run_cmd("git push", "Pushing to GitHub")

    print("\n[✓] Remote asset library published successfully!")


if __name__ == "__main__":
    main()