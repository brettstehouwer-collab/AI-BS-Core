"""Read-only saved-journal/export comparison on a new copied creator fixture."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qualify_rtx_creator import ROOT, SDK, VARIANTS, copy_tree, load, pin, read, tree, write, write_json, need, tool_pins


def main():
    source = VARIANTS/'Creator_LH_20261111_v02'
    output = VARIANTS/'Creator_Export_Diagnostic_20261111_v01'
    need(not output.exists(), 'Diagnostic output must be new')
    tools, before = tool_pins(), tree(source/'project')
    output.mkdir()
    copy_tree(source/'project', output/'project')
    before_journal = pin(output/'project/chapter.aiba')
    qt = ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages'
    sys.path[:0] = [str(ROOT), str(qt)]
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['PATH'] = str(qt/'PyQt6/Qt6/bin')+';C:\\Windows\\System32'
    dll_scope = os.add_dll_directory(str(qt/'PyQt6/Qt6/bin'))
    from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication, QEvent
    from PyQt6.QtWidgets import QApplication
    from PyQt6 import sip
    from native_studio.game_engine.content_view import ContentView

    class NoAI(QObject):
        inventory_ready = pyqtSignal(object, object)
        proposal_ready = pyqtSignal(str, str)
        failed = pyqtSignal(str, str)
        state_changed = pyqtSignal(str)
        busy = False
        def cancel(self): pass
        def refresh_models(self): raise RuntimeError('No AI in diagnostic')
        def generate(self, *args): raise RuntimeError('No AI in diagnostic')

    app = QApplication([])
    view = ContentView(SDK/'aibs_content_host.exe', asset_cooker=SDK/'aibs_assetc.exe', ai_client=NoAI())
    def spin(check, label):
        deadline = time.monotonic()+35
        while not check():
            need(time.monotonic()<deadline, label+' timed out')
            app.processEvents(); time.sleep(.005)
    owner = None
    try:
        view.open_project(output/'project')
        spin(lambda: view.loaded and not view.busy and not view.client.pending_count, 'Read saved journal')
        from qualify_rtx_creator import OwnedProcess
        owner = OwnedProcess(view.client.process_id)
        rows = {row.uuid:{'type':row.type_id,'name':row.name,'fields':dict(row.fields)} for row in view.rows}
        need(rows == load(source/'baseline-rows.json'), 'Saved journal differs from complete baseline fields')
        probe = output/'viewport'; probe.mkdir()
        view.open_viewport(probe_directory=probe)
        spin(lambda: not view.busy and view.viewport.state=='closed' and not view.client.pending_count and
             view.viewport.dependency_process_id==0 and (probe/'viewport.json').is_file(), 'Read-only export')
        snapshot = view._content_snapshot
        write(output/'exported.aibd', snapshot.payload)
        old = read(output/'project/opening.aibd')
        new = snapshot.payload
        report = {'status':'READ_ONLY_DIAGNOSTIC_PASS', 'all_baseline_typed_rows_equal':True,
                  'copied_seed_export':pin(output/'project/opening.aibd'),
                  'actual_saved_journal_export':pin(output/'exported.aibd'),
                  'export_fingerprint':snapshot.fingerprint,'content_revision':snapshot.content_revision,
                  'byte_lengths':[len(old),len(new)],
                  'first_differences':[i for i,(a,b) in enumerate(zip(old,new)) if a!=b][:32],
                  'journal_unchanged':pin(output/'project/chapter.aiba')==before_journal,
                  'input_fixture_unchanged':tree(source/'project')==before,
                  'observation':'Static copied opening.aibd and current saved-journal export are separate artifacts'}
        need(report['journal_unchanged'] and report['input_fixture_unchanged'], 'Read-only preservation failed')
        need(hashlib.sha256(new).hexdigest()==snapshot.fingerprint, 'Export hash/fingerprint mismatch')
        view.close_project(discard=False)
        spin(lambda:view.client.state=='closed' and view._children_closed(), 'Normal close')
        report['host']=owner.finish()
        need(tool_pins()==tools, 'Native tools changed')
        write_json(output/'diagnostic.json',report)
        print(json.dumps(report),flush=True)
    finally:
        if view.client.state=='closed' and view._children_closed():
            view.close(); QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); sip.delete(view)
            app.processEvents()


if __name__=='__main__':
    main()
