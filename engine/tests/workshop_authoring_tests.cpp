#include <aibs/content_authoring.hpp>
#include <aibs/creator_payload.hpp>
#include <aibs/gameplay_codec.hpp>
#include <aibs/opening_workshop.hpp>
#include <aibs/warm_opening.hpp>
#include <algorithm>
#include <filesystem>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {
int checks=0;
void check(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
template<class F>void rejects(F operation,const char* message){bool rejected=false;try{operation();}catch(const std::invalid_argument&){rejected=true;}check(rejected,message);}
ContentEditRequest request(const ContentAuthoringHost& host,std::string id,std::vector<ContentEdit> edits){const auto s=host.snapshot();return {std::move(id),s->revision,s->content.fingerprint(),"Workshop authoring contract",std::move(edits)};}
ContentAuthoringResult apply(ContentAuthoringHost& host,std::string id,std::vector<ContentEdit> edits){const auto q=request(host,std::move(id),std::move(edits));return host.apply(host.snapshot()->scope,q);}
const ContentAuthoringRow& row(const std::vector<ContentAuthoringRow>& rows,const std::string& id){const auto found=std::find_if(rows.begin(),rows.end(),[&](const auto& r){return r.entity_id==id;});if(found==rows.end())throw std::runtime_error("Missing observation row");return *found;}
std::vector<ContentEdit> attach(const FirstBootContentDefinition& target,const FirstBootContentDefinition& source,const OpeningWorkshopBinding& binding){
 std::vector<ContentEdit> edits;
 for(const auto& id:binding.fixtures){const auto found=std::find_if(source.fixtures.begin(),source.fixtures.end(),[&](const auto& f){return f.object.persistent_id==id;});check(found!=source.fixtures.end(),"Factory binding has no fixture");auto fixture=*found;fixture.role=FixtureRole::legacy;edits.push_back(ContentCreateFixture{fixture});edits.push_back(ContentSetField{id,"workshop_role",true});}
 edits.push_back(ContentSetField{target.definition_id,"hint.workshop.binding",encode_opening_workshop_binding(binding)});return edits;
}
void history(ContentAuthoringHost& host,bool redo,const char* id){const auto s=host.snapshot();const auto result=host.travel(s->scope,{id,s->revision,s->content.fingerprint(),redo});check(result.status==(redo?ContentAuthoringStatus::redone:ContentAuthoringStatus::undone),"Workshop history failed");}
void unchanged_rejection(ContentAuthoringHost& host,const std::string& id,std::vector<ContentEdit> edits,const char* why){const auto s=host.snapshot();const auto bytes=first_boot_content_encode(s->content);const auto result=apply(host,id,std::move(edits));check(result.status==ContentAuthoringStatus::rejected,why);check(!result.message.empty(),"Rejection lost diagnostics");check(host.snapshot()==s&&first_boot_content_encode(host.snapshot()->content)==bytes,"Failed workshop edit changed exact logical head");}
}
int main(){try{
 CreatorSession source(first_boot_schema(),"workshop-author-proof","main");check(seed_first_boot(source).ok,"Seed source");
 const auto base=make_warm_opening_draft(source,{});const auto workshop=make_warm_workshop_draft(source,{});
 const auto binding=first_boot_content_workshop_binding(workshop.definition);check(binding.has_value(),"Factory workshop binding missing");
 const auto original=FirstBootContent::create(base.definition);ContentAuthoringHost host(original,"workshop-author-proof","main");
 const auto legacy_id=base.definition.fixtures.front().object.persistent_id;
 auto rows=content_authoring_rows(original);check(row(rows,legacy_id).fields.size()==20&&!row(rows,legacy_id).fields.contains("workshop_role"),"Legacy modern observation shape changed");
 check(std::get<std::string>(row(rows,base.definition.definition_id).fields.at("hint.workshop.binding")).empty(),"Unbound workshop descriptor must be empty");
 const auto virtual_request=request(host,"virtual-false",{ContentSetField{legacy_id,"name",std::string("Legacy renamed without role")},ContentSetField{legacy_id,"workshop_role",false}});
 const auto virtual_preview=host.preview(host.snapshot()->scope,virtual_request);check(virtual_preview.status==ContentAuthoringStatus::prepared,"Legacy fixture rejected virtual false role");
 check(host.snapshot()->content.fingerprint()==original.fingerprint(),"Virtual role preview published state");
 check(host.apply(virtual_preview.change).status==ContentAuthoringStatus::applied,"Virtual false role apply");
 rows=content_authoring_rows(host.snapshot()->content);check(row(rows,legacy_id).fields.size()==20&&!row(rows,legacy_id).fields.contains("workshop_role"),"False role widened legacy observation");
 // CreateFixture keeps exact17-field typed payload. Direct new role cannot be
 // silently discarded by that existing codec or bypass grouped role validation.
 auto sample=workshop.definition.fixtures.back();sample.object.persistent_id=new_uuid();sample.role=FixtureRole::legacy;
 auto wire_request=request(host,"wire17",{ContentCreateFixture{sample}});const auto encoded=encode_content_edit(wire_request);
 creator_payload::detail::Reader reader{encoded};check(reader.number(2)==1,"Legacy fixture request version changed");(void)reader.text(true);(void)reader.number(8);(void)reader.text(true);(void)reader.text();check(reader.number(4)==1&&reader.number(1)==1,"Legacy fixture tag changed");const auto bytes=reader.number(4);const auto record=gameplay_codec::decode_component(reader.data.subspan(reader.offset,static_cast<std::size_t>(bytes)));check(record.fields.size()==17&&!record.fields.contains("workshop_role"),"CreateFixture was widened beyond17fields");check(encode_content_edit(decode_content_edit(encoded))==encoded,"Legacy fixture wire roundtrip changed bytes");
 sample.role=FixtureRole::workshop;rejects([&]{(void)encode_content_edit(request(host,"bad-create-role",{ContentCreateFixture{sample}}));},"Direct nonlegacy role encoded without its flag");
 unchanged_rejection(host,"bad-create-role-apply",{ContentCreateFixture{sample}},"Direct nonlegacy create accepted");
 auto group=attach(host.snapshot()->content.definition(),workshop.definition,*binding);
 const auto before=host.snapshot();const auto prepared=host.preview(before->scope,request(host,"attach",group));
 check(prepared.status==ContentAuthoringStatus::prepared&&prepared.change,"Atomic workshop group preview failed");check(host.snapshot()==before,"Workshop preview was not private");
 check(host.apply(prepared.change).status==ContentAuthoringStatus::applied,"Atomic workshop apply failed");
 const auto attached=host.snapshot()->content;check(attached.definition().format_version==3,"Workshop document downgraded");check(first_boot_content_workshop_binding(attached.definition())==binding,"Applied workshop binding changed");
 rows=content_authoring_rows(attached);
 for(const auto& id:binding->fixtures){const auto& observed=row(rows,id);check(observed.fields.size()==21&&std::get<bool>(observed.fields.at("workshop_role")),"Workshop observation requires exactly one appended true field");check(std::get<std::string>(observed.fields.at("inspection_text")).empty(),"Workshop acquired a read panel");}
 const auto selected=binding->fixtures.front();
 check(apply(host,"geometry-retains-role",{ContentSetField{selected,"name",std::string("Owned workshop probe renamed")}}).status==ContentAuthoringStatus::applied,"Normal fixture edit failed");
 const auto& edited=host.snapshot()->content.definition();const auto fixture=std::find_if(edited.fixtures.begin(),edited.fixtures.end(),[&](const auto& f){return f.object.persistent_id==selected;});check(fixture!=edited.fixtures.end()&&fixture->role==FixtureRole::workshop,"17-field geometry reconstruction dropped workshop role");
 unchanged_rejection(host,"bound-delete",{ContentEraseFixture{selected}},"Bound station delete accepted");
 unchanged_rejection(host,"bound-demote",{ContentSetField{selected,"workshop_role",false}},"Bound station demotion accepted");
 unchanged_rejection(host,"inspection-conflict",{ContentSetField{selected,"inspection_text",std::string("Not an inspection")},ContentSetField{selected,"inspection_source",std::string("Owned authoring test")},ContentSetField{selected,"inspection_action",std::string("read")}},"Workshop inspection ambiguity accepted");
 unchanged_rejection(host,"oversize-binding",{ContentSetField{edited.definition_id,"hint.workshop.binding",std::string(257,'x')}},"Oversized binding accepted");
 unchanged_rejection(host,"wrong-type-role",{ContentSetField{selected,"workshop_role",std::string("true")}},"Nonboolean role accepted");
 auto missing=*binding;missing.fixtures[0]=new_uuid();unchanged_rejection(host,"missing-rebind",{ContentSetField{edited.definition_id,"hint.workshop.binding",encode_opening_workshop_binding(missing)}},"Binding to missing station accepted");
 // Rebind the probe atomically to one freshly created owned fixture; the old
 // UUID remains known but becomes a normal fixture, without stale dependency.
 // Move retired geometry clear: coincident opaque bounds made visibility depend
 // on UUID sort order, so an old prop could occlude every replacement approach.
 auto replacement=*fixture;replacement.object.persistent_id=new_uuid();replacement.role=FixtureRole::legacy;
 const auto retired_y=static_cast<double>(replacement.object.center.y+.8f);
 auto rebound=*binding;rebound.fixtures[0]=replacement.object.persistent_id;
 const auto rebind_result=apply(host,"rebind",{ContentCreateFixture{replacement},ContentSetField{selected,"y",retired_y},ContentSetField{selected,"workshop_role",false},ContentSetField{replacement.object.persistent_id,"workshop_role",true},ContentSetField{edited.definition_id,"hint.workshop.binding",encode_opening_workshop_binding(rebound)}});
 if(rebind_result.status!=ContentAuthoringStatus::applied)std::cerr<<rebind_result.message<<'\n';
 check(rebind_result.status==ContentAuthoringStatus::applied,"Atomic station rebind failed");
 const auto rebind_rows=content_authoring_rows(host.snapshot()->content);const auto& retired=row(rebind_rows,selected);
 check(!retired.fields.contains("workshop_role")&&std::get<double>(retired.fields.at("y"))==retired_y,"Retired geometry was not demoted and moved clear atomically");
 check(first_boot_content_workshop_binding(host.snapshot()->content.definition())==std::optional<OpeningWorkshopBinding>(rebound),"Rebind lost exact ownership");
 history(host,false,"undo-rebind");check(first_boot_content_workshop_binding(host.snapshot()->content.definition())==binding,"Undo did not restore old binding");
 history(host,true,"redo-rebind");check(first_boot_content_workshop_binding(host.snapshot()->content.definition())==std::optional<OpeningWorkshopBinding>(rebound),"Redo did not restore new binding");
 const auto saved_fingerprint=host.snapshot()->content.fingerprint();
 const auto directory=std::filesystem::temp_directory_path()/("aibs-workshop-author-"+new_uuid());std::filesystem::create_directory(directory);const auto file=directory/"chapter.aiba";
 check(host.save(file).status==ContentAuthoringStatus::saved,"Workshop authoring save failed");
 auto reopened=ContentAuthoringHost::open(file,"workshop-author-proof","main");check(reopened.snapshot()->content.fingerprint()==saved_fingerprint,"Reopen changed workshop content");check(first_boot_content_workshop_binding(reopened.snapshot()->content.definition())==std::optional<OpeningWorkshopBinding>(rebound),"Reopen lost exact binding");
 history(reopened,false,"undo-after-reopen");check(first_boot_content_workshop_binding(reopened.snapshot()->content.definition())==binding,"Saved Undo lost binding");history(reopened,true,"redo-after-reopen");
 std::vector<ContentEdit> remove{ContentSetField{reopened.snapshot()->content.definition().definition_id,"hint.workshop.binding",std::string{}}};for(const auto& id:rebound.fixtures)remove.push_back(ContentSetField{id,"workshop_role",false});
 check(apply(reopened,"remove-workflow",remove).status==ContentAuthoringStatus::applied,"Atomic workflow removal failed");check(!first_boot_content_workshop_binding(reopened.snapshot()->content.definition()),"Removed binding retained");check(!reopened.snapshot()->content.definition().hints.contains("workshop.binding"),"Empty binding consumed a hint slot");check(reopened.snapshot()->content.definition().format_version==3,"Removal downgraded document format");
 rows=content_authoring_rows(reopened.snapshot()->content);for(const auto& id:rebound.fixtures)check(row(rows,id).fields.size()==20&&!row(rows,id).fields.contains("workshop_role"),"Demoted fixture retained workshop-only observation field");
 check(reopened.save(file).status==ContentAuthoringStatus::saved,"Save removed workflow");auto removed=ContentAuthoringHost::open(file,"workshop-author-proof","main");check(!first_boot_content_workshop_binding(removed.snapshot()->content.definition()),"Removed workflow resurrected after restart");history(removed,false,"undo-removal-after-open");check(first_boot_content_workshop_binding(removed.snapshot()->content.definition())==std::optional<OpeningWorkshopBinding>(rebound),"History lost removed workflow after reopening");
 // False is a virtual legacy role in old documents too; true may not silently
 // promote a v1/legacy profile or acquire a partial modern binding.
 auto legacy_definition=FirstBootContent::from_template(source).definition();ContentAuthoringHost legacy(FirstBootContent::create(legacy_definition),"legacy-role","main");const auto oldid=legacy_definition.fixtures.front().object.persistent_id;
 check(apply(legacy,"legacy-false",{ContentSetField{oldid,"name",std::string("Legacy rename")},ContentSetField{oldid,"workshop_role",false}}).status==ContentAuthoringStatus::applied,"Legacy false role rejected");
 rows=content_authoring_rows(legacy.snapshot()->content);check(row(rows,oldid).fields.size()==17,"Old fixture observation shape changed");unchanged_rejection(legacy,"legacy-true",{ContentSetField{oldid,"workshop_role",true}},"Workshop role silently promoted legacy profile");
 std::cout<<checks<<" workshop authoring checks passed\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
