-- Project 02: Checkout Conversion Experiment
-- Create cleaned and analysis-ready SQL views.
--
-- The raw source tables are retained unchanged. Cleaning is performed through
-- views so that the transformation from raw data to analysis data is explicit
-- and reproducible.


-- ---------------------------------------------------------------------------
-- 1. Clean event data
--
-- Remove:
--   - deliberately duplicated event records
--   - events outside the 14-day experiment window
--
-- event_id is excluded from the duplicate definition because duplicated
-- ingestion records were deliberately generated with new event IDs.
-- ---------------------------------------------------------------------------

DROP VIEW IF EXISTS clean_events;

CREATE VIEW clean_events AS

SELECT DISTINCT
    user_id,
    event_timestamp,
    event_type
FROM events
WHERE event_timestamp >= '2026-07-06'
  AND event_timestamp < '2026-07-20';


-- ---------------------------------------------------------------------------
-- 2. Summarise experiment events to user level
--
-- The experiment's primary unit of analysis is the user, not the individual
-- event. Binary flags therefore record whether each user experienced an event
-- at least once.
--
-- Event counts are retained where useful for checking repeat activity.
-- ---------------------------------------------------------------------------

DROP VIEW IF EXISTS user_event_summary;

CREATE VIEW user_event_summary AS

SELECT
    user_id,

    MAX(
        CASE
            WHEN event_type = 'checkout_started' THEN 1
            ELSE 0
        END
    ) AS started_checkout,

    MAX(
        CASE
            WHEN event_type = 'payment_submitted' THEN 1
            ELSE 0
        END
    ) AS submitted_payment,

    MAX(
        CASE
            WHEN event_type = 'payment_declined' THEN 1
            ELSE 0
        END
    ) AS had_payment_decline,

    MAX(
        CASE
            WHEN event_type = 'technical_payment_error' THEN 1
            ELSE 0
        END
    ) AS had_technical_payment_error,

    MAX(
        CASE
            WHEN event_type = 'purchase_completed' THEN 1
            ELSE 0
        END
    ) AS converted,

    SUM(
        CASE
            WHEN event_type = 'purchase_completed' THEN 1
            ELSE 0
        END
    ) AS purchase_event_count

FROM clean_events

GROUP BY user_id;


-- ---------------------------------------------------------------------------
-- 3. Summarise orders to user level
--
-- Revenue is taken from genuine completed orders rather than inferred from
-- purchase events. Repeat purchases are therefore included in both order
-- count and total revenue.
-- ---------------------------------------------------------------------------

DROP VIEW IF EXISTS user_order_summary;

CREATE VIEW user_order_summary AS

SELECT
    user_id,
    COUNT(*) AS order_count,
    ROUND(SUM(order_value), 2) AS total_revenue

FROM orders

WHERE order_timestamp >= '2026-07-06'
  AND order_timestamp < '2026-07-20'

GROUP BY user_id;


-- ---------------------------------------------------------------------------
-- 4. Build the experiment analysis dataset
--
-- One row represents one randomised experiment user.
--
-- This combines:
--   - pre-treatment user characteristics
--   - experiment assignment
--   - user-level funnel outcomes
--   - order and revenue outcomes
--
-- LEFT JOINs preserve all randomised users, including users who did not reach
-- later funnel stages.
-- ---------------------------------------------------------------------------

DROP VIEW IF EXISTS experiment_user_metrics;

CREATE VIEW experiment_user_metrics AS

SELECT
    ea.user_id,
    ea.variant,
    ea.assignment_timestamp,

    u.signup_date,
    u.device_type,
    u.acquisition_channel,

    COALESCE(es.started_checkout, 0) AS started_checkout,
    COALESCE(es.submitted_payment, 0) AS submitted_payment,
    COALESCE(es.had_payment_decline, 0) AS had_payment_decline,
    COALESCE(es.had_technical_payment_error, 0)
        AS had_technical_payment_error,
    COALESCE(es.converted, 0) AS converted,
    COALESCE(es.purchase_event_count, 0) AS purchase_event_count,

    COALESCE(os.order_count, 0) AS order_count,
    COALESCE(os.total_revenue, 0.0) AS total_revenue

FROM experiment_assignments AS ea

INNER JOIN users AS u
    ON ea.user_id = u.user_id

LEFT JOIN user_event_summary AS es
    ON ea.user_id = es.user_id

LEFT JOIN user_order_summary AS os
    ON ea.user_id = os.user_id;


-- ---------------------------------------------------------------------------
-- 5. Validate the cleaned event view
-- ---------------------------------------------------------------------------

SELECT
    COUNT(*) AS clean_event_rows
FROM clean_events;


SELECT
    event_type,
    COUNT(*) AS clean_event_count
FROM clean_events
GROUP BY event_type
ORDER BY clean_event_count DESC;


-- ---------------------------------------------------------------------------
-- 6. Validate the user-level analysis dataset
-- ---------------------------------------------------------------------------

SELECT
    COUNT(*) AS analysis_rows,
    COUNT(DISTINCT user_id) AS unique_users
FROM experiment_user_metrics;


SELECT
    variant,
    COUNT(*) AS users
FROM experiment_user_metrics
GROUP BY variant
ORDER BY variant;


-- ---------------------------------------------------------------------------
-- 7. Check event/order consistency after cleaning
--
-- Each genuine purchase event should correspond to one order.
-- ---------------------------------------------------------------------------

SELECT
    SUM(purchase_event_count) AS purchase_events,
    SUM(order_count) AS orders,
    SUM(purchase_event_count) - SUM(order_count) AS difference
FROM experiment_user_metrics;


-- ---------------------------------------------------------------------------
-- 8. Basic funnel sanity check
--
-- These are user counts, rather than raw event counts. A user who retries
-- payment therefore still contributes only once to the payment denominator.
-- ---------------------------------------------------------------------------

SELECT
    variant,
    COUNT(*) AS checkout_users,
    SUM(submitted_payment) AS payment_submitters,
    SUM(converted) AS converted_users,
    SUM(had_payment_decline) AS users_with_payment_decline,
    SUM(had_technical_payment_error) AS users_with_technical_error
FROM experiment_user_metrics
GROUP BY variant
ORDER BY variant;


-- ---------------------------------------------------------------------------
-- 9. Revenue sanity check
-- ---------------------------------------------------------------------------

SELECT
    variant,
    SUM(order_count) AS orders,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    ROUND(AVG(total_revenue), 2) AS revenue_per_checkout_user
FROM experiment_user_metrics
GROUP BY variant
ORDER BY variant;