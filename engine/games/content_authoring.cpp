#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/content_authoring.hpp>
#include <aibs/content_dependencies.hpp>
#include <aibs/creator_payload.hpp>
#include <aibs/gameplay_codec.hpp>
#include <aibs/asset_store.hpp>
#include <aibs/asset_scene.hpp>
#include <algorithm>
#include <fstream>
#include <limits>
#include <tuple>

namespace aibs {
namespace {
using Bytes=std::vector<unsigned char>;using Writer=creator_payload::detail::Writer;using Reader=creator_payload::detail::Reader;
void need(bool value,const char* why){if(!value)throw std::invalid_argument(why);}
void text(const std::string& value){Writer w;w.text(value,true);}
void fingerprint(const std::string& s){need(s.size()==64&&std::all_of(s.begin(),s.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}),"Invalid content fingerprint");}
void raw(Writer& w,std::span<const unsigned char> b){w.number(b.size(),4);need(b.size()<=creator_payload::maximum_bytes-w.data.size(),"Authoring document byte limit");w.data.insert(w.data.end(),b.begin(),b.end());}
std::span<const unsigned char> raw(Reader& r){const auto size=r.number(4);need(size<=r.data.size()-r.offset,"Truncated authoring bytes");const auto result=r.data.subspan(r.offset,static_cast<std::size_t>(size));r.offset+=static_cast<std::size_t>(size);return result;}
void end(const Reader& r){need(r.offset==r.data.size(),"Trailing authoring bytes");}
std::uint32_t crc(std::span<const unsigned char> b){std::uint32_t value=~0u;for(auto c:b){value^=c;for(int i=0;i<8;++i)value=(value>>1)^(0xedb88320u&static_cast<std::uint32_t>(-static_cast<int>(value&1)));}return ~value;}
ComponentRecord fixture_record(const FirstBootContentFixture& f){const auto& o=f.object;return {o.persistent_id,"authoring.Fixture",1,{{"name",o.name},{"x",static_cast<double>(o.center.x)},{"y",static_cast<double>(o.center.y)},{"z",static_cast<double>(o.center.z)},{"half_x",static_cast<double>(o.half_extent.x)},{"half_y",static_cast<double>(o.half_extent.y)},{"half_z",static_cast<double>(o.half_extent.z)},{"color_x",static_cast<double>(o.color.x)},{"color_y",static_cast<double>(o.color.y)},{"color_z",static_cast<double>(o.color.z)},{"rotation_x",static_cast<double>(o.rotation.x)},{"rotation_y",static_cast<double>(o.rotation.y)},{"rotation_z",static_cast<double>(o.rotation.z)},{"rotation_w",static_cast<double>(o.rotation.w)},{"emission",static_cast<double>(o.emission)},{"selectable",o.selectable},{"sheltered_emission",static_cast<double>(f.sheltered_emission)}}};}
FirstBootContentFixture fixture(const ComponentRecord& r){need(r.type_id=="authoring.Fixture"&&r.version==1&&r.fields.size()==17,"Invalid fixture authoring record");auto number=[&](const char* key){const auto n=std::get<double>(r.fields.at(key));const auto f=static_cast<float>(n);need(std::isfinite(f),"Invalid fixture number");return f;};return {{r.entity_id,std::get<std::string>(r.fields.at("name")),{number("x"),number("y"),number("z")},{number("half_x"),number("half_y"),number("half_z")},{number("color_x"),number("color_y"),number("color_z")},number("emission"),std::get<bool>(r.fields.at("selectable")),{number("rotation_x"),number("rotation_y"),number("rotation_z"),number("rotation_w")}},number("sheltered_emission")};}
ComponentRecord placement_record(const FirstBootAssetPlacement& p){
 need(is_uuid(p.entity_id)&&is_uuid(p.asset_id),"Invalid placement UUID");fingerprint(p.asset_sha256);fingerprint(p.pack_sha256);text(p.name);
 return {p.entity_id,"authoring.AssetPlacement",1,{{"name",p.name},{"asset_id",p.asset_id},{"asset_sha256",p.asset_sha256},{"pack_sha256",p.pack_sha256},{"x",static_cast<double>(p.center.x)},{"y",static_cast<double>(p.center.y)},{"z",static_cast<double>(p.center.z)},{"scale_x",static_cast<double>(p.scale.x)},{"scale_y",static_cast<double>(p.scale.y)},{"scale_z",static_cast<double>(p.scale.z)},{"rotation_x",static_cast<double>(p.rotation.x)},{"rotation_y",static_cast<double>(p.rotation.y)},{"rotation_z",static_cast<double>(p.rotation.z)},{"rotation_w",static_cast<double>(p.rotation.w)},{"selectable",p.selectable}}};
}
FirstBootAssetPlacement placement(const ComponentRecord& r){
 need(r.type_id=="authoring.AssetPlacement"&&r.version==1&&r.fields.size()==15,"Invalid asset placement authoring record");
 auto number=[&](const char* key){const auto value=static_cast<float>(std::get<double>(r.fields.at(key)));need(std::isfinite(value),"Invalid placement number");return value;};
 FirstBootAssetPlacement p{r.entity_id,std::get<std::string>(r.fields.at("name")),std::get<std::string>(r.fields.at("asset_id")),std::get<std::string>(r.fields.at("asset_sha256")),std::get<std::string>(r.fields.at("pack_sha256")),{number("x"),number("y"),number("z")},{number("scale_x"),number("scale_y"),number("scale_z")},{number("rotation_x"),number("rotation_y"),number("rotation_z"),number("rotation_w")},std::get<bool>(r.fields.at("selectable"))};
 (void)placement_record(p);return p;
}
void vector_fields(std::map<std::string,GameplayValue>& fields,const std::string& prefix,Vec3 p){fields[prefix+"x"]=static_cast<double>(p.x);fields[prefix+"y"]=static_cast<double>(p.y);fields[prefix+"z"]=static_cast<double>(p.z);}
void assign(Vec3& p,char axis,const GameplayValue& value){const auto n=std::get<double>(value);const auto f=static_cast<float>(n);need(std::isfinite(f),"Invalid authored vector");if(axis=='x')p.x=f;else if(axis=='y')p.y=f;else if(axis=='z')p.z=f;else throw std::invalid_argument("Unknown vector axis");}
constexpr const char* cues[]={"adam.danger","adam.bypass_open","adam.bypass_power","adam.pencil","adam.shelter","adam.repaired_isolated","adam.repaired_connected","adam.isolated","adam.live_fault"};
std::set<std::string> identities(const FirstBootContent& content){const auto& d=content.definition();std::set<std::string> ids{d.definition_id,d.world_id,d.binding_id};for(const auto& [alias,e]:d.hardware){(void)alias;ids.insert(e.persistent_id);}for(const auto& r:d.initial_records)ids.insert(r.entity_id);for(const auto& f:d.fixtures)ids.insert(f.object.persistent_id);for(const auto& p:d.placements)ids.insert(p.entity_id);for(const auto& a:d.companions)ids.insert(a.entity_id);for(const auto& l:d.lights)ids.insert(l.entity_id);for(const auto& m:d.memories)ids.insert(m.entity_id);return ids;}
Bytes history_bytes(const ContentHistoryRequest& q){Writer w;w.number(1,2);w.text(q.id,true);w.number(q.expected_revision,8);fingerprint(q.expected_fingerprint);w.text(q.expected_fingerprint);w.number(q.redo,1);return w.data;}
ContentHistoryRequest history_request(std::span<const unsigned char> b){Reader r{b};need(r.number(2)==1,"Unsupported history request");ContentHistoryRequest q;q.id=r.text(true);q.expected_revision=r.number(8);q.expected_fingerprint=r.text(true);fingerprint(q.expected_fingerprint);const auto redo=r.number(1);need(redo<=1,"Invalid history direction");q.redo=redo==1;end(r);return q;}
}
ComponentRecord memory_record(const FirstBootMemoryBinding& m){
 return {m.entity_id,"authoring.MemoryBinding",1,{{"name",m.name},{"x",static_cast<double>(m.position.x)},{"y",static_cast<double>(m.position.y)},{"z",static_cast<double>(m.position.z)},
  {"audio_asset_id",m.audio.asset_id},{"audio_asset_sha256",m.audio.asset_sha256},{"audio_pack_sha256",m.audio.pack_sha256}}};
}
FirstBootMemoryBinding memory_binding(const ComponentRecord& r){
 need(r.type_id=="authoring.MemoryBinding"&&r.version==1&&r.fields.size()==7&&is_uuid(r.entity_id),"Invalid memory authoring record");
 const auto number=[&](const char* key){const auto n=std::get<double>(r.fields.at(key));const auto f=static_cast<float>(n);need(std::isfinite(n)&&std::isfinite(f)&&static_cast<double>(f)==n,"Invalid canonical memory coordinate");return f;};
 FirstBootMemoryBinding m{r.entity_id,std::get<std::string>(r.fields.at("name")),{number("x"),number("y"),number("z")},{std::get<std::string>(r.fields.at("audio_asset_id")),std::get<std::string>(r.fields.at("audio_asset_sha256")),std::get<std::string>(r.fields.at("audio_pack_sha256"))}};
 text(m.name);need(!m.name.empty()&&m.name.size()<=4096,"Memory name outside1..4096 bytes");validate_asset_pack_reference(m.audio);return m;
}
static std::vector<ContentAuthoringRow> definition_rows(const FirstBootContentDefinition& d){std::vector<ContentAuthoringRow> rows;
 for(const auto& [alias,e]:d.hardware){ComponentRecord r{e.persistent_id,"authoring.Hardware",1,{{"name",e.name}}};(void)alias;for(const auto& [key,value]:e.fields)r.fields.emplace(key,value);rows.push_back(std::move(r));}
 for(const auto& r:d.initial_records){auto row=r;std::erase_if(row.fields,[&](const auto& f){return first_boot_content_runtime_field(r.type_id,f.first);});if(r.type_id=="firstboot.PowerFault")vector_fields(row.fields,"isolation_",d.isolation_switch);rows.push_back(std::move(row));}
 for(const auto& f:d.fixtures){
  auto row=fixture_record(f);
  // Observation-only metadata never widens the17-field CreateFixture payload.
  // Do not validate triples here: ordered grouped edits may be temporarily partial.
  if(d.format_version==3&&d.asset_profile==AssetContentProfile::warm_beginning){
   const auto prefix="inspect."+f.object.persistent_id+".";
   for(const auto* part:{"text","source","action"}){const auto found=d.hints.find(prefix+part);row.fields["inspection_"+std::string(part)]=found==d.hints.end()?std::string{}:found->second;}
  }
  if(f.role==FixtureRole::workshop)row.fields["workshop_role"]=true;
  rows.push_back(std::move(row));
 }
 for(const auto& p:d.placements)rows.push_back(placement_record(p));
 for(const auto& companion:d.companions){
  ComponentRecord row{companion.entity_id,"authoring.CompanionBinding",1,{{"name",companion.name},{"initial_follow",companion.initial_follow},{"model_bound",companion.model.has_value()},
   {"model_asset_id",companion.model?companion.model->asset_id:std::string{}},{"model_asset_sha256",companion.model?companion.model->asset_sha256:std::string{}},{"model_pack_sha256",companion.model?companion.model->pack_sha256:std::string{}}}};
  vector_fields(row.fields,"spawn_",companion.spawn);rows.push_back(std::move(row));
 }
 for(const auto& memory:d.memories){
  ComponentRecord row{memory.entity_id,"authoring.MemoryBinding",1,{{"name",memory.name},
   {"audio_asset_id",memory.audio.asset_id},{"audio_asset_sha256",memory.audio.asset_sha256},{"audio_pack_sha256",memory.audio.pack_sha256}}};
  vector_fields(row.fields,"",memory.position);rows.push_back(std::move(row));
 }
 ComponentRecord settings{d.definition_id,"authoring.ChapterSettings",1,{}};vector_fields(settings.fields,"hub_",d.hub.center);vector_fields(settings.fields,"hub_half_",d.hub.half_extent);vector_fields(settings.fields,"pencil_",d.pencil.center);vector_fields(settings.fields,"pencil_half_",d.pencil.half_extent);
 for(std::size_t i=0;i<d.hub_returns.size();++i)vector_fields(settings.fields,"hub_return."+std::to_string(i)+".",d.hub_returns[i]);for(std::size_t i=0;i<d.jenison_returns.size();++i)vector_fields(settings.fields,"jenison_return."+std::to_string(i)+".",d.jenison_returns[i]);
 if(d.format_version>=3){settings.fields["asset_profile"]=std::string(d.asset_profile==AssetContentProfile::warm_beginning?"warm_beginning":"legacy_v1");settings.fields["exposure"]=static_cast<double>(d.exposure);}
 for(const auto* cue:cues){const auto it=d.hints.find(cue);settings.fields["hint."+std::string(cue)]=it==d.hints.end()?std::string{}:it->second;}
 if(d.format_version==3&&d.asset_profile==AssetContentProfile::warm_beginning){for(const auto* key:{"view.initial_target","workshop.binding"}){const auto it=d.hints.find(key);settings.fields["hint."+std::string(key)]=it==d.hints.end()?std::string{}:it->second;}}
 rows.push_back(std::move(settings));return rows;
}
std::vector<ContentAuthoringRow> content_authoring_rows(const FirstBootContent& c){return definition_rows(c.definition());}
Bytes encode_content_edit(const ContentEditRequest& q){Writer w;const bool memories=std::any_of(q.edits.begin(),q.edits.end(),[](const auto& edit){return edit.index()>=7;});const bool placements=std::any_of(q.edits.begin(),q.edits.end(),[](const auto& edit){return edit.index()>=5;});w.number(memories?3:placements?2:1,2);w.text(q.id,true);w.number(q.expected_revision,8);fingerprint(q.expected_fingerprint);w.text(q.expected_fingerprint);w.text(q.label);need(!q.edits.empty()&&q.edits.size()<=256,"Typed edit count limit");w.number(q.edits.size(),4);
 for(const auto& edit:q.edits){
  w.number(edit.index(),1);
  if(const auto* set=std::get_if<ContentSetField>(&edit)){
   need(set->field.size()<=256,"Authoring field identifier limit");text(set->field);if(const auto* value=std::get_if<std::string>(&set->value)){Writer checked;checked.text(*value);}
   raw(w,gameplay_codec::encode_component({set->entity_id,"authoring.Field",1,{{set->field,set->value}}}));
  }
  else if(const auto* create_fixture=std::get_if<ContentCreateFixture>(&edit)){need(create_fixture->fixture.role==FixtureRole::legacy,"CreateFixture retains its17-field legacy wire contract; set workshop_role in the same group");raw(w,gameplay_codec::encode_component(fixture_record(create_fixture->fixture)));}
  else if(const auto* erase_fixture=std::get_if<ContentEraseFixture>(&edit)){need(is_uuid(erase_fixture->entity_id),"Invalid fixture target UUID");w.text(erase_fixture->entity_id);}
  else if(const auto* create_hardware=std::get_if<ContentCreateHardware>(&edit))raw(w,gameplay_codec::encode_component(durable_first_boot_components(create_hardware->entity).front()));
  else if(const auto* erase_hardware=std::get_if<ContentEraseHardware>(&edit)){need(is_uuid(erase_hardware->entity_id),"Invalid hardware target UUID");w.text(erase_hardware->entity_id);}
  else if(const auto* create_placement=std::get_if<ContentCreateAssetPlacement>(&edit))raw(w,gameplay_codec::encode_component(placement_record(create_placement->placement)));
  else if(const auto* erase_placement=std::get_if<ContentEraseAssetPlacement>(&edit)){need(is_uuid(erase_placement->entity_id),"Invalid placement target UUID");w.text(erase_placement->entity_id);}
  else if(const auto* create_memory=std::get_if<ContentCreateMemoryBinding>(&edit)){const auto row=memory_record(create_memory->memory);(void)memory_binding(row);raw(w,gameplay_codec::encode_component(row));}
  else{const auto& erase_memory=std::get<ContentEraseMemoryBinding>(edit);need(is_uuid(erase_memory.entity_id),"Invalid memory target UUID");w.text(erase_memory.entity_id);}
 }
 return w.data;
}
ContentEditRequest decode_content_edit(std::span<const unsigned char> b){need(b.size()<=creator_payload::maximum_bytes,"Typed request byte limit");Reader r{b};const auto version=r.number(2);need(version==1||version==2||version==3,"Unsupported typed edit request");ContentEditRequest q;q.id=r.text(true);q.expected_revision=r.number(8);q.expected_fingerprint=r.text(true);fingerprint(q.expected_fingerprint);q.label=r.text();const auto count=r.number(4);need(count>0&&count<=256,"Typed edit count limit");
 for(std::uint64_t i=0;i<count;++i){const auto tag=r.number(1);
  if(tag==0){auto f=gameplay_codec::decode_component(raw(r));need(f.type_id=="authoring.Field"&&f.version==1&&f.fields.size()==1,"Invalid typed field request");q.edits.push_back(ContentSetField{f.entity_id,f.fields.begin()->first,f.fields.begin()->second});}
  else if(tag==1)q.edits.push_back(ContentCreateFixture{fixture(gameplay_codec::decode_component(raw(r)))});
  else if(tag==2){auto id=r.text(true);need(is_uuid(id),"Invalid fixture UUID");q.edits.push_back(ContentEraseFixture{id});}
  else if(tag==3){const auto n=gameplay_codec::decode_component(raw(r));need(n.type_id=="firstboot.Node"&&n.version==1&&std::get<bool>(n.fields.at("alive")),"Invalid authored hardware");Entity e{std::get<std::string>(n.fields.at("alias")),std::get<std::string>(n.fields.at("name")),{},n.entity_id};for(const auto& [key,value]:n.fields)if(key!="alias"&&key!="name"&&key!="alive")e.fields.emplace(key,std::get<double>(value));q.edits.push_back(ContentCreateHardware{std::move(e)});}
  else if(tag==4){auto id=r.text(true);need(is_uuid(id),"Invalid hardware UUID");q.edits.push_back(ContentEraseHardware{id});}
  else if(tag==5){need(version>=2,"Placement edits require typed request version2 or later");q.edits.push_back(ContentCreateAssetPlacement{placement(gameplay_codec::decode_component(raw(r)))});}
  else if(tag==6){need(version>=2,"Placement edits require typed request version2 or later");auto id=r.text(true);need(is_uuid(id),"Invalid placement UUID");q.edits.push_back(ContentEraseAssetPlacement{id});}
  else if(tag==7){need(version==3,"Memory edits require typed request version3");q.edits.push_back(ContentCreateMemoryBinding{memory_binding(gameplay_codec::decode_component(raw(r)))});}
  else if(tag==8){need(version==3,"Memory edits require typed request version3");auto id=r.text(true);need(is_uuid(id),"Invalid memory UUID");q.edits.push_back(ContentEraseMemoryBinding{id});}
  else throw std::invalid_argument("Unknown typed edit kind");
 }
 end(r);need(encode_content_edit(q)==Bytes(b.begin(),b.end()),"Noncanonical typed edit bytes");return q;
}
namespace detail {
}
Bytes encode_scoped_content_edit(const ScopedContentEditRequest& q){Writer w;w.number(0x50424941,4);w.number(1,2);w.text(q.scope.project,true);w.text(q.scope.branch,true);need(is_uuid(q.scope.world_id)&&is_uuid(q.definition_id),"Invalid scoped authoring identity");w.text(q.scope.world_id,true);w.text(q.definition_id,true);raw(w,encode_content_edit(q.request));return w.data;}
ScopedContentEditRequest decode_scoped_content_edit(std::span<const unsigned char> bytes){need(bytes.size()<=creator_payload::maximum_bytes,"Scoped authoring byte limit");Reader r{bytes};need(r.number(4)==0x50424941&&r.number(2)==1,"Unsupported scoped authoring request");ScopedContentEditRequest q;q.scope.project=r.text(true);q.scope.branch=r.text(true);q.scope.world_id=r.text(true);q.definition_id=r.text(true);q.request=decode_content_edit(raw(r));end(r);need(encode_scoped_content_edit(q)==Bytes(bytes.begin(),bytes.end()),"Noncanonical scoped authoring request");return q;}
namespace detail {
struct ContentJournalEntry {unsigned kind;Bytes bytes;};
struct ContentReceipt {unsigned kind;Bytes bytes;std::uint64_t revision;};
struct ContentAuthoringData {
 CreatorScope scope;FirstBootContent baseline,current;std::set<std::string> reserved,known;
 std::uint64_t revision=0,high_version=0,saved_revision=0;bool saved=false;std::string checkpoint_id;
 std::vector<FirstBootContent> undo,redo;std::vector<ContentJournalEntry> journal;std::map<std::string,ContentReceipt> receipts;
 ContentAuthoringData(FirstBootContent c,CreatorScope s):scope(std::move(s)),baseline(c),current(c),high_version(c.definition().revision){}
};
}
namespace {
using Data=detail::ContentAuthoringData;
Bytes document(const Data& d,const std::string& checkpoint){Writer w;w.number(0x41424941,4);w.number(1,2);w.text(d.scope.project,true);w.text(d.scope.branch,true);w.text(checkpoint,true);raw(w,first_boot_content_encode(d.baseline));w.number(d.reserved.size(),4);for(const auto& id:d.reserved)w.text(id,true);w.number(d.journal.size(),4);for(const auto& e:d.journal){w.number(e.kind,1);raw(w,e.bytes);}w.number(d.revision,8);w.text(d.current.fingerprint());w.number(crc(w.data),4);return w.data;}
std::size_t charge(const Data& d){std::size_t bytes=first_boot_content_encode(d.current).size()+first_boot_content_encode(d.baseline).size()+d.known.size()*128;for(const auto& c:d.undo)bytes+=first_boot_content_encode(c).size();for(const auto& c:d.redo)bytes+=first_boot_content_encode(c).size();for(const auto& e:d.journal)bytes+=e.bytes.size()*2;need(bytes<=ContentAuthoringHost::maximum_state_bytes&&d.known.size()<=10000&&d.journal.size()<=ContentAuthoringHost::maximum_operations,"Authoring history/state budget exhausted");return bytes;}
std::size_t assess(const Data& d){return document(d,d.checkpoint_id.empty()?"00000000-0000-4000-8000-000000000000":d.checkpoint_id).size();}
void set_field(FirstBootContentDefinition& d,const ContentSetField& edit){
 // Read descriptors from the current staged definition, so grouped create/set
 // operations follow order without exposing runtime-only fields.
 const auto rows=definition_rows(d);const auto row=std::find_if(rows.begin(),rows.end(),[&](const auto& r){return r.entity_id==edit.entity_id;});need(row!=rows.end(),"Typed target UUID is absent");const auto field=row->fields.find(edit.field);const bool virtual_workshop_role=row->type_id=="authoring.Fixture"&&edit.field=="workshop_role";need(virtual_workshop_role?std::holds_alternative<bool>(edit.value):(field!=row->fields.end()&&field->second.index()==edit.value.index()),"Field is runtime-only, unknown or has the wrong type");if(const auto* n=std::get_if<double>(&edit.value))need(std::isfinite(*n),"Nonfinite authored number");
 for(auto& [alias,e]:d.hardware)if(e.persistent_id==edit.entity_id){(void)alias;if(edit.field=="name")e.name=std::get<std::string>(edit.value);else e.fields.at(edit.field)=std::get<double>(edit.value);return;}
 for(auto& r:d.initial_records)if(r.entity_id==edit.entity_id){if(edit.field.starts_with("isolation_")){assign(d.isolation_switch,edit.field.back(),edit.value);return;}r.fields.at(edit.field)=edit.value;if(r.type_id=="firstboot.Door"&&edit.field=="role")r.fields["unlocked"]=std::get<std::string>(edit.value)=="pencil";if(r.type_id=="firstboot.ChapterProgress"&&edit.field.starts_with("spawn_"))assign(d.hub_returns.front(),edit.field.back(),edit.value);return;}
 for(auto& f:d.fixtures)if(f.object.persistent_id==edit.entity_id){
  if(edit.field=="workshop_role"){
   const bool enabled=std::get<bool>(edit.value);
   need(!enabled||(d.format_version==3&&d.asset_profile==AssetContentProfile::warm_beginning),"Workshop fixture authoring requires AIBD3 warm_beginning");
   f.role=enabled?FixtureRole::workshop:FixtureRole::legacy;return;
  }
  if(edit.field=="inspection_text"||edit.field=="inspection_source"||edit.field=="inspection_action"){
   need(d.format_version==3&&d.asset_profile==AssetContentProfile::warm_beginning,"Inspection authoring requires AIBD3 warm_beginning");
   const auto key="inspect."+f.object.persistent_id+"."+edit.field.substr(11);const auto& value=std::get<std::string>(edit.value);
   if(value.empty())d.hints.erase(key);else d.hints[key]=value;
   return; // The complete final candidate validates all-empty or complete atomically.
  }
  const auto role=f.role;auto r=fixture_record(f);r.fields.at(edit.field)=edit.value;f=fixture(r);f.role=role;return;
 }
 for(auto& p:d.placements)if(p.entity_id==edit.entity_id){need(edit.field!="asset_id"&&edit.field!="asset_sha256"&&edit.field!="pack_sha256","Asset placement reference fields are immutable");auto r=placement_record(p);r.fields.at(edit.field)=edit.value;p=placement(r);return;}
 for(auto& companion:d.companions)if(companion.entity_id==edit.entity_id){
  if(edit.field=="name")companion.name=std::get<std::string>(edit.value);
  else if(edit.field=="initial_follow")companion.initial_follow=std::get<bool>(edit.value);
  else if(edit.field.starts_with("spawn_"))assign(companion.spawn,edit.field.back(),edit.value);
  else if(edit.field=="model_bound"){if(std::get<bool>(edit.value)){if(!companion.model)companion.model.emplace();}else companion.model.reset();}
  else{
   need(companion.model.has_value(),"Assign a companion model with a grouped bound flag and complete reference");
   if(edit.field=="model_asset_id")companion.model->asset_id=std::get<std::string>(edit.value);
   else if(edit.field=="model_asset_sha256")companion.model->asset_sha256=std::get<std::string>(edit.value);
   else if(edit.field=="model_pack_sha256")companion.model->pack_sha256=std::get<std::string>(edit.value);
   else throw std::invalid_argument("Unknown companion authoring field");
  }return;
 }
 for(auto& memory:d.memories)if(memory.entity_id==edit.entity_id){
  if(edit.field=="name")memory.name=std::get<std::string>(edit.value);
  else if(edit.field=="x"||edit.field=="y"||edit.field=="z")assign(memory.position,edit.field.back(),edit.value);
  else if(edit.field=="audio_asset_id")memory.audio.asset_id=std::get<std::string>(edit.value);
  else if(edit.field=="audio_asset_sha256")memory.audio.asset_sha256=std::get<std::string>(edit.value);
  else if(edit.field=="audio_pack_sha256")memory.audio.pack_sha256=std::get<std::string>(edit.value);
  else throw std::invalid_argument("Unknown memory authoring field");
  // Reference assignment is one grouped native operation. Final staged content
  // and its complete exact typed closure validate before Preview/Apply/Save.
  return;
 }
 need(edit.entity_id==d.definition_id,"Unknown typed target");const auto& key=edit.field;
 if(key=="asset_profile")throw std::invalid_argument("Content profile is selected for a new document, not changed through field edits");
 if(key=="exposure"){d.exposure=static_cast<float>(std::get<double>(edit.value));return;}
 if(key.starts_with("hint.")){const auto value=std::get<std::string>(edit.value);if(key=="hint.workshop.binding"){need(d.format_version==3&&d.asset_profile==AssetContentProfile::warm_beginning,"Workshop binding authoring requires AIBD3 warm_beginning");need(value.size()<=256,"Workshop binding exceeds256 bytes");}if(value.empty())d.hints.erase(key.substr(5));else d.hints[key.substr(5)]=value;return;}
 for(auto* list:{&d.hub_returns,&d.jenison_returns})for(std::size_t i=0;i<list->size();++i){const auto prefix=std::string(list==&d.hub_returns?"hub_return.":"jenison_return.")+std::to_string(i)+".";if(key==prefix+"x"||key==prefix+"y"||key==prefix+"z"){assign((*list)[i],key.back(),edit.value);if(list==&d.hub_returns&&i==0)for(auto& r:d.initial_records)if(r.type_id=="firstboot.ChapterProgress")r.fields["spawn_"+key.substr(key.size()-1)]=static_cast<double>(key.back()=='x'?(*list)[i].x:key.back()=='y'?(*list)[i].y:(*list)[i].z);return;}}
 if(key.starts_with("hub_half_"))assign(d.hub.half_extent,key.back(),edit.value);else if(key.starts_with("hub_"))assign(d.hub.center,key.back(),edit.value);else if(key.starts_with("pencil_half_"))assign(d.pencil.half_extent,key.back(),edit.value);else if(key.starts_with("pencil_"))assign(d.pencil.center,key.back(),edit.value);else throw std::invalid_argument("Unknown chapter settings field");
}
FirstBootContentPreview stage(Data& d,const ContentEditRequest& q){auto definition=d.current.definition();for(const auto& edit:q.edits){
 if(const auto* set=std::get_if<ContentSetField>(&edit))set_field(definition,*set);
 else if(const auto* create_fixture=std::get_if<ContentCreateFixture>(&edit)){need(create_fixture->fixture.role==FixtureRole::legacy,"CreateFixture requires a legacy17-field fixture; set workshop_role in the same group");const auto& id=create_fixture->fixture.object.persistent_id;need(is_uuid(id)&&d.known.insert(id).second,"Fixture UUID is known/retired or invalid");definition.fixtures.push_back(create_fixture->fixture);}
 else if(const auto* erase_fixture=std::get_if<ContentEraseFixture>(&edit)){const auto size=definition.fixtures.size();std::erase_if(definition.fixtures,[&](const auto& f){return f.object.persistent_id==erase_fixture->entity_id;});need(definition.fixtures.size()+1==size,"Fixture target UUID is absent");const auto prefix="inspect."+erase_fixture->entity_id+".";for(const auto* part:{"text","source","action"})definition.hints.erase(prefix+part);}
 else if(const auto* create_hardware=std::get_if<ContentCreateHardware>(&edit)){need(is_uuid(create_hardware->entity.persistent_id)&&d.known.insert(create_hardware->entity.persistent_id).second,"Hardware UUID is known/retired or invalid");need(definition.hardware.emplace(create_hardware->entity.id,create_hardware->entity).second,"Hardware alias already exists");}
 else if(const auto* erase_hardware=std::get_if<ContentEraseHardware>(&edit)){const auto found=std::find_if(definition.hardware.begin(),definition.hardware.end(),[&](const auto& p){return p.second.persistent_id==erase_hardware->entity_id;});need(found!=definition.hardware.end(),"Hardware target UUID is absent");definition.hardware.erase(found);}
 else if(const auto* create_placement=std::get_if<ContentCreateAssetPlacement>(&edit)){const auto& p=create_placement->placement;need(is_uuid(p.entity_id)&&d.known.insert(p.entity_id).second,"Placement UUID is known/retired or invalid");definition.format_version=std::max<std::uint16_t>(definition.format_version,2);definition.placements.push_back(p);}
 else if(const auto* erase_placement=std::get_if<ContentEraseAssetPlacement>(&edit)){const auto size=definition.placements.size();std::erase_if(definition.placements,[&](const auto& p){return p.entity_id==erase_placement->entity_id;});need(definition.placements.size()+1==size,"Placement target UUID is absent");}
 else if(const auto* create_memory=std::get_if<ContentCreateMemoryBinding>(&edit)){const auto& m=create_memory->memory;(void)memory_binding(memory_record(m));need(definition.asset_profile==AssetContentProfile::warm_beginning,"Memory binding requires warm-beginning content");need(d.known.insert(m.entity_id).second,"Memory UUID is known/retired");definition.format_version=std::max<std::uint16_t>(definition.format_version,3);definition.memories.push_back(m);}
 else{const auto& erase_memory=std::get<ContentEraseMemoryBinding>(edit);const auto size=definition.memories.size();std::erase_if(definition.memories,[&](const auto& m){return m.entity_id==erase_memory.entity_id;});need(definition.memories.size()+1==size,"Memory target UUID is absent");}
 }
 const auto unversioned=FirstBootContent::create(definition);need(unversioned.fingerprint()!=d.current.fingerprint(),"No authoring fields changed");need(d.high_version<std::numeric_limits<std::uint64_t>::max(),"Content revision exhausted");definition.revision=d.high_version+1;auto preview=first_boot_content_preview(d.current,std::move(definition));need(preview.status!=FirstBootContentPreviewStatus::rejected&&preview.candidate.has_value(),preview.message.c_str());d.undo.push_back(d.current);d.redo.clear();d.current=*preview.candidate;d.high_version=d.current.definition().revision;return preview;
}
void validate_legacy_asset_dependencies(const FirstBootContent& content,const std::filesystem::path& store){
 const auto& placements=content.definition().placements;if(placements.empty())return;
 need(!store.empty(),"An explicit asset store is required for placement publication");
 constexpr std::size_t geometry_budget=64u*1024u*1024u,vertex_budget=1000000;
 using Reference=std::tuple<std::string,std::string,std::string>;
 std::map<Reference,MeshAsset> assets;std::size_t charged=0,pack_charged=0;
 const auto charge_geometry=[&](std::size_t size){need(size<=geometry_budget-charged,"Placement resolved geometry exceeds 64 MiB");charged+=size;};
 for(const auto& p:placements){const Reference key{p.asset_id,p.asset_sha256,p.pack_sha256};if(assets.contains(key))continue;
  std::size_t pack_bytes=0;
  auto asset=load_stored_asset(store,{p.asset_id,p.asset_sha256,p.pack_sha256},&pack_bytes,asset_store_maximum_staged_bytes-pack_charged);
  pack_charged+=pack_bytes;
  charge_geometry(asset.vertices.size()*sizeof(AssetVertex));charge_geometry(asset.indices.size()*sizeof(std::uint32_t));charge_geometry(asset.triangle_materials.size()*sizeof(std::uint32_t));charge_geometry(asset.materials.size()*sizeof(MeshMaterial));
  charge_geometry(asset.name.size()+asset.asset_id.size()+asset.source_sha256.size());for(const auto& material:asset.materials)charge_geometry(material.name.size());
  assets.emplace(key,std::move(asset));
 }
 const auto baseline=first_boot_content_baseline(content);
 const GameplayStoreRecovery recovery{{"placement-validation",content.definition().world_id,"main",content.definition().definition_id,GameplayContext::temporary_play},baseline.revision,baseline.sequence,baseline.components};
 std::size_t vertices=mesh_from_snapshot(first_boot_content_scene(recovery,content)).vertices.size();need(vertices<=vertex_budget,"Base chapter exceeds the renderer vertex limit");
 for(const auto& p:placements){const auto& asset=assets.at(Reference{p.asset_id,p.asset_sha256,p.pack_sha256});need(asset.indices.size()<=vertex_budget-vertices,"Composed placement geometry exceeds renderer vertex limit");vertices+=asset.indices.size();
  // Per-placement validation checks transformed geometry/materials without
  // adding any boxes to the authoritative collision/picking scene.
  SceneMesh transformed;append_asset_mesh(transformed,asset,p.center,p.scale,p.rotation);
 }
}
void validate_asset_dependencies(const FirstBootContent& content,const std::filesystem::path& store){
 const auto& definition=content.definition();
 // Legacy publication remains visual-only. Modern admission resolves every
 // memory/character/visual dependency through its exact catalog role.
 if(definition.asset_profile==AssetContentProfile::legacy_v1){need(definition.memories.empty(),"Memory audio requires warm-beginning content profile");for(const auto& companion:definition.companions)need(!companion.model,"Character model requires warm-beginning content profile");validate_legacy_asset_dependencies(content,store);return;}
 need(definition.format_version>=3&&definition.asset_profile==AssetContentProfile::warm_beginning,"Unsupported content profile");
 const auto assets=load_first_boot_content_assets(content,store);
 const auto decoded=assets.decoded_bytes;
 const auto baseline=first_boot_content_baseline(content);
 const GameplayStoreRecovery recovery{{"placement-validation",definition.world_id,"main",definition.definition_id,GameplayContext::temporary_play},baseline.revision,baseline.sequence,baseline.components};
 const auto base=mesh_from_snapshot(first_boot_content_scene(recovery,content));std::size_t vertices=base.vertices.size(),expanded=0;need(vertices<=1000000,"Base chapter exceeds renderer vertex limit");TexturedScene textures;
 for(const auto& p:definition.placements){const auto& asset=assets.require({p.asset_id,p.asset_sha256,p.pack_sha256},FirstBootDependencyKind::visual);
  const auto& geometry=std::holds_alternative<MeshAsset>(asset.payload)?std::get<MeshAsset>(asset.payload):std::get<SurfaceMeshAsset>(asset.payload).geometry;
  need(geometry.indices.size()<=1000000-vertices,"Composed placement geometry exceeds renderer vertex limit");vertices+=geometry.indices.size();
  const auto bytes=geometry.indices.size()*(std::holds_alternative<SurfaceMeshAsset>(asset.payload)?sizeof(TexturedVertex):sizeof(SceneVertex));need(bytes<=asset_store_modern_staged_bytes-decoded-expanded,"Composed dependency residency exceeds128MiB");expanded+=bytes;
  if(const auto* surface=std::get_if<SurfaceMeshAsset>(&asset.payload))append_surface_scene(textures,*surface,p.center,p.scale,p.rotation);
  else{SceneMesh transformed;append_asset_mesh(transformed,geometry,p.center,p.scale,p.rotation);}
 }
}

Bytes read_file(const std::filesystem::path& path){const auto attr=GetFileAttributesW(path.c_str());need(attr!=INVALID_FILE_ATTRIBUTES&&!(attr&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY)),"Authoring slot is absent/redirected/not a file");std::ifstream in(path,std::ios::binary);need(in.good(),"Could not read authoring document");Bytes bytes(ContentAuthoringHost::maximum_file_bytes+1);in.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));bytes.resize(static_cast<std::size_t>(in.gcount()));need(in.eof()&&bytes.size()<=ContentAuthoringHost::maximum_file_bytes,"Authoring document read/size failure");return bytes;}
std::filesystem::path canonical_slot(const std::filesystem::path& path){need(path.has_filename()&&std::filesystem::is_directory(path.parent_path()),"Authoring save requires an existing parent directory");return std::filesystem::canonical(path.parent_path())/path.filename();}
struct Handle {HANDLE value=INVALID_HANDLE_VALUE;~Handle(){if(value!=INVALID_HANDLE_VALUE)CloseHandle(value);}void close(){if(value!=INVALID_HANDLE_VALUE){CloseHandle(value);value=INVALID_HANDLE_VALUE;}}};
}
struct ContentAuthoringHost::State {std::shared_ptr<const Data> document;std::shared_ptr<const ContentAuthoringSnapshot> view;std::string epoch=new_uuid();std::uint64_t generation=0;std::vector<std::weak_ptr<const ContentPreparedChange>> prepared;std::filesystem::path saved_path,asset_store;Bytes saved_bytes;bool replaying=false;};
ContentAuthoringSnapshot::ContentAuthoringSnapshot(std::shared_ptr<const Data> d):owner_(d),scope(d->scope),revision(d->revision),content(d->current),checkpoint_id(d->checkpoint_id),known_ids(d->known),undo_depth(d->undo.size()),redo_depth(d->redo.size()),receipt_count(d->receipts.size()),dirty(!d->saved||d->saved_revision!=d->revision){}
ContentPreparedChange::ContentPreparedChange(std::string owner,std::uint64_t generation,std::shared_ptr<const Data> after,std::shared_ptr<const ContentAuthoringSnapshot> view,FirstBootContentPreview deps,std::size_t charged,std::size_t encoded):owner_(std::move(owner)),generation_(generation),after_(std::move(after)),snapshot_(std::move(view)),dependencies_(std::move(deps)),charged_bytes_(charged),encoded_bytes_(encoded){}
std::shared_ptr<const ContentAuthoringSnapshot> ContentAuthoringHost::describe(std::shared_ptr<const Data> d){return std::shared_ptr<const ContentAuthoringSnapshot>(new ContentAuthoringSnapshot(std::move(d)));}
ContentAuthoringHost::ContentAuthoringHost(FirstBootContent c,std::string project,std::string branch,std::set<std::string> reserved):state_(std::make_unique<State>()){text(project);text(branch);auto d=std::make_shared<Data>(c,CreatorScope{project,branch,c.definition().world_id});d->reserved=std::move(reserved);d->known=identities(c);for(const auto& id:d->reserved){need(is_uuid(id),"Invalid reserved identity");d->known.insert(id);}charge(*d);assess(*d);state_->document=d;state_->view=describe(d);}
ContentAuthoringHost::~ContentAuthoringHost()=default;
ContentAuthoringHost::ContentAuthoringHost(ContentAuthoringHost&&) noexcept=default;
std::shared_ptr<const ContentAuthoringSnapshot> ContentAuthoringHost::snapshot()const noexcept{return state_->view;}
const std::string& ContentAuthoringHost::epoch_id()const noexcept{return state_->epoch;}
void ContentAuthoringHost::bind_asset_store(const std::filesystem::path& path){need(!path.empty(),"Asset store binding must be explicit");for(const auto& component:path)need(component!=L"..","Asset store binding cannot contain parent traversal");state_->asset_store=std::filesystem::absolute(path);}
ContentAuthoringResult ContentAuthoringHost::preview(const CreatorScope& scope,const ContentEditRequest& request){try{
 need(scope==state_->document->scope,"Foreign chapter authoring scope");const auto q=request;const auto bytes=encode_content_edit(q);const auto prior=state_->document->receipts.find(q.id);if(prior!=state_->document->receipts.end()){need(prior->second.kind==0&&prior->second.bytes==bytes,"Operation ID payload conflict");return {ContentAuthoringStatus::duplicate,"Original edit already accepted",prior->second.revision};}
 need(q.expected_revision==state_->view->revision&&q.expected_fingerprint==state_->view->content.fingerprint(),"Chapter authoring head/content conflict");need(state_->document->revision<std::numeric_limits<std::uint64_t>::max()-1&&state_->generation<std::numeric_limits<std::uint64_t>::max(),"Authoring head exhausted");
 std::erase_if(state_->prepared,[](const auto& p){return p.expired();});need(state_->prepared.size()<8,"Prepared chapter budget exhausted");auto d=std::make_shared<Data>(*state_->document);auto dependencies=stage(*d,q);if(!state_->replaying)validate_asset_dependencies(d->current,state_->asset_store);++d->revision;d->journal.push_back({0,bytes});d->receipts.emplace(q.id,detail::ContentReceipt{0,bytes,d->revision});const auto charged=charge(*d),encoded=assess(*d);std::size_t total=charged;for(const auto& p:state_->prepared)if(auto held=p.lock())total+=held->charged_bytes_;need(total<=maximum_state_bytes,"Prepared chapter storage budget exhausted");auto view=describe(d);auto prepared=ContentPreparedPtr(new ContentPreparedChange(state_->epoch,state_->generation,d,view,std::move(dependencies),charged,encoded));state_->prepared.push_back(prepared);return {ContentAuthoringStatus::prepared,"Private typed preview; changed content needs a new Play branch",d->revision,prepared};
 }catch(const std::bad_alloc&){throw;}catch(const std::exception& error){return {ContentAuthoringStatus::rejected,error.what(),state_->view->revision};}}
ContentAuthoringResult ContentAuthoringHost::apply(ContentPreparedPtr p){if(!p||p->owner_!=state_->epoch||p->generation_!=state_->generation)return {ContentAuthoringStatus::rejected,"Prepared chapter is stale/foreign",state_->view->revision};try{if(!state_->replaying)validate_asset_dependencies(p->after_->current,state_->asset_store);}catch(const std::bad_alloc&){throw;}catch(const std::exception& error){return {ContentAuthoringStatus::rejected,error.what(),state_->view->revision};}ContentAuthoringResult result{ContentAuthoringStatus::applied,"Grouped chapter edit applied",p->snapshot_->revision};state_->document=p->after_;state_->view=p->snapshot_;++state_->generation;state_->prepared.clear();return result;}
ContentAuthoringResult ContentAuthoringHost::apply(const CreatorScope& s,const ContentEditRequest& q){auto result=preview(s,q);if(result.status!=ContentAuthoringStatus::prepared)return result;return apply(result.change);}
ContentAuthoringResult ContentAuthoringHost::preview(const ScopedContentEditRequest& q){if(q.definition_id!=state_->document->current.definition().definition_id)return {ContentAuthoringStatus::rejected,"Foreign chapter definition",state_->view->revision};return preview(q.scope,q.request);}
ContentAuthoringResult ContentAuthoringHost::apply(const ScopedContentEditRequest& q){auto result=preview(q);return result.status==ContentAuthoringStatus::prepared?apply(result.change):result;}
ContentAuthoringResult ContentAuthoringHost::travel(const CreatorScope& scope,const ContentHistoryRequest& q){try{need(scope==state_->document->scope,"Foreign history scope");const auto bytes=history_bytes(q);const unsigned kind=q.redo?2u:1u;const auto prior=state_->document->receipts.find(q.id);if(prior!=state_->document->receipts.end()){need(prior->second.kind==kind&&prior->second.bytes==bytes,"History operation ID conflict");return {ContentAuthoringStatus::duplicate,"Original history operation already accepted",prior->second.revision};}
 need(q.expected_revision==state_->view->revision&&q.expected_fingerprint==state_->view->content.fingerprint(),"History head/content conflict");need(state_->document->revision<std::numeric_limits<std::uint64_t>::max()-1&&state_->generation<std::numeric_limits<std::uint64_t>::max(),"Authoring head exhausted");auto d=std::make_shared<Data>(*state_->document);auto& source=q.redo?d->redo:d->undo;auto& destination=q.redo?d->undo:d->redo;need(!source.empty(),"No history in that direction");destination.push_back(d->current);d->current=source.back();source.pop_back();++d->revision;d->journal.push_back({kind,bytes});d->receipts.emplace(q.id,detail::ContentReceipt{kind,bytes,d->revision});if(!state_->replaying)validate_asset_dependencies(d->current,state_->asset_store);charge(*d);assess(*d);auto view=describe(d);ContentAuthoringResult result{q.redo?ContentAuthoringStatus::redone:ContentAuthoringStatus::undone,"Chapter history restored exact content",d->revision};state_->document=d;state_->view=std::move(view);++state_->generation;state_->prepared.clear();return result;
 }catch(const std::bad_alloc&){throw;}catch(const std::exception& error){return {ContentAuthoringStatus::rejected,error.what(),state_->view->revision};}}
ContentAuthoringResult ContentAuthoringHost::save(const std::filesystem::path& input){std::filesystem::path temporary;try{validate_asset_dependencies(state_->document->current,state_->asset_store);const auto path=canonical_slot(input);need(state_->saved_path.empty()||state_->saved_path==path,"Save As requires an explicit new authoring document/branch");auto lock=path;lock+=L".lock";Handle held;held.value=CreateFileW(lock.c_str(),GENERIC_READ|GENERIC_WRITE,0,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);need(held.value!=INVALID_HANDLE_VALUE,"Authoring save is locked");BY_HANDLE_FILE_INFORMATION info{};need(GetFileInformationByHandle(held.value,&info)&&!(info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT),"Authoring lock redirects");
 if(state_->saved_path.empty())need(!std::filesystem::exists(path),"Authoring target already exists; open it explicitly");else need(read_file(path)==state_->saved_bytes,"Authoring document changed under this owner");
 need(state_->generation<std::numeric_limits<std::uint64_t>::max(),"Authoring generation exhausted");auto d=std::make_shared<Data>(*state_->document);d->checkpoint_id=new_uuid();d->saved=true;d->saved_revision=d->revision;auto bytes=document(*d,d->checkpoint_id);auto view=describe(d);auto saved_path=path;ContentAuthoringResult result{ContentAuthoringStatus::saved,"Chapter authoring journal saved",d->revision};temporary=path;temporary+=L"."+std::filesystem::path(new_uuid()).wstring()+L".tmp";Handle file;file.value=CreateFileW(temporary.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);need(file.value!=INVALID_HANDLE_VALUE,"Could not create authoring staging file");DWORD written=0;need(WriteFile(file.value,bytes.data(),static_cast<DWORD>(bytes.size()),&written,nullptr)&&written==bytes.size()&&FlushFileBuffers(file.value),"Could not flush authoring journal");file.close();const DWORD flags=MOVEFILE_WRITE_THROUGH|(state_->saved_path.empty()?0:MOVEFILE_REPLACE_EXISTING);need(MoveFileExW(temporary.c_str(),path.c_str(),flags)!=0,"Could not publish authoring journal");temporary.clear();state_->document=d;state_->view=std::move(view);state_->saved_path=std::move(saved_path);state_->saved_bytes=std::move(bytes);++state_->generation;state_->prepared.clear();return result;
 }catch(const std::bad_alloc&){if(!temporary.empty())std::filesystem::remove(temporary);throw;}catch(const std::exception& error){if(!temporary.empty()){std::error_code ignored;std::filesystem::remove(temporary,ignored);}return {ContentAuthoringStatus::rejected,error.what(),state_->view->revision};}}
ContentAuthoringHost ContentAuthoringHost::open(const std::filesystem::path& input,const std::string& project,const std::string& branch){const auto path=canonical_slot(input);auto bytes=read_file(path);need(bytes.size()>4,"Truncated authoring journal");Reader trailer{std::span<const unsigned char>(bytes).last(4)};need(trailer.number(4)==crc(std::span<const unsigned char>(bytes).first(bytes.size()-4)),"Authoring journal checksum mismatch");Reader r{std::span<const unsigned char>(bytes).first(bytes.size()-4)};need(r.number(4)==0x41424941&&r.number(2)==1,"Unsupported chapter authoring journal");const auto p=r.text(true),b=r.text(true),checkpoint=r.text(true);need(p==project&&b==branch&&is_uuid(checkpoint),"Foreign/invalid authoring document scope");auto content=first_boot_content_decode(raw(r));const auto count=r.number(4);need(count<=10000,"Reserved identity limit");std::set<std::string> reserved;for(std::uint64_t i=0;i<count;++i){auto id=r.text(true);need(is_uuid(id)&&reserved.insert(id).second,"Duplicate/invalid reserved UUID");}ContentAuthoringHost host(content,p,b,reserved);host.state_->replaying=true;const auto operations=r.number(4);need(operations<=maximum_operations,"Authoring journal operation limit");for(std::uint64_t i=0;i<operations;++i){const auto kind=r.number(1);auto body=raw(r);ContentAuthoringResult result=kind==0?host.apply(host.snapshot()->scope,decode_content_edit(body)):host.travel(host.snapshot()->scope,history_request(body));need(kind<=2&&((kind==0&&result.status==ContentAuthoringStatus::applied)||(kind==1&&result.status==ContentAuthoringStatus::undone)||(kind==2&&result.status==ContentAuthoringStatus::redone)),"Authoring journal replay failed");}
 const auto head=r.number(8);const auto expected=r.text(true);end(r);need(head==host.snapshot()->revision&&expected==host.snapshot()->content.fingerprint(),"Authoring journal head mismatch");auto d=std::make_shared<Data>(*host.state_->document);d->checkpoint_id=checkpoint;d->saved=true;d->saved_revision=d->revision;need(document(*d,checkpoint)==bytes,"Noncanonical authoring journal");host.state_->document=d;host.state_->view=describe(d);host.state_->saved_path=path;host.state_->saved_bytes=std::move(bytes);host.state_->replaying=false;return host;
}
}
