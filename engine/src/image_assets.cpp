#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <wincodec.h>
#include <wrl/client.h>
#include <aibs/image_assets.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
namespace aibs { namespace {
using Microsoft::WRL::ComPtr;
void need(bool b,const char*m){if(!b)throw std::invalid_argument(m);}
void ok(HRESULT hr){need(SUCCEEDED(hr),"PNG decoder rejected input or WIC unavailable");}
std::size_t bytes(std::uint32_t w,std::uint32_t h){need(w>0&&h>0&&w<=4096&&h<=4096,"Image dimensions exceed1..4096");return static_cast<std::size_t>(w)*h*4;}
void check(const ImageAsset&i,bool complete){
 need(static_cast<unsigned>(i.semantic)<=2&&!i.levels.empty()&&i.levels.size()<=13,"Invalid image semantic/mip count");
 auto w=i.levels[0].width,h=i.levels[0].height;std::size_t total=0;
 for(std::size_t n=0;n<i.levels.size();++n){const auto&l=i.levels[n];need(l.width==w&&l.height==h&&l.rgba.size()==bytes(w,h),"Invalid image mip dimensions/bytes");need(l.rgba.size()<=image_asset_maximum_bytes-total,"Decoded image budget exceeded");total+=l.rgba.size();if(n+1<i.levels.size())need(w!=1||h!=1,"Extra image mip");w=std::max(1u,w/2);h=std::max(1u,h/2);}
 if(complete)need(i.levels.back().width==1&&i.levels.back().height==1,"Incomplete mip chain");
}
double linear(double c){return c<=.04045?c/12.92:std::pow((c+.055)/1.055,2.4);}
double srgb(double c){return c<=.0031308?12.92*c:1.055*std::pow(c,1/2.4)-.055;}
unsigned char quantize(double c){return static_cast<unsigned char>(std::lround(std::clamp(c,0.,1.)*255));}
}
std::size_t image_resident_bytes(const ImageAsset&i){check(i,false);std::size_t n=0;for(const auto&l:i.levels)n+=l.rgba.size();return n;}
void validate_image_asset(const ImageAsset&i){check(i,true);}
void generate_image_mips(ImageAsset&i,std::size_t budget){
 check(i,false);need(budget<=image_asset_maximum_bytes,"Unsupported image budget");
 std::size_t required=0;auto w=i.levels[0].width,h=i.levels[0].height;
 for(;;){const auto n=bytes(w,h);need(n<=budget-required,"Mip chain exceeds byte budget");required+=n;if(w==1&&h==1)break;w=std::max(1u,w/2);h=std::max(1u,h/2);}
 ImageAsset out{i.semantic,{i.levels[0]}};
 while(out.levels.back().width!=1||out.levels.back().height!=1){
  const auto&s=out.levels.back();ImageMip d{std::max(1u,s.width/2),std::max(1u,s.height/2),{}};d.rgba.resize(bytes(d.width,d.height));
  for(std::uint32_t y=0;y<d.height;++y)for(std::uint32_t x=0;x<d.width;++x){std::array<double,4> sum{};unsigned count=0;
   const auto x0=x*s.width/d.width,x1=(x+1)*s.width/d.width,y0=y*s.height/d.height,y1=(y+1)*s.height/d.height;
   for(auto sy=y0;sy<y1;++sy)for(auto sx=x0;sx<x1;++sx){const auto p=(static_cast<std::size_t>(sy)*s.width+sx)*4;const double a=s.rgba[p+3]/255.;for(unsigned c=0;c<3;++c){double v=s.rgba[p+c]/255.;if(i.semantic==ImageSemantic::srgb_color)v=linear(v)*a;else if(i.semantic==ImageSemantic::normal_map)v=2*v-1;sum[c]+=v;}sum[3]+=a;++count;}
   for(auto&v:sum)v/=count;
   if(i.semantic==ImageSemantic::normal_map){const double length=std::sqrt(sum[0]*sum[0]+sum[1]*sum[1]+sum[2]*sum[2]);if(length<1e-8)sum={0,0,1,sum[3]};else for(unsigned c=0;c<3;++c)sum[c]/=length;for(unsigned c=0;c<3;++c)sum[c]=sum[c]*.5+.5;}
   else if(i.semantic==ImageSemantic::srgb_color)for(unsigned c=0;c<3;++c)sum[c]=sum[3]>0?srgb(sum[c]/sum[3]):0;
   const auto p=(static_cast<std::size_t>(y)*d.width+x)*4;for(unsigned c=0;c<4;++c)d.rgba[p+c]=quantize(sum[c]);
  }
  out.levels.push_back(std::move(d));
 }
 validate_image_asset(out);i=std::move(out);
}
ImageAsset decode_png_image(std::span<const unsigned char> input,ImageSemantic semantic,std::size_t budget){
 constexpr std::array<unsigned char,8> signature{137,80,78,71,13,10,26,10};
 need(input.size()>=33&&input.size()<=image_asset_maximum_bytes&&std::equal(signature.begin(),signature.end(),input.begin()),"Expected bounded PNG input");
 const auto read=[&](std::size_t p){return (std::uint32_t(input[p])<<24)|(std::uint32_t(input[p+1])<<16)|(std::uint32_t(input[p+2])<<8)|input[p+3];};
 need(read(8)==13&&input[12]=='I'&&input[13]=='H'&&input[14]=='D'&&input[15]=='R'&&input[24]==8,"Expected8-bit PNG IHDR");
 const auto w=read(16),h=read(20);auto mw=w,mh=h;std::size_t total=0;need(budget<=image_asset_maximum_bytes,"Unsupported image budget");
 for(;;){const auto n=bytes(mw,mh);need(n<=budget-total,"Decoded mip budget exceeded");total+=n;if(mw==1&&mh==1)break;mw=std::max(1u,mw/2);mh=std::max(1u,mh/2);}
 struct ComScope{HRESULT hr=CoInitializeEx(nullptr,COINIT_MULTITHREADED);~ComScope(){if(SUCCEEDED(hr))CoUninitialize();}} scope;
 need(SUCCEEDED(scope.hr)||scope.hr==RPC_E_CHANGED_MODE,"COM initialization failed");
 ComPtr<IWICImagingFactory> factory;ok(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory)));
 ComPtr<IWICStream> stream;ok(factory->CreateStream(&stream));ok(stream->InitializeFromMemory(const_cast<BYTE*>(input.data()),static_cast<DWORD>(input.size())));
 ComPtr<IWICBitmapDecoder> decoder;ok(factory->CreateDecoderFromStream(stream.Get(),nullptr,WICDecodeMetadataCacheOnDemand,&decoder));UINT frames=0;ok(decoder->GetFrameCount(&frames));need(frames==1,"Only single-frame PNG supported");
 ComPtr<IWICBitmapFrameDecode> frame;ok(decoder->GetFrame(0,&frame));UINT dw=0,dh=0;ok(frame->GetSize(&dw,&dh));need(dw==w&&dh==h,"PNG size disagreement");
 ComPtr<IWICFormatConverter> converter;ok(factory->CreateFormatConverter(&converter));ok(converter->Initialize(frame.Get(),GUID_WICPixelFormat32bppRGBA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom));
 ImageAsset image{semantic,{{w,h,std::vector<unsigned char>(bytes(w,h))}}};ok(converter->CopyPixels(nullptr,w*4,static_cast<UINT>(image.levels[0].rgba.size()),image.levels[0].rgba.data()));generate_image_mips(image,budget);return image;
}
}
