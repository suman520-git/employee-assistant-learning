import unittest
from unittest.mock import patch

from fastapi import HTTPException

from chunking import split_into_chunks
from rag import build_context
from rate_limit import check_rate_limit, request_times


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        # Give each test fresh rate-limit counters.
        request_times.clear()

    def test_chunking_keeps_overlap_and_final_words(self):
        chunks = split_into_chunks(
            "one two three four five six seven",
            chunk_size=4,
            overlap=1
        )

        self.assertEqual(
            chunks,
            [
                "one two three four",
                "four five six seven"
            ]
        )

    def test_ask_and_search_limits(self):
        # Freeze time so the test does not depend on execution speed.
        with patch("rate_limit.time.monotonic", return_value=100):
            for path, limit in [("/ask", 5), ("/search", 10)]:
                with self.subTest(path=path):
                    for _ in range(limit):
                        check_rate_limit(1, path)

                    with self.assertRaises(HTTPException) as caught:
                        check_rate_limit(1, path)

                    self.assertEqual(caught.exception.status_code, 429)
                    self.assertEqual(
                        caught.exception.detail,
                        "Rate limit exceeded. Please try again later."
                    )

    def test_requests_allowed_after_window_expires(self):
        with patch("rate_limit.time.monotonic", return_value=100):
            for _ in range(5):
                check_rate_limit(1, "/ask")

            with self.assertRaises(HTTPException):
                check_rate_limit(1, "/ask")

        # Move the clock forward without actually waiting.
        with patch("rate_limit.time.monotonic", return_value=160):
            check_rate_limit(1, "/ask")

    def test_users_have_separate_limits(self):
        with patch("rate_limit.time.monotonic", return_value=100):
            for _ in range(5):
                check_rate_limit(1, "/ask")

            # User 1 has exhausted their allowance.
            with self.assertRaises(HTTPException):
                check_rate_limit(1, "/ask")

            # User 2 still has their own allowance.
            check_rate_limit(2, "/ask")

    def test_document_upload_shares_document_limit(self):
        with patch("rate_limit.time.monotonic", return_value=100):
            for _ in range(20):
                check_rate_limit(1, "/documents")

            with self.assertRaises(HTTPException) as caught:
                check_rate_limit(1, "/documents/upload")

            self.assertEqual(caught.exception.status_code, 429)

    def test_context_labels_match_evidence(self):
        sources = [
            {
                "document_id": 42,
                "title": "Nisha Profile",
                "text": "Nisha knows Python."
            }
        ]

        graph_facts = [
            {
                "source": "Nisha",
                "relationship": "HAS_SKILL",
                "target": "python"
            }
        ]

        context = build_context(sources, graph_facts)

        self.assertIn("[D1] Document ID: 42", context)
        self.assertIn("Nisha knows Python.", context)
        self.assertIn(
            "[G1] Nisha --HAS_SKILL--> python",
            context
        )


if __name__ == "__main__":
    unittest.main()