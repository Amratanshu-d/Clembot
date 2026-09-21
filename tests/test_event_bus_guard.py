"""Task 8 — Event Bus: duplicate-subscription guard and thread-safety tests."""
import threading
import time
import unittest

from app.core.event_bus import EventBus


class TestEventBusGuard(unittest.TestCase):
    # ------------------------------------------------------------------
    # Duplicate subscription prevention
    # ------------------------------------------------------------------

    def test_subscribe_same_handler_twice_only_fires_once(self):
        bus = EventBus()
        counter = {"n": 0}

        def handler(_):
            counter["n"] += 1

        bus.subscribe("ping", handler)
        bus.subscribe("ping", handler)  # duplicate — should be silently ignored

        bus.emit("ping")
        self.assertEqual(counter["n"], 1, "Duplicate handler must fire exactly once")

    def test_subscribe_different_handlers_both_fire(self):
        bus = EventBus()
        log = []

        bus.subscribe("evt", lambda _: log.append("A"))
        bus.subscribe("evt", lambda _: log.append("B"))
        bus.emit("evt")

        self.assertEqual(sorted(log), ["A", "B"])

    def test_unsubscribe_removes_handler(self):
        bus = EventBus()
        counter = {"n": 0}

        def handler(_):
            counter["n"] += 1

        bus.subscribe("x", handler)
        bus.unsubscribe("x", handler)
        bus.emit("x")
        self.assertEqual(counter["n"], 0, "Unsubscribed handler must not fire")

    def test_unsubscribe_nonexistent_handler_is_noop(self):
        """Calling unsubscribe for a handler that was never subscribed must not raise."""
        bus = EventBus()
        bus.unsubscribe("ghost", lambda _: None)  # should not raise

    def test_emit_unknown_event_is_noop(self):
        bus = EventBus()
        bus.emit("no_one_listening")  # must not raise

    # ------------------------------------------------------------------
    # Thread-safety
    # ------------------------------------------------------------------

    def test_concurrent_subscribe_does_not_duplicate(self):
        """Concurrent subscribe of the same handler from multiple threads must register it once."""
        bus = EventBus()
        counter = {"n": 0}

        def handler(_):
            counter["n"] += 1

        def register():
            for _ in range(50):
                bus.subscribe("concurrent", handler)

        threads = [threading.Thread(target=register) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        bus.emit("concurrent")
        self.assertEqual(counter["n"], 1, "Handler registered from multiple threads must fire once")

    def test_concurrent_emit_does_not_raise(self):
        """Multiple threads emitting simultaneously must not crash."""
        bus = EventBus()
        results = []

        def handler(data):
            results.append(data)

        bus.subscribe("storm", handler)

        def emit_many():
            for i in range(20):
                bus.emit("storm", i)

        threads = [threading.Thread(target=emit_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 100)  # 5 threads × 20 emits

    # ------------------------------------------------------------------
    # Resilience: subscriber exception must not stop other subscribers
    # ------------------------------------------------------------------

    def test_failing_subscriber_does_not_block_others(self):
        bus = EventBus()
        fired = {"ok": False}

        def bad_handler(_):
            raise RuntimeError("I explode!")

        def good_handler(_):
            fired["ok"] = True

        bus.subscribe("boom", bad_handler)
        bus.subscribe("boom", good_handler)
        bus.emit("boom")  # must not propagate RuntimeError

        self.assertTrue(fired["ok"], "Good handler must still fire after bad handler crashes")

    # ------------------------------------------------------------------
    # Idempotency: emitting the same event twice fires handlers twice
    # (dedup is the orchestrator's job, not the bus)
    # ------------------------------------------------------------------

    def test_emit_twice_fires_twice(self):
        bus = EventBus()
        counter = {"n": 0}
        bus.subscribe("tick", lambda _: counter.__setitem__("n", counter["n"] + 1))
        bus.emit("tick")
        bus.emit("tick")
        self.assertEqual(counter["n"], 2)


if __name__ == "__main__":
    unittest.main()
