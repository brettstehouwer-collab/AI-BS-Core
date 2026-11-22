from pathlib import Path
root=Path(r'C:\AI-BS');work=Path(r'C:\Users\footb\Documents\Codex\2026-10-22\c-ai-bs\work')
old=(work/'test_planning_client_v45.cjs').read_text(encoding='utf-8')
old=old.replace("__dirname+'/planning_controls_v45_checkpoint.txt'","__dirname+'/proposal_ui_v47_checkpoint.txt'")
old=old.replace("'refreshPlans','morePlans'","'refreshPlans','morePlans','reviewProposal','generateProposal','inspectProposal','recoverProposal','cancelProposal'")
marker="fs.writeFileSync(cp+'/client_'+phase+'.json'"
assert old.count(marker)==1
old=old.replace(marker,(root/'workspace/proposal_client_cases_v47.txt').read_text(encoding='utf-8')+'\n'+marker)
client_path=root/'workspace/test_proposal_client_v47.cjs'
if client_path.exists():assert client_path.read_text(encoding='utf-8')==old
else:
    with client_path.open('x',encoding='utf-8') as out:out.write(old)
print('Created proposal client runner with retained41planning cases and new proposal cases')
view=(work/'test_planning_view_v45.cjs').read_text(encoding='utf-8')
view=view.replace("__dirname+'/planning_controls_v45_checkpoint.txt'","__dirname+'/proposal_ui_v47_checkpoint.txt'")
marker="fs.writeFileSync(cp+'/view_'+phase+'.json'"
assert view.count(marker)==1
view=view.replace(marker,(root/'workspace/proposal_view_cases_v47.txt').read_text(encoding='utf-8')+'\n'+marker)
view_path=root/'workspace/test_proposal_view_v47.cjs'
if view_path.exists():assert view_path.read_text(encoding='utf-8')==view
else:
    with view_path.open('x',encoding='utf-8') as out:out.write(view)
