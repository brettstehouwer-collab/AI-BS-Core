#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/persistence.hpp>
#include <algorithm>
#include <bit>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <utility>

namespace aibs {
namespace {
using Bytes = std::vector<unsigned char>;
constexpr std::size_t max_items = 10000;
constexpr std::size_t max_expanded_items = 200000;
constexpr std::size_t max_replay_bytes = 64 * 1024 * 1024;
void ensure(bool condition, const char* why) { if (!condition) throw std::runtime_error(why); }
struct Writer {
 Bytes bytes;
 std::size_t remaining_items = max_expanded_items;
 void consume(std::size_t count) { ensure(count <= remaining_items, "Checkpoint expansion budget exceeded"); remaining_items -= count; }
 void number(std::uint64_t n, unsigned width = 8) {
  ensure(bytes.size() + width <= CheckpointStore::maximum_file_bytes, "Checkpoint exceeds size limit");
  for (unsigned i = 0; i < width; ++i) bytes.push_back(static_cast<unsigned char>(n >> (8 * i)));
 }
 void count(std::size_t n) { ensure(n <= max_items, "Checkpoint collection limit exceeded"); number(n, 4); }
 void text(const std::string& s) {
  ensure(s.size() <= 4096 && bytes.size() + 4 + s.size() <= CheckpointStore::maximum_file_bytes, "Checkpoint string/size limit exceeded");
  number(s.size(), 4); bytes.insert(bytes.end(), s.begin(), s.end());
 }
};
struct Reader {
 const Bytes& bytes;
 std::size_t cursor = 0;
 std::size_t remaining_items = max_expanded_items;
 void consume(std::size_t count) { ensure(count <= remaining_items, "Checkpoint expansion budget exceeded"); remaining_items -= count; }
 std::uint64_t number(unsigned width = 8) {
  ensure(cursor <= bytes.size() && width <= bytes.size() - cursor, "Truncated checkpoint");
  std::uint64_t n = 0;
  for (unsigned i = 0; i < width; ++i) n |= static_cast<std::uint64_t>(bytes[cursor++]) << (8 * i);
  return n;
 }
 std::size_t count() { const auto n = number(4); ensure(n <= max_items, "Checkpoint collection limit exceeded"); return static_cast<std::size_t>(n); }
 std::string text() {
  const auto n = number(4);
  ensure(n <= 4096 && n <= bytes.size() - cursor, "Invalid checkpoint string length");
  std::string s(bytes.begin() + static_cast<std::ptrdiff_t>(cursor), bytes.begin() + static_cast<std::ptrdiff_t>(cursor + n));
  cursor += static_cast<std::size_t>(n); return s;
 }
};
std::uint32_t crc32(const Bytes& bytes) {
 std::uint32_t crc = 0xffffffffu;
 for (const auto byte : bytes) {
  crc ^= byte;
  for (unsigned bit = 0; bit < 8; ++bit) crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
 }
 return ~crc;
}
struct Handle {
 HANDLE value = INVALID_HANDLE_VALUE;
 explicit Handle(HANDLE handle) : value(handle) {}
 ~Handle() { if (value != INVALID_HANDLE_VALUE) CloseHandle(value); }
 Handle(const Handle&) = delete;
 Handle& operator=(const Handle&) = delete;
 void close() { if (value != INVALID_HANDLE_VALUE) { CloseHandle(value); value = INVALID_HANDLE_VALUE; } }
};
Bytes read_file(const std::filesystem::path& path) {
 const auto size = std::filesystem::file_size(path);
 ensure(size >= 24 && size <= CheckpointStore::maximum_file_bytes, "Invalid checkpoint file size");
 Bytes bytes(static_cast<std::size_t>(size));
 std::ifstream stream(path, std::ios::binary);
 ensure(stream.good(), "Could not open checkpoint");
 stream.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
 ensure(stream.good(), "Could not read complete checkpoint");
 return bytes;
}
std::filesystem::path lock_path(const std::filesystem::path& path) { auto result = path; result += L".lock"; return result; }
}

struct SnapshotCodec {
 static void entity(Writer& w, const Entity& e) {
  w.consume(1 + e.fields.size());
  w.text(e.id); w.text(e.name); w.text(e.persistent_id); w.count(e.fields.size());
  for (const auto& [id, value] : e.fields) { w.text(id); w.number(std::bit_cast<std::uint64_t>(value)); }
 }
 static Entity entity(Reader& r) {
  r.consume(1);
  Entity e; e.id = r.text(); e.name = r.text(); e.persistent_id = r.text();
  const auto fields = r.count();
  r.consume(fields);
  for (std::size_t i = 0; i < fields; ++i) {
   auto id = r.text(); const auto value = std::bit_cast<double>(r.number());
   ensure(e.fields.emplace(std::move(id), value).second, "Duplicate entity field");
  }
  return e;
 }
 static void world(Writer& w, const World& value) {
  w.count(value.size());
  for (const auto& [id, e] : value) { ensure(id == e.id, "World key differs from entity alias"); entity(w, e); }
 }
 static World world(Reader& r) {
  World value; const auto count = r.count();
  for (std::size_t i = 0; i < count; ++i) {
   auto e = entity(r); const auto alias = e.id;
   ensure(value.emplace(alias, std::move(e)).second, "Duplicate entity alias");
  }
  return value;
 }
 static void edits(Writer& w, const std::vector<Edit>& values) {
  w.count(values.size());
  for (const auto& edit : values) {
   w.number(edit.index(), 1);
   if (const auto* create = std::get_if<Create>(&edit)) entity(w, create->entity);
   else if (const auto* erase = std::get_if<Erase>(&edit)) { w.text(erase->entity); w.text(erase->persistent_id); }
   else { const auto& set = std::get<SetField>(edit); w.text(set.entity); w.text(set.field); w.number(std::bit_cast<std::uint64_t>(set.value)); w.text(set.persistent_id); }
  }
 }
 static std::vector<Edit> edits(Reader& r) {
  std::vector<Edit> values; const auto count = r.count();
  for (std::size_t i = 0; i < count; ++i) {
   const auto kind = r.number(1);
   if (kind == 0) values.push_back(Create{entity(r)});
   else if (kind == 1) { auto alias = r.text(); values.push_back(Erase{std::move(alias), r.text()}); }
   else if (kind == 2) {
    auto alias = r.text(); auto field = r.text(); const auto number = std::bit_cast<double>(r.number());
    values.push_back(SetField{std::move(alias), std::move(field), number, r.text()});
   } else throw std::runtime_error("Unknown checkpoint edit type");
  }
  return values;
 }
 static void transaction(Writer& w, const Transaction& t) { w.text(t.id); w.number(t.expected_revision); edits(w, t.edits); w.text(t.description); }
 static Transaction transaction(Reader& r) {
  Transaction t; t.id = r.text(); t.expected_revision = r.number(); t.edits = edits(r); t.description = r.text(); return t;
 }
 static void valid_world(const CreatorSession& s, const World& value) {
  std::set<std::string> present;
  for (const auto& [id, e] : value) {
   ensure(!id.empty() && id == e.id && is_uuid(e.persistent_id) && s.used_entity_ids_.contains(e.persistent_id) && present.insert(e.persistent_id).second, "Invalid/duplicate persistent entity identity");
   for (const auto& [field, number] : e.fields) ensure(s.schemas_.accepts(field, number), "Saved field conflicts with registered schema");
  }
 }
 static void replay(const CreatorSession& s, World& value, const std::vector<Edit>& values) {
  for (const auto& edit : values) {
   if (const auto* create = std::get_if<Create>(&edit)) {
    const auto& e = create->entity;
    ensure(!e.id.empty() && is_uuid(e.persistent_id) && s.used_entity_ids_.contains(e.persistent_id), "Invalid journal creation identity");
    for (const auto& [field, number] : e.fields) ensure(s.schemas_.accepts(field, number), "Invalid journal creation field");
    ensure(value.emplace(create->entity.id, create->entity).second, "Journal creates an existing alias");
   } else if (const auto* erase = std::get_if<Erase>(&edit)) {
    const auto it = value.find(erase->entity);
    ensure(it != value.end() && it->second.persistent_id == erase->persistent_id, "Journal erase target mismatch");
    value.erase(it);
   } else {
    const auto& set = std::get<SetField>(edit); auto it = value.find(set.entity);
    ensure(it != value.end() && it->second.persistent_id == set.persistent_id && s.schemas_.accepts(set.field, set.value), "Journal field target/schema mismatch");
    it->second.fields[set.field] = set.value;
   }
  }
  valid_world(s, value);
 }
 static void validate(const CreatorSession& s) {
  ensure(is_uuid(s.world_id_) && is_uuid(s.checkpoint_id_), "Invalid world/checkpoint UUID");
  ensure(s.revision_ == s.memory_.events_.size(), "Journal revision mismatch");
  for (const auto& id : s.used_entity_ids_) ensure(is_uuid(id), "Invalid retired identity");
  valid_world(s, s.world_);
  World current;
  std::vector<CreatorSession::History> undo, redo;
  std::set<std::string> allocated;
  std::size_t applied = 0;
  std::size_t work_remaining = max_expanded_items;
  std::size_t bytes_remaining = max_replay_bytes;
  auto entity_weight = [](const Entity& entity) {
   std::size_t bytes = 256 + entity.id.size() + entity.name.size() + entity.persistent_id.size();
   for (const auto& [field, value] : entity.fields) { (void)value; bytes += 128 + field.size(); }
   return bytes;
  };
  for (std::size_t i = 0; i < s.memory_.events_.size(); ++i) {
   const auto& event = s.memory_.events_[i];
   ensure(event.revision == i + 1 && event.project == s.project_ && event.branch == s.branch_ && event.world_id == s.world_id_, "Journal scope/sequence mismatch");
   const auto work = current.size() * 3 + event.edits.size();
   ensure(work <= work_remaining, "Checkpoint replay budget exceeded"); work_remaining -= work;
   std::size_t byte_work = event.edits.size() * 256;
   for (const auto& [id, entity] : current) { (void)id; byte_work += 3 * entity_weight(entity); }
   for (const auto& edit : event.edits) if (const auto* create = std::get_if<Create>(&edit)) byte_work += 3 * entity_weight(create->entity);
   ensure(byte_work <= bytes_remaining, "Checkpoint replay byte budget exceeded"); bytes_remaining -= byte_work;
   auto next = current; replay(s, next, event.edits);
   if (event.kind == "authoring.applied") {
    ++applied;
    const auto receipt = s.receipts_.find(event.operation);
    ensure(receipt != s.receipts_.end(), "Missing operation receipt");
    auto normalized = receipt->second.transaction;
    ensure(!normalized.id.empty() && normalized.id == event.operation && normalized.expected_revision == i && normalized.description == event.description && normalized.edits.size() == event.edits.size() && !normalized.edits.empty() && normalized.edits.size() <= 1024, "Receipt request mismatch");
    for (std::size_t j = 0; j < event.edits.size(); ++j) {
     auto& request = normalized.edits[j]; const auto& realized = event.edits[j];
     ensure(request.index() == realized.index(), "Receipt edit type mismatch");
     if (auto* c = std::get_if<Create>(&request)) {
      const auto& realized_id = std::get<Create>(realized).entity.persistent_id;
      if (c->entity.persistent_id.empty()) c->entity.persistent_id = realized_id;
      ensure(allocated.insert(realized_id).second, "Persistent UUID recycled by creation");
     } else if (auto* e = std::get_if<Erase>(&request)) {
      if (e->persistent_id.empty()) e->persistent_id = std::get<Erase>(realized).persistent_id;
     } else {
      auto& set = std::get<SetField>(request);
      if (set.persistent_id.empty()) set.persistent_id = std::get<SetField>(realized).persistent_id;
     }
     ensure(request == realized, "Receipt differs from realized operation");
    }
    ensure(receipt->second.result.ok && receipt->second.result.revision == event.revision, "Invalid saved operation receipt");
    undo.push_back({current, next}); redo.clear();
   } else if (event.kind == "authoring.undone") {
    ensure(!undo.empty() && next == undo.back().before, "Invalid undo journal");
    redo.push_back(undo.back()); undo.pop_back();
   } else if (event.kind == "authoring.redone") {
    ensure(!redo.empty() && next == redo.back().after, "Invalid redo journal");
    undo.push_back(redo.back()); redo.pop_back();
   } else throw std::runtime_error("Unsupported memory event kind");
   current.swap(next);
  }
  ensure(applied == s.receipts_.size() && allocated == s.used_entity_ids_ && current == s.world_, "World/identity/journal continuity mismatch");
  auto same_history = [&](const auto& saved, const auto& rebuilt) {
   ensure(saved.size() == rebuilt.size(), "History size mismatch");
   for (std::size_t i = 0; i < saved.size(); ++i) {
    valid_world(s, saved[i].before); valid_world(s, saved[i].after);
    ensure(saved[i].before == rebuilt[i].before && saved[i].after == rebuilt[i].after, "History differs from journal");
   }
  };
  same_history(s.undo_, undo); same_history(s.redo_, redo);
 }
 static Bytes encode(const CreatorSession& s) {
  validate(s);
  Writer w;
  w.text(s.project_); w.text(s.branch_); w.text(s.world_id_); w.text(s.checkpoint_id_); w.number(s.revision_);
  w.count(s.schemas_.fields_.size());
  for (const auto& [id, field] : s.schemas_.fields_) { w.text(id); w.number(std::bit_cast<std::uint64_t>(field.minimum)); w.number(std::bit_cast<std::uint64_t>(field.maximum)); }
  w.count(s.used_entity_ids_.size()); for (const auto& id : s.used_entity_ids_) w.text(id);
  world(w, s.world_);
  w.count(s.memory_.events_.size());
  for (const auto& event : s.memory_.events_) {
   w.text(event.project); w.text(event.branch); w.text(event.operation); w.text(event.kind); w.number(event.revision); w.text(event.world_id); edits(w, event.edits); w.text(event.description);
  }
  w.count(s.receipts_.size());
  for (const auto& [id, receipt] : s.receipts_) {
   ensure(id == receipt.transaction.id, "Receipt key mismatch");
   transaction(w, receipt.transaction); w.text(receipt.result.message); w.number(receipt.result.revision);
  }
  for (const auto* history : {&s.undo_, &s.redo_}) {
   w.count(history->size()); for (const auto& h : *history) { world(w, h.before); world(w, h.after); }
  }
  Writer header;
  for (const auto c : std::string("AIBSSAVE")) header.number(static_cast<unsigned char>(c), 1);
  header.number(CheckpointStore::format_version, 4); header.number(w.bytes.size()); header.number(crc32(w.bytes), 4);
  ensure(header.bytes.size() + w.bytes.size() <= CheckpointStore::maximum_file_bytes, "Checkpoint exceeds size limit");
  header.bytes.insert(header.bytes.end(), w.bytes.begin(), w.bytes.end());
  return header.bytes;
 }
 static CreatorSession decode(const Bytes& bytes, const CreatorSession& expected) {
  Reader h{bytes}; std::string magic;
  for (int i = 0; i < 8; ++i) magic += static_cast<char>(h.number(1));
  ensure(magic == "AIBSSAVE" && h.number(4) == CheckpointStore::format_version, "Unsupported checkpoint format/version");
  const auto length = h.number(); const auto crc = h.number(4);
  ensure(length == bytes.size() - h.cursor, "Checkpoint length mismatch");
  Bytes payload(bytes.begin() + static_cast<std::ptrdiff_t>(h.cursor), bytes.end());
  ensure(crc32(payload) == crc, "Checkpoint checksum mismatch");
  Reader r{payload};
  auto project = r.text(); auto branch = r.text();
  ensure(project == expected.project_ && branch == expected.branch_, "Checkpoint project/branch mismatch");
  CreatorSession s(expected.schemas_, std::move(project), std::move(branch));
  s.world_id_ = r.text(); s.checkpoint_id_ = r.text(); s.revision_ = r.number();
  SchemaRegistry saved;
  const auto field_count = r.count();
  for (std::size_t i = 0; i < field_count; ++i) {
   auto id = r.text(); const auto minimum = std::bit_cast<double>(r.number()); const auto maximum = std::bit_cast<double>(r.number());
   ensure(saved.add({std::move(id), minimum, maximum}), "Invalid checkpoint schema");
  }
  ensure(saved.fields_ == expected.schemas_.fields_, "Schema changed; checkpoint requires migration");
  const auto ids = r.count();
  for (std::size_t i = 0; i < ids; ++i) ensure(s.used_entity_ids_.insert(r.text()).second, "Duplicate retired UUID");
  s.world_ = world(r);
  const auto events = r.count();
  for (std::size_t i = 0; i < events; ++i) {
   MemoryEvent e; e.project = r.text(); e.branch = r.text(); e.operation = r.text(); e.kind = r.text(); e.revision = r.number(); e.world_id = r.text(); e.edits = edits(r); e.description = r.text();
   s.memory_.events_.push_back(std::move(e));
  }
  const auto receipts = r.count();
  for (std::size_t i = 0; i < receipts; ++i) {
   auto request = transaction(r); const auto id = request.id; auto message = r.text(); const auto revision = r.number();
   ensure(s.receipts_.emplace(id, CreatorSession::Receipt{std::move(request), {true, std::move(message), revision}}).second, "Duplicate operation receipt");
  }
  for (auto* history : {&s.undo_, &s.redo_}) {
   const auto count = r.count();
   for (std::size_t i = 0; i < count; ++i) { auto before = world(r); auto after = world(r); history->push_back({std::move(before), std::move(after)}); }
  }
  ensure(r.cursor == payload.size(), "Trailing checkpoint bytes");
  validate(s);
  return s;
 }
};

CheckpointAssessment CheckpointStore::assess(const CreatorSession& session) {
 try {
  auto snapshot = session;
  // Encoding requires an identity even before the first save. A fixed valid
  // placeholder has the real checkpoint UUID's byte width and uses no entropy.
  if (snapshot.checkpoint_id_.empty()) snapshot.checkpoint_id_ = "00000000-0000-4000-8000-000000000000";
  const auto bytes = SnapshotCodec::encode(snapshot);
  return {true, bytes.size(), "Compatible with checkpoint format 1; not published"};
 } catch (const std::exception& error) {
  return {false, 0, error.what()};
 }
}

CheckpointResult CheckpointStore::save(const std::filesystem::path& path, CreatorSession& session, SaveObserver observer) {
 std::filesystem::path temporary;
 try {
  Handle lock(CreateFileW(lock_path(path).c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr));
  ensure(lock.value != INVALID_HANDLE_VALUE, "Checkpoint is busy or directory unavailable");
  if (std::filesystem::exists(path)) {
   const auto previous = SnapshotCodec::decode(read_file(path), session);
   ensure(previous.world_id_ == session.world_id_ && previous.checkpoint_id_ == session.checkpoint_id_, "Slot belongs to another world or checkpoint head changed; reload before saving");
  }
  auto snapshot = session;
  snapshot.checkpoint_id_ = new_uuid();
  const auto bytes = SnapshotCodec::encode(snapshot);
  temporary = path; temporary += L"." + std::filesystem::path(snapshot.checkpoint_id_).wstring() + L".tmp";
  Handle file(CreateFileW(temporary.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr));
  ensure(file.value != INVALID_HANDLE_VALUE, "Could not create checkpoint temporary file");
  DWORD written = 0;
  ensure(WriteFile(file.value, bytes.data(), static_cast<DWORD>(bytes.size()), &written, nullptr) && written == bytes.size(), "Could not write complete checkpoint");
  ensure(FlushFileBuffers(file.value) != 0, "Could not flush checkpoint");
  file.close();
  CheckpointResult result{true, "Checkpoint published", session.revision_, snapshot.checkpoint_id_};
  if (observer) observer(SaveStage::before_publish);
  ensure(MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0, "Could not publish checkpoint");
  session.checkpoint_id_.swap(snapshot.checkpoint_id_);
  if (observer) observer(SaveStage::after_publish);
  return result;
 } catch (const std::exception& e) {
  if (!temporary.empty()) DeleteFileW(temporary.c_str());
  return {false, e.what(), session.revision_, session.checkpoint_id_};
 }
}
CheckpointResult CheckpointStore::load(const std::filesystem::path& path, CreatorSession& session, CheckpointValidator validator) {
 try {
  Handle lock(CreateFileW(lock_path(path).c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr));
  ensure(lock.value != INVALID_HANDLE_VALUE, "Checkpoint is busy or directory unavailable");
  auto candidate = SnapshotCodec::decode(read_file(path), session);
  if (validator) validator(candidate);
  CheckpointResult result{true, "Checkpoint restored", candidate.revision_, candidate.checkpoint_id_};
  session.swap_state(candidate);
  return result;
 } catch (const std::exception& e) { return {false, e.what(), session.revision_, session.checkpoint_id_}; }
}
}
