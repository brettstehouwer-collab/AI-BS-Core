// Private native application controller. No gameplay/save events originate here.
class MemoryPanel {
 static constexpr wchar_t property[]=L"AIBS.MemoryPanel.1";
 static constexpr int play_id=0x7a10,pause_id=0x7a11,stop_id=0x7a12;
 HWND parent_=nullptr,caption_=nullptr,play_=nullptr,pause_=nullptr,stop_=nullptr;
 WNDPROC previous_=nullptr,caption_previous_=nullptr;
 unsigned pending_=0;std::array<bool,3> held_{};bool active_=true;
 std::wstring last_text_;
 static LRESULT CALLBACK caption_proc(HWND child,UINT message,WPARAM wp,LPARAM lp){
  const auto parent=GetParent(child);auto* self=static_cast<MemoryPanel*>(GetPropW(parent,property));
  if(!self)return DefWindowProcW(child,message,wp,lp);
  // Keep ordinary game key edges working even after clicking the read-only
  // transcript. Mouse wheel/scrollbar handling remains in the native edit.
  if(message==WM_KEYDOWN||message==WM_KEYUP||message==WM_SYSKEYDOWN||message==WM_SYSKEYUP)return SendMessageW(parent,message,wp,lp);
  return CallWindowProcW(self->caption_previous_,child,message,wp,lp);
 }
 static LRESULT CALLBACK procedure(HWND window,UINT message,WPARAM wp,LPARAM lp){
  auto* self=static_cast<MemoryPanel*>(GetPropW(window,property));if(!self)return DefWindowProcW(window,message,wp,lp);
  if(message==WM_ACTIVATEAPP){self->active_=wp!=0;if(!wp){self->held_.fill(false);self->pending_=0;}}
  if(message==WM_SIZE&&wp==SIZE_MINIMIZED){self->held_.fill(false);self->pending_=0;}
  if(message==WM_KEYDOWN||message==WM_SYSKEYDOWN||message==WM_KEYUP||message==WM_SYSKEYUP){
   const int index=wp=='P'?0:wp=='O'?1:wp=='K'?2:-1;
   if(index>=0){const auto slot=static_cast<std::size_t>(index);const bool down=message==WM_KEYDOWN||message==WM_SYSKEYDOWN;
    if(down&&!self->held_[slot]&&self->active_)self->pending_|=1u<<slot;
    self->held_[slot]=down;return 0;}
  }
  if(message==WM_COMMAND&&HIWORD(wp)==BN_CLICKED){
   const auto id=LOWORD(wp);const auto sender=reinterpret_cast<HWND>(lp);
   if((id==play_id&&sender==self->play_)||(id==pause_id&&sender==self->pause_)||(id==stop_id&&sender==self->stop_)){
    self->pending_|=id==play_id?1u:id==pause_id?2u:4u;SetFocus(window);return 0;}
  }
  return CallWindowProcW(self->previous_,window,message,wp,lp);
 }
public:
 explicit MemoryPanel(NativeWindow& window):parent_(static_cast<HWND>(window.native_handle())){}
 ~MemoryPanel(){
  if(IsWindow(caption_)&&caption_previous_)SetWindowLongPtrW(caption_,GWLP_WNDPROC,reinterpret_cast<LONG_PTR>(caption_previous_));
  if(IsWindow(parent_)){
   if(previous_&&reinterpret_cast<WNDPROC>(GetWindowLongPtrW(parent_,GWLP_WNDPROC))==procedure)SetWindowLongPtrW(parent_,GWLP_WNDPROC,reinterpret_cast<LONG_PTR>(previous_));
   RemovePropW(parent_,property);
  }
  for(auto child:{caption_,play_,pause_,stop_})if(IsWindow(child))DestroyWindow(child);
 }
 void initialize(){
  require(GetPropW(parent_,property)==nullptr&&SetPropW(parent_,property,this),"Cannot attach owned memory controls");
  SetLastError(0);previous_=reinterpret_cast<WNDPROC>(SetWindowLongPtrW(parent_,GWLP_WNDPROC,reinterpret_cast<LONG_PTR>(procedure)));
  require(previous_!=nullptr,"Cannot attach memory key routing");
  const auto instance=GetModuleHandleW(nullptr);
  caption_=CreateWindowExW(WS_EX_CLIENTEDGE,L"EDIT",L"",WS_CHILD|WS_VISIBLE|WS_VSCROLL|ES_MULTILINE|ES_READONLY|ES_AUTOVSCROLL,12,440,800,120,parent_,nullptr,instance,nullptr);
  play_=CreateWindowExW(0,L"BUTTON",L"Play / Resume (P)",WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON,12,568,150,30,parent_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(play_id)),instance,nullptr);
  pause_=CreateWindowExW(0,L"BUTTON",L"Pause (O)",WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON,170,568,120,30,parent_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(pause_id)),instance,nullptr);
  stop_=CreateWindowExW(0,L"BUTTON",L"Stop (K)",WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON,298,568,120,30,parent_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(stop_id)),instance,nullptr);
  require(caption_&&play_&&pause_&&stop_,"Cannot create native memory playback controls");
  SendMessageW(caption_,EM_SETLIMITTEXT,300000,0);
  for(auto child:{caption_,play_,pause_,stop_})SendMessageW(child,WM_SETFONT,reinterpret_cast<WPARAM>(GetStockObject(DEFAULT_GUI_FONT)),TRUE);
  caption_previous_=reinterpret_cast<WNDPROC>(SetWindowLongPtrW(caption_,GWLP_WNDPROC,reinterpret_cast<LONG_PTR>(caption_proc)));
  require(caption_previous_!=nullptr,"Cannot preserve game keys in read-only caption panel");
 }
 unsigned take(bool active)noexcept{const auto result=active?pending_:0u;pending_=0;return result;}
 void update(const NativeWindow& window,const std::wstring& text,bool can_play,bool can_pause,bool can_stop){
  const auto width=static_cast<int>(window.width()),height=static_cast<int>(window.height());
  const int w=std::max(1,std::min(900,width-24)),panel=std::clamp(height/4,90,220),top=std::max(12,height-panel-48);
  SetWindowPos(caption_,nullptr,12,top,w,panel,SWP_NOZORDER|SWP_NOACTIVATE);
  SetWindowPos(play_,nullptr,12,top+panel+4,150,30,SWP_NOZORDER|SWP_NOACTIVATE);
  SetWindowPos(pause_,nullptr,170,top+panel+4,120,30,SWP_NOZORDER|SWP_NOACTIVATE);
  SetWindowPos(stop_,nullptr,298,top+panel+4,120,30,SWP_NOZORDER|SWP_NOACTIVATE);
  EnableWindow(play_,can_play);EnableWindow(pause_,can_pause);EnableWindow(stop_,can_stop);
  if(text!=last_text_){SetWindowTextW(caption_,text.c_str());SendMessageW(caption_,EM_SETSEL,0,0);SendMessageW(caption_,EM_SCROLLCARET,0,0);last_text_=text;}
 }
 HWND caption_handle()const noexcept{return caption_;}
 HWND play_handle()const noexcept{return play_;}
 std::wstring caption_text()const{
  const auto size=GetWindowTextLengthW(caption_);require(size>=0&&size<=300000,"Caption readback exceeds bound");
  std::wstring value(static_cast<std::size_t>(size)+1,L'\0');value.resize(static_cast<std::size_t>(GetWindowTextW(caption_,value.data(),static_cast<int>(value.size()))));return value;
 }
 bool capture_caption(const std::filesystem::path& path)const{
  RECT client{};require(GetClientRect(caption_,&client)&&client.right>0&&client.bottom>0&&client.right<=2048&&client.bottom<=1024,"Caption capture dimensions outside bound");
  HDC source=GetDC(caption_),target=source?CreateCompatibleDC(source):nullptr;
  require(source&&target,"Cannot create actual caption readback DC");
  BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=client.right;info.bmiHeader.biHeight=-client.bottom;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
  void* pixels=nullptr;const auto bitmap=CreateDIBSection(source,&info,DIB_RGB_COLORS,&pixels,nullptr,0);require(bitmap&&pixels,"Cannot allocate bounded caption readback");
  const auto previous=SelectObject(target,bitmap);PatBlt(target,0,0,client.right,client.bottom,WHITENESS);SendMessageW(caption_,WM_PRINTCLIENT,reinterpret_cast<WPARAM>(target),PRF_CLIENT|PRF_ERASEBKGND);
  const auto* rgba=static_cast<const unsigned char*>(pixels);std::size_t ink=0;
  for(int y=5;y<client.bottom-5;++y)for(int x=5;x<client.right-20;++x){const auto at=(static_cast<std::size_t>(y)*static_cast<std::size_t>(client.right)+static_cast<std::size_t>(x))*4;ink+=rgba[at+2]>100&&rgba[at+1]>100&&rgba[at]<245;}
  BITMAPFILEHEADER header{};header.bfType=0x4d42;header.bfOffBits=sizeof(header)+sizeof(BITMAPINFOHEADER);header.bfSize=header.bfOffBits+static_cast<DWORD>(client.right*client.bottom*4);
  std::ofstream file(path,std::ios::binary);file.write(reinterpret_cast<const char*>(&header),sizeof(header));file.write(reinterpret_cast<const char*>(&info.bmiHeader),sizeof(info.bmiHeader));file.write(static_cast<const char*>(pixels),static_cast<std::streamsize>(client.right)*client.bottom*4);const bool written=file.good();
  SelectObject(target,previous);DeleteObject(bitmap);DeleteDC(target);ReleaseDC(caption_,source);return written&&ink>100;
 }
};

class ChapterMemoryRuntime {
 const std::shared_ptr<const FirstBootContent> content_;
 const std::shared_ptr<const PlacedAssetVisuals> visuals_;
 Dx12Renderer& renderer_;NativeWindow& window_;
 MemoryPlaybackSession session_;
 std::unique_ptr<MemoryPanel> panel_;
 SceneSnapshot stations_;SceneMesh marker_mesh_;
 std::string media_notice_="Optional original recording. Aim at a memory station and press E to select it; playback starts only on Play.";
 std::size_t marker_residency_=0,retained_companion_bytes_=0;
 static std::size_t sum(std::size_t a,std::size_t b){if(b>memory_playback_maximum_resident_bytes||a>memory_playback_maximum_resident_bytes-b)throw std::invalid_argument("Memory/scene residency exceeds128MiB; Stop the optional recording before a larger world change");return a+b;}
 const FirstBootMemoryBinding* station(std::string_view id)const{
  for(const auto& entry:content_->definition().memories)if(entry.entity_id==id)return &entry;return nullptr;
 }
 std::shared_ptr<const AudioAsset> source(const FirstBootMemoryBinding& binding)const{
  const auto& closure=visuals_->asset_closure();require(closure!=nullptr,"Admitted memory dependency closure is unavailable");
  const auto& payload=closure->require(binding.audio,FirstBootDependencyKind::audio).payload;
  const auto* audio=std::get_if<AudioAsset>(&payload);require(audio!=nullptr,"Memory binding must resolve its exact role-tagged adopted audio reference");
  return std::shared_ptr<const AudioAsset>(closure,audio);
 }
 std::size_t total()const{
  const auto gpu=renderer_.stats().scene_active_gpu_bytes;require(gpu<=memory_playback_maximum_resident_bytes,"Active GPU content exceeds memory profile");
  // A bounded native edit/current UTF16 caption copy reserve is charged too.
  return sum(sum(visuals_->resident_bytes(),static_cast<std::size_t>(gpu)),sum(sum(marker_residency_,retained_companion_bytes_),2u*1024u*1024u));
 }
 std::size_t other(const std::shared_ptr<const AudioAsset>& candidate={}){
  const auto current=session_.snapshot().asset;auto result=total();
  const auto subtract=[&](const std::shared_ptr<const AudioAsset>& asset){if(!asset)return;const auto cost=audio_asset_cost(*asset).decoded_bytes;require(cost<=result,"Memory source exclusion exceeds admitted chapter residency");result-=cost;};
  subtract(current);
  if(candidate&&(!current||candidate.get()!=current.get()||candidate.owner_before(current)||current.owner_before(candidate)))subtract(candidate);
  return result;
 }
 bool accept(MemoryPlaybackResult result,const char* success){
  if(result){media_notice_=success;return true;}
  media_notice_="Memory playback unavailable ("+std::to_string(static_cast<unsigned>(result.error))+" / "+std::to_string(static_cast<unsigned>(result.audio.error))+"). The chapter and previous binding are retained.";return false;
 }
 SceneSnapshot pick_world(const SceneSnapshot& scene)const{
  auto output=scene;for(auto& object:output.objects)object.selectable=true;
  output.objects.insert(output.objects.end(),stations_.objects.begin(),stations_.objects.end());return output;
 }
 bool reachable(const FirstBootMemoryBinding& binding,const SceneSnapshot& scene,const Camera& camera,Vec3 feet)const{
  if(std::hypot(feet.x-binding.position.x,feet.y-binding.position.y,feet.z-binding.position.z)>3.2f)return false;
  const Vec3 target{binding.position.x,binding.position.y+.45f,binding.position.z};
  const Vec3 direction{target.x-camera.position.x,target.y-camera.position.y,target.z-camera.position.z};
  const auto hit=pick_scene(pick_world(scene),camera.position,direction,10);
  return hit&&hit->persistent_id==binding.entity_id;
 }
 const FirstBootMemoryBinding* aimed(const SceneSnapshot& scene,const Camera& camera,const WindowInput& input)const{
  const auto direction=ray(camera,input.pointer_interact?input.pointer_x:0,input.pointer_interact?input.pointer_y:0,
   static_cast<float>(window_.width())/static_cast<float>(window_.height()));
  const auto hit=pick_scene(pick_world(scene),camera.position,direction,10);return hit?station(hit->persistent_id):nullptr;
 }
 bool bind(const FirstBootMemoryBinding& binding){
  const auto audio=source(binding);const auto result=session_.bind(binding.entity_id,audio,other(audio));
  return accept(result,"Original memory selected. Playback is stopped; press Play / P to begin.");
 }
 static std::wstring clock_text(std::uint64_t frames,std::uint32_t rate){const auto seconds=rate?frames/rate:0;const auto remainder=seconds%60;return std::to_wstring(seconds/60)+L":"+(remainder<10?L"0":L"")+std::to_wstring(remainder);}
public:
 ChapterMemoryRuntime(std::shared_ptr<const FirstBootContent> content,std::shared_ptr<const PlacedAssetVisuals> visuals,
  NativeWindow& window,Dx12Renderer& renderer,bool muted_proof,std::size_t retained_companion_bytes=0)
  :content_(std::move(content)),visuals_(std::move(visuals)),renderer_(renderer),window_(window),stations_{content_->definition().world_id,0,{}},retained_companion_bytes_(retained_companion_bytes){
  require(visuals_&&visuals_->asset_closure(),"Memory stations require the complete admitted typed dependency closure");
  for(const auto& binding:content_->definition().memories){
   (void)source(binding);stations_.objects.push_back({binding.entity_id,binding.name,{binding.position.x,binding.position.y+.45f,binding.position.z},{.45f,.45f,.35f},{.82f,.47f,.12f},.25f,true,{}});
  }
  marker_mesh_=mesh_from_snapshot(stations_);marker_residency_=marker_mesh_.vertices.capacity()*sizeof(SceneVertex)+stations_.objects.capacity()*sizeof(SceneObject)+stations_.world_id.capacity()+1+marker_mesh_.landmarks.capacity()*sizeof(std::string);
  for(const auto& object:stations_.objects)marker_residency_+=object.persistent_id.capacity()+object.name.capacity()+2;
  for(const auto& name:marker_mesh_.landmarks)marker_residency_+=name.capacity()+1;
  require(marker_residency_<=512u*1024u,"Authored memory marker capacities exceed the bounded startup reserve");
  (void)total();require(static_cast<bool>(session_.set_volume(muted_proof?0.f:1.f)),"Cannot configure optional memory source volume");
  panel_=std::make_unique<MemoryPanel>(window_);panel_->initialize();
 }
 ~ChapterMemoryRuntime(){(void)session_.close();}
 const SceneMesh& markers()const noexcept{return marker_mesh_;}
 const SceneSnapshot& station_scene()const noexcept{return stations_;}
 MemoryPlaybackSnapshot snapshot(){return session_.snapshot();}
 const MemoryPanel& panel()const noexcept{return *panel_;}
 std::uint64_t remaining_gpu_bytes(const SceneMesh& composed){
  const auto pcm=session_.snapshot().playback.owned_pcm_bytes;
  const auto cpu=sum(sum(sum(visuals_->resident_bytes(),marker_residency_),retained_companion_bytes_),sum(2u*1024u*1024u,pcm));
  // The renderer stages actual native allocations and rejects before
  // publication if its entire active content layer exceeds this remainder.
  return static_cast<std::uint64_t>(memory_scene_gpu_remainder(cpu,composed));
 }
 bool interact(const SceneSnapshot& scene,const Camera& camera,Vec3 feet,const WindowInput& input,bool& consumed){
  consumed=false;
  try{const auto* binding=aimed(scene,camera,input);if(!binding)return false;consumed=true;
   if(!reachable(*binding,scene,camera,feet)){media_notice_="Move within reach of this memory station; closed walls and doors block selection.";return false;}
   return bind(*binding);
  }catch(const std::exception& error){media_notice_="Memory selection rejected; current chapter retained: "+std::string(error.what());return false;}
 }
 void stop_for_reload(){(void)session_.stop();media_notice_="Reload stops the optional recording. Use Play to start again; no playback cursor is saved.";}
 void close(){(void)session_.close();}
 void tick(const SceneSnapshot& scene,const Camera& camera,Vec3 feet,const WindowInput& input,bool paused,bool exiting){
  const auto commands=panel_->take(input.active&&!exiting);
  try{
   if(exiting){(void)session_.stop();}
   else{
    const bool manual=(commands&6u)!=0;
    if(commands&4u)(void)accept(session_.stop(),"Original recording stopped.");
    else if(commands&2u)(void)accept(session_.pause(),"Original recording manually paused.");
    const auto before=session_.snapshot();if(before.game_paused!=paused)(void)accept(session_.set_game_paused(paused,other()),paused?"Recording paused with the game.":"Game resumed; only a previously playing recording resumes.");
    if(!manual&&(commands&1u)){
     if(paused)media_notice_="Return to active play before starting a recording.";
     else{
      auto state=session_.snapshot();const FirstBootMemoryBinding* binding=state.asset?station(state.station_id()):nullptr;
      bool ready=true;
      if(const auto* target=aimed(scene,camera,WindowInput{});target&&(!binding||target->entity_id!=binding->entity_id)){
       if(!reachable(*target,scene,camera,feet)){media_notice_="Move within reach of the selected memory station.";ready=false;}
       else if(!bind(*target))ready=false;else binding=target;
      }
      if(ready){
       if(!binding||!reachable(*binding,scene,camera,feet))media_notice_="Aim at a nearby memory station and press E to select it before Play.";
       else(void)accept(session_.play_or_resume(other()),"Original recording playing. Pause or Stop at any time.");
      }
     }
    }
   }
   const auto state=session_.snapshot();
   std::wstring text=L"OPTIONAL ORIGINAL RECORDING - ";const auto* binding=state.asset?station(state.station_id()):nullptr;
   text+=binding?wide(binding->name):L"no station selected";
   const wchar_t* label=state.playback.state==AudioPlaybackState::playing?L"Playing":state.playback.state==AudioPlaybackState::paused?L"Paused":state.playback.state==AudioPlaybackState::completed?L"Finished":state.playback.state==AudioPlaybackState::failed?L"Unavailable":L"Stopped";
   text+=L" | "+std::wstring(label)+L" "+clock_text(state.playback.played_frames,state.playback.sample_rate)+L" / "+clock_text(state.playback.total_frames,state.playback.sample_rate)+L"\r\n";
   if(state.caption_index)text+=L"Checked original-recording caption: "+wide(state.asset->captions[*state.caption_index].text)+L"\r\n";
   else if(state.review_pending)text+=L"Captions await review and are withheld. New Adam guidance remains authored text.\r\n";
   text+=wide(media_notice_);const bool active=state.playback.state==AudioPlaybackState::playing||state.playback.state==AudioPlaybackState::paused;
   panel_->update(window_,text,binding&&!paused&&!exiting,active&&!exiting,static_cast<bool>(state.asset)&&!exiting);
  }catch(const std::exception& error){media_notice_="Memory controls rejected before publication: "+std::string(error.what());}
 }
 void write_report(std::ostream& file){
  const auto state=session_.snapshot();file<<"{\"station\":"<<quoted(std::string(state.station_id()))<<",\"bound\":"<<(state.asset?"true":"false")<<",\"state\":"<<static_cast<unsigned>(state.playback.state)<<",\"source_rate\":"<<state.playback.sample_rate<<",\"channels\":"<<state.playback.channels<<",\"played_frames\":"<<state.playback.played_frames<<",\"total_frames\":"<<state.playback.total_frames<<",\"owned_pcm_bytes\":"<<state.playback.owned_pcm_bytes<<",\"resident_bytes\":"<<state.resident_bytes<<",\"reserved_peak_bytes\":"<<state.reserved_peak_bytes<<",\"review_pending\":"<<(state.review_pending?"true":"false")<<",\"caption_index\":";
  if(state.caption_index)file<<*state.caption_index;else file<<"null";file<<'}';
 }
};
