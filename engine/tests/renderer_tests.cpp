#include <aibs/render.hpp>
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace aibs;
void require(bool ok, const char* why) { if (!ok) throw std::runtime_error(why); }
int main() {
 try {
  using TransientDraw = void (Dx12Renderer::*)(const Camera&, const SceneMesh&);
  const auto transient_draw = static_cast<TransientDraw>(&Dx12Renderer::render);
  require(transient_draw != nullptr, "transient geometry draw API is exported");
  auto scene = make_motherboard_scene();
  require(scene.vertices.size() > 2000 && scene.vertices.size() % 3 == 0, "triangle motherboard geometry");
  require(scene.landmarks.size() >= 4, "CPU, RAM, GPU and board landmarks");
  for (const auto& vertex : scene.vertices) {
   require(std::isfinite(vertex.position.x) && std::isfinite(vertex.position.y) && std::isfinite(vertex.position.z), "finite vertices");
   require(vertex.color.x >= 0 && vertex.color.x <= 1 && vertex.color.y >= 0 && vertex.color.y <= 1, "normalized colors");
  }
  Camera camera;
  auto prior = camera.position;
  WindowInput input; input.forward = 1;
  camera.update(input, 1);
  require(camera.position != prior, "camera moves");
  auto moved = camera.position;
  camera.update(input, -1);
  require(camera.position == moved, "negative elapsed time rejected");
  input.pitch_delta = 10000;
  camera.update(input, 0.01f);
  require(camera.pitch < 1.5f && camera.pitch > -1.5f, "pitch bounded");
  for (float value : camera.view_projection(16.0f / 9.0f)) require(std::isfinite(value), "finite view projection");
  bool rejected = false;
  try { (void)camera.view_projection(0); } catch (const std::invalid_argument&) { rejected = true; }
  require(rejected, "invalid aspect rejected");
  std::cout << "PASS: motherboard geometry and camera contracts\n";
  return 0;
 } catch (const std::exception& error) { std::cerr << "FAIL: " << error.what() << '\n'; return 1; }
}
