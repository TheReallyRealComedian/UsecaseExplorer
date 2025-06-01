#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import Set

# Configuration
SOURCE_DIR = "/Users/olivergluth/CODE/UsecaseExplorer"  # Source directory
TARGET_DIR = "/Users/olivergluth/LLM-Interaction/UsecaseExplorer/files"  # Directory where the combined file will be created
ALLOWED_EXTENSIONS = {".css", ".html", ".py", ".js", ".md", ".yml", ".yaml", ".txt"}
# Add a set for specific filenames to include, regardless of extension (or lack thereof)
ALLOWED_FILENAMES = {"Dockerfile", ".env"} 
EXCLUDED_DIRS = {".git", "node_modules", "__pycache__", "venv", "content", "env", ".vscode", ".codebuddy", ".pytest_cache"}
# New: Add a set for specific file paths to exclude (paths are relative to SOURCE_DIR)
EXCLUDED_RELATIVE_FILE_PATHS = {
    "backend/export_service.py"
}

def ensure_target_dir_exists() -> Path:
    """
    Ensure that the target directory exists. Create it if it does not.
    
    Returns:
        Path: Path to the target directory.
    """
    target_path = Path(TARGET_DIR)
    if not target_path.exists():
        print(f"Creating target directory at {target_path}")
        target_path.mkdir(parents=True, exist_ok=True)
    else:
        print(f"Target directory already exists at {target_path}")
    return target_path

def create_file_tree(source_dir: str, excluded_dirs: Set[str], excluded_relative_file_paths: Set[str]) -> str:
    """
    Create a visual representation of the file tree starting from the source directory,
    excluding any directories in 'excluded_dirs' and specific files in 'excluded_relative_file_paths'.
    
    Args:
        source_dir: The root directory to start from.
        excluded_dirs: Set of directory names to exclude.
        excluded_relative_file_paths: Set of file paths (relative to source_dir) to exclude.
    
    Returns:
        str: String representation of the file tree.
    """
    source_path = Path(source_dir)
    if not source_path.exists():
        print(f"Error: Source directory '{source_dir}' does not exist.")
        sys.exit(1)
    
    root_name = source_path.name
    tree = [f"{root_name}/"]
    
    def _build_tree(directory: Path, prefix: str = "") -> None:
        # Sort entries, directories first, then files, case-insensitively
        entries = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        
        filtered_entries = []
        for entry in entries:
            # Filter out excluded directories
            if entry.is_dir() and entry.name in excluded_dirs:
                continue
            
            # Filter out explicitly excluded files
            if entry.is_file():
                try:
                    # Get the path relative to the SOURCE_DIR for comparison
                    relative_path_str = str(entry.relative_to(source_path))
                    if relative_path_str in excluded_relative_file_paths:
                        continue # Skip this file
                except ValueError:
                    # This should ideally not happen if 'entry' is within 'source_path',
                    # but added for defensive programming.
                    pass 
            filtered_entries.append(entry)
        
        entries = filtered_entries # Update entries with the filtered list
        
        num_entries = len(entries)
        for index, entry in enumerate(entries):
            connector = "└── " if index == num_entries - 1 else "├── "
            tree.append(f"{prefix}{connector}{entry.name}" + ("/" if entry.is_dir() else ""))
            if entry.is_dir():
                extension_prefix = "    " if index == num_entries - 1 else "│   "
                _build_tree(entry, prefix + extension_prefix)
                
    _build_tree(source_path)
    return "\n".join(tree)

def combine_files(source_dir: str, combined_file_path: Path, allowed_extensions: Set[str], allowed_filenames: Set[str], excluded_dirs: Set[str], excluded_relative_file_paths: Set[str]) -> None:
    """
    Traverse the source directory, first write a file tree at the top of the combined file,
    then read allowed files and append their contents to the combined file.
    
    For each file, the output contains:
      ### START of Content from <path/to/parsed/file/<filename> ###
      <file content>
      ### END of Content from <path/to/parsed/file/<filename> ###
    
    Args:
        source_dir (str): The root directory to scan.
        combined_file_path (Path): The path to the combined output file.
        allowed_extensions (Set[str]): Set of allowed file extensions.
        allowed_filenames (Set[str]): Set of allowed specific filenames.
        excluded_dirs (Set[str]): Set of directory names to exclude.
        excluded_relative_file_paths (Set[str]): Set of file paths (relative to source_dir) to explicitly exclude.
    """
    source_path = Path(source_dir)
    files_processed = 0
    
    # Create the file tree representation, passing the new exclusion list
    file_tree = create_file_tree(source_dir, excluded_dirs, excluded_relative_file_paths)
    
    with open(combined_file_path, "w", encoding="utf-8") as outfile:
        # Write the file tree at the top of the combined file
        outfile.write("FILE TREE:\n")
        outfile.write(file_tree)
        outfile.write("\n\n")
        
        # Traverse and combine file contents
        for root, dirs, files in os.walk(source_path):
            # Skip excluded directories by modifying 'dirs' in-place
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            # Sort files for consistent order
            files.sort()
            
            for file_name in files:
                file_path = Path(root) / file_name
                
                # Convert file_path to a path relative to SOURCE_DIR for comparison
                try:
                    relative_file_path_str = str(file_path.relative_to(source_path))
                except ValueError:
                    # This means 'file_path' is not inside 'source_path', which is unexpected for os.walk
                    # when processing within source_path. Log and skip.
                    print(f"Warning: {file_path} is not relative to {source_path}. Skipping.")
                    continue 

                # New: Check if the file is in the explicitly excluded list
                if relative_file_path_str in excluded_relative_file_paths:
                    print(f"Skipping explicitly excluded file: {file_path}")
                    continue # Skip this file

                # Existing: Check if the file extension is allowed OR if the filename itself is specifically allowed
                if file_path.suffix.lower() in allowed_extensions or file_path.name in allowed_filenames:
                    print(f"Processing: {file_path}")
                    outfile.write(f"### START of Content from {file_path} ###\n")
                    try:
                        with open(file_path, "r", encoding="utf-8", errors='ignore') as infile: # Added errors='ignore' for robustness
                            content = infile.read()
                            outfile.write(content)
                    except Exception as e:
                        outfile.write(f"Error reading file {file_path}: {e}\n")
                    outfile.write(f"\n### END of Content from {file_path} ###\n\n")
                    files_processed += 1
                # else: # Optional: uncomment to see skipped files
                #     print(f"Skipping: {file_path} (Extension: '{file_path.suffix}', Name: '{file_path.name}')")


    print(f"Total files processed: {files_processed}")

def main() -> None:
    """Main function to execute the script."""
    print("Starting directory crawler script...")
    
    # Validate the source directory exists
    if not Path(SOURCE_DIR).exists():
        print(f"Error: Source directory '{SOURCE_DIR}' does not exist.")
        sys.exit(1)
    
    # Ensure the target directory exists
    target_dir = ensure_target_dir_exists()
    
    # Set the name for the combined file (using the name of the scanned root directory)
    root_name = Path(SOURCE_DIR).name
    combined_file_path = target_dir / f"{root_name}_combined_content.txt" # Slightly more descriptive name
    print(f"Combined file will be created at: {combined_file_path.absolute()}")
    
    # Combine the file tree and file contents into one file, passing the new exclusion list
    combine_files(SOURCE_DIR, combined_file_path, ALLOWED_EXTENSIONS, ALLOWED_FILENAMES, EXCLUDED_DIRS, EXCLUDED_RELATIVE_FILE_PATHS)
    
    print("Directory crawler script completed successfully!")
    print(f"Combined file created at: {combined_file_path.absolute()}")

if __name__ == "__main__":
    main()