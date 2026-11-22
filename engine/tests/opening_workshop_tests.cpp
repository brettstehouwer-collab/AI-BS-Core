#include <aibs/opening_workshop.hpp>
#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <set>
#include <stdexcept>
using namespace aibs;
namespace {
int checks=0;
void check(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
template<class F>void rejects(F operation,const char* message){bool rejected=false;try{operation();}catch(const std::invalid_argument&){rejected=true;}check(rejected,message);}
OpeningWorkshopBinding binding(){return {{{"a0000000-0000-4000-8000-000000000001","a0000000-0000-4000-8000-000000000002","a0000000-0000-4000-8000-000000000003","a0000000-0000-4000-8000-000000000004","a0000000-0000-4000-8000-000000000005"}}};}
OpeningWorkshopCircuit dead(){OpeningWorkshopCircuit c;c.fault_id="b0000000-0000-4000-8000-000000000001";return c;}
OpeningWorkshopCircuit main_feed(){auto c=dead();c.capacity=100;return c;}
OpeningWorkshopCircuit bypass_feed(){auto c=dead();c.isolated=true;c.bypass_connected=true;c.relay_alive=true;c.relay_id="b0000000-0000-4000-8000-000000000002";c.relay_capacity=100;return c;}
OpeningWorkshopActor actor(const OpeningWorkshopBinding& b,OpeningWorkshopAction action){OpeningWorkshopActor a;a.target_id=b.fixtures[static_cast<std::size_t>(action)];a.distance=1;a.grounded=true;a.visible=true;a.in_shelter=true;return a;}
const std::string& stamp(const ComponentRecord& r,const char* name){return std::get<std::string>(r.fields.at(name));}
ComponentRecord step(const ComponentRecord& before,const OpeningWorkshopBinding& b,const OpeningWorkshopCircuit& c,OpeningWorkshopAction action,const char* attribute){const auto result=plan_opening_workshop(before,b,c,action,actor(b,action));check(result.has_value(),"Expected workshop change missing");check(result->outcome==MechanismOutcome{b.fixtures[4],attribute,false,true},"Wrong owned mechanism outcome");validate_opening_workshop_record(result->component,b,c.fault_id);return result->component;}
void invalid_action(const ComponentRecord& state,const OpeningWorkshopBinding& b,const OpeningWorkshopCircuit& c,OpeningWorkshopAction action,const OpeningWorkshopActor& a,const char* message){const auto before=state;rejects([&]{(void)plan_opening_workshop(state,b,c,action,a);},message);check(state==before,"Rejected action changed source component");}
}
int main(){try{
 const auto b=binding();const auto encoded=encode_opening_workshop_binding(b);
 check(encoded.size()==199&&encoded.starts_with("AIBWORKSHOP 1\n")&&encoded.back()=='\n',"Binding must have exact199-byte versioned LF format");
 check(decode_opening_workshop_binding(encoded)==b,"Binding roundtrip changed ownership order");
 rejects([&]{(void)decode_opening_workshop_binding("");},"Empty binding accepted");
 rejects([&]{(void)decode_opening_workshop_binding(encoded.substr(0,encoded.size()-1));},"Missing final LF accepted");
 rejects([&]{(void)decode_opening_workshop_binding(encoded+"\n");},"Trailing binding bytes accepted");
 auto malformed=encoded;malformed[12]='2';rejects([&]{(void)decode_opening_workshop_binding(malformed);},"Unsupported binding version accepted");
 malformed=encoded;malformed[13]='\r';rejects([&]{(void)decode_opening_workshop_binding(malformed);},"CR instead of LF accepted");
 auto duplicate=b;duplicate.fixtures[4]=duplicate.fixtures[0];rejects([&]{(void)encode_opening_workshop_binding(duplicate);},"Duplicate fixture encoded");
 malformed=encoded;malformed.replace(14+37,36,b.fixtures[0]);rejects([&]{(void)decode_opening_workshop_binding(malformed);},"Duplicate fixture decoded");
 for(const std::string bad:{std::string("not-a-uuid"),std::string("A0000000-0000-4000-8000-000000000001"),std::string("a0000000-0000-1000-8000-000000000001"),std::string("a0000000-0000-4000-0000-000000000001")}){auto broken=b;broken.fixtures[2]=bad;rejects([&]{(void)encode_opening_workshop_binding(broken);},"Noncanonical fixture UUID encoded");}
 const auto schema=opening_workshop_schema();check(schema.type_id==opening_workshop_component_type&&schema.version==1&&schema.fields.size()==5,"Workshop schema identity/field count changed");
 const std::set<std::string> expected{"has_probe","supply_sample","path_sample","tested_signature","bench_claimed"};std::set<std::string> actual;
 for(const auto& field:schema.fields){actual.insert(field.id);check(field.required,"Workshop schema field became optional");check(field.kind==((field.id=="has_probe"||field.id=="bench_claimed")?GameplayValueKind::boolean:GameplayValueKind::text),"Wrong workshop schema field kind");}check(actual==expected,"Unexpected workshop schema fields");
 const auto initial=opening_workshop_initial(b);validate_opening_workshop_record(initial,b,dead().fault_id);
 check(initial.entity_id==b.fixtures[4]&&initial.fields.size()==5&&!std::get<bool>(initial.fields.at("has_probe"))&&!std::get<bool>(initial.fields.at("bench_claimed")),"Initial workshop progress forged");
 check(!opening_workshop_online(initial,b,main_feed()),"Unclaimed bench became online from power alone");
 for(const auto action:{OpeningWorkshopAction::sample_supply,OpeningWorkshopAction::sample_path,OpeningWorkshopAction::test_feed,OpeningWorkshopAction::commission_bench})invalid_action(initial,b,main_feed(),action,actor(b,action),"Action bypassed probe collection");
 const auto collected=step(initial,b,dead(),OpeningWorkshopAction::collect_probe,"has_probe");check(std::get<bool>(collected.fields.at("has_probe")),"Probe not retained");check(initial!=collected&&!std::get<bool>(initial.fields.at("has_probe")),"Planner mutated initial state");
 check(!plan_opening_workshop(collected,b,dead(),OpeningWorkshopAction::collect_probe,actor(b,OpeningWorkshopAction::collect_probe)),"Collecting twice emitted another change");
 const auto collect=OpeningWorkshopAction::collect_probe;
 auto a=actor(b,collect);a.target_id=b.fixtures[1];invalid_action(initial,b,dead(),collect,a,"Wrong owned target accepted");
 a=actor(b,collect);a.target_id=new_uuid();invalid_action(initial,b,dead(),collect,a,"Foreign fixture accepted");
 for(const double distance:{-1.,3.200001,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}){a=actor(b,collect);a.distance=distance;invalid_action(initial,b,dead(),collect,a,"Invalid/out-of-reach distance accepted");}
 a=actor(b,collect);a.grounded=false;invalid_action(initial,b,dead(),collect,a,"Airborne actor accepted");
 a=actor(b,collect);a.inspection_mode=true;invalid_action(initial,b,dead(),collect,a,"Inspection actor accepted");
 a=actor(b,collect);a.visible=false;invalid_action(initial,b,dead(),collect,a,"Occluded station accepted");
 a=actor(b,collect);a.distance=3.2;check(plan_opening_workshop(initial,b,dead(),collect,a).has_value(),"Exact reach boundary rejected");
 rejects([&]{(void)plan_opening_workshop(initial,b,dead(),static_cast<OpeningWorkshopAction>(5),a);},"Unknown action accepted");
 const auto supply_only=step(collected,b,dead(),OpeningWorkshopAction::sample_supply,"supply_sampled");
 check(stamp(supply_only,"supply_sample")==opening_workshop_signature(dead()),"Supply observation lost exact initial source tuple");
 check(stamp(supply_only,"path_sample").empty(),"Supply sampling invented path observation");
 check(!plan_opening_workshop(supply_only,b,main_feed(),OpeningWorkshopAction::sample_supply,actor(b,OpeningWorkshopAction::sample_supply)),"Later source silently overwrote first supply sample");
 invalid_action(collected,b,main_feed(),OpeningWorkshopAction::test_feed,actor(b,OpeningWorkshopAction::test_feed),"Testing accepted no samples");
 invalid_action(supply_only,b,main_feed(),OpeningWorkshopAction::test_feed,actor(b,OpeningWorkshopAction::test_feed),"Testing accepted missing path sample");
 const auto path_only=step(collected,b,dead(),OpeningWorkshopAction::sample_path,"path_sampled");invalid_action(path_only,b,main_feed(),OpeningWorkshopAction::test_feed,actor(b,OpeningWorkshopAction::test_feed),"Testing accepted missing supply sample");
 const auto sampled=step(supply_only,b,dead(),OpeningWorkshopAction::sample_path,"path_sampled");
 check(stamp(sampled,"path_sample")==opening_workshop_signature(dead()),"Path sample lost source tuple");
 check(!plan_opening_workshop(sampled,b,bypass_feed(),OpeningWorkshopAction::sample_path,actor(b,OpeningWorkshopAction::sample_path)),"Later source overwrote first path sample");
 invalid_action(sampled,b,dead(),OpeningWorkshopAction::test_feed,actor(b,OpeningWorkshopAction::test_feed),"Dead feed passed testing");
 auto incomplete=main_feed();incomplete.capacity=99.9;invalid_action(sampled,b,incomplete,OpeningWorkshopAction::test_feed,actor(b,OpeningWorkshopAction::test_feed),"Incomplete main feed passed");
 auto not_isolated=bypass_feed();not_isolated.isolated=false;invalid_action(sampled,b,not_isolated,OpeningWorkshopAction::test_feed,actor(b,OpeningWorkshopAction::test_feed),"Unisolated bypass passed");
 const auto tested=step(sampled,b,main_feed(),OpeningWorkshopAction::test_feed,"feed_verified");check(stamp(tested,"tested_signature")==opening_workshop_signature(main_feed()),"Successful test lost current exact source tuple");
 check(stamp(tested,"supply_sample")==stamp(sampled,"supply_sample")&&stamp(tested,"path_sample")==stamp(sampled,"path_sample"),"Test replaced first-only observations");
 check(!plan_opening_workshop(tested,b,main_feed(),OpeningWorkshopAction::test_feed,actor(b,OpeningWorkshopAction::test_feed)),"Repeated identical test emitted change");
 check(!opening_workshop_online(tested,b,main_feed()),"Successful feed test auto-claimed bench");
 a=actor(b,OpeningWorkshopAction::commission_bench);a.in_shelter=false;invalid_action(tested,b,main_feed(),OpeningWorkshopAction::commission_bench,a,"Outside actor commissioned shelter bench");
 invalid_action(tested,b,bypass_feed(),OpeningWorkshopAction::commission_bench,actor(b,OpeningWorkshopAction::commission_bench),"Changed healthy source bypassed re-test");
 auto relay_changed=main_feed();relay_changed.relay_id=new_uuid();relay_changed.relay_alive=true;relay_changed.relay_capacity=20;
 invalid_action(tested,b,relay_changed,OpeningWorkshopAction::commission_bench,actor(b,OpeningWorkshopAction::commission_bench),"Changed relay identity bypassed exact pre-claim test");
 const auto retested=step(tested,b,bypass_feed(),OpeningWorkshopAction::test_feed,"feed_verified");
 auto replaced_relay=bypass_feed();replaced_relay.relay_id=new_uuid();invalid_action(retested,b,replaced_relay,OpeningWorkshopAction::commission_bench,actor(b,OpeningWorkshopAction::commission_bench),"Equivalent-capacity replacement relay reused old test");
 const auto replacement_tested=step(retested,b,replaced_relay,OpeningWorkshopAction::test_feed,"feed_verified");
 const auto claimed=step(replacement_tested,b,replaced_relay,OpeningWorkshopAction::commission_bench,"bench_claimed");
 check(std::get<bool>(claimed.fields.at("bench_claimed"))&&opening_workshop_online(claimed,b,replaced_relay),"Claimed healthy bypass bench not online");
 check(!plan_opening_workshop(claimed,b,replaced_relay,OpeningWorkshopAction::commission_bench,actor(b,OpeningWorkshopAction::commission_bench)),"Duplicate commissioning emitted another claim");
 const auto permanent=claimed;
 check(!opening_workshop_online(claimed,b,dead()),"Loss of all power left bench online");
 check(claimed==permanent&&std::get<bool>(claimed.fields.at("bench_claimed")),"Power loss erased permanent claim");
 check(opening_workshop_online(claimed,b,main_feed()),"Alternate healthy main feed required re-claim");
 check(opening_workshop_online(claimed,b,relay_changed),"Unused relay changes turned off a claimed healthy main feed");
 auto failed_relay=replaced_relay;failed_relay.relay_alive=false;check(!opening_workshop_online(claimed,b,failed_relay),"Dead bypass relay left bench online");
 check(opening_workshop_online(claimed,b,replaced_relay)&&claimed==permanent,"Restored alternate healthy feed changed claim/history");
 // Exact closed schema and causal prerequisites protect persisted components.
 for(const auto& field:expected){auto bad=initial;bad.fields.erase(field);rejects([&]{validate_opening_workshop_record(bad,b);},"Missing required field accepted");}
 auto bad=initial;bad.fields["extra"]=false;rejects([&]{validate_opening_workshop_record(bad,b);},"Extra forged field accepted");
 bad=initial;bad.entity_id=b.fixtures[0];rejects([&]{validate_opening_workshop_record(bad,b);},"Foreign component owner accepted");
 bad=initial;bad.type_id="forged.Workshop";rejects([&]{validate_opening_workshop_record(bad,b);},"Forged component type accepted");
 bad=initial;bad.version=2;rejects([&]{validate_opening_workshop_record(bad,b);},"Unknown component version accepted");
 bad=initial;bad.fields["has_probe"]=std::string("true");rejects([&]{validate_opening_workshop_record(bad,b);},"String probe flag accepted");
 bad=initial;bad.fields["bench_claimed"]=true;rejects([&]{validate_opening_workshop_record(bad,b);},"Claimed bench with no successful test accepted");
 bad=sampled;bad.fields["has_probe"]=false;rejects([&]{validate_opening_workshop_record(bad,b);},"Samples without probe accepted");
 bad=collected;bad.fields["tested_signature"]=opening_workshop_signature(main_feed());rejects([&]{validate_opening_workshop_record(bad,b);},"Successful test with no samples accepted");
 bad=sampled;bad.fields["tested_signature"]=opening_workshop_signature(dead());rejects([&]{validate_opening_workshop_record(bad,b);},"Dead-source signature forged a successful test");
 for(const std::string invalid:{std::string("not-a-stamp"),std::string(257,'x'),opening_workshop_signature(dead())+"|extra"}){bad=sampled;bad.fields["path_sample"]=invalid;rejects([&]{validate_opening_workshop_record(bad,b);},"Malformed/oversized source stamp accepted");}
 auto foreign=dead();foreign.fault_id=new_uuid();bad=sampled;bad.fields["path_sample"]=opening_workshop_signature(foreign);rejects([&]{validate_opening_workshop_record(bad,b,dead().fault_id);},"Foreign fault observation accepted");
 rejects([&]{(void)opening_workshop_online(claimed,b,foreign);},"A different fault identity reused claim history");
 const auto signature=opening_workshop_signature(bypass_feed());auto changed=bypass_feed();changed.capacity=1;check(opening_workshop_signature(changed)!=signature,"Capacity not included in exact source signature");changed=bypass_feed();changed.isolated=false;check(opening_workshop_signature(changed)!=signature,"Isolation absent from signature");changed=bypass_feed();changed.bypass_connected=false;check(opening_workshop_signature(changed)!=signature,"Path connection absent from signature");changed=bypass_feed();changed.relay_alive=false;check(opening_workshop_signature(changed)!=signature,"Relay liveness absent from signature");changed=bypass_feed();changed.relay_capacity=99;check(opening_workshop_signature(changed)!=signature,"Relay capacity absent from signature");
 for(const double value:{-1.,101.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}){auto invalid=dead();invalid.capacity=value;rejects([&]{(void)opening_workshop_signature(invalid);},"Invalid capacity signed");invalid=dead();invalid.relay_capacity=value;rejects([&]{(void)opening_workshop_supply(invalid);},"Invalid relay capacity accepted");}
 changed=dead();changed.relay_alive=true;rejects([&]{(void)opening_workshop_signature(changed);},"Live relay without identity accepted");changed=dead();changed.fault_id="invalid";rejects([&]{(void)opening_workshop_supply(changed);},"Invalid source UUID accepted");
 check(opening_workshop_reading(main_feed())=="Capacity 100% | isolation OFF | feed main","Main HUD reading changed");check(opening_workshop_reading(bypass_feed())=="Capacity 0% | isolation ON | feed bypass","Bypass HUD reading changed");check(opening_workshop_reading(dead())=="Capacity 0% | isolation OFF | feed none","Dead HUD reading changed");
 std::cout<<checks<<" opening workshop pure contract checks passed\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
