import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
from unittest.mock import patch
from research_lab.warfighter.cli import main
from research_lab.warfighter.tests.test_verify import DEMO

class TestCli(unittest.TestCase):
    def invoke(self,*argv,input_text=None,tty=False):
        out=io.StringIO();err=io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            with patch('sys.stdin.isatty',return_value=tty),patch('builtins.input',return_value=input_text or ''):
                code=main(list(argv))
        try:
            data=json.loads(out.getvalue())
        except json.JSONDecodeError:
            data=out.getvalue()
        return code,data,err.getvalue()

    def test_status_without_workspace_and_doctor(self):
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/'no-create')
            a,report,err=self.invoke('status','--workspace',path)
            self.assertEqual(a,0)
            self.assertEqual(report['authority'],'RESEARCH_ONLY')
            self.assertFalse(Path(path).exists())
            a,doctor,_=self.invoke('doctor')
            self.assertEqual(a,0)
            self.assertEqual(doctor['external_calls'],0)

    def test_real_end_to_end_research_lifecycle(self):
        with tempfile.TemporaryDirectory() as td:
            work=str(Path(td)/'workspace');root=Path(td)/'input';root.mkdir()
            source=root/'synthetic.json';source.write_text(json.dumps(DEMO))
            args=['--workspace',work]
            a,result,err=self.invoke('simulate',str(source),'--input-root',str(root),*args)
            self.assertEqual(a,0,msg=err)
            run_id=result['run_id']
            self.assertEqual(result['authority'],'RESEARCH_ONLY')
            a,data,_=self.invoke('publish',run_id,*args)
            self.assertEqual(a,4)
            a,data,_=self.invoke('verify',run_id,*args)
            self.assertEqual(a,0)
            a,data,_=self.invoke('review',run_id,'--decision','approve','--reviewer','operator-label','--rationale','replayed model',*args,tty=False)
            self.assertEqual(a,4)
            a,data,_=self.invoke('review',run_id,'--decision','approve','--reviewer','operator-label','--rationale','replayed model',*args,tty=True,input_text=result['run_sha256'])
            self.assertEqual(a,0)
            a,pub,_=self.invoke('publish',run_id,*args)
            self.assertEqual(a,0)
            self.assertEqual(pub['authority'],'RESEARCH_ONLY')
            a,findings,_=self.invoke('findings',*args)
            self.assertEqual(len(findings['findings']),1)
            a,revoked,_=self.invoke('revoke',pub['id'],'--reason','superseded',*args)
            self.assertEqual(a,0)
            a,findings,_=self.invoke('findings',*args)
            self.assertEqual(findings['findings'],[])

    def test_no_implicit_network_and_no_xqe_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'safe.json';p.write_text(json.dumps(DEMO))
            with patch('socket.socket',side_effect=AssertionError('network prohibited')):
                a,data,err=self.invoke('simulate',str(p),'--input-root',str(root),'--workspace',str(root/'ws'))
            self.assertEqual(a,0,msg=err)
            self.assertFalse('operational_ready' in str(data))

    def test_reject_real_data_and_no_automatic_publish(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'nope.json'
            p.write_text(json.dumps(dict(DEMO,classification='PUBLIC',synthetic=False)))
            a,data,err=self.invoke('simulate',str(p),'--input-root',str(root),'--workspace',str(root/'ws'))
            self.assertEqual(a,2)
            self.assertFalse((root/'ws').exists())
