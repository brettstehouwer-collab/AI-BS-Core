#include <aibs/creator_payload.hpp>
#include <array>
#include <filesystem>
#include <iostream>
#include <map>
#include <new>
#include <string_view>
#include <fcntl.h>
#include <io.h>

namespace {
using namespace aibs;
namespace wire=creator_wire;
namespace payload=creator_payload;
using Reader=payload::detail::Reader;
using Writer=payload::detail::Writer;
using payload::detail::ensure;
enum class Status:std::uint16_t {ok=0,prepared=1,applied=2,duplicate=3,undone=4,redone=5,saved=6,playing=7,stopped=8,rejected=100};
struct Reply {
 Status status=Status::ok;
 std::string message="Command completed";
 std::uint64_t operation_revision=0;
 std::string token;
 bool compatible=false;
 std::uint64_t save_bytes=0;
 std::string save_message="Not assessed";
 std::vector<unsigned char> body;
};
Status status(CreatorHostStatus value) {
 switch(value) {
 case CreatorHostStatus::prepared:return Status::prepared;
 case CreatorHostStatus::applied:return Status::applied;
 case CreatorHostStatus::duplicate:return Status::duplicate;
 case CreatorHostStatus::undone:return Status::undone;
 case CreatorHostStatus::redone:return Status::redone;
 case CreatorHostStatus::saved:return Status::saved;
 case CreatorHostStatus::playing:return Status::playing;
 case CreatorHostStatus::stopped:return Status::stopped;
 case CreatorHostStatus::rejected:return Status::rejected;
 }
 throw std::runtime_error("Unknown native owner result");
}
std::string bounded_message(std::string message) {
 if(!payload::detail::utf8(message)) return "Creator operation failed; diagnostic is not UTF-8";
 if(message.size()>4096) {
  message.resize(4096);
  while(!payload::detail::utf8(message)) message.pop_back();
 }
 return message;
}
std::array<unsigned char,16> epoch_bytes() {
 std::array<unsigned char,16> bytes{};const auto id=new_uuid();unsigned nibble=0;
 for(const char c:id) {
  if(c=='-') continue;
  const auto value=static_cast<unsigned>(c<='9'?c-'0':c-'a'+10);
  auto& byte=bytes[nibble/2];byte=static_cast<unsigned char>((byte<<4)|value);++nibble;
 }
 return bytes;
}
void end(const Reader& reader) {ensure(reader.offset==reader.data.size(),"Trailing command bytes");}
Reader reader(const wire::Frame& frame) {
 ensure(frame.payload.size()<=payload::maximum_bytes,"Request exceeds 1 MiB");
 Reader r{frame.payload};ensure(r.number(2)==1,"Unsupported command version");return r;
}
struct ScopeRequest {CreatorScope scope;std::string host_epoch;};
ScopeRequest scope(Reader& r) {
 ScopeRequest result;result.scope.project=r.text(true);result.scope.branch=r.text(true);
 result.scope.world_id=r.text(true);result.host_epoch=r.text(true);
 payload::detail::uuid(result.scope.world_id);payload::detail::uuid(result.host_epoch);return result;
}
void entity(Writer& w,const Entity& value) {
 w.text(value.id,true);w.text(value.name);w.text(value.persistent_id,true);w.number(value.fields.size(),4);
 for(const auto& [key,number]:value.fields) {w.text(key,true);w.real(number);}
}
class Owner {
 std::filesystem::path root_;
 bool negotiated_=false;
 std::unique_ptr<CreatorHost> host_;
 std::map<std::string,CreatorPreparedPtr> tokens_;
 void check_scope(const ScopeRequest& request) const {
  ensure(host_!=nullptr,"No document open");
  ensure(request.scope==host_->snapshot()->scope&&request.host_epoch==host_->epoch_id(),"Document scope or host epoch mismatch");
 }
 void check_head(const wire::Frame& frame) const {
  ensure(host_&&frame.revision==host_->snapshot()->revision,"Authored revision conflict");
 }
 std::filesystem::path slot() const {
  const auto path=root_/L"world.aibs";
  ensure(std::filesystem::weakly_canonical(path)==path,"Workspace checkpoint redirects outside the selected slot");
  const auto lock=root_/L"world.aibs.lock";
  ensure(!std::filesystem::is_symlink(lock),"Checkpoint lock redirects outside the selected slot");
  return path;
 }
 Reply result(CreatorHostResult result) {
  Reply reply;reply.status=status(result.status);reply.message=std::move(result.message);reply.operation_revision=result.revision;
  if(result.status==CreatorHostStatus::prepared) {
   ensure(tokens_.size()<8,"Prepared handle budget exceeded");
   reply.token=new_uuid();const auto& dependencies=result.change->dependencies();
   reply.compatible=dependencies.save.compatible;reply.save_bytes=dependencies.save.encoded_bytes;
   reply.save_message=dependencies.save.message;
   tokens_.emplace(reply.token,std::move(result.change));
  }
  if(result.status==CreatorHostStatus::applied||result.status==CreatorHostStatus::undone||
     result.status==CreatorHostStatus::redone||result.status==CreatorHostStatus::saved) tokens_.clear();
  return reply;
 }
public:
 const std::array<unsigned char,16> epoch=epoch_bytes();
 bool shutdown=false;
 explicit Owner(std::filesystem::path root):root_(std::filesystem::canonical(root)) {
  ensure(std::filesystem::is_directory(root_),"Workspace must be an existing directory");
 }
 Reply dispatch(const wire::Frame& frame) {
  try {
   ensure(!frame.response,"A request must not set the response flag");
   if(frame.opcode==wire::Opcode::hello) {
    ensure(!negotiated_&&frame.epoch==std::array<unsigned char,16>{}&&frame.revision==wire::unscoped_revision&&frame.payload.empty(),"Invalid Hello negotiation");
    Writer body;body.text("numeric-authoring-v1;in-process-play;no-native-viewport");
    body.number(payload::maximum_bytes,4);body.number(8,4);
    Reply reply;reply.body=std::move(body.data);negotiated_=true;return reply;
   }
   ensure(negotiated_&&frame.epoch==epoch,"Process epoch mismatch or Hello required");
   if(frame.opcode==wire::Opcode::shutdown) {
    ensure(frame.revision==wire::unscoped_revision&&frame.payload.empty(),"Invalid Shutdown request");
    Reply reply;shutdown=true;return reply; // Deliberately no implicit save.
   }
   if(frame.opcode==wire::Opcode::open) {
    ensure(frame.revision==wire::unscoped_revision&&!host_,"Open requires an unopened owner process");
    auto r=reader(frame);auto project=r.text(true);auto branch=r.text(true);const auto create=r.number(1);const auto count=r.number(4);
    ensure(create<=1&&count>0&&count<=64,"Invalid Open mode or schema count");SchemaRegistry registry;
    for(std::uint64_t i=0;i<count;++i) {
     auto id=r.text(true);const auto low=r.real(),high=r.real();
     ensure(registry.add({std::move(id),low,high}),"Invalid or duplicate schema field");
    }
    end(r);const auto path=slot();CreatorSession session(std::move(registry),std::move(project),std::move(branch));
    if(std::filesystem::exists(path)) {
     const auto loaded=CheckpointStore::load(path,session);ensure(loaded.ok,loaded.message.c_str());
    } else ensure(create==1,"Checkpoint does not exist; explicit create is required");
    auto owner=std::make_unique<CreatorHost>(std::move(session));host_.swap(owner);return Reply{};
   }
   if(frame.opcode==wire::Opcode::preview||frame.opcode==wire::Opcode::apply_transaction) {
    const auto request=payload::decode_edit(frame.payload);check_scope({request.scope,request.host_epoch});
    ensure(frame.revision==request.transaction.expected_revision,"Frame and transaction revisions differ");
    // Do not check the current head here: durable retries resolve first in host.
    return result(frame.opcode==wire::Opcode::preview?host_->preview(request.scope,request.transaction):host_->apply(request.scope,request.transaction));
   }
   auto r=reader(frame);const auto request=scope(r);check_scope(request);
   if(frame.opcode==wire::Opcode::history) {
    auto id=r.text(true);const auto direction=r.number(1);ensure(direction<=1,"Invalid history direction");end(r);
    return result(host_->travel({std::move(id),request.host_epoch,request.scope,frame.revision,
      direction?CreatorHistoryDirection::redo:CreatorHistoryDirection::undo}));
   }
   check_head(frame);
   if(frame.opcode==wire::Opcode::describe) {
    end(r);Writer body;const auto view=host_->snapshot();body.number(view->schemas.size(),4);
    for(const auto& [id,field]:view->schemas) {body.text(id,true);body.real(field.minimum);body.real(field.maximum);}
    Reply reply;reply.body=std::move(body.data);return reply;
   }
   if(frame.opcode==wire::Opcode::snapshot_page) {
    const auto checkpoint=r.text();const auto after=r.text();const auto limit=r.number(4);end(r);
    const auto view=host_->snapshot();ensure(checkpoint==view->checkpoint_id,"Snapshot checkpoint cursor is stale");
    ensure(limit>0&&limit<=64,"Snapshot page count limit");
    auto it=after.empty()?view->world.begin():view->world.upper_bound(after);Writer rows;std::uint64_t count=0;std::string cursor=after;
    while(it!=view->world.end()&&count<limit) {
     Writer next;entity(next,it->second);
     if(rows.data.size()+next.data.size()>500*1024) {ensure(count!=0,"Entity exceeds page byte budget");break;}
     rows.data.insert(rows.data.end(),next.data.begin(),next.data.end());cursor=it->first;++count;++it;
    }
    Writer body;body.text(cursor);body.number(it!=view->world.end()?1:0,1);body.number(count,4);
    body.data.insert(body.data.end(),rows.data.begin(),rows.data.end());Reply reply;reply.body=std::move(body.data);return reply;
   }
   if(frame.opcode==wire::Opcode::apply_prepared||frame.opcode==wire::Opcode::release_prepared||frame.opcode==wire::Opcode::stop_play) {
    const auto handle=r.text(true);payload::detail::uuid(handle);end(r);
    if(frame.opcode==wire::Opcode::stop_play) return result(host_->stop_play(handle));
    const auto found=tokens_.find(handle);ensure(found!=tokens_.end(),"Prepared handle expired or unknown");
    if(frame.opcode==wire::Opcode::release_prepared) {tokens_.erase(found);return Reply{};}
    return result(host_->apply(found->second));
   }
   if(frame.opcode==wire::Opcode::save) {end(r);return result(host_->save(slot()));}
   if(frame.opcode==wire::Opcode::start_play) {end(r);return result(host_->start_play(request.scope,frame.revision));}
   throw payload::PayloadError("Command is not implemented");
  } catch(const std::bad_alloc&) {throw;} // Unknown outcome: terminate, never report rejection after a commit.
    catch(const std::exception& error) {
     Reply reply;reply.status=Status::rejected;reply.message=bounded_message(error.what());return reply;
    }
 }
 wire::Frame response(const wire::Frame& request,const Reply& reply) const {
  Writer w;w.number(1,2);w.number(static_cast<std::uint16_t>(reply.status),2);w.text(bounded_message(reply.message));
  const auto view=host_?host_->snapshot():nullptr;
  w.text(host_?host_->epoch_id():"");w.text(view?view->scope.project:"");w.text(view?view->scope.branch:"");w.text(view?view->scope.world_id:"");
  w.number(view?view->revision:0,8);w.text(view?view->checkpoint_id:"");w.number(reply.operation_revision,8);w.text(reply.token);
  w.text(host_&&host_->play()?host_->play()->epoch:"");w.number(reply.compatible?1:0,1);w.number(reply.save_bytes,8);w.text(bounded_message(reply.save_message));
  w.number(view?view->world.size():0,4);w.number(view?view->undo_depth:0,8);w.number(view?view->redo_depth:0,8);
  ensure(reply.body.size()<=512*1024,"Response body exceeds budget");w.number(reply.body.size(),4);w.data.insert(w.data.end(),reply.body.begin(),reply.body.end());
  return {request.opcode,request.request_id,negotiated_?epoch:std::array<unsigned char,16>{},view?view->revision:0,std::move(w.data),true};
 }
};
}
int wmain(int argc,wchar_t** argv) {
 _setmode(_fileno(stdin),_O_BINARY);_setmode(_fileno(stdout),_O_BINARY);
 if(argc!=3||std::wstring_view(argv[1])!=L"--workspace") {std::cerr<<"Usage: aibs_creator_host --workspace EXISTING_DIRECTORY\n";return 64;}
 try {
  Owner owner{std::filesystem::path(argv[2])};wire::Parser parser;
  while(!owner.shutdown) {
   std::array<unsigned char,48> header{};
   std::cin.read(reinterpret_cast<char*>(header.data()),header.size());const auto got=std::cin.gcount();
   if(got==0&&std::cin.eof()) {parser.finish();break;}
   ensure(got==static_cast<std::streamsize>(header.size()),"Truncated pipe header");
   auto frames=parser.feed(header);const auto length=wire::detail::number(header,12,4);
   ensure(length<=payload::maximum_bytes&&wire::detail::number(header,10,2)==0,"Invalid request size or response flag");
   std::size_t left=static_cast<std::size_t>(length);std::array<unsigned char,65536> chunk{};
   while(left) {
    const auto take=(std::min)(left,chunk.size());std::cin.read(reinterpret_cast<char*>(chunk.data()),static_cast<std::streamsize>(take));
    ensure(std::cin.gcount()==static_cast<std::streamsize>(take),"Truncated pipe payload");
    auto next=parser.feed({chunk.data(),take});frames.insert(frames.end(),std::make_move_iterator(next.begin()),std::make_move_iterator(next.end()));left-=take;
   }
   ensure(frames.size()==1,"Expected exactly one complete request");
   const auto reply=owner.dispatch(frames.front());const auto bytes=wire::encode(owner.response(frames.front(),reply));
   std::cout.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));std::cout.flush();
   ensure(std::cout.good(),"Creator response pipe closed");
  }
  return 0;
 } catch(const std::exception& error) {std::cerr<<bounded_message(error.what())<<'\n';return 2;}
}
