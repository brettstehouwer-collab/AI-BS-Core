// Included inside Dx12Renderer::Impl. Live opaque HUD pixels share the final
// backbuffer: diagnostic captures and Present now contain the same overlay.
// Upload storage is private, bounded, and reused only after that slot's fence.
owned_hud::Snapshot hud{static_cast<HWND>(window.native_handle())};
struct HudSlot {ComPtr<ID3D12Resource> upload;std::size_t capacity=0;std::uint64_t version=0;};
std::array<HudSlot,frame_count> hud_slots{};
void prepare_hud(UINT index){
 hud.refresh(width,height);
 if(hud.bytes().empty())return;
 auto& slot=hud_slots.at(index);if(slot.version==hud.version())return;
 const auto size=hud.bytes().size();
 if(size>owned_hud::maximum_bytes)throw std::invalid_argument("Live HUD upload exceeds its fixed bound");
 ComPtr<ID3D12Resource> candidate;
 if(size>slot.capacity){
  const auto description=buffer_description(size);const auto heap=heap_properties(D3D12_HEAP_TYPE_UPLOAD);
  checked(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&description,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&candidate)),"Live HUD upload slot");
 }
 auto* target=candidate?candidate.Get():slot.upload.Get();
 void* mapped=nullptr;const D3D12_RANGE empty{0,0};checked(target->Map(0,&empty,&mapped),"Live HUD upload map");
 std::memcpy(mapped,hud.bytes().data(),size);const D3D12_RANGE written{0,size};target->Unmap(0,&written);
 if(candidate){slot.upload.Swap(candidate);slot.capacity=size;++owned_hud::upload_allocations;}
 slot.version=hud.version();
}
void finish_with_hud(UINT index){
 auto barrier=transition(targets[index].Get(),D3D12_RESOURCE_STATE_RENDER_TARGET,
  hud.bytes().empty()?D3D12_RESOURCE_STATE_PRESENT:D3D12_RESOURCE_STATE_COPY_DEST);
 commands->ResourceBarrier(1,&barrier);
 if(hud.bytes().empty())return;
 D3D12_TEXTURE_COPY_LOCATION destination{};destination.pResource=targets[index].Get();destination.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
 for(std::size_t n=0;n<hud.count();++n){const auto& region=hud.region(n);if(!region.width)continue;
  D3D12_TEXTURE_COPY_LOCATION source{};source.pResource=hud_slots[index].upload.Get();source.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
  source.PlacedFootprint.Offset=region.offset;auto& footprint=source.PlacedFootprint.Footprint;
  footprint.Format=DXGI_FORMAT_R8G8B8A8_UNORM;footprint.Width=region.width;footprint.Height=region.height;footprint.Depth=1;footprint.RowPitch=region.pitch;
  commands->CopyTextureRegion(&destination,region.x,region.y,0,&source,nullptr);
 }
 barrier=transition(targets[index].Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_PRESENT);commands->ResourceBarrier(1,&barrier);
}
