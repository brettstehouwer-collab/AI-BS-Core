#include <aibs/opening_workshop.hpp>
#include <algorithm>
#include <bit>
#include <charconv>
#include <cmath>
#include <set>
#include <stdexcept>
#include <vector>
namespace aibs {namespace {
void need(bool v,const char* why){if(!v)throw std::invalid_argument(why);}
void binding(const OpeningWorkshopBinding& b){std::set<std::string> ids;for(const auto& id:b.fixtures)need(is_uuid(id)&&ids.insert(id).second,"Workshop requires five distinct canonical fixture UUIDs");}
void circuit(const OpeningWorkshopCircuit& c){need(is_uuid(c.fault_id)&&(c.relay_id.empty()||is_uuid(c.relay_id)),"Workshop circuit has an invalid source identity");need(std::isfinite(c.capacity)&&c.capacity>=0&&c.capacity<=100&&std::isfinite(c.relay_capacity)&&c.relay_capacity>=0&&c.relay_capacity<=100,"Workshop source capacity is outside its bound");need(!c.relay_alive||!c.relay_id.empty(),"A live workshop relay needs an identity");}
std::string hex(double d){constexpr char digits[]="0123456789abcdef";auto bits=std::bit_cast<std::uint64_t>(d);std::string s(16,'0');for(unsigned n=0;n<16;++n)s[15-n]=digits[(bits>>(n*4))&15];return s;}
double unhex(std::string_view s){need(s.size()==16,"Invalid workshop capacity stamp");std::uint64_t bits=0;for(char c:s){need((c>='0'&&c<='9')||(c>='a'&&c<='f'),"Noncanonical workshop capacity stamp");bits=(bits<<4)|static_cast<unsigned>(c<='9'?c-'0':c-'a'+10);}return std::bit_cast<double>(bits);}
OpeningWorkshopCircuit parse(std::string_view s){
 std::vector<std::string_view> parts;std::size_t start=0;for(;;){const auto end=s.find('|',start);parts.push_back(s.substr(start,end==s.npos?s.size()-start:end-start));if(end==s.npos)break;start=end+1;need(parts.size()<8,"Workshop stamp has trailing fields");}
 need(parts.size()==8&&parts[0]=="W1","Invalid workshop source stamp");auto flag=[](std::string_view v){need(v=="0"||v=="1","Invalid workshop source flag");return v=="1";};
 OpeningWorkshopCircuit c;c.fault_id=parts[1];c.capacity=unhex(parts[2]);c.isolated=flag(parts[3]);c.bypass_connected=flag(parts[4]);if(parts[5]!="-")c.relay_id=parts[5];c.relay_alive=flag(parts[6]);c.relay_capacity=unhex(parts[7]);circuit(c);need(opening_workshop_signature(c)==s,"Noncanonical workshop stamp");return c;
}
const std::string& text(const ComponentRecord& r,const char* field){const auto p=r.fields.find(field);need(p!=r.fields.end()&&std::holds_alternative<std::string>(p->second),"Workshop text field missing or wrongly typed");return std::get<std::string>(p->second);}
bool flag(const ComponentRecord& r,const char* field){const auto p=r.fields.find(field);need(p!=r.fields.end()&&std::holds_alternative<bool>(p->second),"Workshop flag missing or wrongly typed");return std::get<bool>(p->second);}
}}
namespace aibs {
std::string encode_opening_workshop_binding(const OpeningWorkshopBinding& b){binding(b);std::string out="AIBWORKSHOP 1\n";for(const auto& id:b.fixtures)out+=id+'\n';return out;}
OpeningWorkshopBinding decode_opening_workshop_binding(std::string_view s){need(s.size()==199&&s.starts_with("AIBWORKSHOP 1\n"),"Workshop binding requires its exact versioned five-UUID format");OpeningWorkshopBinding b;std::size_t n=14;for(auto& id:b.fixtures){need(s[n+36]=='\n',"Workshop binding requires canonical LF lines");id=s.substr(n,36);n+=37;}binding(b);need(encode_opening_workshop_binding(b)==s,"Noncanonical workshop binding");return b;}
ComponentSchema opening_workshop_schema(){return {std::string(opening_workshop_component_type),1,{{"has_probe",GameplayValueKind::boolean},{"supply_sample",GameplayValueKind::text},{"path_sample",GameplayValueKind::text},{"tested_signature",GameplayValueKind::text},{"bench_claimed",GameplayValueKind::boolean}}};}
ComponentRecord opening_workshop_initial(const OpeningWorkshopBinding& b){binding(b);return {b.fixtures[4],std::string(opening_workshop_component_type),1,{{"has_probe",false},{"supply_sample",std::string{}},{"path_sample",std::string{}},{"tested_signature",std::string{}},{"bench_claimed",false}}};}
ComponentSchema opening_workshop_assembly_schema(){return {std::string(opening_workshop_assembly_component_type),1,{{"collected",GameplayValueKind::boolean},{"available",GameplayValueKind::boolean},{"legacy",GameplayValueKind::boolean}}};}
ComponentRecord opening_workshop_assembly_record(const OpeningWorkshopBinding& b,bool available,bool legacy){binding(b);return {b.fixtures[2],std::string(opening_workshop_assembly_component_type),1,{{"collected",true},{"available",available},{"legacy",legacy}}};}
void validate_opening_workshop_assembly(const ComponentRecord& r,const OpeningWorkshopBinding& b){
 binding(b);need(r.entity_id==b.fixtures[2]&&r.type_id==opening_workshop_assembly_component_type&&r.version==1&&r.fields.size()==3,"Invalid owned Workshop relay assembly");
 need(flag(r,"collected"),"Assembly record requires an explicit collection or retained relay adoption");(void)flag(r,"available");(void)flag(r,"legacy");
}
void validate_opening_workshop_record(const ComponentRecord& r,const OpeningWorkshopBinding& b,std::string_view fault){
 binding(b);need(r.entity_id==b.fixtures[4]&&r.type_id==opening_workshop_component_type&&r.version==1&&r.fields.size()==5,"Invalid owned workshop component");
 const auto probe=flag(r,"has_probe"),claimed=flag(r,"bench_claimed");bool samples=true;
 for(const auto* key:{"supply_sample","path_sample","tested_signature"}){const auto& value=text(r,key);need(value.size()<=256,"Workshop source stamp exceeds bound");if(value.empty()){if(std::string_view(key)!="tested_signature")samples=false;continue;}const auto c=parse(value);need(fault.empty()||c.fault_id==fault,"Workshop observation belongs to a foreign fault");need(probe,"Workshop observations require the collected probe");}
 need(text(r,"tested_signature").empty()||samples,"Workshop test needs both actual contact samples");need(!claimed||!text(r,"tested_signature").empty(),"Claimed workshop needs a recorded successful test");
 if(!text(r,"tested_signature").empty())need(opening_workshop_supply(parse(text(r,"tested_signature")))!="none","A failed source cannot be recorded as a successful test");
}
std::string opening_workshop_signature(const OpeningWorkshopCircuit& c){circuit(c);return "W1|"+c.fault_id+'|'+hex(c.capacity)+'|'+(c.isolated?"1":"0")+'|'+(c.bypass_connected?"1":"0")+'|'+(c.relay_id.empty()?"-":c.relay_id)+'|'+(c.relay_alive?"1":"0")+'|'+hex(c.relay_capacity);}
std::string opening_workshop_supply(const OpeningWorkshopCircuit& c){circuit(c);if(c.capacity==100&&!c.isolated)return "main";if(c.isolated&&c.bypass_connected&&!c.relay_id.empty()&&c.relay_alive&&c.relay_capacity==100)return "bypass";return "none";}
bool opening_workshop_online(const ComponentRecord& r,const OpeningWorkshopBinding& b,const OpeningWorkshopCircuit& c){validate_opening_workshop_record(r,b,c.fault_id);return flag(r,"bench_claimed")&&opening_workshop_supply(c)!="none";}
std::optional<OpeningWorkshopChange> plan_opening_workshop(const ComponentRecord& before,const OpeningWorkshopBinding& b,const OpeningWorkshopCircuit& c,OpeningWorkshopAction action,const OpeningWorkshopActor& actor){
 validate_opening_workshop_record(before,b,c.fault_id);const auto index=static_cast<std::size_t>(action);need(index<5,"Unknown workshop action");need(actor.target_id==b.fixtures[index],"Workshop action targets the wrong owned fixture");need(actor.grounded&&!actor.inspection_mode&&actor.visible&&std::isfinite(actor.distance)&&actor.distance>=0&&actor.distance<=3.2,"Move within visible grounded reach of that workshop fixture");
 auto after=before;std::string attribute;
 if(action==OpeningWorkshopAction::collect_probe){if(flag(before,"has_probe"))return {};after.fields["has_probe"]=true;attribute="has_probe";}
 else{
  need(flag(before,"has_probe"),"Collect the diagnostic probe in the reserve nook first");
  if(action==OpeningWorkshopAction::sample_supply||action==OpeningWorkshopAction::sample_path){const char* key=action==OpeningWorkshopAction::sample_supply?"supply_sample":"path_sample";if(!text(before,key).empty())return {};after.fields[key]=opening_workshop_signature(c);attribute=action==OpeningWorkshopAction::sample_supply?"supply_sampled":"path_sampled";}
  else if(action==OpeningWorkshopAction::test_feed){need(!text(before,"supply_sample").empty()&&!text(before,"path_sample").empty(),"Sample both actual contacts before verifying a feed");need(opening_workshop_supply(c)!="none","No healthy repaired main or connected isolated bypass is available");const auto stamp=opening_workshop_signature(c);if(text(before,"tested_signature")==stamp)return {};after.fields["tested_signature"]=stamp;attribute="feed_verified";}
  else{need(actor.in_shelter,"Commission the workbench from inside the actual shelter");if(flag(before,"bench_claimed"))return {};need(opening_workshop_supply(c)!="none"&&text(before,"tested_signature")==opening_workshop_signature(c),"The current feed differs from its successful test; test the present source again");after.fields["bench_claimed"]=true;attribute="bench_claimed";}
 }
 validate_opening_workshop_record(after,b,c.fault_id);return OpeningWorkshopChange{std::move(after),{b.fixtures[4],std::move(attribute),false,true}};
}
std::string opening_workshop_reading(const OpeningWorkshopCircuit& c){circuit(c);char bytes[32]{};const auto result=std::to_chars(bytes,bytes+32,c.capacity,std::chars_format::general,6);need(result.ec==std::errc{},"Capacity display overflow");return "Capacity "+std::string(bytes,result.ptr)+"% | isolation "+(c.isolated?"ON":"OFF")+" | feed "+opening_workshop_supply(c);}
std::optional<std::string> opening_workshop_saved_reading(const ComponentRecord& r,const OpeningWorkshopBinding& b,OpeningWorkshopAction action,const std::string& fault){
 need(is_uuid(fault),"Saved workshop reading requires its owned fault identity");validate_opening_workshop_record(r,b,fault);
 const char* field=action==OpeningWorkshopAction::sample_supply?"supply_sample":action==OpeningWorkshopAction::sample_path?"path_sample":nullptr;
 if(!field)return {};const auto& sample=text(r,field);if(sample.empty())return {};
 return opening_workshop_reading(parse(sample));
}
}
