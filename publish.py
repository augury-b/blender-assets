import os
import shutil
import subprocess
import sys

POSSIBLE_BLENDER_PATHS = [
    r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender\blender.exe",
]


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


def main():
    blender = get_blender_binary()
    if not blender:
        print(
            "[-] Blender executable not found. Check system PATH or publish.py."
        )
        sys.exit(1)

    # 1. Run native asset listing generator from repo root
    print(f"[+] Using Blender binary: {blender}")
    run_cmd(
        f'"{blender}" -b -c asset_listing generate .',
        "Generating Asset Listing & Previews",
    )

    # 2. Check for Git changes
    status = subprocess.check_output(
        "git status --porcelain", shell=True
    ).decode("utf-8")
    if not status.strip():
        print("\n[✓] Everything is up to date. Nothing to push.")
        return

    # 3. Stage, commit, and push
    commit_msg = input(
        "\nEnter commit summary (or press Enter for default): "
    ).strip()
    if not commit_msg:
        commit_msg = "Update remote asset library"

    run_cmd("git add .", "Staging files")
    run_cmd(f'git commit -m "{commit_msg}"', "Committing changes")
    run_cmd("git push", "Pushing to GitHub")

    print("\n[✓] Remote asset library published successfully!")


if __name__ == "__main__":
    main()