#include <aibs/opening_inspections.hpp>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
using namespace aibs;
namespace {
int checks=0;
void check(bool condition,const char* message){++checks;if(!condition)throw std::runtime_error(message);}
template<class F> void rejects(F operation,const char* message){bool rejected=false;try{operation();}catch(const std::invalid_argument&){rejected=true;}check(rejected,message);}
constexpr const char* id="12345678-1234-4234-8234-123456789abc";
constexpr const char* id2="12345678-1234-4234-8234-123456789abd";
const std::string prefix=std::string("inspect.")+id+".";
FirstBootContentDefinition definition(){FirstBootContentDefinition d;d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;d.fixtures.push_back({{id,"Controller and turning",{0,.8f,0},{.3f,.15f,.2f},{1,1,1},0,true},-1});d.hints[prefix+"text"]="Adam taught BS to look and turn in games. Try the mouse, then choose a route.";d.hints[prefix+"source"]="Echos Within, paragraph 682. Gameplay guidance is newly authored.";d.hints[prefix+"action"]="read";return d;}
}
int main(){try{
 auto d=definition();const auto before=d.hints;OpeningInspectionCatalog catalog(d);
 check(catalog.entries().size()==1,"Complete owned inspection missing");
 check(catalog.find(id)&&catalog.find(id)->title=="Controller and turning","Fixture title must stay a normal readable label");
 check(catalog.find(id)->action==OpeningInspectionAction::read,"Read action missing");
 check(catalog.find(id)->text==d.hints.at(prefix+"text"),"Text changed");
 check(catalog.find(id)->source==d.hints.at(prefix+"source"),"Source attribution changed");
 check(!catalog.find(id2),"Foreign fixture returned");check(d.hints==before,"Validation mutated definition");
 OpeningInspectionSession session(catalog);check(!session.snapshot(),"New session must not open a panel");
 check(session.select(id,{0,.2f,2},true),"Supported close inspection failed");
 check(session.snapshot()&&session.snapshot()->fixture_id==id,"Owned selected panel missing");
 check(!session.select(id,{0,.2f,2},false),"Occluded inspection accepted");
 check(session.snapshot()&&session.snapshot()->fixture_id==id,"Rejected selection lost current panel");
 check(!session.select(id,{0,.2f,4},true),"Out of reach inspection accepted");
 check(!session.select(id2,{0,.2f,2},true),"Foreign selection accepted");
 check(!session.select(id,{std::numeric_limits<float>::quiet_NaN(),0,0},true),"NaN feet accepted");
 check(!session.select(id,{0,std::numeric_limits<float>::infinity(),0},true),"Infinite feet accepted");
 session.close();check(!session.snapshot(),"Close retained panel");
 d.hints[prefix+"action"]="seat";OpeningInspectionCatalog seats(d);OpeningInspectionSession seated(seats);
 check(seated.select(id,{0,.2f,2},true)&&seated.snapshot()->action==OpeningInspectionAction::seat,"Quiet seat action missing");
 const auto owned=seated.snapshot();seated.close();check(owned->title=="Controller and turning","Snapshot text lifetime depends on live panel");
 d=definition();d.format_version=2;rejects([&]{OpeningInspectionCatalog c(d);},"Legacy definition accepted modern inspection");
 d=definition();d.asset_profile=AssetContentProfile::legacy_v1;rejects([&]{OpeningInspectionCatalog c(d);},"Legacy profile accepted inspection");
 d=definition();d.fixtures.clear();rejects([&]{OpeningInspectionCatalog c(d);},"Orphan inspection accepted");
 d=definition();d.fixtures.front().object.selectable=false;rejects([&]{OpeningInspectionCatalog c(d);},"Unselectable fixture accepted interactive text");
 d=definition();d.fixtures.push_back(d.fixtures.front());rejects([&]{OpeningInspectionCatalog c(d);},"Duplicate owner identity accepted");
 for(const char* field:{"text","source","action"}){d=definition();d.hints.erase(prefix+field);rejects([&]{OpeningInspectionCatalog c(d);},"Incomplete inspection triple accepted");}
 for(const char* field:{"text","source","action"}){d=definition();d.hints[prefix+field]="";rejects([&]{OpeningInspectionCatalog c(d);},"Empty inspection field accepted");}
 d=definition();d.hints[prefix+"unknown"]="value";rejects([&]{OpeningInspectionCatalog c(d);},"Unknown inspection field accepted");
 d=definition();d.hints["inspect.bad.text"]="x";rejects([&]{OpeningInspectionCatalog c(d);},"Non UUID inspection target accepted");
 for(const std::string invalid_id:{"12345678-1234-1234-8234-123456789abc","12345678-1234-4234-1234-123456789abc"}){d=definition();d.fixtures.front().object.persistent_id=invalid_id;const auto values=d.hints;d.hints.clear();for(const auto& [key,value]:values)d.hints["inspect."+invalid_id+"."+key.substr(45)]=value;rejects([&]{OpeningInspectionCatalog c(d);},"Inspection UUID must match the engine v4/variant contract");}
 d=definition();d.hints[prefix+"action"]="complete_shelter";rejects([&]{OpeningInspectionCatalog c(d);},"Outcome action accepted as inspection");
 d=definition();d.hints[prefix+"text"]=std::string(2049,'x');rejects([&]{OpeningInspectionCatalog c(d);},"Oversized text accepted");
 d=definition();d.hints[prefix+"source"]=std::string(513,'x');rejects([&]{OpeningInspectionCatalog c(d);},"Oversized source accepted");
 d=definition();d.hints[prefix+"text"]=std::string("wrong\0text",10);rejects([&]{OpeningInspectionCatalog c(d);},"Embedded NUL accepted");
 d=definition();d.hints[prefix+"text"]=std::string("\xc0\x80",2);rejects([&]{OpeningInspectionCatalog c(d);},"Overlong UTF8 accepted");
 d=definition();d.hints[prefix+"text"]=std::string("\xed\xa0\x80",3);rejects([&]{OpeningInspectionCatalog c(d);},"UTF8 surrogate accepted");
 d=definition();d.hints[prefix+"text"]=std::string("\xf4\x90\x80\x80",4);rejects([&]{OpeningInspectionCatalog c(d);},"Out of range UTF8 accepted");
 d=definition();d.hints[prefix+"text"]="A page\nA pause\tA route. \xe2\x80\x94";check(OpeningInspectionCatalog(d).find(id)!=nullptr,"Valid UTF8/newline/tab rejected");
 d=definition();d.hints[prefix+"text"]=std::string(2048,'x');d.hints[prefix+"source"]=std::string(512,'s');check(OpeningInspectionCatalog(d).entries().size()==1,"Exact per field limit rejected");
 d=definition();d.hints.clear();d.fixtures.clear();d.format_version=1;d.asset_profile=AssetContentProfile::legacy_v1;check(OpeningInspectionCatalog(d).entries().empty(),"Old content without inspections lost compatibility");
 d=definition();d.hints["adam.live_fault"]="Existing authored cue";check(OpeningInspectionCatalog(d).entries().size()==1,"Existing Adam cue was interpreted as inspection");
 // The catalog validates only its own namespace. FirstBootContent validates the
 // remaining keys and its global collection limit before publication.
 d=definition();d.hints["future.namespace"]="Kept by extension validation";check(OpeningInspectionCatalog(d).entries().size()==1,"Extension dropped unrelated guidance");
 std::cout<<checks<<" opening inspection checks passed\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
