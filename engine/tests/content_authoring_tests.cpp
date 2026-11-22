#include <aibs/content_authoring.hpp>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {void require(bool value,const char* why){if(!value)throw std::runtime_error(why);}}
int wmain(int argc,wchar_t** argv){try{
 if(argc>=3){const auto directory=std::filesystem::path(argv[2]);const auto file=directory/"chapter.aiba";
  if(std::wstring(argv[1])==L"--proposal-context"&&argc==3){auto owner=[&]{if(std::filesystem::exists(file))return ContentAuthoringHost::open(file,"typed-proposal-proof","main");CreatorSession source(first_boot_schema(),"typed-proposal-proof","main");require(seed_first_boot(source).ok,"proposal seed");ContentAuthoringHost created(FirstBootContent::from_template(source),"typed-proposal-proof","main");require(created.save(file).status==ContentAuthoringStatus::saved,"proposal baseline save");return created;};auto host=owner();const auto snapshot=host.snapshot();std::string target;for(const auto& r:snapshot->content.definition().initial_records)if(r.type_id=="firstboot.Door"&&std::get<std::string>(r.fields.at("role"))=="main")target=r.entity_id;
   std::ofstream context(directory/"context.json");context<<"{\"project\":\"typed-proposal-proof\",\"branch\":\"main\",\"world_id\":\""<<snapshot->scope.world_id<<"\",\"definition_id\":\""<<snapshot->content.definition().definition_id<<"\",\"revision\":"<<snapshot->revision<<",\"fingerprint\":\""<<snapshot->content.fingerprint()<<"\",\"fields\":[[\""<<target<<"\",\"x\",\"number\"]]}";require(context.good(),"proposal context export");return 0;}
  if(std::wstring(argv[1])==L"--proposal-apply"&&argc==4){std::ifstream input(std::filesystem::path(argv[3]),std::ios::binary);std::vector<unsigned char> bytes(ContentAuthoringHost::maximum_file_bytes+1);input.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));bytes.resize(static_cast<std::size_t>(input.gcount()));require(input.eof()&&bytes.size()<=ContentAuthoringHost::maximum_file_bytes,"proposal input read");auto host=ContentAuthoringHost::open(file,"typed-proposal-proof","main");auto result=host.apply(decode_scoped_content_edit(bytes));require(result.status==ContentAuthoringStatus::applied||result.status==ContentAuthoringStatus::duplicate,result.message.c_str());if(result.status==ContentAuthoringStatus::applied)require(host.save(file).status==ContentAuthoringStatus::saved,"proposal publication");std::cout<<(result.status==ContentAuthoringStatus::duplicate?"duplicate ":"applied ")<<host.snapshot()->revision<<' '<<host.snapshot()->content.fingerprint()<<'\n';return 0;}
  throw std::runtime_error("Unknown authoring proof mode");
 }
 CreatorSession source(first_boot_schema(),"typed-author","main");require(seed_first_boot(source).ok,"seed");
 ContentAuthoringHost host(FirstBootContent::from_template(source),"typed-author","main");
 const auto original=host.snapshot();const auto& records=original->content.definition().initial_records;
 const auto door=std::find_if(records.begin(),records.end(),[](const auto& r){return r.type_id=="firstboot.Door"&&std::get<std::string>(r.fields.at("role"))=="main";});
 ContentEditRequest edit{"move-main",original->revision,original->content.fingerprint(),"Moved main aperture",{ContentSetField{door->entity_id,"x",-32.5}}};
 const auto preview=host.preview(original->scope,edit);require(preview.status==ContentAuthoringStatus::prepared&&preview.change,"typed preview");
 require(host.snapshot()==original,"preview private");require(preview.change->dependencies().collision_rebuild&&!preview.change->dependencies().save_compatible,"actual content dependency/new Play branch");
 require(host.apply(preview.change).status==ContentAuthoringStatus::applied,"publish grouped edit");
 require(host.apply(original->scope,edit).status==ContentAuthoringStatus::duplicate,"exact old edit retry");
 require(host.apply(preview.change).status==ContentAuthoringStatus::rejected,"published prepared handle cannot be applied twice");
 auto conflict=edit;std::get<ContentSetField>(conflict.edits[0]).value=-32.6;require(host.apply(original->scope,conflict).status==ContentAuthoringStatus::rejected,"same operation ID different bytes");
 auto live=host.snapshot();ContentHistoryRequest undo{"undo-main",live->revision,live->content.fingerprint(),false};
 require(host.travel(live->scope,undo).status==ContentAuthoringStatus::undone,"typed undo");require(host.snapshot()->content.fingerprint()==original->content.fingerprint(),"undo restores exact content");
 require(host.apply(original->scope,edit).status==ContentAuthoringStatus::duplicate&&host.snapshot()->content.fingerprint()==original->content.fingerprint(),"Retry after undo never resurrects the reverted change");
 live=host.snapshot();require(host.travel(live->scope,{"redo-main",live->revision,live->content.fingerprint(),true}).status==ContentAuthoringStatus::redone,"typed redo");
 const auto id=new_uuid();FirstBootContentFixture fixture{{id,"Seat study",{-35,.4f,10},{.4f,.4f,.4f},{.3f,.2f,.1f}},-1};
 auto initially_blocked=fixture;initially_blocked.object.center={-32.5f,.4f,4};
 live=host.snapshot();require(host.apply(live->scope,{"seat",live->revision,live->content.fingerprint(),"Add and place seat atomically",{ContentCreateFixture{initially_blocked},ContentSetField{id,"x",-35.0},ContentSetField{id,"z",10.0}}}).status==ContentAuthoringStatus::applied,"grouped fixture creation validates final geometry only");
 live=host.snapshot();require(host.apply(live->scope,{"remove-seat",live->revision,live->content.fingerprint(),"Remove seat",{ContentEraseFixture{id}}}).status==ContentAuthoringStatus::applied,"fixture removal");
 live=host.snapshot();require(host.apply(live->scope,{"reuse-seat",live->revision,live->content.fingerprint(),"No recycled identity",{ContentCreateFixture{fixture}}}).status==ContentAuthoringStatus::rejected,"retired ID not reusable");
 const auto directory=std::filesystem::temp_directory_path()/("aibs-author-"+new_uuid());std::filesystem::create_directory(directory);const auto file=directory/"chapter.aiba";
 require(host.save(file).status==ContentAuthoringStatus::saved,"atomic authoring journal save");
 auto reopened=ContentAuthoringHost::open(file,"typed-author","main");require(reopened.snapshot()->revision==host.snapshot()->revision&&reopened.snapshot()->known_ids.contains(id),"reopen restores head/retired IDs");
 require(reopened.apply(original->scope,edit).status==ContentAuthoringStatus::duplicate,"saved receipt retry does not repeat effect");
 live=reopened.snapshot();require(reopened.travel(live->scope,{"undo-after-open",live->revision,live->content.fingerprint(),false}).status==ContentAuthoringStatus::undone,"undo survives reopen");
 live=reopened.snapshot();ContentEditRequest forbidden{"fake-progress",live->revision,live->content.fingerprint(),"Reject runtime state",{ContentSetField{door->entity_id,"unlocked",true}}};
 require(reopened.apply(live->scope,forbidden).status==ContentAuthoringStatus::rejected,"authoring cannot modify runtime-only flags");
 require(reopened.save(file).status==ContentAuthoringStatus::saved,"owner saves updated history");require(host.save(file).status==ContentAuthoringStatus::rejected,"stale second owner cannot overwrite newer file");
 const auto corrupt=directory/"corrupt.aiba";std::filesystem::copy_file(file,corrupt);{std::fstream changed(corrupt,std::ios::binary|std::ios::in|std::ios::out);changed.put('X');}
 bool refused=false;try{auto damaged=ContentAuthoringHost::open(corrupt,"typed-author","main");(void)damaged;}catch(const std::exception&){refused=true;}require(refused,"damaged saved authoring journal rejected");
 std::cout<<"Typed private preview, grouped edit, exact retries, history, retired identities and durable authoring journal passed\n";return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
