-- Project 02: Checkout Conversion Experiment
-- Initial data validation checks.


-- ---------------------------------------------------------------------------
-- 1. Row counts
-- ---------------------------------------------------------------------------

SELECT 'users' AS table_name, COUNT(*) AS row_count
FROM users

UNION ALL

SELECT 'experiment_assignments', COUNT(*)
FROM experiment_assignments

UNION ALL

SELECT 'events', COUNT(*)
FROM events

UNION ALL

SELECT 'orders', COUNT(*)
FROM orders;


-- ---------------------------------------------------------------------------
-- 2. User ID uniqueness
-- ---------------------------------------------------------------------------

SELECT
    COUNT(*) AS total_users,
    COUNT(DISTINCT user_id) AS unique_users
FROM users;


-- ---------------------------------------------------------------------------
-- 3. Assignment uniqueness
-- Each experiment user should have exactly one assignment.
-- ---------------------------------------------------------------------------

SELECT
    COUNT(*) AS total_assignments,
    COUNT(DISTINCT user_id) AS unique_assigned_users
FROM experiment_assignments;


-- ---------------------------------------------------------------------------
-- 4. Experiment allocation
-- ---------------------------------------------------------------------------

SELECT
    variant,
    COUNT(*) AS users
FROM experiment_assignments
GROUP BY variant
ORDER BY variant;


-- ---------------------------------------------------------------------------
-- 5. Assignment balance by device
-- ---------------------------------------------------------------------------

SELECT
    u.device_type,
    ea.variant,
    COUNT(*) AS users
FROM experiment_assignments AS ea
INNER JOIN users AS u
    ON ea.user_id = u.user_id
GROUP BY
    u.device_type,
    ea.variant
ORDER BY
    u.device_type,
    ea.variant;


-- ---------------------------------------------------------------------------
-- 6. Missing acquisition channels
-- ---------------------------------------------------------------------------

SELECT
    COUNT(*) AS missing_acquisition_channels
FROM users
WHERE acquisition_channel IS NULL;


-- ---------------------------------------------------------------------------
-- 7. Duplicate event summary
-- A duplicate is defined using the business fields rather than event_id,
-- because duplicate ingestion gives the copied row a new event_id.
-- ---------------------------------------------------------------------------

WITH duplicate_groups AS (
    SELECT
        user_id,
        event_timestamp,
        event_type,
        COUNT(*) AS duplicate_count
    FROM events
    GROUP BY
        user_id,
        event_timestamp,
        event_type
    HAVING COUNT(*) > 1
)

SELECT
    COUNT(*) AS duplicate_groups,
    SUM(duplicate_count - 1) AS duplicate_rows_to_remove
FROM duplicate_groups;


-- ---------------------------------------------------------------------------
-- 8. Duplicate events by type
-- ---------------------------------------------------------------------------

WITH duplicate_groups AS (
    SELECT
        user_id,
        event_timestamp,
        event_type,
        COUNT(*) AS duplicate_count
    FROM events
    GROUP BY
        user_id,
        event_timestamp,
        event_type
    HAVING COUNT(*) > 1
)

SELECT
    event_type,
    COUNT(*) AS duplicate_groups,
    SUM(duplicate_count - 1) AS duplicate_rows_to_remove
FROM duplicate_groups
GROUP BY event_type
ORDER BY duplicate_rows_to_remove DESC;


-- ---------------------------------------------------------------------------
-- 9. Out-of-period events
-- The experiment runs from 6 July to 19 July 2026 inclusive.
-- ---------------------------------------------------------------------------

SELECT
    COUNT(*) AS out_of_period_events
FROM events
WHERE event_timestamp < '2026-07-06'
   OR event_timestamp >= '2026-07-20';


-- ---------------------------------------------------------------------------
-- 10. Raw event type counts
-- ---------------------------------------------------------------------------

SELECT
    event_type,
    COUNT(*) AS event_count
FROM events
GROUP BY event_type
ORDER BY event_count DESC;


-- ---------------------------------------------------------------------------
-- 11. Referential integrity
-- Check that assignment, event and order user IDs all exist in users.
-- ---------------------------------------------------------------------------

SELECT
    'experiment_assignments' AS table_name,
    COUNT(*) AS missing_users
FROM experiment_assignments AS ea
LEFT JOIN users AS u
    ON ea.user_id = u.user_id
WHERE u.user_id IS NULL

UNION ALL

SELECT
    'events',
    COUNT(*)
FROM events AS e
LEFT JOIN users AS u
    ON e.user_id = u.user_id
WHERE u.user_id IS NULL

UNION ALL

SELECT
    'orders',
    COUNT(*)
FROM orders AS o
LEFT JOIN users AS u
    ON o.user_id = u.user_id
WHERE u.user_id IS NULL;


-- ---------------------------------------------------------------------------
-- 12. Orders and purchase-event reconciliation
-- Raw purchase events include deliberate duplicate ingestion. Once duplicate
-- event records are removed, genuine in-period purchases should reconcile
-- exactly to the orders table.
-- ---------------------------------------------------------------------------

SELECT
    (SELECT COUNT(*)
     FROM orders) AS order_rows,

    (SELECT COUNT(*)
     FROM events
     WHERE event_type = 'purchase_completed'
       AND event_timestamp >= '2026-07-06'
       AND event_timestamp < '2026-07-20'
    ) AS raw_in_period_purchase_events,

    (SELECT COUNT(*)
     FROM (
         SELECT DISTINCT
             user_id,
             event_timestamp,
             event_type
         FROM events
         WHERE event_type = 'purchase_completed'
           AND event_timestamp >= '2026-07-06'
           AND event_timestamp < '2026-07-20'
     )
    ) AS deduplicated_in_period_purchases;