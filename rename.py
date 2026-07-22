import os
import glob

def rename_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content.replace('Cripple', 'Cripple')
    new_content = new_content.replace('cripple', 'cripple')
    new_content = new_content.replace('CRIPPLE', 'CRIPPLE')

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

def main():
    extensions = ['*.py', '*.md', '*.bat', '.gitignore']
    for ext in extensions:
        for filepath in glob.glob(f"**/{ext}", recursive=True):
            if '.venv' in filepath or 'venv' in filepath or 'env' in filepath or 'build' in filepath or 'dist' in filepath or '.git' in filepath:
                continue
            rename_in_file(filepath)

if __name__ == "__main__":
    main()
