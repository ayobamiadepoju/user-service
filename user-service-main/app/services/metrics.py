from prometheus_client import Counter, Histogram, Gauge
import time

user_registrations_total = Counter(
    'user_registrations_total',
    'Total number of user registrations'
)

login_attempts_total = Counter(
    'login_attempts_total',
    'Total number of login attempts',
    ['status']
)

token_refresh_total = Counter(
    'token_refresh_total',
    'Total number of token refresh requests',
    ['status']
)

cache_operations_total = Counter(
    'cache_operations_total',
    'Total number of cache operations',
    ['operation', 'status']
)

active_users_gauge = Gauge(
    'active_users_total',
    'Total number of registered users'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation']
)

cache_hit_rate = Counter(
    'cache_hit_rate_total',
    'Cache hit/miss counter',
    ['result']
)