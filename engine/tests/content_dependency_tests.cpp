#include <aibs/content_dependencies.hpp>
#include <aibs/first_boot.hpp>
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <iomanip>
#include <algorithm>
using namespace aibs;
namespace {
std::size_t checks=0;
void need(bool b,const char* m){++checks;if(!b)throw std::runtime_error(m);}
template<class F>void reject(F f,const char* m){bool bad=false;try{f();}catch(const std::invalid_argument&){bad=true;}need(bad,m);}
AssetPackReference reference(char a,char p){return {new_uuid(),std::string(64,a),std::string(64,p)};}
FirstBootAssetPlacement placement(const AssetPackReference& r){return {new_uuid(),"Synthetic part",r.asset_id,r.asset_sha256,r.pack_sha256,{-35,.4f,10},{1,1,1},{},true};}
}
int main(){try{
 CreatorSession source(first_boot_schema(),"dependency-test","main");need(seed_first_boot(source).ok,"Seed failed");const auto old=FirstBootContent::from_template(source);need(first_boot_content_dependencies(old).empty(),"Legacy chapter invented dependencies");
 auto d=old.definition();d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;const auto visual=reference('1','2'),model=reference('3','4'),audio=reference('5','6');
 d.placements={placement(visual),placement(visual)};FirstBootCompanionBinding guide;guide.entity_id=new_uuid();guide.name="Adam memory";guide.spawn=d.jenison_returns.front();guide.spawn.x+=2;guide.model=model;d.companions={guide};d.memories={{new_uuid(),"Optional original recording",d.jenison_returns.front(),audio}};
 const auto authored=FirstBootContent::create(d);const auto deps=first_boot_content_dependencies(authored);
 need(deps.size()==3,"Complete closure omitted nonplacement bindings or failed deduplication");
 need(deps[0]==FirstBootDependency{visual,FirstBootDependencyKind::visual}&&deps[1]==FirstBootDependency{model,FirstBootDependencyKind::character}&&deps[2]==FirstBootDependency{audio,FirstBootDependencyKind::audio},"Closure identity/kind/order differs from native declarations");
 need(first_boot_content_dependencies(first_boot_content_decode(first_boot_content_encode(authored)))==deps,"AIBD3 roundtrip changes complete closure");
 auto reverse=d;std::reverse(reverse.placements.begin(),reverse.placements.end());need(first_boot_content_dependencies(FirstBootContent::create(reverse))==deps,"Visible row ordering changes canonical closure");
 auto conflict=d;conflict.companions[0].model=visual;reject([&]{(void)first_boot_content_dependencies(FirstBootContent::create(conflict));},"Same pack interpreted as visual and character");
 conflict=d;conflict.memories[0].audio=model;reject([&]{(void)first_boot_content_dependencies(FirstBootContent::create(conflict));},"Same pack interpreted as character and audio");
 conflict=d;conflict.placements[1].asset_id=new_uuid();reject([&]{(void)first_boot_content_dependencies(FirstBootContent::create(conflict));},"Conflicting asset UUID for one pack admitted");
 auto many=old.definition();many.format_version=3;many.asset_profile=AssetContentProfile::warm_beginning;
 for(unsigned i=0;i<33;++i){std::ostringstream digest;digest<<std::hex<<std::setw(64)<<std::setfill('0')<<i+1;AssetPackReference r{new_uuid(),std::string(64,'1'),digest.str()};many.placements.push_back(placement(r));}
 reject([&]{(void)first_boot_content_dependencies(FirstBootContent::create(many));},"Closure exceeded32unique packs");
 std::cout<<"PASS "<<checks<<" complete native dependency contracts\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
