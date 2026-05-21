import re, pathlib

ROOT = pathlib.Path(__file__).parent / "src"
files = [
    "features/orders/services/build_request_service.js",
    "features/shipments/services/shipping_service.js",
    "features/buildplans/services/build_plan_revision_service.js",
    "features/admin/services/user_service.js",
    "features/admin/services/role_service.js",
    "features/admin/services/lookup_service.js",
    "features/admin/services/department_service.js",
]

for rel in files:
    p = ROOT / rel
    src = p.read_text()
    out = src

    def ml_repl(m):
        indent = m.group(1)
        nxt = m.group(2)
        if "credentials" in nxt:
            return m.group(0)
        return f"{indent}headers: authHeaders(),\n{indent}credentials: \"include\",\n{nxt}"

    out = re.sub(
        r"^([ \t]+)headers: authHeaders\(\),\n(.*)$",
        ml_repl,
        out,
        flags=re.MULTILINE,
    )
    out = out.replace(
        "{ headers: authHeaders() }",
        '{ headers: authHeaders(), credentials: "include" }',
    )

    if out != src:
        p.write_text(out)
        print(f"updated: {rel}")
    else:
        print(f"no change: {rel}")
