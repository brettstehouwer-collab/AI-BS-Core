from pathlib import Path
root=Path(r'C:\AI-BS');w=root/'workspace'
for kind,marker in [('client',"fs.writeFileSync(cp+'/client_'+phase+'.json'"),('view',"fs.writeFileSync(cp+'/view_'+phase+'.json'")]:
    source=(w/('test_proposal_'+kind+'_v47.cjs')).read_text(encoding='utf-8').replace('proposal_ui_v47_checkpoint.txt','proposal_history_v48_checkpoint.txt')
    if kind=='client':source=source.replace("'inspectProposal','recoverProposal','cancelProposal'","'inspectProposal','recoverProposal','cancelProposal','refreshProposals','moreProposals'",1)
    assert source.count(marker)==1
    source=source.replace(marker,(w/('proposal_history_'+kind+'_cases_v48.txt')).read_text(encoding='utf-8')+'\n'+marker)
    with (w/('test_proposal_history_'+kind+'_v48.cjs')).open('x',encoding='utf-8') as out:out.write(source)
print('Created client/view history runners preserving prior70/26cases')
