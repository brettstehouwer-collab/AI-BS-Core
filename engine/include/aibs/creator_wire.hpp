#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

namespace aibs::creator_wire {
inline constexpr std::size_t maximum_payload = 4 * 1024 * 1024;
inline constexpr std::size_t maximum_chunk = 65536;
inline constexpr std::size_t maximum_burst = 8;
inline constexpr std::uint64_t unscoped_revision = (std::numeric_limits<std::uint64_t>::max)();
enum class Opcode : std::uint16_t {
 hello=1, open=0x10, describe=0x11, snapshot_page=0x12,
 preview=0x20, apply_prepared=0x21, apply_transaction=0x22, release_prepared=0x23,
 history=0x30, save=0x40, start_play=0x50, stop_play=0x51, shutdown=0xff
};
struct Frame {
 Opcode opcode;
 std::uint64_t request_id;
 std::array<unsigned char,16> epoch;
 std::uint64_t revision;
 std::vector<unsigned char> payload;
 bool response = false;
 bool operator==(const Frame&) const = default;
};
class WireError : public std::runtime_error { public: using std::runtime_error::runtime_error; };
namespace detail {
inline void ensure(bool condition, const char* message) { if (!condition) throw WireError(message); }
inline bool known(std::uint64_t op) noexcept {
 switch(op) {
 case 1: case 0x10: case 0x11: case 0x12: case 0x20: case 0x21: case 0x22: case 0x23:
 case 0x30: case 0x40: case 0x50: case 0x51: case 0xff: return true;
 default: return false;
 }
}
inline std::uint64_t number(std::span<const unsigned char> bytes, std::size_t offset, unsigned width) {
 std::uint64_t value=0;
 for (unsigned i=0;i<width;++i) value |= static_cast<std::uint64_t>(bytes[offset+i]) << (8*i);
 return value;
}
inline void append(std::vector<unsigned char>& bytes, std::uint64_t value, unsigned width) {
 for(unsigned i=0;i<width;++i) bytes.push_back(static_cast<unsigned char>(value >> (8*i)));
}
}
inline std::vector<unsigned char> encode(const Frame& frame) {
 detail::ensure(detail::known(static_cast<std::uint16_t>(frame.opcode)), "Unknown creator opcode");
 detail::ensure(frame.request_id && frame.payload.size()<=maximum_payload, "Invalid creator request or payload size");
 std::vector<unsigned char> bytes; bytes.reserve(48+frame.payload.size());
 for(const auto c : {'A','I','B','C'}) bytes.push_back(static_cast<unsigned char>(c));
 detail::append(bytes,1,2); detail::append(bytes,48,2);
 detail::append(bytes,static_cast<std::uint16_t>(frame.opcode),2); detail::append(bytes,frame.response?1:0,2);
 detail::append(bytes,frame.payload.size(),4); detail::append(bytes,frame.request_id,8);
 bytes.insert(bytes.end(),frame.epoch.begin(),frame.epoch.end()); detail::append(bytes,frame.revision,8);
 bytes.insert(bytes.end(),frame.payload.begin(),frame.payload.end()); return bytes;
}
// Framing only; payload schemas, epoch negotiation and owner dispatch are later
// layers. Dispatch returned batches only after feed succeeds. Errors terminate
// the connection. Per-read bounds do not replace the client's pending queue cap.
class Parser {
 std::vector<unsigned char> buffer_;
 Frame pending_{};
 std::size_t payload_size_=0;
 bool pending_header_=false, failed_=false, closed_=false;
 void header() {
  const std::span<const unsigned char> bytes(buffer_);
  detail::ensure(bytes[0]=='A'&&bytes[1]=='I'&&bytes[2]=='B'&&bytes[3]=='C'&&
   detail::number(bytes,4,2)==1&&detail::number(bytes,6,2)==48,"Unsupported creator header");
  const auto op=detail::number(bytes,8,2), flags=detail::number(bytes,10,2);
  const auto length=detail::number(bytes,12,4), request=detail::number(bytes,16,8);
  detail::ensure(detail::known(op)&&flags<=1&&length<=maximum_payload&&request,"Invalid creator header fields");
  pending_.opcode=static_cast<Opcode>(op); pending_.request_id=request;
  std::copy(bytes.begin()+24,bytes.begin()+40,pending_.epoch.begin());
  pending_.revision=detail::number(bytes,40,8); pending_.response=flags==1;
  payload_size_=static_cast<std::size_t>(length); pending_header_=true; buffer_.clear();
 }
public:
 std::size_t buffered_bytes() const noexcept { return buffer_.size(); }
 std::vector<Frame> feed(std::span<const unsigned char> chunk) {
  detail::ensure(!failed_&&!closed_,"Creator connection closed");
  try {
   detail::ensure(chunk.size()<=maximum_chunk,"Creator pipe chunk too large");
   std::size_t offset=0; std::vector<Frame> result;
   while(offset<chunk.size()||pending_header_) {
    const auto target=pending_header_?payload_size_:48;
    const auto take=(std::min)(target-buffer_.size(),chunk.size()-offset);
    buffer_.insert(buffer_.end(),chunk.begin()+static_cast<std::ptrdiff_t>(offset),chunk.begin()+static_cast<std::ptrdiff_t>(offset+take)); offset+=take;
    if(buffer_.size()<target) break;
    if(!pending_header_) header();
    else {
     detail::ensure(result.size()<maximum_burst,"Creator frame burst too large");
     pending_.payload=std::move(buffer_); result.push_back(std::move(pending_));
     buffer_.clear(); pending_=Frame{}; pending_header_=false;
    }
   }
   return result;
  } catch(...) { failed_=true; buffer_.clear(); pending_=Frame{}; pending_header_=false; throw; }
 }
 void finish() {
  if(failed_||!buffer_.empty()||pending_header_) { failed_=true; throw WireError("Truncated creator connection"); }
  closed_=true;
 }
};
}
