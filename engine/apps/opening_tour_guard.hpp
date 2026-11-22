#pragma once
#include <aibs/opening_inspections.hpp>
#include <stdexcept>
namespace aibs {
// Private diagnostic owner. No catalog/panel pointer survives a frame or F9.
class OpeningTourReadGuard {
 OpeningInspection expected_;unsigned reloads_=0;
 static const OpeningInspection& bounded(const OpeningInspection& entry){if(!is_uuid(entry.fixture_id)||entry.title.size()>256||entry.text.empty()||entry.text.size()>2048||entry.source.empty()||entry.source.size()>512)throw std::invalid_argument("Tour inspection exceeds its owned bounded entry contract");return entry;}
public:
 OpeningTourReadGuard(const OpeningInspection& entry,unsigned reloads):expected_(bounded(entry)),reloads_(reloads){}
 const OpeningInspection& expected()const noexcept{return expected_;}
 void after_walk(unsigned reloads)const{if(reloads!=reloads_)throw std::invalid_argument("Tour interrupted by actual F9 reload; start a fresh diagnostic timeline");}
 void reading(unsigned reloads,const std::optional<OpeningInspection>& selected,bool visible)const{after_walk(reloads);if(!visible||!selected||selected->fixture_id!=expected_.fixture_id||selected->title!=expected_.title||selected->text!=expected_.text||selected->source!=expected_.source||selected->center!=expected_.center||selected->action!=expected_.action)throw std::invalid_argument("Tour selection changed or closed; actual selected fixture UUID/text/source must match its owned role");}
};
}
