#include <aibs/image_assets.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
void need(bool b){if(!b)throw std::runtime_error("Image contract failed");}
template<class F>void reject(F f){bool failed=false;try{f();}catch(const std::invalid_argument&){failed=true;}need(failed);}
int main(int argc,char**argv){try{
 need(argc==2);std::ifstream in(argv[1],std::ios::binary);std::vector<unsigned char> source((std::istreambuf_iterator<char>(in)),{});
 auto color=decode_png_image(source,ImageSemantic::srgb_color);need(color.levels.size()==2);need(color.levels[0].width==2&&color.levels[0].height==2);need(color.levels[0].rgba[0]==255);need(color.levels[1].rgba[0]>=187&&color.levels[1].rgba[0]<=189);need(image_resident_bytes(color)==20);
 auto linear=decode_png_image(source,ImageSemantic::linear_data);need(linear.levels[1].rgba[0]==128);
 reject([&]{decode_png_image(source,ImageSemantic::srgb_color,19);});reject([&]{decode_png_image({},ImageSemantic::linear_data);});
 auto corrupt=source;corrupt[0]=0;reject([&]{decode_png_image(corrupt,ImageSemantic::linear_data);});
 auto bad=color;bad.levels[1].rgba.pop_back();reject([&]{validate_image_asset(bad);});
 bad=color;bad.levels.pop_back();reject([&]{validate_image_asset(bad);});
 ImageAsset odd{ImageSemantic::linear_data,{{3,1,{0,0,0,255,255,255,255,255,255,255,255,255}}}};
 generate_image_mips(odd);need(odd.levels[1].rgba[0]==170);validate_image_asset(odd);
 ImageAsset normal{ImageSemantic::normal_map,{{2,1,{255,128,128,255,128,255,128,255}}}};generate_image_mips(normal);need(normal.levels[1].rgba[0]>210&&normal.levels[1].rgba[1]>210);validate_image_asset(normal);
 const auto saved=color;reject([&]{generate_image_mips(color,19);});need(color==saved);
 std::cout<<"PASS image decode, budgets, linear/sRGB mips, normal maps and rollback\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
