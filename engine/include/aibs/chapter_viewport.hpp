#pragma once
#include <aibs/content_authoring.hpp>
#include <aibs/creator_payload.hpp>

namespace aibs {
// Mode2 is an independent, immutable typed chapter projection. The content
// budget is separate from its bounded identity envelope; no player saves exist.
inline constexpr std::size_t chapter_viewport_maximum_bytes=creator_payload::maximum_bytes+64*1024;
struct ChapterViewportSnapshot {
 std::string snapshot_id;
 CreatorScope scope;
 std::string checkpoint_id,selected_id;
 std::uint64_t revision=0;
 FirstBootContent content;
};
inline ChapterViewportSnapshot decode_chapter_viewport_snapshot(std::span<const unsigned char> bytes){
 using namespace creator_payload::detail;
 ensure(bytes.size()<=chapter_viewport_maximum_bytes,"Chapter viewport envelope exceeds bound");Reader r{bytes};
 ensure(r.number(4)==0x56424941&&r.number(2)==1&&r.number(1)==2,"Unsupported typed chapter viewport envelope");
 auto snapshot=r.text(true);uuid(snapshot);CreatorScope scope{r.text(true),r.text(true),r.text(true)};uuid(scope.world_id);
 auto checkpoint=r.text();uuid(checkpoint,true);const auto revision=r.number(8);auto selected=r.text();uuid(selected,true);
 const auto size=r.number(4);ensure(size>0&&size<=creator_payload::maximum_bytes&&size==r.data.size()-r.offset,"Invalid chapter content byte length");
 auto content=first_boot_content_decode(r.data.subspan(r.offset,static_cast<std::size_t>(size)));
 ensure(content.definition().world_id==scope.world_id,"Chapter content world differs from viewport scope");
 const auto rows=content_authoring_rows(content);
 ensure(selected.empty()||std::any_of(rows.begin(),rows.end(),[&](const auto& row){return row.entity_id==selected;}),"Selected chapter UUID is absent");
 return {std::move(snapshot),std::move(scope),std::move(checkpoint),std::move(selected),revision,std::move(content)};
}
inline SceneSnapshot chapter_viewport_scene(const ChapterViewportSnapshot& snapshot){
 const auto baseline=first_boot_content_baseline(snapshot.content);
 const GameplayStoreRecovery recovery{{snapshot.scope.project,snapshot.scope.world_id,snapshot.scope.branch,snapshot.content.definition().definition_id,GameplayContext::temporary_play},baseline.revision,baseline.sequence,baseline.components};
 auto scene=first_boot_content_scene(recovery,snapshot.content);scene.revision=snapshot.revision;
 std::set<std::string> authoring_ids;for(const auto& row:content_authoring_rows(snapshot.content))authoring_ids.insert(row.entity_id);
 for(auto& object:scene.objects)object.selectable=authoring_ids.contains(object.persistent_id);
 return scene;
}
}
