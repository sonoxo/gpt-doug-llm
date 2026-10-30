"""Offline contract tests for bounded, non-propagating public satellite integration."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.satellite_readonly import bridge

ROW = {"NORAD_CAT_ID":25544,"OBJECT_NAME":"ISS (ZARYA)","EPOCH":"2026-10-21T12:00:00Z"}
class Response(io.BytesIO):
    def geturl(self): return bridge.CATALOG_URL

class Contract(unittest.TestCase):
    def test_public_provenance(self):
        raw=json.dumps([ROW]).encode()
        data=bridge.decode_catalog(raw,source="fixture")
        self.assertEqual(data["source_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(data["satellites"],[{"norad_id":25544,"name":"ISS (ZARYA)","epoch":ROW["EPOCH"]}])
        self.assertFalse(data["spacecraft_commands_enabled"])

    def test_invalid_records_fail_closed(self):
        for payload in ({},[ROW,ROW],[dict(ROW,NORAD_CAT_ID=True)]):
            with self.assertRaises(bridge.BridgeError):
                bridge.decode_catalog(json.dumps(payload).encode(),source="fixture")

    def test_catalog_is_single_explicit_get(self):
        calls=[]
        def opener(request,timeout):
            calls.append((request.full_url,request.get_method(),timeout))
            return Response(json.dumps([ROW]).encode())
        bridge.public_catalog(opener=opener)
        self.assertEqual(calls,[(bridge.CATALOG_URL,"GET",8.0)])

    def test_redirect_handler_blocks(self):
        with self.assertRaises(bridge.BridgeError):
            bridge.NoRedirect().redirect_request(None,None,302,"redirect",{},"https://example.org")

    def test_offline_no_unrequested_fetch(self):
        with patch("urllib.request.urlopen",side_effect=AssertionError("network")):
            with patch("sys.stdout",new_callable=io.StringIO):
                self.assertEqual(bridge.main(["catalog"]),0)

    def test_replica_manifest_never_deploys(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"model.gguf").write_bytes(b"model")
            report=bridge.replica_plan(root,"model.gguf")
            self.assertFalse(report["self_propagation_enabled"])
            self.assertFalse(report["deployment_enabled"])
            self.assertEqual(report["sha256"],hashlib.sha256(b"model").hexdigest())
            for name in ("../model.gguf","/tmp/model.gguf","other.json"):
                with self.assertRaises(bridge.BridgeError): bridge.approved_model(root,name)
            (root/"link.gguf").symlink_to(root/"model.gguf")
            with self.assertRaises(bridge.BridgeError): bridge.approved_model(root,"link.gguf")

    def test_missing_rea_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"model.gguf").write_bytes(b"x")
            with patch("shutil.which",return_value=None):
                with self.assertRaises(bridge.BridgeError): bridge.rea_model_inspect(root,"model.gguf")

if __name__=="__main__": unittest.main()
