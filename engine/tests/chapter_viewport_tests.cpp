#include <aibs/chapter_viewport.hpp>
#include <aibs/content_authoring.hpp>
#include <iostream>

namespace {
void need(bool condition,const char* why){if(!condition)throw std::runtime_error(why);}
template<class F>void rejects(F f,const char* why){bool bad=false;try{f();}catch(const std::exception&){bad=true;}need(bad,why);}
std::vector<unsigned char> packet(const aibs::FirstBootContent& content,std::string world={},std::string selected={}){
 aibs::creator_payload::detail::Writer w;w.number(0x56424941,4);w.number(1,2);w.number(2,1);
 w.text("11111111-1111-4111-8111-111111111111");w.text("BS chapter");w.text("main");
 w.text(world.empty()?content.definition().world_id:world);w.text("");w.number(17,8);w.text(selected);
 const auto bytes=aibs::first_boot_content_encode(content);w.number(bytes.size(),4);w.data.insert(w.data.end(),bytes.begin(),bytes.end());return w.data;
}
}
int main(){try{
 aibs::CreatorSession source(aibs::first_boot_schema(),"BS chapter","main");need(aibs::seed_first_boot(source).ok,"seed");
 auto definition=aibs::FirstBootContent::from_template(source).definition();
 auto& fixture=definition.fixtures.front();fixture.object.name="Authored preview fixture";fixture.object.color={.9f,.1f,.2f};
 const auto id=fixture.object.persistent_id;const auto content=aibs::FirstBootContent::create(definition);const auto bytes=packet(content,{},id);
 const auto snapshot=aibs::decode_chapter_viewport_snapshot(bytes);need(snapshot.revision==17&&snapshot.content.fingerprint()==content.fingerprint(),"typed identity/head/immutable definition");
 const auto scene=aibs::chapter_viewport_scene(snapshot);need(scene.world_id==definition.world_id&&scene.revision==17,"authoring head projected");
 const auto found=std::find_if(scene.objects.begin(),scene.objects.end(),[&](const auto& object){return object.persistent_id==id;});
 need(found!=scene.objects.end()&&found->name=="Authored preview fixture"&&found->color==fixture.object.color,"actual authored fixture projected");
 need(!aibs::mesh_from_snapshot(scene).vertices.empty(),"real native scene mesh");
 for(const auto& object:scene.objects)if(object.selectable){const auto rows=aibs::content_authoring_rows(content);need(std::any_of(rows.begin(),rows.end(),[&](const auto& row){return row.entity_id==object.persistent_id;}),"only published typed IDs selectable");}
 for(const auto n:std::vector<std::size_t>{0,4,6,7,bytes.size()/2,bytes.size()-1})rejects([&]{(void)aibs::decode_chapter_viewport_snapshot(std::span(bytes).first(n));},"truncated typed packet accepted");
 auto bad=bytes;bad.push_back(0);rejects([&]{(void)aibs::decode_chapter_viewport_snapshot(bad);},"trailing accepted");
 bad=bytes;bad[6]=3;rejects([&]{(void)aibs::decode_chapter_viewport_snapshot(bad);},"unknown mode accepted");
 bad=bytes;bad.back()^=1;rejects([&]{(void)aibs::decode_chapter_viewport_snapshot(bad);},"corrupt definition accepted");
 bad=bytes;const auto& duplicate=definition.fixtures.at(1).object.persistent_id;const auto position=std::search(bad.begin(),bad.end(),duplicate.begin(),duplicate.end());need(position!=bad.end(),"duplicate fixture test target");std::copy(id.begin(),id.end(),position);rejects([&]{(void)aibs::decode_chapter_viewport_snapshot(bad);},"duplicate content UUID accepted");
 rejects([&]{(void)aibs::decode_chapter_viewport_snapshot(packet(content,"22222222-2222-4222-8222-222222222222"));},"foreign content world accepted");
 rejects([&]{(void)aibs::decode_chapter_viewport_snapshot(packet(content,{},"33333333-3333-4333-8333-333333333333"));},"foreign selection accepted");
 std::vector<unsigned char> oversized(aibs::chapter_viewport_maximum_bytes+1);rejects([&]{(void)aibs::decode_chapter_viewport_snapshot(oversized);},"overbound accepted");
 std::cout<<"Typed chapter viewport envelope, immutable projection, scope and bounds passed\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
