"""The Anthropic client takes the FinSync-specific key and the public API address when that key is set."""

import os
import unittest
from unittest import mock

from finsync.categorization.llm import FINSYNC_KEY_VARIABLE, PUBLIC_API_URL, AnthropicClient


class FinSyncKeyTest(unittest.TestCase):
    def test_own_key_goes_to_the_public_api(self):
        environment = {FINSYNC_KEY_VARIABLE: "test-key", "ANTHROPIC_BASE_URL": "http://proxy.invalid"}
        with mock.patch.dict(os.environ, environment):
            client = AnthropicClient()
        self.assertEqual(client._client.api_key, "test-key")
        self.assertEqual(str(client._client.base_url).rstrip("/"), PUBLIC_API_URL)


if __name__ == "__main__":
    unittest.main()
