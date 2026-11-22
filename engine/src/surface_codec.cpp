#include <aibs/surface_codec.hpp>
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <stdexcept>
namespace aibs {namespace {
constexpr std::array<std::byte,8> magic{std::byte{'A'},std::byte{'I'},std::byte{'B'},std::byte{'S'},std::byte{'u'},std::byte{'r'},std::byte{'f'},std::byte{'2'}};
constexpr std::size_t header_bytes=48,corner_bytes=28;
void need(bool b,const char*m){if(!b)throw std::invalid_argument(m);}
std::array<std::byte,32> digest(std::span<const std::byte> b){
 const auto text=asset_sha256(b);std::array<std::byte,32> result{};
 const auto digit=[](char c){return c<='9'?c-'0':c-'a'+10;};
 for(std::size_t i=0;i<result.size();++i)result[i]=static_cast<std::byte>(digit(text[i*2])*16+digit(text[i*2+1]));
 return result;
}
void material_semantics(const SurfaceMeshAsset&a){
 for(const auto index:a.albedo_images)if(index!=surface_no_image)need(a.images[index].semantic!=ImageSemantic::normal_map,"Normal-map image cannot be an albedo binding");
}
struct Writer{
 std::vector<std::byte> data;
 void integer(std::uint32_t n){for(unsigned s=0;s<32;s+=8)data.push_back(static_cast<std::byte>((n>>s)&255));}
 void scalar(float n){integer(n==0?0:std::bit_cast<std::uint32_t>(n));}
 void bytes(std::span<const std::byte>b){data.insert(data.end(),b.begin(),b.end());}
};
struct Reader{
 std::span<const std::byte> data;
 std::span<const std::byte> take(std::size_t n){need(n<=data.size(),"Truncated surface payload");const auto result=data.first(n);data=data.subspan(n);return result;}
 std::uint32_t integer(){const auto b=take(4);std::uint32_t n=0;for(unsigned s=0;s<32;s+=8)n|=std::to_integer<std::uint32_t>(b[s/8])<<s;return n;}
 float scalar(){const auto n=integer();need(n!=0x80000000,"Noncanonical surface signed zero");const auto f=std::bit_cast<float>(n);need(std::isfinite(f),"Nonfinite surface scalar");return f;}
 std::size_t count(std::size_t maximum,std::size_t stride){const auto n=integer();need(n<=maximum&&static_cast<std::size_t>(n)<=data.size()/stride,"Surface count exceeds bound or remaining payload");return n;}
};
std::size_t image_bytes(std::uint32_t w,std::uint32_t h){need(w>=1&&h>=1&&w<=4096&&h<=4096,"Surface image dimensions outside1..4096");return static_cast<std::size_t>(w)*h*4;}
}
std::vector<std::byte> encode_surface_asset(const SurfaceMeshAsset&a){
 validate_surface_asset(a);material_semantics(a);const auto geometry=encode_mesh_asset(a.geometry);
 std::size_t size=4+geometry.size()+4+a.corners.size()*corner_bytes+4+4+a.albedo_images.size()*4;
 const auto add=[&](std::size_t n){need(size<=surface_asset_max_input_bytes-header_bytes&&n<=surface_asset_max_input_bytes-header_bytes-size,"Cooked surface exceeds32MiB");size+=n;};
 add(0);
 for(const auto&i:a.images){add(8);for(const auto&l:i.levels){add(12);add(l.rgba.size());}}
 Writer payload;payload.data.reserve(size);payload.integer(static_cast<std::uint32_t>(geometry.size()));payload.bytes(geometry);
 payload.integer(static_cast<std::uint32_t>(a.corners.size()));
 for(const auto&c:a.corners){payload.scalar(c.u);payload.scalar(c.v);payload.scalar(c.tangent.x);payload.scalar(c.tangent.y);payload.scalar(c.tangent.z);payload.scalar(c.tangent_sign);payload.integer(c.tangent_valid?1u:0u);}
 payload.integer(static_cast<std::uint32_t>(a.images.size()));
 for(const auto&i:a.images){payload.integer(static_cast<std::uint32_t>(i.semantic));payload.integer(static_cast<std::uint32_t>(i.levels.size()));for(const auto&l:i.levels){payload.integer(l.width);payload.integer(l.height);payload.integer(static_cast<std::uint32_t>(l.rgba.size()));payload.bytes({reinterpret_cast<const std::byte*>(l.rgba.data()),l.rgba.size()});}}
 payload.integer(static_cast<std::uint32_t>(a.albedo_images.size()));for(const auto i:a.albedo_images)payload.integer(i);
 need(payload.data.size()==size,"Surface size accounting mismatch");const auto checksum=digest(payload.data);
 Writer output;output.data.reserve(header_bytes+size);output.bytes(magic);output.integer(2);output.integer(static_cast<std::uint32_t>(size));output.bytes(checksum);output.bytes(payload.data);return output.data;
}
SurfaceMeshAsset decode_surface_asset(std::span<const std::byte>b){
 need(b.size()>=header_bytes&&b.size()<=surface_asset_max_input_bytes,"Cooked surface size outside32MiB bound");
 Reader header{b};const auto signature=header.take(magic.size());need(std::equal(signature.begin(),signature.end(),magic.begin())&&header.integer()==2,"Unsupported surface magic/version");
 const auto length=header.integer();need(length==b.size()-header_bytes,"Surface payload length/trailing bytes invalid");const auto checksum=header.take(32);const auto calculated=digest(header.data);need(std::equal(checksum.begin(),checksum.end(),calculated.begin()),"Surface checksum mismatch");
 Reader r{header.data};SurfaceMeshAsset a;const auto geometry_size=r.count(mesh_asset_max_input_bytes,1);a.geometry=decode_mesh_asset(r.take(geometry_size));
 const auto corners=r.count(mesh_asset_max_triangles*3,corner_bytes);need(corners==a.geometry.indices.size(),"Surface corner count does not match geometry");a.corners.reserve(corners);
 for(std::size_t n=0;n<corners;++n){SurfaceCorner c;c.u=r.scalar();c.v=r.scalar();c.tangent={r.scalar(),r.scalar(),r.scalar()};c.tangent_sign=r.scalar();const auto valid=r.integer();need(valid<=1,"Unknown surface tangent flags");c.tangent_valid=valid==1;a.corners.push_back(c);}
 const auto images=r.count(32,8);a.images.reserve(images);std::size_t all_image_bytes=0;
 for(std::size_t n=0;n<images;++n){const auto semantic=r.integer();need(semantic<=static_cast<std::uint32_t>(ImageSemantic::normal_map),"Unknown surface image semantic");ImageAsset image;image.semantic=static_cast<ImageSemantic>(semantic);const auto levels=r.count(13,12);need(levels>=1,"Surface image has no mips");image.levels.reserve(levels);std::size_t total=0;std::uint32_t w=0,h=0;
  for(std::size_t m=0;m<levels;++m){const auto width=r.integer(),height=r.integer();const auto expected=image_bytes(width,height);if(m==0){w=width;h=height;}need(width==w&&height==h,"Surface mip dimensions do not form a chain");need(expected<=image_asset_maximum_bytes-total&&expected<=128u*1024u*1024u-all_image_bytes,"Surface decoded image budget exceeded");need(r.integer()==expected,"Surface image byte count does not match dimensions");const auto rgba=r.take(expected);ImageMip mip{width,height,{}};mip.rgba.resize(expected);std::transform(rgba.begin(),rgba.end(),mip.rgba.begin(),[](std::byte v){return std::to_integer<unsigned char>(v);});image.levels.push_back(std::move(mip));total+=expected;all_image_bytes+=expected;
   if(m+1<levels)need(w!=1||h!=1,"Extra surface image mip");w=std::max(1u,w/2);h=std::max(1u,h/2);
  }
  validate_image_asset(image);a.images.push_back(std::move(image));
 }
 const auto refs=r.count(mesh_asset_max_materials,4);need(refs==a.geometry.materials.size(),"Surface material binding count mismatch");a.albedo_images.reserve(refs);for(std::size_t n=0;n<refs;++n)a.albedo_images.push_back(r.integer());
 need(r.data.empty(),"Surface payload contains trailing bytes");validate_surface_asset(a);material_semantics(a);return a;
}
}
