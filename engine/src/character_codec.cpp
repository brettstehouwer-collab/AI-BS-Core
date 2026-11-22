#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/character_codec.hpp>
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <stdexcept>
namespace aibs {namespace {
constexpr std::array<std::byte,8> magic{std::byte{'A'},std::byte{'I'},std::byte{'B'},std::byte{'C'},std::byte{'h'},std::byte{'a'},std::byte{'r'},std::byte{'2'}};
constexpr std::size_t header_bytes=48;
void need(bool b,const char* message){if(!b)throw std::invalid_argument(message);}
std::size_t add(std::size_t a,std::size_t b){need(b<=std::numeric_limits<std::size_t>::max()-a,"Character decoded accounting overflow");return a+b;}
std::size_t multiply(std::size_t a,std::size_t b){need(!a||b<=std::numeric_limits<std::size_t>::max()/a,"Character decoded accounting overflow");return a*b;}
std::array<std::byte,32> digest(std::span<const std::byte> bytes){
 need(bytes.size()<=character_asset_max_input_bytes,"Character hash input exceeds bound");
 struct Algorithm{BCRYPT_ALG_HANDLE value=nullptr;~Algorithm(){if(value)BCryptCloseAlgorithmProvider(value,0);}} algorithm;
 if(BCryptOpenAlgorithmProvider(&algorithm.value,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)throw std::runtime_error("Character SHA-256 provider unavailable");
 std::array<std::byte,32> result{};
 if(BCryptHash(algorithm.value,nullptr,0,const_cast<PUCHAR>(reinterpret_cast<const unsigned char*>(bytes.data())),static_cast<ULONG>(bytes.size()),reinterpret_cast<PUCHAR>(result.data()),static_cast<ULONG>(result.size()))<0)throw std::runtime_error("Character SHA-256 computation failed");
 return result;
}
struct Writer {
 std::vector<std::byte> data;
 void integer(std::uint32_t value){for(unsigned shift=0;shift<32;shift+=8)data.push_back(static_cast<std::byte>((value>>shift)&255));}
 void half(std::uint16_t value){data.push_back(static_cast<std::byte>(value&255));data.push_back(static_cast<std::byte>(value>>8));}
 void scalar(float value){integer(value==0?0:std::bit_cast<std::uint32_t>(value));}
 void bytes(std::span<const std::byte> value){data.insert(data.end(),value.begin(),value.end());}
 void text(std::string_view value){integer(static_cast<std::uint32_t>(value.size()));bytes({reinterpret_cast<const std::byte*>(value.data()),value.size()});}
 void vector(Vec3 value){scalar(value.x);scalar(value.y);scalar(value.z);}
 void transform(const CharacterJointTransform& value){vector(value.translation);scalar(value.rotation.x);scalar(value.rotation.y);scalar(value.rotation.z);scalar(value.rotation.w);vector(value.scale);}
};
struct Reader {
 std::span<const std::byte> data;
 std::span<const std::byte> take(std::size_t count){need(count<=data.size(),"Truncated character payload");auto result=data.first(count);data=data.subspan(count);return result;}
 std::uint32_t integer(){const auto b=take(4);std::uint32_t value=0;for(unsigned shift=0;shift<32;shift+=8)value|=std::to_integer<std::uint32_t>(b[shift/8])<<shift;return value;}
 std::uint16_t half(){const auto b=take(2);return static_cast<std::uint16_t>(std::to_integer<unsigned>(b[0])|(std::to_integer<unsigned>(b[1])<<8));}
 float scalar(){const auto bits=integer();need(bits!=0x80000000,"Noncanonical character signed zero");const auto value=std::bit_cast<float>(bits);need(std::isfinite(value),"Nonfinite character scalar");return value;}
 std::string_view text(std::size_t maximum){const auto n=integer();need(n>0&&n<=maximum,"Character text length exceeds bound");const auto b=take(n);return {reinterpret_cast<const char*>(b.data()),b.size()};}
 std::size_t count(std::size_t maximum){const auto n=integer();need(n<=maximum,"Character count exceeds profile");return n;}
 void reserved(){need(integer()==0,"Unknown character reserved flags");}
 Vec3 vector(){return {scalar(),scalar(),scalar()};}
 CharacterJointTransform transform(){CharacterJointTransform t;t.translation=vector();t.rotation={scalar(),scalar(),scalar(),scalar()};t.scale=vector();(void)character_transform_matrix(t);return t;}
};
struct Budget {
 std::size_t bytes=sizeof(CharacterAsset);
 void charge(std::size_t value){bytes=add(bytes,value);need(bytes<=character_maximum_decoded_bytes,"Decoded character exceeds64MiB");}
 void text(std::size_t size){charge(add(std::max<std::size_t>(15,size),1));}
};
void label(std::string_view name){
 need(std::none_of(name.begin(),name.end(),[](unsigned char c){return c<32||c==127;}),"Invalid character text label");
 need(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,name.data(),static_cast<int>(name.size()),nullptr,0)>0,"Character text label must be UTF-8");
}
void identity(std::string_view id,std::string_view sha){
 need(id.size()==36&&id[14]=='4'&&(id[19]=='8'||id[19]=='9'||id[19]=='a'||id[19]=='b'),"Invalid character UUID");
 const auto hex=[](char c){return(c>='0'&&c<='9')||(c>='a'&&c<='f');};
 for(std::size_t i=0;i<id.size();++i)need(i==8||i==13||i==18||i==23?id[i]=='-':hex(id[i]),"Noncanonical character UUID");
 need(sha.size()==64&&std::all_of(sha.begin(),sha.end(),hex),"Invalid character source digest");
}
void vertex(const CharacterVertex& v,std::size_t joints){
 const auto bounded=[](float f){return std::abs(static_cast<double>(f))<=1e6;};
 const auto unit=[](float f){return f>=0&&f<=1;};
 need(bounded(v.position.x)&&bounded(v.position.y)&&bounded(v.position.z)&&bounded(v.u)&&bounded(v.v),"Character vertex/UV outside bounds");
 const double n=static_cast<double>(v.normal.x)*v.normal.x+static_cast<double>(v.normal.y)*v.normal.y+static_cast<double>(v.normal.z)*v.normal.z;
 need(std::abs(n-1)<=1e-4&&unit(v.color.x)&&unit(v.color.y)&&unit(v.color.z)&&v.emission>=0&&v.emission<=16,"Invalid character vertex normal/color/emission");
 double sum=0;for(unsigned i=0;i<4;++i){need(v.joints[i]<joints&&unit(v.weights[i]),"Invalid character joint index/weight");sum+=v.weights[i];}need(std::abs(sum-1)<=1e-5,"Invalid character weight sum");
}
// First pass scans all variable lengths, scalar encodings and decoded charges
// without creating owned arrays. Only a complete successful preflight permits
// the second pass to reserve/copy data. Neither pass uses external resources.
void parse(std::span<const std::byte> payload,CharacterAsset* output,std::uint32_t version){
 Reader r{payload};Budget budget;
 const auto id=r.text(36),name=r.text(128),source=r.text(64);identity(id,source);label(name);budget.text(id.size());budget.text(name.size());budget.text(source.size());
 const auto vertices=r.count(character_maximum_vertices),indices=r.count(character_maximum_indices),joints=r.count(character_maximum_joints),clips=r.count(character_maximum_clips),images=r.count(character_asset_maximum_images),materials=r.count(character_asset_maximum_materials),draws=r.count(character_asset_maximum_draws);r.reserved();
 need(vertices>0&&indices>0&&indices%3==0&&joints>0&&materials>0&&draws>0,"Character requires geometry/skeleton/materials/draws");
 const auto fixed=add(multiply(vertices,72),add(multiply(indices,4),add(multiply(joints,108),add(multiply(materials,version==3?28u:24u),multiply(draws,12)))));
 need(fixed<=r.data.size(),"Character declared fixed arrays exceed remaining payload");
 budget.charge(add(multiply(vertices,sizeof(CharacterVertex)),add(multiply(indices,sizeof(std::uint32_t)),add(multiply(joints,sizeof(CharacterJoint)),add(multiply(clips,sizeof(CharacterClip)),add(multiply(images,sizeof(ImageAsset)),add(multiply(materials,sizeof(CharacterMaterial)),multiply(draws,sizeof(CharacterDraw)))))))));
 if(output){output->asset_id=id;output->name=name;output->source_sha256=source;output->mesh.vertices.reserve(vertices);output->mesh.indices.reserve(indices);output->mesh.joints.reserve(joints);output->mesh.clips.reserve(clips);output->images.reserve(images);output->materials.reserve(materials);output->draws.reserve(draws);}
 for(std::size_t i=0;i<vertices;++i){CharacterVertex v;v.position=r.vector();v.normal=r.vector();v.color=r.vector();v.emission=r.scalar();v.u=r.scalar();v.v=r.scalar();for(auto& j:v.joints)j=r.half();for(auto& w:v.weights)w=r.scalar();vertex(v,joints);if(output)output->mesh.vertices.push_back(v);}
 for(std::size_t i=0;i<indices;++i){const auto index=r.integer();need(index<vertices,"Character triangle index outside vertex array");if(output)output->mesh.indices.push_back(index);}
 CharacterJointTransform root;
 for(std::size_t i=0;i<joints;++i){CharacterJoint joint;const auto parent=r.integer();need(i==0?parent==0xffffffffu:parent<i,"Character joint hierarchy must be parent before child");joint.parent=parent==0xffffffffu?-1:static_cast<std::int32_t>(parent);joint.bind_local=r.transform();if(i==0)root=joint.bind_local;for(auto& v:joint.inverse_bind){v=r.scalar();need(std::abs(static_cast<double>(v))<=1e12,"Character inverse bind exceeds matrix bounds");}if(output)output->mesh.joints.push_back(joint);}
 for(std::size_t i=0;i<clips;++i){const auto clip_name=r.text(64);label(clip_name);budget.text(clip_name.size());CharacterClip clip;clip.duration_seconds=r.scalar();clip.frame_count=static_cast<std::uint32_t>(r.count(character_maximum_clip_frames));const auto loop=r.integer();r.reserved();need(clip.duration_seconds>0&&clip.duration_seconds<=3600&&clip.frame_count>0&&loop<=1,"Invalid character clip header");clip.looping=loop!=0;
  const auto samples=multiply(clip.frame_count,joints);need(samples<=r.data.size()/40,"Character clip samples exceed remaining bytes");budget.charge(multiply(samples,sizeof(CharacterJointTransform)));if(output){clip.name=clip_name;clip.samples.reserve(samples);}
  for(std::size_t n=0;n<samples;++n){const auto sample=r.transform();if(n%joints==0)need(sample.translation==root.translation,"Character clip has root motion");if(output)clip.samples.push_back(sample);}if(output)output->mesh.clips.push_back(std::move(clip));
 }
 std::array<ImageSemantic,character_asset_maximum_images> semantics{};
 for(std::size_t i=0;i<images;++i){const auto semantic=r.integer();const auto levels=r.count(13);r.reserved();need(semantic<=2&&levels>0,"Invalid character image semantic/mip count");semantics[i]=static_cast<ImageSemantic>(semantic);budget.charge(multiply(levels,sizeof(ImageMip)));ImageAsset image;image.semantic=semantics[i];if(output)image.levels.reserve(levels);std::uint32_t expected_width=0,expected_height=0;
  for(std::size_t m=0;m<levels;++m){const auto w=r.integer(),h=r.integer(),size=r.integer();r.reserved();need(w>0&&h>0&&w<=4096&&h<=4096,"Character image dimensions outside1..4096");const auto required=multiply(multiply(w,h),4);need(size==required,"Character mip byte count disagrees with dimensions");if(m==0){expected_width=w;expected_height=h;}need(w==expected_width&&h==expected_height,"Character mip chain dimensions disagree");budget.charge(required);const auto pixels=r.take(required);for(std::size_t alpha=3;alpha<pixels.size();alpha+=4)need(pixels[alpha]==std::byte{255},"Opaque character image requires alpha255");
   if(output){ImageMip mip{w,h,{}};mip.rgba.resize(required);std::transform(pixels.begin(),pixels.end(),mip.rgba.begin(),[](std::byte v){return std::to_integer<unsigned char>(v);});image.levels.push_back(std::move(mip));}
   if(m+1<levels)need(w!=1||h!=1,"Extra character mip");else need(w==1&&h==1,"Incomplete character mip chain");expected_width=std::max(1u,w/2);expected_height=std::max(1u,h/2);
  }if(output)output->images.push_back(std::move(image));
 }
 for(std::size_t i=0;i<materials;++i){CharacterMaterial material;material.albedo_image=r.integer();material.base_color=r.vector();material.emission=r.scalar();const auto sided=r.integer();need(sided<=1,"Unknown character material sidedness");material.double_sided=sided!=0;if(version==3)material.roughness=r.scalar();need(material.roughness>=.04f&&material.roughness<=1,"Character roughness outside0.04..1");const auto unit=[](float f){return f>=0&&f<=1;};need(unit(material.base_color.x)&&unit(material.base_color.y)&&unit(material.base_color.z)&&material.emission>=0&&material.emission<=16,"Invalid character material");if(material.albedo_image!=character_no_image)need(material.albedo_image<images&&semantics[material.albedo_image]==ImageSemantic::srgb_color,"Character albedo binding requires owned sRGB image");if(output)output->materials.push_back(material);}
 std::size_t cursor=0;for(std::size_t i=0;i<draws;++i){CharacterDraw draw{r.integer(),r.integer(),r.integer()};need(draw.first_index==cursor&&draw.index_count>0&&draw.index_count%3==0&&draw.index_count<=indices-cursor&&draw.material<materials,"Character draw ranges do not cover geometry canonically");cursor+=draw.index_count;if(output)output->draws.push_back(draw);}need(cursor==indices&&r.data.empty(),"Character draw omission or trailing payload bytes");
}
}
std::vector<std::byte> encode_character_asset(const CharacterAsset& asset){
 validate_character_asset(asset);const auto cost=character_asset_cost(asset);need(cost.payload_bytes<=character_asset_max_input_bytes,"Cooked character exceeds32MiB");Writer w;w.data.reserve(cost.payload_bytes);w.bytes(magic);const auto version=character_asset_payload_version(asset);w.integer(version);w.integer(static_cast<std::uint32_t>(cost.payload_bytes-header_bytes));const std::array<std::byte,32> empty{};w.bytes(empty);
 w.text(asset.asset_id);w.text(asset.name);w.text(asset.source_sha256);w.integer(static_cast<std::uint32_t>(asset.mesh.vertices.size()));w.integer(static_cast<std::uint32_t>(asset.mesh.indices.size()));w.integer(static_cast<std::uint32_t>(asset.mesh.joints.size()));w.integer(static_cast<std::uint32_t>(asset.mesh.clips.size()));w.integer(static_cast<std::uint32_t>(asset.images.size()));w.integer(static_cast<std::uint32_t>(asset.materials.size()));w.integer(static_cast<std::uint32_t>(asset.draws.size()));w.integer(0);
 for(const auto& v:asset.mesh.vertices){w.vector(v.position);w.vector(v.normal);w.vector(v.color);w.scalar(v.emission);w.scalar(v.u);w.scalar(v.v);for(auto j:v.joints)w.half(j);for(float weight:v.weights)w.scalar(weight);}
 for(auto index:asset.mesh.indices)w.integer(index);
 for(const auto& joint:asset.mesh.joints){w.integer(static_cast<std::uint32_t>(joint.parent));w.transform(joint.bind_local);for(float value:joint.inverse_bind)w.scalar(value);}
 for(const auto& clip:asset.mesh.clips){w.text(clip.name);w.scalar(clip.duration_seconds);w.integer(clip.frame_count);w.integer(clip.looping?1u:0u);w.integer(0);for(const auto& sample:clip.samples)w.transform(sample);}
 for(const auto& image:asset.images){w.integer(static_cast<std::uint32_t>(image.semantic));w.integer(static_cast<std::uint32_t>(image.levels.size()));w.integer(0);for(const auto& mip:image.levels){w.integer(mip.width);w.integer(mip.height);w.integer(static_cast<std::uint32_t>(mip.rgba.size()));w.integer(0);w.bytes({reinterpret_cast<const std::byte*>(mip.rgba.data()),mip.rgba.size()});}}
 for(const auto& material:asset.materials){w.integer(material.albedo_image);w.vector(material.base_color);w.scalar(material.emission);w.integer(material.double_sided?1u:0u);if(version==3)w.scalar(material.roughness);}
 for(const auto& draw:asset.draws){w.integer(draw.first_index);w.integer(draw.index_count);w.integer(draw.material);}
 need(w.data.size()==cost.payload_bytes,"Character payload accounting mismatch");const auto checksum=digest(std::span(w.data).subspan(header_bytes));std::copy(checksum.begin(),checksum.end(),w.data.begin()+16);return w.data;
}
CharacterAsset decode_character_asset(std::span<const std::byte> bytes){
 need(bytes.size()>=header_bytes&&bytes.size()<=character_asset_max_input_bytes,"Cooked character size outside32MiB bound");Reader header{bytes};const auto signature=header.take(8);const auto version=header.integer();need(std::equal(signature.begin(),signature.end(),magic.begin())&&(version==2||version==3),"Unsupported character magic/version");need(header.integer()==bytes.size()-header_bytes,"Character payload length/trailing bytes invalid");const auto expected=header.take(32);const auto actual=digest(header.data);need(std::equal(expected.begin(),expected.end(),actual.begin()),"Character checksum mismatch");
 parse(header.data,nullptr,version);CharacterAsset result;parse(header.data,&result,version);validate_character_asset(result);need(character_asset_payload_version(result)==version,"Noncanonical default-only surface promotion");need(character_asset_cost(result).payload_bytes==bytes.size(),"Noncanonical character payload size");return result;
}
}
