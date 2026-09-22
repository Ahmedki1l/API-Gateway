"""Behavioral coverage for vehicle-registry alert auto-resolution."""
import base64
import os
import unittest
from unittest.mock import patch

with patch.dict(os.environ, {
    "CAMERAS_ENCRYPTION_KEY": base64.urlsafe_b64encode(bytes(32)).decode(),
    "CAMERAS_INTERNAL_TOKEN": "unused",
}, clear=False):
    from app.services.alert_auto_resolve import _clears_alert


class AlertAutoResolveTests(unittest.TestCase):
    def test_registry_updates_clear_only_supported_alerts(self):
        self.assertTrue(_clears_alert("vehicle_intrusion", "ceo", "ceo", False))
        self.assertTrue(_clears_alert("named_slot_violation", "ceo", "ceo", False))
        self.assertTrue(_clears_alert("unknown_vehicle", "", "", True))
        self.assertFalse(_clears_alert("vehicle_intrusion", "visitor", "ceo", False))
        self.assertFalse(_clears_alert("unknown_vehicle", "", "", False))
        self.assertFalse(_clears_alert("overstay", "ceo", "ceo", True))
