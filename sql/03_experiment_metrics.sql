-- Project 02: Checkout Conversion Experiment
-- Core experiment metrics.
--
-- All calculations use the cleaned, one-row-per-user
-- experiment_user_metrics view.


-- ---------------------------------------------------------------------------
-- 1. Core metrics by experiment variant
-- ---------------------------------------------------------------------------

SELECT
    variant,
    COUNT(*) AS checkout_users,

    SUM(submitted_payment) AS payment_submitters,
    ROUND(
        100.0 * SUM(submitted_payment) / COUNT(*),
        2
    ) AS payment_submission_rate_pct,

    SUM(converted) AS converted_users,
    ROUND(
        100.0 * SUM(converted) / COUNT(*),
        2
    ) AS conversion_rate_pct,

    SUM(order_count) AS orders,

    ROUND(
        SUM(total_revenue),
        2
    ) AS total_revenue,

    ROUND(
        SUM(total_revenue) / COUNT(*),
        2
    ) AS revenue_per_checkout_user

FROM experiment_user_metrics

GROUP BY variant
ORDER BY variant;


-- ---------------------------------------------------------------------------
-- 2. Treatment uplift versus control
--
-- Absolute conversion uplift is reported in percentage points.
-- Relative uplift expresses the proportional improvement over control.
-- ---------------------------------------------------------------------------

WITH variant_metrics AS (
    SELECT
        variant,
        COUNT(*) AS users,
        1.0 * SUM(converted) / COUNT(*) AS conversion_rate,
        1.0 * SUM(total_revenue) / COUNT(*) AS revenue_per_user
    FROM experiment_user_metrics
    GROUP BY variant
),

control AS (
    SELECT *
    FROM variant_metrics
    WHERE variant = 'control'
),

treatment AS (
    SELECT *
    FROM variant_metrics
    WHERE variant = 'treatment'
)

SELECT
    ROUND(
        100.0 * control.conversion_rate,
        3
    ) AS control_conversion_pct,

    ROUND(
        100.0 * treatment.conversion_rate,
        3
    ) AS treatment_conversion_pct,

    ROUND(
        100.0 *
        (treatment.conversion_rate - control.conversion_rate),
        3
    ) AS absolute_conversion_uplift_pp,

    ROUND(
        100.0 *
        (
            treatment.conversion_rate
            / control.conversion_rate
            - 1
        ),
        2
    ) AS relative_conversion_uplift_pct,

    ROUND(
        control.revenue_per_user,
        2
    ) AS control_revenue_per_user,

    ROUND(
        treatment.revenue_per_user,
        2
    ) AS treatment_revenue_per_user,

    ROUND(
        treatment.revenue_per_user
        - control.revenue_per_user,
        2
    ) AS revenue_per_user_uplift

FROM control
CROSS JOIN treatment;


-- ---------------------------------------------------------------------------
-- 3. Payment decline rate
--
-- Denominator = users who submitted payment.
-- Each user is counted at most once even if they experienced multiple
-- payment declines.
-- ---------------------------------------------------------------------------

SELECT
    variant,
    SUM(submitted_payment) AS payment_submitters,
    SUM(had_payment_decline) AS users_with_payment_decline,

    ROUND(
        100.0
        * SUM(had_payment_decline)
        / SUM(submitted_payment),
        3
    ) AS payment_decline_rate_pct

FROM experiment_user_metrics

GROUP BY variant
ORDER BY variant;


-- ---------------------------------------------------------------------------
-- 4. Technical payment-error guardrail
--
-- Denominator = users who submitted payment.
--
-- The planned investigation threshold is an increase of more than
-- 0.5 percentage points in treatment versus control.
-- ---------------------------------------------------------------------------

WITH guardrail AS (
    SELECT
        variant,
        SUM(submitted_payment) AS payment_submitters,
        SUM(had_technical_payment_error) AS users_with_technical_error,

        1.0
        * SUM(had_technical_payment_error)
        / SUM(submitted_payment) AS technical_error_rate

    FROM experiment_user_metrics

    GROUP BY variant
),

control AS (
    SELECT *
    FROM guardrail
    WHERE variant = 'control'
),

treatment AS (
    SELECT *
    FROM guardrail
    WHERE variant = 'treatment'
)

SELECT
    control.payment_submitters
        AS control_payment_submitters,

    control.users_with_technical_error
        AS control_technical_errors,

    ROUND(
        100.0 * control.technical_error_rate,
        3
    ) AS control_error_rate_pct,

    treatment.payment_submitters
        AS treatment_payment_submitters,

    treatment.users_with_technical_error
        AS treatment_technical_errors,

    ROUND(
        100.0 * treatment.technical_error_rate,
        3
    ) AS treatment_error_rate_pct,

    ROUND(
        100.0 *
        (
            treatment.technical_error_rate
            - control.technical_error_rate
        ),
        3
    ) AS absolute_error_increase_pp,

    CASE
        WHEN
            100.0 *
            (
                treatment.technical_error_rate
                - control.technical_error_rate
            ) > 0.5
        THEN 'Investigate'
        ELSE 'Below investigation threshold'
    END AS guardrail_status

FROM control
CROSS JOIN treatment;


-- ---------------------------------------------------------------------------
-- 5. Core metrics by device and variant
--
-- Device was used in the stratified randomisation and is therefore an
-- important pre-planned subgroup for checking whether the treatment effect
-- is broadly consistent across mobile and desktop users.
-- ---------------------------------------------------------------------------

SELECT
    device_type,
    variant,

    COUNT(*) AS checkout_users,

    SUM(converted) AS converted_users,

    ROUND(
        100.0 * SUM(converted) / COUNT(*),
        3
    ) AS conversion_rate_pct,

    ROUND(
        SUM(total_revenue) / COUNT(*),
        2
    ) AS revenue_per_checkout_user,

    SUM(submitted_payment) AS payment_submitters,

    ROUND(
        100.0
        * SUM(had_technical_payment_error)
        / SUM(submitted_payment),
        3
    ) AS technical_error_rate_pct

FROM experiment_user_metrics

GROUP BY
    device_type,
    variant

ORDER BY
    device_type,
    variant;


-- ---------------------------------------------------------------------------
-- 6. Conversion uplift by device
-- ---------------------------------------------------------------------------

WITH device_metrics AS (
    SELECT
        device_type,
        variant,
        1.0 * SUM(converted) / COUNT(*) AS conversion_rate
    FROM experiment_user_metrics
    GROUP BY
        device_type,
        variant
),

control AS (
    SELECT
        device_type,
        conversion_rate
    FROM device_metrics
    WHERE variant = 'control'
),

treatment AS (
    SELECT
        device_type,
        conversion_rate
    FROM device_metrics
    WHERE variant = 'treatment'
)

SELECT
    control.device_type,

    ROUND(
        100.0 * control.conversion_rate,
        3
    ) AS control_conversion_pct,

    ROUND(
        100.0 * treatment.conversion_rate,
        3
    ) AS treatment_conversion_pct,

    ROUND(
        100.0 *
        (
            treatment.conversion_rate
            - control.conversion_rate
        ),
        3
    ) AS absolute_uplift_pp,

    ROUND(
        100.0 *
        (
            treatment.conversion_rate
            / control.conversion_rate
            - 1
        ),
        2
    ) AS relative_uplift_pct

FROM control

INNER JOIN treatment
    ON control.device_type = treatment.device_type

ORDER BY control.device_type;