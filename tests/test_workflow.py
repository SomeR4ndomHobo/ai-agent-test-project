import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api_worker

class AdapterTests(unittest.TestCase):
    def test_each_engine_calls_original_entrypoint_without_changing_report(self):
        for engine, (module, function) in api_worker.ENGINES.items():
            run = Mock(return_value="Original output")
            original = types.SimpleNamespace(**{function:run})
            with tempfile.TemporaryDirectory() as temp:
                work=Path(temp)
                lines=[{"text":"CARD", "confidence":.9}]
                (work/"request.json").write_text(json.dumps({"engine":engine,"lines":lines}))
                with patch.object(api_worker.importlib,"import_module",return_value=original) as load:
                    self.assertEqual(api_worker.execute("research",work),{"report":"Original output"})
                load.assert_called_once_with(module)
                run.assert_called_once_with(lines,"card")

    def test_ocr_calls_original_entrypoint(self):
        result={"raw_ocr":[{"text":"CARD","confidence":.9}]}
        read=Mock(return_value=result)
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            (work/"request.json").write_text("{}")
            with patch.object(api_worker.importlib,"import_module",return_value=types.SimpleNamespace(identify_card=read)) as load:
                self.assertEqual(api_worker.execute("ocr",work),result)
            load.assert_called_once_with("ocr")
            read.assert_called_once_with(str(work/"image.png"))

if __name__ == "__main__": unittest.main()
