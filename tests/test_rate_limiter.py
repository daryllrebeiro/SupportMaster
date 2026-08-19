import unittest
import time
from supportmaster.rate_limiter import TenantRateLimiter


class RateLimiterTests(unittest.TestCase):
    def test_token_bucket_limits_and_refills(self) -> None:
        # 2 tokens capacity, refills at 10 tokens/sec
        limiter = TenantRateLimiter(default_capacity=2.0, default_fill_rate=10.0)

        # Consume initial capacity
        self.assertTrue(limiter.consume("tenant-a"))
        self.assertTrue(limiter.consume("tenant-a"))
        # Third attempt fails (exhausted)
        self.assertFalse(limiter.consume("tenant-a"))

        # Different tenant has independent bucket
        self.assertTrue(limiter.consume("tenant-b"))

        # Sleep to refill
        time.sleep(0.2)
        # Should now be refilled and allowed
        self.assertTrue(limiter.consume("tenant-a"))


if __name__ == "__main__":
    unittest.main()
