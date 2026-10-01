# Plateful Monitoring & Observability

This guide outlines the critical metrics, logs, and alerts needed to monitor Plateful in a production environment.

## 1. Application Logging

Plateful uses structured JSON logging in production to facilitate querying and analysis.

### What is Logged:
- **HTTP Requests**: Method, path, status code, processing time (`duration_ms`), and `request_id`.
- **Errors**: Domain errors (e.g., validation failures, budget constraints) are logged at the `INFO` or `WARNING` level. Unhandled exceptions are logged at the `ERROR` level with stack traces.
- **AI Integrations**: Gemini API call durations, fallback triggers (when deterministic mode activates), and structured output validation failures.

### What is NOT Logged:
- Passwords (plaintext or hashed).
- Bearer tokens (JWTs) or password reset/verification tokens.
- Raw SQL queries with sensitive user data.

### Log Aggregation:
Ensure your hosting provider (e.g., Render) exports logs to a centralized aggregator like Datadog, New Relic, or AWS CloudWatch. Set up parsers for the JSON structured logs to extract the `request_id`, `status_code`, and `duration_ms`.

## 2. Key Metrics to Monitor

Set up dashboards for the following critical metrics:

### Traffic & Performance
- **Request Volume**: Total requests per minute (RPM).
- **Latency**: P50, P90, and P99 response times for key endpoints (especially `/api/v1/plans/generate`).
- **Error Rates**: Percentage of 4xx and 5xx responses.

### Business Metrics
- **Plan Generation Rate**: Number of successful plans generated per hour.
- **AI Fallback Rate**: The ratio of plans generated with `ai_mode=deterministic` versus `ai_mode=gemini`. A spike indicates Gemini API issues or quota exhaustion.
- **Recipe Swap Rate**: Frequency of users swapping meals in generated plans (indicates plan quality/satisfaction).

### Database & Infrastructure
- **Connection Pool**: Number of active and idle database connections.
- **Database CPU & Memory**: Resource utilization of the PostgreSQL instance.
- **Rate Limiting**: Number of 429 Too Many Requests responses served.

## 3. Alerts & Thresholds

Configure automated alerts for your on-call team based on these thresholds:

| Alert Name | Condition | Severity | Action |
|---|---|---|---|
| **High Error Rate** | 5xx responses > 5% for 5 minutes | Critical | Check backend logs for unhandled exceptions or database connection failures. |
| **API Latency Spike** | P90 latency > 3s for 10 minutes | Warning | Check Gemini API latency or database query performance. |
| **AI Degradation** | AI Fallback Rate > 20% for 15 minutes | Warning | Check Google Cloud status page and Gemini API quotas. |
| **Database Load** | DB CPU > 80% for 10 minutes | Critical | Investigate slow queries, active connections, or scale up the database. |
| **Health Check Failure** | `/health` endpoint fails or times out | Critical | Verify backend service health and database connectivity. |

## 4. Tracing Requests

Every request is assigned a unique UUID (`request_id`). This ID is included in the JSON logs and returned in the HTTP response headers as `X-Request-ID`. If a user reports an issue, ask them for the `request_id` or the exact timestamp to trace the complete lifecycle of their request through the logs.
