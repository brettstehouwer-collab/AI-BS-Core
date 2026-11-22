#include "../apps/memory_content_budget.hpp"
#include <iostream>
#include <stdexcept>
using namespace aibs;
int main(){try{
 unsigned checks=0;auto need=[&](bool value,const char* why){++checks;if(!value)throw std::runtime_error(why);};
 SceneMesh mesh;need(memory_scene_mesh_bytes(mesh)==0,"Empty projection must have no data allocation");
 mesh.vertices.reserve(900000);mesh.vertices.resize(3);mesh.landmarks.reserve(7);mesh.landmarks.emplace_back(400,'x');
 const auto exact=mesh.vertices.capacity()*sizeof(SceneVertex)+mesh.landmarks.capacity()*sizeof(std::string)+mesh.landmarks.front().capacity()+1;
 need(memory_scene_mesh_bytes(mesh)==exact,"Composed mesh capacity and landmark text charge must be exact");
 need(exact>32u*1024u*1024u,"Large retained capacity must not be hidden by logical vertex count");
 constexpr std::size_t limit=128u*1024u*1024u;const auto other=limit-exact-65536;
 need(memory_scene_gpu_remainder(other,mesh)==65536,"CPU projection must reduce joint profile before GPU admission");
 need(memory_scene_gpu_remainder(limit-exact,mesh)==0,"Exact CPU-only threshold must succeed");
 bool rejected=false;try{(void)memory_scene_gpu_remainder(limit-exact+1,mesh);}catch(const std::invalid_argument&){rejected=true;}need(rejected,"One byte over combined profile must reject");
 mesh={};need(memory_scene_mesh_bytes(mesh)==0,"Released startup mesh must relinquish retained capacity");
 std::cout<<"PASS "<<checks<<" composed memory scene budget checks\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
