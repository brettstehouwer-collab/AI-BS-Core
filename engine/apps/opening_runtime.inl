// Private native adapter. Include opening_inspection_panel.inl first.
class ChapterOpeningRuntime {
 aibs::OpeningInspectionCatalog catalog_;
 aibs::OpeningInspectionSession session_;
 OpeningInspectionPanel panel_;
 std::string notice_;
public:
 ChapterOpeningRuntime(const aibs::FirstBootContentDefinition& content,HWND parent,bool presentation=true):catalog_(content),session_(catalog_),panel_(parent,presentation){
  require(resident_bytes()<=512u*1024u,"Opening catalog exceeds the charged native panel reserve");
 }
 // direction is the actual centre/click ray already computed by ChapterLive.
 // Every collision object blocks this aimed selection, even non-selectable
 // decorative walls. No new render/collision or gameplay-state publication.
 bool interact(const aibs::SceneSnapshot& scene,const aibs::Camera& camera,aibs::Vec3 direction,aibs::Vec3 feet,bool& consumed){
  consumed=false;auto occluders=scene;for(auto& object:occluders.objects)object.selectable=true;
  const auto hit=aibs::pick_scene(occluders,camera.position,direction,10);if(!hit||!catalog_.find(hit->persistent_id))return false;consumed=true;
  if(!session_.select(hit->persistent_id,feet,true)){notice_="Move closer to read this.";return false;}
  require(resident_bytes()<=512u*1024u,"Opening selection exceeds the charged native panel reserve");
  const auto selection=session_.snapshot();panel_.show(*selection);notice_="Take your time. Continue or Escape returns to BS.";return true;
 }
 bool visible()const noexcept{return panel_.visible();}
 std::optional<aibs::OpeningInspection> selection()const{return session_.snapshot();}
 void close()noexcept{panel_.hide();session_.close();}
 const std::string& notice()const noexcept{return notice_;}
 const OpeningInspectionPanel& panel()const noexcept{return panel_;}
 std::size_t count()const noexcept{return catalog_.entries().size();}
 std::size_t resident_bytes()const noexcept{return catalog_.resident_bytes()+session_.resident_bytes();}
 const aibs::OpeningInspection* find(std::string_view id)const noexcept{return catalog_.find(id);}
};
