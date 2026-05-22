# NPI DBMS Documentation

This folder contains the user-facing guides and developer references rendered
inside the application's **Documentation** page.

Pages are stored as Markdown so changes are easy to review in pull requests.
Images embedded in the docs live under [`assets/screenshots/`](assets/screenshots/)
and are served by the backend at the URL prefix `/static/docs-assets/screenshots/`.

Structure:

```
docs/
  user-guide/
    screen-guide.md
    admin.md
    program-manager.md
    requestor.md
  developer/
    api-documentation.md
    db-erd/
      current-db.md
      external-db.md
    architecture-summary.md
  assets/
    screenshots/
```

The set of pages and where they appear in the sidebar is defined by
`DOC_TREE` in `backend/app/api/v1/endpoints/documentation.py`. Adding a new
page requires updating that tree and creating the corresponding markdown
file here.
