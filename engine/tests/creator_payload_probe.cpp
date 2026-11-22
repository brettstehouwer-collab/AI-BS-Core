#include <aibs/creator_payload.hpp>
#include <iostream>
#include <fcntl.h>
#include <io.h>
int main() {
 _setmode(_fileno(stdin), _O_BINARY); _setmode(_fileno(stdout), _O_BINARY);
 try {
  std::vector<unsigned char> bytes; char chunk[4096];
  while(std::cin) {
   std::cin.read(chunk,sizeof(chunk)); const auto n=static_cast<std::size_t>(std::cin.gcount());
   if(bytes.size()+n>aibs::creator_payload::maximum_bytes) throw std::runtime_error("Payload too large");
   bytes.insert(bytes.end(),chunk,chunk+n);
  }
  const auto request=aibs::creator_payload::decode_edit(bytes);
  const auto output=aibs::creator_payload::encode_edit(request);
  std::cout.write(reinterpret_cast<const char*>(output.data()),static_cast<std::streamsize>(output.size())); return 0;
 } catch(const std::exception& e) {std::cerr<<e.what();return 2;}
}
