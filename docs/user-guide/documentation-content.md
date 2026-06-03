# User Summary

NPI DBMS is a centralized web-based platform for managing Intel New Product Introduction (NPI) data and workflows. It enables different user roles — including Program Managers, Requestors/Viewers, and ODM partners — to securely create, view, update, and manage build plan information through a unified interface.

The system provides dashboards and analytics for reporting, tracking, and monitoring NPI activities, helping teams make data-driven decisions efficiently. It supports database integration across multiple Business Units (BUs), improving data consistency, collaboration, and process visibility throughout the organization.

---

# Admin Page Overview

## Dashboard

Displays analytics summaries of build plan information from the database. There are two primary dashboard views:
- **My Build Plans**: Standardized dashboard with visuals for build plans managed by the current PM.
- **Overview**: Dashboard with analytics charts for all build plans in the database.

### My Build Plans
- **Filterable by family code** (default: all)
- **Charts/Graphs/Cards**:
  - Build Plans: Total number of build configs handled/created by the current PM
  - New/Hold/Plan/Completed: Status breakdowns
  - Build Requests: Total managed by current PM
  - Shipments: Total related to current PM's build plans
  - My Recent Build Plans: 5 most recent
  - Recent Build Requests: 5 most recent activities
  - Recent Shipments: 5 most recent updates

### Overview
- **Filterable by Year, Family, Form Factor, Status** (default: all)
- **Charts/Graphs/Cards**:
  - Total Builds, Total Boards, Families, Form Factors
  - Milestone Builds
  - Family × Form Factor breakdown (pie chart)
  - Family × Attribute breakdown (Silicon Stepping, PCB Revision, HW Revision)
  - Number of Builds/Boards by Support Activity and Form Factor (stacked bar)
  - Milestone Builds Timeline (monthly)
  - Component charts (by Supplier, by PCB Supplier, details by attributes)

---

## My Build Plans

Displays a list of build plans managed by the current PM. Features:
- Tabs for status: Managed by me, New, Hold, Plan, Completed
- Sortable columns, filterable by family/form factor/status, searchable, column visibility

## Manage Build Request

Displays build requests managed by the current PM. Features:
- Tabs for status: Managed by me, Draft, Submitted, Under Review, Approved, Planned, Locked, Completed, Rejected, Cancelled
- Sortable columns, filterable by family/form factor, searchable, column visibility

## Tracker

Read-only views for searching plans, requests, and shipments.

## Administration
- **Import Build Plan**: Import build plan Excel files (step-by-step guidance)
- **Import Shipments**: Import shipment Excel files (step-by-step guidance)
- **User Management**: Edit, assign roles, merge users
- **Role Management**: Edit, set permissions, delete, add new roles
- **DB Tables**: Maintain lookup/reference tables

## Glossary
See [Glossary](glossary.md) for definitions of key terms.

---

_This content is intended to be mapped to the Documentation page sections or referenced as needed. For more details, see the user guide markdown files._
