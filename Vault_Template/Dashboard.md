# Agent Dashboard

> **Last Updated:** `=date(now)`

## Overview

This dashboard provides a real-time summary of all task folders in the vault.

---

## 📥 Needs Action
*Incoming raw tasks and triggers awaiting processing*

```dataview
TABLE file.ctime as "Created", file.mtime as "Modified"
FROM "Needs_Action"
SORT file.mtime DESC
```

**Count:** `$= dv.pages('"Needs_Action"').length` items

---

## 🔄 In Progress
*Tasks currently being handled by the agent*

```dataview
TABLE file.ctime as "Created", file.mtime as "Modified"
FROM "In_Progress"
SORT file.mtime DESC
```

**Count:** `$= dv.pages('"In_Progress"').length` items

---

## ✅ Approved
*Human-vetted actions ready for execution (payments, emails, etc.)*

```dataview
TABLE file.ctime as "Created", file.mtime as "Modified"
FROM "Approved"
SORT file.mtime DESC
```

**Count:** `$= dv.pages('"Approved"').length` items

---

## 📦 Done
*Completed and archived tasks*

```dataview
TABLE file.ctime as "Created", file.mtime as "Modified"
FROM "Done"
SORT file.mtime DESC
LIMIT 10
```

**Count:** `$= dv.pages('"Done"').length` items

---

## 📋 Logs
*Daily agent activity tracking*

```dataview
TABLE file.ctime as "Created"
FROM "Logs"
SORT file.name DESC
LIMIT 7
```

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Pending Tasks | `$= dv.pages('"Needs_Action"').length` |
| In Progress | `$= dv.pages('"In_Progress"').length` |
| Awaiting Approval | `$= dv.pages('"Approved"').length` |
| Completed (Total) | `$= dv.pages('"Done"').length` |

---

## Navigation

- [[Company_Handbook|Company Handbook & Rules of Engagement]]
- [[Logs/|Activity Logs]]
