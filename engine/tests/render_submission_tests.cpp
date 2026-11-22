#include "../src/render_submission.hpp"
#include <iostream>
#include <memory>
#include <stdexcept>
namespace {
struct Resource {int* live;explicit Resource(int& n):live(&n){++*live;}~Resource(){--*live;}};
void need(bool value){if(!value)throw std::runtime_error("Submission lifetime contract failed");}
template<class F>void rejects(F f){bool rejected=false;try{f();}catch(const std::runtime_error&){rejected=true;}need(rejected);}
}
int main(){try{
 int live=0,submissions=0;
 aibs::detail::SubmissionLifetime<Resource> owner;
 owner.prepare(std::make_unique<Resource>(live));
 auto completed=owner.submit_and_wait([&]{++submissions;},[]{});
 need(live==1&&submissions==1&&!owner.poisoned()&&!owner.has_pending());
 completed.reset();need(live==0);
 owner.prepare(std::make_unique<Resource>(live));
 rejects([&]{owner.submit_and_wait([&]{++submissions;},[]{throw std::runtime_error("Injected fence timeout");});});
 need(owner.poisoned()&&owner.has_pending()&&live==1&&submissions==2);
 rejects([&]{owner.require_healthy();});
 rejects([&]{owner.submit_and_wait([&]{++submissions;},[]{});});
 need(live==1&&submissions==2);
 // Only a separately proven queue completion/device removal permits release.
 owner.release_after_completion();need(live==0&&!owner.has_pending()&&owner.poisoned());
 aibs::detail::SubmissionLifetime<Resource> signal_failure;
 signal_failure.prepare(std::make_unique<Resource>(live));
 rejects([&]{signal_failure.submit_and_wait([]{throw std::runtime_error("Injected queue signal failure");},[]{});});
 need(signal_failure.poisoned()&&signal_failure.has_pending()&&live==1);
 signal_failure.release_after_completion();need(live==0);
 aibs::detail::SubmissionLifetime<Resource> pre_submit;
 rejects([&]{pre_submit.submit_and_wait([]{},[]{});});
 need(!pre_submit.poisoned());
 std::cout<<"PASS CPU injected upload timeout/signal failure retention, poison rejection and completed release\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
