#include <aibs/first_boot_content.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace aibs;
int wmain(int argc,wchar_t** argv){
 try{
  if(argc!=2)throw std::runtime_error("Usage: aibs_content_play_fixture NEW_DIRECTORY");
  const std::filesystem::path directory(argv[1]);if(std::filesystem::exists(directory))throw std::runtime_error("Fixture directory must be new");
  CreatorSession source(first_boot_schema(),"managed-content-proof","edited");if(!seed_first_boot(source).ok)throw std::runtime_error("Fixture seed failed");
  auto definition=FirstBootContent::from_template(source).definition();++definition.revision;
  for(auto& r:definition.initial_records){
   if(r.type_id=="firstboot.Door"&&std::get<std::string>(r.fields.at("role"))=="main")r.fields["x"]=-32.5;
   if(r.type_id=="firstboot.PowerFault")r.fields["socket_x"]=-41.5;
   if(r.type_id=="firstboot.NPCQuest")r.fields["x"]=-39.5;
  }
  for(auto& f:definition.fixtures)if(f.object.name=="Pencil Room writing desk"||f.object.name=="Pencil and blank page")f.object.center.x+=.5f;
  definition.hints["adam.live_fault"]="Authored Adam hint: The edited world remembers. Start with what still responds.";
  definition.hints["adam.danger"]="Authored Adam hint: Take the safe edge of this edited fault.";
  const auto content=FirstBootContent::create(definition);std::filesystem::create_directories(directory);
  auto write=[&](const char* name,const FirstBootContent& value){const auto bytes=first_boot_content_encode(value);std::ofstream file(directory/name,std::ios::binary);file.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));if(!file)throw std::runtime_error("Fixture output failed");};
  write("definition.aibd",content);++definition.revision;definition.hints["adam.live_fault"]="Authored Adam hint: A different immutable revision.";write("wrong.aibd",FirstBootContent::create(definition));
  std::cout<<"Canonical moved door/socket/NPC/desk content fixture exported\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
