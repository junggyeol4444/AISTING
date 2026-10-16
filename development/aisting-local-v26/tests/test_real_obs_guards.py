"""Guard-only tests; not an OBS server test or broadcaster validation."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload' / 'src'))
from ai_broadcaster.original_plan_obs import OfficialObsWebsocket, ObsConnectionError


class RealObsGuards(unittest.TestCase):
    def test_no_broadcast_by_construct_or_status(self):
        obs = OfficialObsWebsocket('not-saved-test-only')
        self.assertIsNone(obs._client)
        self.assertRaises(ObsConnectionError, obs.status)
        self.assertRaises(PermissionError, obs.start_stream)
        self.assertRaises(PermissionError, obs.stop_stream)

    def test_requires_real_auth_and_valid_port(self):
        self.assertRaises(ValueError, OfficialObsWebsocket, '')
        self.assertRaises(ValueError, OfficialObsWebsocket, 'key', port=0)
        self.assertRaises(ValueError, OfficialObsWebsocket, 'key', port=65536)
        # Existing OBS connection package absence is an actual missing
        # dependency, not a synthetic success. Do not call connect here.

    def test_start_requires_separate_explicit_authorization(self):
        old = os.environ.get('AISTING_APPROVED_OBS_OUTGOING')
        try:
            os.environ.pop('AISTING_APPROVED_OBS_OUTGOING', None)
            obs = OfficialObsWebsocket('not-saved-test-only')
            with self.assertRaises(PermissionError):
                obs.start_stream(operator_confirmed=True)
        finally:
            if old is not None:
                os.environ['AISTING_APPROVED_OBS_OUTGOING'] = old
            else:
                os.environ.pop('AISTING_APPROVED_OBS_OUTGOING', None)


if __name__ == '__main__':
    unittest.main()
