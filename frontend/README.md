# CPE 595 · AI-Powered Student Planner frontend

A responsive, dependency-free frontend using native JavaScript components, HTML, and CSS. The repository had no established frontend framework or package configuration, so this implementation adds no build tools, external fonts, calendar packages, or runtime dependencies. Only `frontend/` is changed.

## Run locally

Open `frontend/index.html` in a current Chrome, Edge, Firefox, or Safari browser. No backend, Node.js, installation, or build is required. Enable JavaScript and browser local storage.

For a consistent development origin, optionally serve the repository with an existing Python installation:

```powershell
cd C:\Users\enoch\Documents\CPE595-Project
python -m http.server 5500 --bind 127.0.0.1
```

Open http://127.0.0.1:5500/frontend/ and stop the server with Ctrl+C. A local server is recommended if your browser restricts storage for `file:` URLs. File and HTTP origins may have separate saved data. No Python installation is bundled.

## Components and responsibilities

- `index.html`: accessible navigation, page container, assignment form, deletion confirmation, and live notification region.
- `styles.css`: shared visual styles, responsive desktop/mobile layouts, focus indicators, and reduced-motion support. The desktop calendar is seven columns; phones show seven daily agenda rows.
- `src/app.js`: view components (`assignmentsPage`, `calendarPage`, `schedulePage`), shared view state, filters, calendar navigation, forms, and mutation feedback. Hash navigation supports browser back/forward and direct section links.
- `src/data.js`: asynchronous demo repository with `load`, `saveAssignment`, `deleteAssignment`, and `reset`. Owns validation, fixtures, and persistence; views never read or write local storage directly.
- `src/dates.js`: local calendar-date formatting, Monday-based weeks, date arithmetic, and study duration calculations. Date-only strings are parsed as local dates to avoid UTC date shifts.
- `tests.html`: dependency-free checks for repository behavior and calendar dates. Open it through the optional local HTTP server; it uses isolated in-memory storage and does not change your planner data.

## Current behavior

**Assignments:** create, edit, delete with confirmation, filter by text/course/status, and track status or actual hours. Lists sort by deadline. Required fields, date validity, category values, length limits, and nonnegative hours are validated. Existing past dates are allowed and marked overdue for unfinished work.

**Calendar:** previous/next week, Today, day selection with an expanded agenda, date-only assignment deadlines, recurring weekly commitments, and study sessions. Selecting a deadline or study session opens its assignment. Commitments are read-only.

**Study Schedule:** sample study blocks grouped and sorted by date/time, weekly navigation, per-session duration, and total planned hours. Sessions for completed assignments are hidden; deleting an assignment removes associated demo blocks. Marking it incomplete shows its retained blocks again.

**Shared behavior:** loading and saving states, disabled duplicate submissions, empty/filter states, visible failures, retry, and explicit demo reset. Assignment changes persist across refreshes using `studywise.demo.v1` in this browser's local storage. Reset replaces saved edits after confirmation. Demo dates are relative to the week of the first load or reset, and do not shift every refresh.

Estimates and study sessions are preloaded examples, **not live AI output**. New assignments have no estimate or scheduled blocks. Editing deadlines does not reschedule blocks. There is no frontend scheduling or prediction algorithm and no live backend integration. Demo data is local, not a secure multi-user account store. Avoid entering sensitive information.

## Connect FastAPI later

Replace `window.PlannerRepository` with an HTTP adapter preserving its async interface; keep component rendering independent of transport. Each mutation currently resolves to the updated `{ assignments, commitments, study_blocks }` snapshot. An HTTP adapter can perform a mutation and reload those collections.

Planner routes do not exist in the current backend. Agree with its owner on these proposed routes before implementing integration:

| Route | Purpose |
| --- | --- |
| `GET /assignments` | Assignment collection |
| `POST /assignments` | Create assignment |
| `PATCH /assignments/{id}` | Edit assignment/status |
| `DELETE /assignments/{id}` | Delete assignment |
| `GET /commitments` | Weekly commitments |
| `GET /schedule?start=YYYY-MM-DD&end=YYYY-MM-DD` | Generated study blocks |

Use a configurable base URL and native `fetch`; check `response.ok`, map validation errors into useful messages, and attach the agreed authentication credentials. Configure the backend's `CORS_ORIGINS` for the frontend origin. Authentication screens and schedule generation are outside this implementation.

The frontend follows model field names. Assignments use numeric IDs, `course`, `title`, `type`, `difficulty`, `due_date`, `status`, nullable `ai_prediction_hrs`, and nullable `actual_hrs`. Study blocks use `assignment_id`, `date`, `start_time`, and `end_time`; commitments use `day_of_week` (0 = Monday). Agree on local `YYYY-MM-DD` dates, 24-hour `HH:mm` / `HH:mm:ss` times, timezone interpretation, enum values, error shapes, and deletion semantics. User ownership must be derived and enforced by the server. If the backend returns joined assignment details or different response shapes, normalize them in the adapter.

## Test locally

1. With the optional local server running, open http://127.0.0.1:5500/frontend/tests.html; all 14 checks should pass. The test page fetches the repository source and requires HTTP in browsers that block file fetches. These checks do not replace browser UI testing.
2. Open `index.html`. Confirm the loading state resolves into six sample assignments and three navigation sections.
3. Create an assignment with a unique title and course. Try an empty/whitespace title, missing date, and negative actual hours; invalid values must not save. Valid assignments appear with “Not estimated.”
4. Search for the new title; filter by course/status; clear filters. Edit its title/date, change its status, and refresh to verify persistence.
5. Navigate to Calendar. Browse weeks, return to Today, select a day, and select an assignment deadline to edit it. Confirm recurring commitments appear each week.
6. Open Study Schedule in the sample week. Check chronological grouping, durations, and weekly totals. Mark a scheduled assignment Done: its study sessions disappear from both views. Mark it incomplete: they return.
7. Cancel a deletion, then confirm one. Verify its deadline and sample sessions disappear. Reset demo data to recover the initial dataset.
8. Test a 390px mobile viewport, desktop width, keyboard navigation, Escape/cancel in dialogs, and browser back/forward. Navigation and forms should remain usable; the assignment table scrolls horizontally on narrow screens.
9. To exercise read errors, use browser developer tools → Application/Storage to set `studywise.demo.v1` to invalid JSON, then refresh. Expect an error with Retry and Reset actions. Reset should recover. Disallowing browser storage should produce a storage error rather than pretending data was saved.

No commits, backend changes, machine-learning changes, or scheduling changes are required to run this frontend.
