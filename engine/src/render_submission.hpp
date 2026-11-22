#pragma once
#include <memory>
#include <stdexcept>
#include <utility>
namespace aibs::detail {
// The renderer owner must outlive unfinished GPU work, including failed waits.
// This slot is filled before submission and emptied only after proven completion.
template<class Payload>class SubmissionLifetime {
 std::unique_ptr<Payload> pending_;
 bool poisoned_=false;
public:
 bool poisoned()const noexcept{return poisoned_;}
 bool has_pending()const noexcept{return static_cast<bool>(pending_);}
 void poison()noexcept{poisoned_=true;}
 void require_healthy()const{
  if(poisoned_)throw std::runtime_error("Renderer unavailable after GPU synchronization failure");
 }
 void prepare(std::unique_ptr<Payload> payload){
  require_healthy();
  if(!payload||pending_)throw std::runtime_error("Invalid or overlapping GPU submission ownership");
  pending_=std::move(payload);
 }
 template<class Submit,class Wait>std::unique_ptr<Payload> submit_and_wait(Submit submit,Wait wait){
  require_healthy();
  if(!pending_)throw std::runtime_error("GPU submission has no retained resources");
  try{submit();wait();}catch(...){poison();throw;}
  return std::move(pending_);
 }
 void release_after_completion()noexcept{pending_.reset();}
};
}
