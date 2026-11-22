#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/engine.hpp>
#include <array>
#include <stdexcept>

namespace aibs {
std::string new_uuid() {
 std::array<unsigned char, 16> bytes{};
 if (BCryptGenRandom(nullptr, bytes.data(), static_cast<ULONG>(bytes.size()), BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0)
  throw std::runtime_error("Operating-system UUID entropy unavailable");
 bytes[6] = static_cast<unsigned char>((bytes[6] & 0x0f) | 0x40);
 bytes[8] = static_cast<unsigned char>((bytes[8] & 0x3f) | 0x80);
 constexpr char hex[] = "0123456789abcdef";
 std::string result;
 result.reserve(36);
 for (std::size_t i = 0; i < bytes.size(); ++i) {
  if (i == 4 || i == 6 || i == 8 || i == 10) result += '-';
  result += hex[bytes[i] >> 4]; result += hex[bytes[i] & 15];
 }
 return result;
}
bool is_uuid(const std::string& s) noexcept {
 if (s.size() != 36 || s[14] != '4' || (s[19] != '8' && s[19] != '9' && s[19] != 'a' && s[19] != 'b')) return false;
 for (std::size_t i = 0; i < s.size(); ++i) {
  if (i == 8 || i == 13 || i == 18 || i == 23) { if (s[i] != '-') return false; }
  else if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f'))) return false;
 }
 return true;
}
}
