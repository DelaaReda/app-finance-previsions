# Integration Playbook for Dash Pages

This playbook provides clear instructions for developers on how to add and extend Dash pages in the project.

## Dash Conventions

*   **Imports:** Use modern imports like `from dash import html, dcc, dash_table`.
*   **Layout Structure:** Structure the layout of a Dash page using `html.Div` and other appropriate HTML components. Use a consistent structure across all pages.
*   **Empty States:** Use French empty state messages (e.g., "Aucune donnée disponible").
*   **Badges:** Use badges to highlight important information or status indicators.
*   **Styles:** Apply styles using CSS or inline styles. Ensure styles are consistent with the overall application theme.

## Reading Data

*   Prefer existing loaders (e.g., `dash_app/data/loader.py`).
*   Use data partitions (`dt=YYYYMMDD[...]`) to efficiently load data for specific dates or periods.

## DEV vs PROD Pages

*   Use `DEVTOOLS_ENABLED=1` for integration pages to enable debugging tools and features. This setting should be disabled in production.

## Testing

*   **Smoke routes:** Ensure all routes are accessible and do not return errors.
*   **Selecting stable IDs:** Use stable IDs for elements to ensure tests are reliable.
*   **UI Health:** Monitor the UI for any errors or performance issues.

## Commands

*   `make dash-restart-bg`: Restarts the Dash application in the background.
*   `make dash-smoke`: Runs smoke tests to verify basic functionality.
*   `make ui-health`: Runs UI health checks to identify any issues.
*   `make artifacts-zip`: Creates a zip archive of artifacts for deployment.

## Updating Documentation

*   Update `docs/PROGRESS.md` (Delivered/Next/How-to-run) for each delivery to track progress and provide instructions for running the application.