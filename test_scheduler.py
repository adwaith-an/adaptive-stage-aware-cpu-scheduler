"""Unit tests for scheduler.py. Run with: python -m unittest test_scheduler.py"""

import unittest

from scheduler import simulate, compare_algorithms


TASKS = [
    {"name": "A", "arrival": 0, "burst": 5, "priority": 2},
    {"name": "B", "arrival": 1, "burst": 3, "priority": 1},
    {"name": "C", "arrival": 2, "burst": 1, "priority": 3},
]


class SchedulerTests(unittest.TestCase):
    def test_all_algorithms_return_results(self):
        results = compare_algorithms(TASKS)
        self.assertEqual(set(results), {"FCFS", "SJF", "RR", "PRIORITY"})

        for result in results.values():
            self.assertEqual(len(result["tasks"]), 3)
            self.assertGreaterEqual(result["average_waiting"], 0)
            self.assertGreaterEqual(result["average_turnaround"], 0)
            self.assertGreaterEqual(result["average_response"], 0)

    def test_fcfs_metrics(self):
        result = simulate(TASKS, "FCFS")
        self.assertEqual(result["average_waiting"], 3.33)
        self.assertEqual(result["average_turnaround"], 6.33)
        self.assertEqual(result["average_response"], 3.33)

    def test_round_robin_quantum(self):
        result = simulate(TASKS, "RR", quantum=2)
        self.assertEqual(result["policy"], "RR")
        self.assertEqual(result["quantum"], 2)

    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            simulate(TASKS, "UNKNOWN")

    def test_invalid_burst(self):
        invalid_tasks = [
            {"name": "A", "arrival": 0, "burst": 0, "priority": 1}
        ]
        with self.assertRaises(ValueError):
            simulate(invalid_tasks, "FCFS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
