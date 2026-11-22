#include <aibs/opening_tour.hpp>
#include <aibs/opening_inspections.hpp>
#include <algorithm>
#include <set>
#include <stdexcept>
namespace aibs {namespace {
constexpr std::string_view roles[]{"controller","truck","diagnostic","bypass","seats","shelter","pencil"};
void validate(const FirstBootContent& content,const OpeningTourTargets& targets){
 const OpeningInspectionCatalog catalog(content.definition());std::set<std::string> seen;
 for(const auto& id:targets.ids)if(!is_uuid(id)||!catalog.find(id)||!seen.insert(id).second)throw std::invalid_argument("Tour roles require seven unique owned inspection fixtures; regenerate bindings");
}
}
std::string_view opening_tour_role_name(OpeningTourRole role)noexcept{const auto i=static_cast<std::size_t>(role);return i<opening_tour_stop_count?roles[i]:std::string_view{};}
std::vector<unsigned char> encode_opening_tour(const FirstBootContent& content,const OpeningTourTargets& targets){
 validate(content,targets);const auto& d=content.definition();std::string text="AIBTOUR 1\n"+d.definition_id+" "+d.world_id+" "+content.fingerprint()+"\n";
 for(std::size_t i=0;i<opening_tour_stop_count;++i)text+=std::string(roles[i])+" "+targets.ids[i]+"\n";
 if(text.size()>4096)throw std::invalid_argument("Tour sidecar exceeds4096bytes");return {text.begin(),text.end()};
}
OpeningTourTargets decode_opening_tour(std::span<const unsigned char> bytes,const FirstBootContent& content){
 if(bytes.empty()||bytes.size()>4096||bytes.back()!='\n')throw std::invalid_argument("Bounded canonical tour sidecar required; regenerate bindings");
 for(const auto byte:bytes)if((byte<32&&byte!='\n')||byte>126)throw std::invalid_argument("Tour sidecar must be canonical bounded ASCII/UTF8; regenerate bindings");
 const std::string_view text(reinterpret_cast<const char*>(bytes.data()),bytes.size());std::size_t offset=0;
 const auto line=[&](){if(offset>=text.size())throw std::invalid_argument("Truncated tour sidecar; regenerate bindings");const auto end=text.find('\n',offset);if(end==std::string_view::npos)throw std::invalid_argument("Tour sidecar requires canonical LF; regenerate bindings");const auto value=text.substr(offset,end-offset);offset=end+1;return value;};
 if(line()!="AIBTOUR 1")throw std::invalid_argument("Unsupported tour sidecar version; regenerate bindings");
 const auto& d=content.definition();if(line()!=d.definition_id+" "+d.world_id+" "+content.fingerprint())throw std::invalid_argument("Tour sidecar belongs to another or edited chapter; regenerate bindings");
 OpeningTourTargets targets;for(std::size_t i=0;i<opening_tour_stop_count;++i){const auto row=line();const auto prefix=std::string(roles[i])+" ";if(!row.starts_with(prefix))throw std::invalid_argument("Tour role order/identity is not canonical; regenerate bindings");targets.ids[i]=row.substr(prefix.size());}
 if(offset!=text.size())throw std::invalid_argument("Tour sidecar has trailing data; regenerate bindings");validate(content,targets);return targets;
}
}
