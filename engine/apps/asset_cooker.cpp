#include <aibs/assets.hpp>
#include <aibs/asset_scene.hpp>
#include <aibs/asset_store.hpp>
#include <aibs/surface_codec.hpp>
#include <aibs/character_codec.hpp>
#include <aibs/audio_codec.hpp>
#include <aibs/character_import.hpp>
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <algorithm>
#include <charconv>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <locale>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string_view>

namespace {
namespace fs = std::filesystem;
using Bytes = std::vector<std::byte>;
constexpr std::size_t text_limit = 64u * 1024u;
void require(bool condition, const char* message) {
 if (!condition) throw std::invalid_argument(message);
}
struct Handle {
 HANDLE value = INVALID_HANDLE_VALUE;
 ~Handle() { if (value != INVALID_HANDLE_VALUE) CloseHandle(value); }
 Handle() = default;
 Handle(const Handle&) = delete;
 Handle& operator=(const Handle&) = delete;
};
std::string utf8(const std::wstring& text) {
 require(text.size() <= 32768, "CLI text exceeds limit");
 if (text.empty()) return {};
 const int count = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, text.data(),
     static_cast<int>(text.size()), nullptr, 0, nullptr, nullptr);
 require(count > 0, "Invalid Unicode CLI text");
 std::string result(static_cast<std::size_t>(count), '\0');
 require(WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, text.data(),
     static_cast<int>(text.size()), result.data(), count, nullptr, nullptr) == count,
     "Could not encode CLI text");
 return result;
}
fs::path plain_path(const fs::path& input) {
 auto absolute = fs::absolute(input).lexically_normal();
 for (auto current = absolute; !current.empty();) {
  const auto attributes = GetFileAttributesW(current.c_str());
  require(attributes != INVALID_FILE_ATTRIBUTES, "Input/output parent is absent or inaccessible");
  require((attributes & FILE_ATTRIBUTE_REPARSE_POINT) == 0, "Redirected inputs/output parents are not admitted");
  const auto parent = current.parent_path();
  if (parent == current) break;
  current = parent;
 }
 return absolute;
}
Bytes read_bounded(const fs::path& path, std::size_t maximum) {
 const auto input = plain_path(path);
 Handle file;
 file.value = CreateFileW(input.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
     OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
 require(file.value != INVALID_HANDLE_VALUE, "Could not open regular input");
 BY_HANDLE_FILE_INFORMATION info{};
 require(GetFileInformationByHandle(file.value, &info) != 0 &&
     (info.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY)) == 0,
     "Only regular unredirected inputs are admitted");
 LARGE_INTEGER length{};
 require(GetFileSizeEx(file.value, &length) != 0 && length.QuadPart >= 0 &&
     static_cast<unsigned long long>(length.QuadPart) <= maximum, "Input exceeds byte limit");
 Bytes result(static_cast<std::size_t>(length.QuadPart));
 std::size_t offset = 0;
 while (offset < result.size()) {
  const DWORD requested = static_cast<DWORD>(std::min<std::size_t>(1024u * 1024u, result.size() - offset));
  DWORD received = 0;
  require(ReadFile(file.value, result.data() + offset, requested, &received, nullptr) != 0 &&
      received == requested, "Input changed or could not be read");
  offset += received;
 }
 LARGE_INTEGER final_length{};
 require(GetFileSizeEx(file.value, &final_length) != 0 && final_length.QuadPart == length.QuadPart,
     "Input changed while reading");
 return result;
}
std::string_view text(const Bytes& bytes) {
 return {reinterpret_cast<const char*>(bytes.data()), bytes.size()};
}
Bytes bytes(std::string_view value) {
 const auto* begin = reinterpret_cast<const std::byte*>(value.data());
 return {begin, begin + value.size()};
}
float number(const std::string& token) {
 float value = 0;
 const auto parsed = std::from_chars(token.data(), token.data() + token.size(), value);
 require(parsed.ec == std::errc{} && parsed.ptr == token.data() + token.size() &&
     std::isfinite(value) && value >= 0 && value <= 1, "Material values must be finite and normalized");
 return value == 0 ? 0 : value;
}
std::vector<aibs::MeshMaterial> parse_materials(const Bytes& source) {
 require(!source.empty(), "Material declaration is empty");
 std::istringstream stream{std::string(text(source))};
 std::string line;
 require(static_cast<bool>(std::getline(stream, line)), "Missing material header");
 if (!line.empty() && line.back() == '\r') line.pop_back();
 require(line == "AIBMAT 1", "Unsupported material declaration header");
 std::vector<aibs::MeshMaterial> materials;
 std::set<std::string> names;
 while (std::getline(stream, line)) {
  if (!line.empty() && line.back() == '\r') line.pop_back();
  if (line.empty()) continue;
  std::istringstream row(line);
  std::string name, red, green, blue, emission, extra;
  require(static_cast<bool>(row >> name >> red >> green >> blue >> emission) && !(row >> extra),
      "Material row requires a name, RGB and emission");
  require(!name.empty() && name.size() <= 64 && std::all_of(name.begin(), name.end(),
      [](unsigned char c) { return c > 32 && c <= 126; }), "Material names require 1-64 visible ASCII bytes");
  require(names.insert(name).second && materials.size() < aibs::mesh_asset_max_materials,
      "Duplicate material or material count limit");
  materials.push_back({std::move(name), {number(red), number(green), number(blue)}, number(emission)});
 }
 require(!materials.empty(), "At least one material is required");
 return materials;
}
std::string json_quote(std::string_view value) {
 require(value.size() <= 1024u * 1024u, "JSON text exceeds its encoding bound");
 require(value.empty() || MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
     static_cast<int>(value.size()), nullptr, 0) > 0, "JSON text is not valid UTF-8");
 constexpr char hex[] = "0123456789abcdef";
 std::string result = "\"";
 for (const unsigned char c : value) {
  if (c == '\\' || c == '"') { result += '\\'; result += static_cast<char>(c); }
  else if (c < 32) { result += "\\u00"; result += hex[c >> 4]; result += hex[c & 15]; }
  else result += static_cast<char>(c);
 }
 return result + '"';
}
void write_new(const fs::path& path, const Bytes& value) {
 Handle file;
 file.value = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW,
     FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
 require(file.value != INVALID_HANDLE_VALUE, "Could not create fresh staging file");
 std::size_t offset = 0;
 while (offset < value.size()) {
  const DWORD requested = static_cast<DWORD>(std::min<std::size_t>(1024u * 1024u, value.size() - offset));
  DWORD written = 0;
  require(WriteFile(file.value, value.data() + offset, requested, &written, nullptr) != 0 &&
      written == requested, "Could not write complete staging file");
  offset += written;
 }
 require(FlushFileBuffers(file.value) != 0, "Could not flush staging file");
}
// The owner deletes only exact files it created, then its empty directory.
// It never recursively removes a computed path or touches an existing pack.
struct Stage {
 fs::path directory;
 std::vector<fs::path> owned_files;
 bool published = false;
 Stage(const fs::path& parent, const fs::path& name) {
  for (unsigned attempt = 0; attempt < 16; ++attempt) {
   auto suffix = L".assetc-" + std::to_wstring(GetCurrentProcessId()) + L"-" +
       std::to_wstring(GetTickCount64()) + L"-" + std::to_wstring(attempt);
   auto candidate = parent / (name.wstring() + suffix);
   if (CreateDirectoryW(candidate.c_str(), nullptr) != 0) { directory = std::move(candidate); return; }
   require(GetLastError() == ERROR_ALREADY_EXISTS, "Could not create owned sibling staging directory");
  }
  throw std::runtime_error("No fresh staging directory available");
 }
 ~Stage() {
  if (!published) {
   for (const auto& file : owned_files) DeleteFileW(file.c_str());
   if (!directory.empty()) RemoveDirectoryW(directory.c_str());
  }
 }
 void add(const std::string& name, const Bytes& value) {
  const auto path = directory / name;
  owned_files.push_back(path);
  write_new(path, value);
  require(read_bounded(path, value.size()) == value, "Staging readback mismatch");
 }
 void publish(const fs::path& output) {
  require(MoveFileExW(directory.c_str(), output.c_str(), MOVEFILE_WRITE_THROUGH) != 0,
      "Fresh output publication failed; existing output is preserved");
  published = true;
 }
};
std::string input_record(const Bytes& value) {
 return "{\"sha256\":" + json_quote(aibs::asset_sha256(value)) + ",\"bytes\":" +
     std::to_string(value.size()) + "}";
}
std::string reference_json(const aibs::AssetPackReference& reference) {
 return "{\"asset_id\":"+json_quote(reference.asset_id)+",\"asset_sha256\":"+
     json_quote(reference.asset_sha256)+",\"pack_sha256\":"+json_quote(reference.pack_sha256)+"}";
}
fs::path plain_store_path(const fs::path& input) {
 // New store-mode preflight only. Original cook/inspect path policy is retained.
 auto spelling=input.native();
 if(spelling.starts_with(L"\\\\?\\UNC\\")) spelling=L"\\\\"+spelling.substr(8);
 else if(spelling.starts_with(L"\\\\?\\")) spelling=spelling.substr(4);
 const auto absolute=fs::absolute(fs::path(spelling)).lexically_normal().make_preferred();
 require(absolute.native().size()<=32760,"Asset store path exceeds Windows length bound");
 const auto extended=[](const fs::path& path) {
  const auto& value=path.native();
  return fs::path(value.starts_with(L"\\\\")?L"\\\\?\\UNC\\"+value.substr(2):L"\\\\?\\"+value);
 };
 for(auto current=absolute;!current.empty();) {
  const auto attributes=GetFileAttributesW(extended(current).c_str());
  require(attributes!=INVALID_FILE_ATTRIBUTES&&(attributes&FILE_ATTRIBUTE_REPARSE_POINT)==0,
      "Store inspection requires existing unredirected components");
  const auto parent=current.parent_path();
  if(parent==current||(absolute.root_path().native().starts_with(L"\\\\")&&parent==absolute.root_path())) break;
  current=parent;
 }
 return extended(absolute);
}
#include "character_cooker.inl"
#include "audio_cooker.inl"
int store_mode(int argc,wchar_t** argv) {
 const std::wstring_view mode(argv[1]);
 if(mode==L"--adopt") {
  require(argc==5&&std::wstring_view(argv[3])==L"--store","Use --adopt PACK --store EXISTING_STORE");
  const auto reference=aibs::adopt_asset_pack(fs::path(argv[2]),fs::path(argv[4]));
  std::cout<<"{\"status\":\"passed\",\"asset_id\":"<<json_quote(reference.asset_id)
      <<",\"asset_sha256\":"<<json_quote(reference.asset_sha256)<<",\"pack_sha256\":"
      <<json_quote(reference.pack_sha256)<<"}\n";
  return 0;
 }
 require(mode==L"--stage-store"||mode==L"--inspect-store","Unknown native asset store mode");
 require(argc>=3,"An explicit native asset store root is required");
 const fs::path source(argv[2]);fs::path output;
 bool merge=false,modern=false;
 std::vector<aibs::AssetPackReference> references;
 for(int index=3;index<argc;++index) {
  const std::wstring_view argument(argv[index]);
  if(argument==L"--profile") {
   require(!modern&&index+1<argc&&std::wstring_view(argv[index+1])==L"warm-beginning","Use --profile warm-beginning once for typed content");
   modern=true;++index;
  } else if(argument==L"--merge") {
   require(mode==L"--stage-store"&&!merge,"Merge is supported once in stage-store mode only");merge=true;
  } else if(argument==L"--output") {
   require(mode==L"--stage-store"&&output.empty()&&index+1<argc,"One explicit stage destination is required");
   output=fs::path(argv[++index]);
  } else if(argument==L"--ref") {
   require(index+3<argc&&references.size()<aibs::asset_store_maximum_references,"Asset reference requires UUID, mesh SHA, pack SHA; at most64 references");
   aibs::AssetPackReference reference{utf8(argv[index+1]),utf8(argv[index+2]),utf8(argv[index+3])};index+=3;
   aibs::validate_asset_pack_reference(reference);references.push_back(std::move(reference));
  } else throw std::invalid_argument("Unknown native asset store option");
 }
 if(mode==L"--stage-store") {
  require(!output.empty(),"Use --stage-store STORE --output NEWSTORE --ref UUID MESHSHA PACKSHA [--merge]");
  aibs::stage_asset_packs(source,references,output,merge,modern?aibs::AssetContentProfile::warm_beginning:aibs::AssetContentProfile::legacy_v1);
  std::string report="{\"status\":\"passed\",\"refs\":[";
  for(std::size_t index=0;index<references.size();++index) {
   if(index) report+=',';
   report+=reference_json(references[index]);
  }
  report+="]}\n";require(report.size()<=text_limit,"Stage receipt exceeds64 KiB");std::cout<<report;
 } else {
  require(!references.empty(),"Use --inspect-store STORE --ref UUID MESHSHA PACKSHA");
  std::map<std::string,aibs::AssetPackReference> unique;
  for(const auto& reference:references) {
   const auto [found,inserted]=unique.emplace(reference.pack_sha256,reference);
   require(inserted||found->second==reference,"One pack digest has conflicting asset references");
  }
  require(unique.size()<=aibs::asset_store_maximum_unique_packs,"Inspect-store exceeds32 unique packs");
  for(const auto& part:source.relative_path()) require(part!=L"..","Asset store path traversal is not admitted");
  const auto root=plain_store_path(source);std::size_t total=0,decoded=0;
  std::string report="{\"status\":\"passed\",\"assets\":[";bool first=true;
  for(const auto& [pack_sha,reference]:unique) {
   if(modern) {
    const auto inspection=aibs::inspect_asset_pack(source/pack_sha,aibs::asset_store_modern_staged_bytes-total);
    require(inspection.reference==reference,"Inspect-store typed pack differs from requested immutable reference");
    const auto& asset=inspection.asset;
    require(asset.decoded_bytes<=aibs::asset_store_modern_staged_bytes-decoded,"Inspect-store decoded dependency bytes exceed128MiB");
    total+=asset.encoded_bytes;decoded+=asset.decoded_bytes;
    if(!first)report+=',';first=false;
    auto row=reference_json(reference);row.pop_back();report+=row+fields_for_asset(asset);
    if(inspection.kind==aibs::StoredAssetKind::character_v2||inspection.kind==aibs::StoredAssetKind::audio_v2)report+=",\"sha256\":"+json_quote(reference.asset_sha256);
    report+='}';
    require(report.size()+3<=text_limit,"Inspect-store report exceeds64 KiB");
    continue;
   }
   // Preflight the bounded dependency byte charge before native pack loading.
   // load_stored_asset subsequently holds/rechecks regular paths and all hashes.
   const auto directory=root/pack_sha;
   for(const auto& filename:std::array<std::string,4>{"catalog.aibcat",reference.asset_sha256+".aibmesh","LICENSE.txt","provenance.json"}) {
    const auto path=plain_store_path(directory/filename);const auto count=fs::file_size(path);
    require(count<=aibs::asset_store_maximum_staged_bytes-total,"Inspect-store dependency bytes exceed64 MiB");
    total+=static_cast<std::size_t>(count);
   }
   const auto asset=aibs::load_stored_asset(source,reference);
   if(!first) report+=',';first=false;
   auto row=reference_json(reference);row.pop_back();
   report+=row+",\"name\":"+json_quote(asset.name)+",\"triangles\":"+std::to_string(asset.indices.size()/3)+
       ",\"materials\":"+std::to_string(asset.materials.size())+"}";
   require(report.size()+3<=text_limit,"Inspect-store report exceeds64 KiB");
  }
  report+="]}\n";std::cout<<report;
 }
 return 0;
}
int inspect(const fs::path& input) {
 const auto root = plain_path(input);
 const auto declaration=read_bounded(root/"catalog.aibcat",1024u*1024u);
 if(text(declaration).starts_with("AIBCAT 2\n")) {
  const auto pack=aibs::inspect_asset_pack(root,aibs::asset_store_maximum_audio_pack_bytes);
  auto row=reference_json(pack.reference);row.pop_back();
  const auto report="{\"status\":\"passed\",\"assets\":["+row+",\"sha256\":"+json_quote(pack.reference.asset_sha256)+fields_for_asset(pack.asset)+"}]}\n";
  require(report.size()<=text_limit,"CLI inspection report exceeds64 KiB");std::cout<<report;return 0;
 }
 aibs::AssetCatalog catalog(root);
 require(catalog.records().size() <= 64, "CLI inspection admits at most 64 assets per report");
 std::string report = "{\"status\":\"passed\",\"assets\":[";
 bool first = true;
 for (const auto& record : catalog.records()) {
  const auto asset = catalog.load(record.asset_id);
  if (!first) report += ',';
  first = false;
  report += "{\"asset_id\":" + json_quote(asset.asset_id) + ",\"name\":" + json_quote(asset.name) +
      ",\"sha256\":" + json_quote(record.sha256) + ",\"triangles\":" + std::to_string(asset.indices.size() / 3) +
      ",\"materials\":" + std::to_string(asset.materials.size()) + "}";
  require(report.size() + 3 <= text_limit, "CLI inspection report exceeds 64 KiB");
 }
 report += "]}\n";
 require(report.size() <= text_limit, "CLI inspection report exceeds 64 KiB");
 std::cout << report;
 return 0;
}
std::string texture_basename(const std::string& filename) {
 require(filename.size()>4&&filename.size()<=128&&filename.find("..") == std::string::npos&&
     filename.front()!='.'&&std::all_of(filename.begin(),filename.end(),[](unsigned char c){
      return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.';}),
     "Surface textures require bounded plain PNG basenames");
 auto normalized=filename;for(auto& c:normalized)if(c>='A'&&c<='Z')c=static_cast<char>(c-'A'+'a');
 require(normalized.ends_with(".png"),"Surface textures require PNG basenames");
 const auto stem=normalized.substr(0,normalized.find('.'));
 const bool numbered=stem.size()==4&&(stem.starts_with("com")||stem.starts_with("lpt"))&&stem[3]>='1'&&stem[3]<='9';
 require(stem!="con"&&stem!="prn"&&stem!="aux"&&stem!="nul"&&!numbered,"Windows device texture basenames are not admitted");
 return normalized;
}
int cook_surface(int argc,wchar_t** argv) {
 require(argc==16,"Surface mode requires exactly seven unique named option pairs");
 const std::set<std::wstring> allowed{L"--source",L"--materials",L"--asset-id",L"--name",L"--license",L"--output",L"--uv-origin"};
 std::map<std::wstring,std::wstring> options;
 for(int index=2;index<argc;index+=2)require(allowed.contains(argv[index])&&options.emplace(argv[index],argv[index+1]).second,"Unknown or duplicate surface cooker option");
 const auto origin=utf8(options.at(L"--uv-origin"));
 require(origin=="top-left"||origin=="bottom-left","Explicit surface UV origin must be top-left or bottom-left");
 const auto output=fs::absolute(fs::path(options.at(L"--output"))).lexically_normal();
 require(output.has_filename()&&!fs::exists(output),"Output must be a fresh directory; existing paths are preserved");
 const auto parent=plain_path(output.parent_path());require(fs::is_directory(parent),"Output parent must be an existing unredirected directory");
 const auto source=read_bounded(fs::path(options.at(L"--source")),aibs::mesh_asset_max_input_bytes);
 const auto material_path=plain_path(fs::path(options.at(L"--materials")));
 const auto declarations=read_bounded(material_path,text_limit),license=read_bounded(fs::path(options.at(L"--license")),text_limit);
 require(!license.empty()&&std::none_of(license.begin(),license.end(),[](std::byte c){return c==std::byte{0};})&&std::any_of(license.begin(),license.end(),[](std::byte c){return std::to_integer<unsigned char>(c)>32;}),"An explicit nonempty text license/rights declaration is required");
 (void)json_quote(text(license));
 std::istringstream lines{std::string(text(declarations))};std::string line;require(static_cast<bool>(std::getline(lines,line)),"Missing material header");
 if(!line.empty()&&line.back()=='\r')line.pop_back();require(line=="AIBMAT 2","Surface mode requires AIBMAT2");
 std::vector<aibs::MeshMaterial> materials;std::vector<std::uint32_t> bindings;std::vector<aibs::ImageAsset> images;
 std::set<std::string> names;std::map<std::string,std::uint32_t> image_slots;std::string texture_provenance="[";std::size_t decoded_images=0;
 while(std::getline(lines,line)) {
  if(!line.empty()&&line.back()=='\r')line.pop_back();if(line.empty())continue;
  std::istringstream row(line);std::string name,r,g,b,emission,filename,extra;
  require(static_cast<bool>(row>>name>>r>>g>>b>>emission>>filename)&&!(row>>extra),"AIBMAT2 row requires name, RGB, emission and PNG basename or '-'");
  require(!name.empty()&&name.size()<=64&&std::all_of(name.begin(),name.end(),[](unsigned char c){return c>32&&c<=126;}),"Material names require1-64 visible ASCII bytes");
  require(materials.size()<aibs::mesh_asset_max_materials&&names.insert(name).second,"Duplicate material or material count limit");
  materials.push_back({name,{number(r),number(g),number(b)},number(emission)});
  if(filename=="-"){bindings.push_back(aibs::surface_no_image);continue;}
  const auto key=texture_basename(filename);const auto found=image_slots.find(key);
  if(found!=image_slots.end()){bindings.push_back(found->second);continue;}
  require(images.size()<32,"Surface image count exceeds32");
  const auto raw=read_bounded(material_path.parent_path()/filename,aibs::image_asset_maximum_bytes);
  require(decoded_images<aibs::surface_asset_max_input_bytes,"Surface decoded images exceed32MiB cooked budget");
  auto image=aibs::decode_png_image({reinterpret_cast<const unsigned char*>(raw.data()),raw.size()},aibs::ImageSemantic::srgb_color,aibs::surface_asset_max_input_bytes-decoded_images);
  const auto index=static_cast<std::uint32_t>(images.size());image_slots.emplace(key,index);bindings.push_back(index);decoded_images+=aibs::image_resident_bytes(image);images.push_back(std::move(image));
  if(texture_provenance.size()>1)texture_provenance+=',';
  auto record=input_record(raw);record.erase(record.begin());texture_provenance+="{\"file\":"+json_quote(filename)+","+record;
 }
 texture_provenance+=']';require(!materials.empty(),"At least one material is required");
 const auto id=utf8(options.at(L"--asset-id")),name=utf8(options.at(L"--name"));
 auto asset=aibs::import_surface_obj(text(source),materials,id,name,origin=="top-left"?aibs::ObjUvOrigin::top_left:aibs::ObjUvOrigin::bottom_left);
 asset.images=std::move(images);asset.albedo_images=std::move(bindings);
 const auto encoded=aibs::encode_surface_asset(asset);const auto digest=aibs::asset_sha256(encoded),filename=digest+".aibsurf";
 const auto catalog="AIBCAT 2\nsurface "+id+" "+digest+" "+filename+"\n";
 const auto provenance="{\n  \"schema_version\":2,\n  \"asset_id\":"+json_quote(id)+",\n  \"name\":"+json_quote(name)+
     ",\n  \"source\":"+input_record(source)+",\n  \"materials\":"+input_record(declarations)+",\n  \"license\":"+input_record(license)+
     ",\n  \"textures\":"+texture_provenance+",\n  \"license_review\":\"Supplied declaration copied verbatim; ownership/permission not inferred\","+
     "\n  \"importer\":{\"name\":\"aibs-surface-obj\",\"format_version\":2},\n  \"options\":{\"units\":\"meters\",\"up_axis\":\"+Y\",\"axis_conversion\":\"none\",\"uv_origin\":"+json_quote(origin)+
     ",\"cooked_uv_origin\":\"top-left\",\"material_model\":\"opaque-albedo-emission-v2\",\"image_semantic\":\"srgb-color\",\"external_material_libraries\":\"ignored-explicit-material-table-only\"},"+
     "\n  \"cooked\":{\"file\":"+json_quote(filename)+",\"sha256\":"+json_quote(digest)+",\"bytes\":"+std::to_string(encoded.size())+"}\n}\n";
 const auto success="{\"status\":\"passed\",\"kind\":\"surface\",\"asset_id\":"+json_quote(id)+",\"sha256\":"+json_quote(digest)+",\"output_root\":"+json_quote(utf8(output.wstring()))+
     ",\"vertices\":"+std::to_string(asset.geometry.vertices.size())+",\"triangles\":"+std::to_string(asset.geometry.indices.size()/3)+",\"image_count\":"+std::to_string(asset.images.size())+",\"decoded_image_bytes\":"+std::to_string(decoded_images)+"}\n";
 require(provenance.size()<=text_limit&&success.size()<=text_limit,"Surface provenance/receipt exceeds64KiB");
 Stage stage(parent,output.filename());stage.add(filename,encoded);stage.add("catalog.aibcat",bytes(catalog));stage.add("LICENSE.txt",license);stage.add("provenance.json",bytes(provenance));stage.publish(output);std::cout<<success;return 0;
}
int cook(int argc, wchar_t** argv) {
 if(argc>1&&std::wstring_view(argv[1])==L"--cook-audio")return cook_audio(argc,argv);
 if(argc>1&&std::wstring_view(argv[1])==L"--cook-character")return cook_character(argc,argv);
 if(argc>1&&std::wstring_view(argv[1])==L"--cook-surface")return cook_surface(argc,argv);
 if(argc>1&&(std::wstring_view(argv[1])==L"--adopt"||std::wstring_view(argv[1])==L"--stage-store"||
     std::wstring_view(argv[1])==L"--inspect-store")) return store_mode(argc,argv);
 if (argc == 3 && std::wstring_view(argv[1]) == L"--inspect") return inspect(fs::path(argv[2]));
 if (argc == 2 && std::wstring_view(argv[1]) == L"--help") {
  std::cout << "aibs_assetc --source OBJ --materials AIBMAT --asset-id UUID --name TEXT --license TXT --output NEWFOLDER\n"
      "aibs_assetc --cook-surface --source OBJ --materials AIBMAT2 --asset-id UUID --name TEXT --license TXT --output NEWFOLDER --uv-origin top-left|bottom-left\n"
      "aibs_assetc --cook-character --source GLB|glTF --asset-id UUID --name TEXT --license TXT --output NEWFOLDER [--clip INDEX NAME loop|once] [--resource URI FILE] [--bake-rate 1..60]\n"
      "aibs_assetc --cook-audio --source WAV --asset-id UUID --name TEXT --license TXT --output NEWFOLDER (source-rate PCM16LE mono/stereo; no resampling)\n"
      "aibs_assetc --inspect PACKROOT (at most 64 assets / 64 KiB report)\n"
      "aibs_assetc --adopt PACKROOT --store EXISTING_STORE\n"
      "aibs_assetc --stage-store STORE --output NEWSTORE --ref UUID MESHSHA PACKSHA [--ref ...] [--merge]\n"
      "aibs_assetc --inspect-store STORE --ref UUID MESHSHA PACKSHA [--ref ...]\n"
      "Typed stage/inspect-store require --profile warm-beginning (128MiB encoded/decoded closure).\n";
  return 0;
 }
 require(argc == 13, "Exactly six unique named options are required; use --help");
 const std::set<std::wstring> allowed{L"--source", L"--materials", L"--asset-id", L"--name", L"--license", L"--output"};
 std::map<std::wstring, std::wstring> options;
 for (int index = 1; index < argc; index += 2) {
  const std::wstring key(argv[index]);
  require(allowed.contains(key) && options.emplace(key, argv[index + 1]).second,
      "Unknown or duplicate cooker option");
 }
 const auto output = fs::absolute(fs::path(options.at(L"--output"))).lexically_normal();
 require(output.has_filename() && !fs::exists(output), "Output must be a fresh directory; existing paths are preserved");
 const auto parent = plain_path(output.parent_path());
 require(fs::is_directory(parent), "Output parent must be an existing unredirected directory");
 const auto source = read_bounded(fs::path(options.at(L"--source")), aibs::mesh_asset_max_input_bytes);
 const auto material_bytes = read_bounded(fs::path(options.at(L"--materials")), text_limit);
 const auto license = read_bounded(fs::path(options.at(L"--license")), text_limit);
 require(!license.empty() && std::none_of(license.begin(), license.end(),
     [](std::byte c) { return c == std::byte{0}; }) && std::any_of(license.begin(), license.end(),
     [](std::byte c) { return std::to_integer<unsigned char>(c) > 32; }),
     "An explicit nonempty text license/rights declaration is required");
 const auto materials = parse_materials(material_bytes);
 const auto asset_id = utf8(options.at(L"--asset-id"));
 const auto name = utf8(options.at(L"--name"));
 const auto asset = aibs::import_obj(text(source), materials, asset_id, name);
 const auto encoded = aibs::encode_mesh_asset(asset);
 const auto digest = aibs::asset_sha256(encoded);
 const auto filename = digest + ".aibmesh";
 const auto catalog = "AIBCAT 1\n" + asset_id + " " + digest + " " + filename + "\n";
 const auto provenance = "{\n  \"schema_version\":1,\n  \"asset_id\":" + json_quote(asset_id) +
     ",\n  \"name\":" + json_quote(name) + ",\n  \"source\":" + input_record(source) +
     ",\n  \"materials\":" + input_record(material_bytes) + ",\n  \"license\":" + input_record(license) +
     ",\n  \"license_review\":\"Supplied declaration copied verbatim; ownership/permission not inferred\"," +
     "\n  \"importer\":{\"name\":\"aibs-obj\",\"format_version\":1}," +
     "\n  \"options\":{\"units\":\"meters\",\"up_axis\":\"+Y\",\"axis_conversion\":\"none\",\"material_model\":\"opaque-base-color-emission-v1\",\"external_material_libraries\":\"ignored-explicit-material-table-only\"}," +
     "\n  \"cooked\":{\"file\":" + json_quote(filename) + ",\"sha256\":" + json_quote(digest) +
     ",\"bytes\":" + std::to_string(encoded.size()) + "}\n}\n";
 const auto success = "{\"status\":\"passed\",\"asset_id\":" + json_quote(asset_id) +
     ",\"sha256\":" + json_quote(digest) + ",\"output_root\":" + json_quote(utf8(output.wstring())) +
     ",\"vertices\":" + std::to_string(asset.vertices.size()) + ",\"triangles\":" +
     std::to_string(asset.indices.size() / 3) + "}\n";
 require(success.size() <= text_limit, "Cook success report exceeds 64 KiB; choose a shorter output path");
 Stage stage(parent, output.filename());
 stage.add(filename, encoded);
 stage.add("catalog.aibcat", bytes(catalog));
 stage.add("LICENSE.txt", license);
 stage.add("provenance.json", bytes(provenance));
 stage.publish(output);
 std::cout << success;
 return 0;
}
}
int wmain(int argc, wchar_t** argv) {
 try { return cook(argc, argv); }
 catch (const std::exception& error) { std::cerr << "Asset cook rejected: " << error.what() << '\n'; return 1; }
}
