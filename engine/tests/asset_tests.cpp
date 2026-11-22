#include <aibs/assets.hpp>
#include <aibs/engine.hpp>
#include <array>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
std::size_t checks = 0;
void need(bool condition, const char* message) { ++checks; if (!condition) throw std::runtime_error(message); }
template<class F> void rejects(F&& action, const char* message) {
 bool rejected = false;
 try { action(); } catch (const std::exception&) { rejected = true; }
 need(rejected, message);
}
std::span<const std::byte> bytes(std::string_view text) {
 return {reinterpret_cast<const std::byte*>(text.data()), text.size()};
}
void integer(std::vector<std::byte>& data, std::size_t offset, std::uint32_t value) {
 for (unsigned i=0;i<4;++i) data.at(offset+i)=static_cast<std::byte>((value>>(8*i))&255);
}
void rechecksum(std::vector<std::byte>& data) {
 const auto sha=aibs::asset_sha256(std::span<const std::byte>(data).subspan(48));
 const auto digit=[](char c) { return static_cast<unsigned>(c <= '9' ? c-'0' : c-'a'+10); };
 for (std::size_t i=0;i<32;++i) data.at(16+i)=static_cast<std::byte>((digit(sha[2*i])<<4)|digit(sha[2*i+1]));
}
const std::string triangle = "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n";
const std::array<aibs::MeshMaterial, 2> materials{{{"red", {1,0,0}, .25f}, {"green", {0,1,0}, 0}}};
aibs::MeshAsset imported(std::string_view source = triangle) {
 return aibs::import_obj(source, materials, "5d40817e-d515-47de-8849-55d6569b03df", "Triangle");
}
struct Scratch {
 std::filesystem::path root = std::filesystem::temp_directory_path() / ("aibs-assets-" + aibs::new_uuid());
 Scratch() { if (!std::filesystem::create_directory(root)) throw std::runtime_error("Could not create unique test directory"); }
 ~Scratch() {
  std::error_code error;
  for (const auto* name : {"mesh.aibmesh", "large.aibmesh", "invalid.aibmesh"}) std::filesystem::remove(root/name, error);
  std::filesystem::remove(root, error);
 }
};
}

int main() {
 try {
  using namespace aibs;
  need(asset_sha256({}) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "SHA-256 empty known answer");
  need(asset_sha256(bytes("abc")) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "SHA-256 abc known answer");
  auto asset = imported();
  need(asset.vertices.size() == 3 && asset.indices.size() == 3 && asset.triangle_materials.size() == 1, "native indexed triangle");
  need(asset.vertices[0].normal == Vec3{0,0,1}, "missing normals generated per face");
  need(asset.source_sha256 == asset_sha256(bytes(triangle)), "source SHA identifies exact OBJ bytes");
  need(asset.triangle_materials[0] == 0 && asset.materials[0].emission == .25f, "explicit engine materials copied");
  const auto referenced = imported("mtllib never-read.mtl\no test\ng mesh\ns off\n# safe metadata\nv 0 0 0\nv 1 0 0\nv 0 1 0\nvt .2 .3\nvn 0 0 2\nusemtl green\nf -3/1/1 -2/1/1 -1/1/1\n");
  need(referenced.triangle_materials[0] == 1 && referenced.vertices[0].normal == Vec3{0,0,1}, "negative indices, checked UV and named material");
  need(imported("v 0 0 0\nv 1 0 0\nv 0 1 0\nvn 0 0 1\nf 1//1 2//1 3//1\n").indices.size() == 3, "normal-only OBJ references");
  for (const auto& malformed : {
       std::string("v nan 0 0\n"), std::string("v 0 inf 0\n"),
       triangle + "unknown command\n", triangle + "usemtl missing\n",
       std::string("v 0 0 0\nv 1 0 0\nv 2 0 0\nf 1 2 3\n"),
       std::string("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 0 2 3\n"),
       std::string("v 0 0 0\nv 1 0 0\nv 0 1 0\nf -4 2 3\n"),
       std::string("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3 1\n"),
       std::string("v 0 0 0\nv 1 0 0\nv 0 1 0\nvn 0 0 0\nf 1//1 2//1 3//1\n"),
       std::string("v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nf 1/1/2 2/1/2 3/1/2\n")}) {
   rejects([&] { (void)imported(malformed); }, "malformed/unsupported OBJ rejected");
  }
  for (const auto& double_sign : {
       std::string("v +-1 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
       std::string("v 0 0 0\nv 1 0 0\nv 0 1 0\nvn +-1 0 1\nf 1//1 2//1 3//1\n"),
       std::string("v 0 0 0\nv 1 0 0\nv 0 1 0\nf +-3 2 3\n")}) {
   rejects([&] { (void)imported(double_sign); }, "double-sign OBJ numbers/references rejected");
  }
  rejects([&] { (void)imported(std::string(mesh_asset_max_input_bytes+1, ' ')); }, "OBJ input cap checked");
  std::string too_many_positions;
  for (std::size_t i=0;i<=mesh_asset_max_vertices;++i) too_many_positions+="v 0 0 0\n";
  rejects([&] { (void)imported(too_many_positions); }, "OBJ position budget checked before append");
  std::string too_many_triangles="v 0 0 0\nv 1 0 0\nv 0 1 0\n";
  for (std::size_t i=0;i<=mesh_asset_max_triangles;++i) too_many_triangles+="f 1 2 3\n";
  rejects([&] { (void)imported(too_many_triangles); }, "OBJ triangle budget checked before append");
  std::vector<MeshMaterial> excessive(mesh_asset_max_materials+1, materials[0]);
  rejects([&] { (void)import_obj(triangle, excessive, asset.asset_id, asset.name); }, "material budget checked");
  for (unsigned mutation = 0; mutation < 8; ++mutation) {
   auto invalid = asset;
   if (mutation == 0) invalid.asset_id = "not-a-uuid";
   if (mutation == 1) invalid.source_sha256 = "not-a-sha";
   if (mutation == 2) invalid.indices[0] = 100;
   if (mutation == 3) invalid.triangle_materials[0] = 100;
   if (mutation == 4) invalid.vertices[0].position.x = std::numeric_limits<float>::infinity();
   if (mutation == 5) invalid.materials[0].base_color.x = 2;
   if (mutation == 6) invalid.vertices[0].normal = {};
   if (mutation == 7) invalid.triangle_materials.clear();
   rejects([&] { validate_mesh_asset(invalid); }, "invalid native asset rejected");
  }
  const auto encoded = encode_mesh_asset(asset);
  need(encode_mesh_asset(decode_mesh_asset(encoded)) == encoded, "canonical deterministic binary roundtrip");
  auto negative_zero = asset;
  negative_zero.vertices[0].position.x = -0.0f;
  need(encode_mesh_asset(negative_zero) == encoded, "signed zero encoded canonically");
  auto corrupt = encoded;
  corrupt.back() ^= std::byte{1};
  rejects([&] { (void)decode_mesh_asset(corrupt); }, "payload checksum enforced");
  corrupt = encoded; corrupt[0] = std::byte{0};
  rejects([&] { (void)decode_mesh_asset(corrupt); }, "binary magic enforced");
  corrupt = encoded; corrupt[8] = std::byte{2};
  rejects([&] { (void)decode_mesh_asset(corrupt); }, "unknown binary version rejected");
  corrupt = encoded; corrupt.pop_back();
  rejects([&] { (void)decode_mesh_asset(corrupt); }, "truncated binary rejected");
  corrupt = encoded; corrupt.push_back(std::byte{0});
  rejects([&] { (void)decode_mesh_asset(corrupt); }, "trailing binary data rejected");
  corrupt = encoded;
  for (std::size_t i = 12; i < 16; ++i) corrupt[i] = std::byte{255};
  rejects([&] { (void)decode_mesh_asset(corrupt); }, "oversized declared payload rejected before allocation");
  const auto vertex_count_offset=48+12+asset.asset_id.size()+asset.name.size()+asset.source_sha256.size();
  corrupt=encoded;integer(corrupt,vertex_count_offset,0xffffffffu);rechecksum(corrupt);
  rejects([&] { (void)decode_mesh_asset(corrupt); }, "checksummed oversized vertex count rejected before allocation");
  corrupt=encoded;integer(corrupt,vertex_count_offset+4,0x80000000u);rechecksum(corrupt);
  rejects([&] { (void)decode_mesh_asset(corrupt); }, "checksummed noncanonical signed zero rejected");
  Scratch scratch;
  const auto file = scratch.root/"mesh.aibmesh";
  save_mesh_asset(file, asset);
  need(encode_mesh_asset(load_mesh_asset(file)) == encoded, "asset file load/save");
  rejects([&] { save_mesh_asset(file, referenced); }, "published asset cannot be overwritten");
  need(encode_mesh_asset(load_mesh_asset(file)) == encoded, "failed overwrite preserves exact original");
  auto invalid = asset; invalid.indices[0] = 99;
  rejects([&] { save_mesh_asset(scratch.root/"invalid.aibmesh", invalid); }, "invalid asset cannot publish");
  need(!std::filesystem::exists(scratch.root/"invalid.aibmesh"), "failed save leaves no partial final file");
  { std::ofstream oversized(scratch.root/"large.aibmesh", std::ios::binary); oversized.seekp(static_cast<std::streamoff>(mesh_asset_max_input_bytes)); oversized.put('x'); }
  rejects([&] { (void)load_mesh_asset(scratch.root/"large.aibmesh"); }, "oversized file rejected before read allocation");
  std::cout << "PASS: " << checks << " bounded OBJ/material/binary/immutable-file checks\n";
  return 0;
 } catch (const std::exception& error) { std::cerr << "FAIL: " << error.what() << '\n'; return 1; }
}
