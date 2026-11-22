#include <aibs/opening_tour.hpp>
#include "opening_tour_guard.hpp"
#include <aibs/warm_opening.hpp>
#include <aibs/opening_inspections.hpp>
#include <aibs/initial_view.hpp>
#include <algorithm>
#include <iostream>
#include <memory>
#include <stdexcept>
using namespace aibs;
namespace {unsigned checks=0;void check(bool v,const char* why){++checks;if(!v)throw std::runtime_error(why);}template<class F>void rejects(F action,const char* why){bool failed=false;try{action();}catch(const std::invalid_argument&){failed=true;}check(failed,why);}}
int main(){try{
 CreatorSession source(first_boot_schema(),"opening-tour-unit","main");check(seed_first_boot(source).ok,"Seed failed");const auto draft=make_warm_opening_draft(source,{});const auto& d=draft.definition;check(d.hints.size()==31,"Framing should add exactly one map key");check(d.hints.at(std::string(first_boot_initial_view_key))==draft.tour.ids[static_cast<std::size_t>(OpeningTourRole::controller)],"Framing and authored controller binding disagree");const auto content=FirstBootContent::create(d);const OpeningInspectionCatalog catalog(d);const auto targets=draft.tour;check(catalog.entries().size()==opening_tour_stop_count,"Seven catalog stops expected");for(const auto& id:targets.ids)check(catalog.find(id)!=nullptr,"Factory typed binding is not an owned inspection");
 const auto before=first_boot_content_encode(content);const auto bytes=encode_opening_tour(content,targets);check(bytes.size()<=4096,"Unbounded sidecar");check(decode_opening_tour(bytes,content).ids==targets.ids,"Typed role identity lost");check(first_boot_content_encode(content)==before,"Diagnostic sidecar mutated game content");
 for(std::size_t i=0;i<opening_tour_stop_count;++i)check(!opening_tour_role_name(static_cast<OpeningTourRole>(i)).empty(),"Role enum label missing");
 auto invalid=targets;invalid.ids[1]=invalid.ids[0];rejects([&]{encode_opening_tour(content,invalid);},"Duplicate target accepted");invalid=targets;invalid.ids[0]=new_uuid();rejects([&]{encode_opening_tour(content,invalid);},"Foreign fixture accepted");
 auto truncated=bytes;truncated.pop_back();rejects([&]{decode_opening_tour(truncated,content);},"Missing canonical terminal LF accepted");
 auto extra=bytes;extra.push_back('\n');rejects([&]{decode_opening_tour(extra,content);},"Extra untyped data accepted");
 auto nul=bytes;nul[3]=0;rejects([&]{decode_opening_tour(nul,content);},"NUL source accepted");
 std::vector<unsigned char> huge(4097,'x');rejects([&]{decode_opening_tour(huge,content);},"Oversized sidecar accepted");
 auto changed=d;changed.exposure=1.1f;const auto updated=FirstBootContent::create(changed);bool actionable=false;try{decode_opening_tour(bytes,updated);}catch(const std::invalid_argument& e){actionable=std::string(e.what()).find("regenerate bindings")!=std::string::npos;}check(actionable,"Stale chapter did not require explicit regeneration");
 check(decode_opening_tour(encode_opening_tour(updated,targets),updated).ids==targets.ids,"Explicit regeneration lost stable targets");
 auto renamed=d;for(auto& fixture:renamed.fixtures)if(fixture.object.persistent_id==targets.ids[0])fixture.object.name="Creator edited label";const auto edited=FirstBootContent::create(renamed);check(decode_opening_tour(encode_opening_tour(edited,targets),edited).ids==targets.ids,"Bindings depend on fixture label syntax");
 OpeningTourReadGuard guard(catalog.entries().front(),2);check(guard.expected().fixture_id==catalog.entries().front().fixture_id,"Guard lost owned target identity");auto selected=std::optional<OpeningInspection>{guard.expected()};guard.after_walk(2);guard.reading(2,selected,true);
 auto wrong=selected;wrong->fixture_id=new_uuid();rejects([&]{guard.reading(2,wrong,true);},"Identical-text wrong fixture passed selection identity");rejects([&]{guard.after_walk(3);},"Actual reload while walking was not detected");rejects([&]{guard.reading(3,selected,true);},"Actual reload while reading was not detected");rejects([&]{guard.reading(2,{},true);},"Missing replacement selection accepted");rejects([&]{guard.reading(2,selected,false);},"Hidden/reloaded panel accepted");wrong=selected;wrong->text+="changed";rejects([&]{guard.reading(2,wrong,true);},"Changed actual panel text accepted");wrong=selected;wrong->source+="changed";rejects([&]{guard.reading(2,wrong,true);},"Changed actual source accepted");
 auto temporary=std::make_unique<OpeningInspection>(guard.expected());OpeningTourReadGuard retained(*temporary,0);const auto retained_id=temporary->fixture_id;temporary.reset();check(retained.expected().fixture_id==retained_id,"Guard retained destroyed catalog storage");retained.reading(0,retained.expected(),true);
 auto oversized=guard.expected();oversized.text.resize(2049,'x');rejects([&]{OpeningTourReadGuard invalid_guard(oversized,0);},"Guard copied unbounded entry before validation");
 std::cout<<checks<<" typed fingerprint-bound tour-sidecar checks passed\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
