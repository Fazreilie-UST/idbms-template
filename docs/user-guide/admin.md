# Admin Guide

Administrators have full access to every screen in the application plus the
following responsibilities:

## User & role management

- **User Management** (`/pm/admin/users`) – create users, deactivate users,
  reset passwords, and assign roles.
- **Role Management** (`/pm/admin/roles`) – review the available roles and
  the permissions they grant. Permissions are seeded from the backend and
  enforced via JWT claims.

## Reference data

- **DB Tables** (`/pm/admin/db-tables`) – maintain lookup tables (forwarders,
  warehouses, addresses, components, suppliers, etc.).

## Documentation

- Only users with the **Admin** role see the **Edit** button on documentation
  pages. Use it to update the page contents and upload screenshots.
- Updates are written back to markdown files in the project repository so
  every change is captured in version control.
