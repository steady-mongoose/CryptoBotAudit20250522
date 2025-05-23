import os
import shutil

def clean_pycache(root_dir):
    """Recursively remove all __pycache__ directories in the given root directory."""
    for root, dirs, files in os.walk(root_dir):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                pycache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(pycache_path)
                    print(f"Removed: {pycache_path}")
                except Exception as e:
                    print(f"Error removing {pycache_path}: {e}")

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    print(f"Cleaning __pycache__ directories in {project_root}")
    clean_pycache(project_root)
    print("Cleanup complete.")
