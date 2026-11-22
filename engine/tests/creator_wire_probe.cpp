#include <aibs/creator_wire.hpp>
#include <iostream>
#include <array>
#include <fcntl.h>
#include <io.h>
int main() {
 _setmode(_fileno(stdin), _O_BINARY); _setmode(_fileno(stdout), _O_BINARY);
 try {
  aibs::creator_wire::Parser parser;
  std::array<unsigned char, 37> chunk{};
  while (std::cin) {
   std::cin.read(reinterpret_cast<char*>(chunk.data()), chunk.size());
   const auto count = static_cast<std::size_t>(std::cin.gcount());
   for (const auto& frame : parser.feed({chunk.data(), count})) {
    const auto bytes = aibs::creator_wire::encode(frame);
    std::cout.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
   }
  }
  parser.finish(); return 0;
 } catch (const std::exception& error) { std::cerr << error.what(); return 2; }
}
