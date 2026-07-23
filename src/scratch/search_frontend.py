import os

frontend_dir = r"d:\DoAnTotNghiep\DATN\New folder (2)\New folder\frontend\src"

for root, dirs, files in os.walk(frontend_dir):
    for file in files:
        if file.endswith((".ts", ".tsx")):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if "conversations" in content or "history" in content or "session" in content:
                    print(f"Found in {file}:")
                    for line_num, line in enumerate(content.splitlines(), 1):
                        if any(x in line for x in ["conversations", "history", "session", "/api/"]):
                            print(f"  Line {line_num}: {line.strip()}")
