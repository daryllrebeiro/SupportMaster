# Staging reproduction

Run report generation, cancel the request during database streaming, and
repeat until the connection pool reaches its limit. v4.8.0 reproduces the
pool exhaustion; v4.7.9 does not.
