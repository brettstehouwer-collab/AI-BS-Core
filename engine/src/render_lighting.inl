// Included inside Dx12Renderer::Impl. Lighting resources share its queue/lifetime.
static constexpr UINT64 lighting_upload_bytes=1280;
static_assert(sizeof(GpuLightingConstants)==1168&&lighting_upload_bytes%256==0);
struct ShadowGpu {
 ComPtr<ID3D12Resource> texture;
 ComPtr<ID3D12DescriptorHeap> dsv;
 UINT resolution=0;
};
struct LightingStage {
 GpuLightingConstants constants{};
 std::shared_ptr<ShadowGpu> shadow;
 ComPtr<ID3D12DescriptorHeap> heap;
};
GpuLightingConstants lighting_constants{};
std::shared_ptr<ShadowGpu> directional_shadow;
ComPtr<ID3D12DescriptorHeap> lighting_heap;
ComPtr<ID3D12Resource> lighting_buffers[frame_count];
ComPtr<ID3D12RootSignature> shadow_root;
ComPtr<ID3D12PipelineState> shadow_pipeline;

D3D12_STATIC_SAMPLER_DESC shadow_sampler()const{
 D3D12_STATIC_SAMPLER_DESC s{};s.Filter=D3D12_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT;
 s.AddressU=s.AddressV=s.AddressW=D3D12_TEXTURE_ADDRESS_MODE_BORDER;
 s.ComparisonFunc=D3D12_COMPARISON_FUNC_LESS_EQUAL;s.BorderColor=D3D12_STATIC_BORDER_COLOR_OPAQUE_WHITE;
 s.MaxAnisotropy=1;s.MaxLOD=D3D12_FLOAT32_MAX;s.ShaderRegister=1;s.ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;return s;
}
void shadow_descriptor(ID3D12Resource* texture,D3D12_CPU_DESCRIPTOR_HANDLE handle){
 D3D12_SHADER_RESOURCE_VIEW_DESC desc{};desc.Format=DXGI_FORMAT_R32_FLOAT;desc.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2D;
 desc.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;desc.Texture2D.MipLevels=1;
 device->CreateShaderResourceView(texture,&desc,handle);
}
void shadow_pipeline_initialize(){
 if(shadow_pipeline)return;
 D3D12_ROOT_PARAMETER p{};p.ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;p.Constants.Num32BitValues=16;p.Constants.ShaderRegister=0;p.ShaderVisibility=D3D12_SHADER_VISIBILITY_VERTEX;
 D3D12_ROOT_SIGNATURE_DESC desc{};desc.NumParameters=1;desc.pParameters=&p;desc.Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;
 ComPtr<ID3DBlob> signature,error;checked(D3D12SerializeRootSignature(&desc,D3D_ROOT_SIGNATURE_VERSION_1,&signature,&error),"Shadow root serialization");
 ComPtr<ID3D12RootSignature> candidate_root;checked(device->CreateRootSignature(0,signature->GetBufferPointer(),signature->GetBufferSize(),IID_PPV_ARGS(&candidate_root)),"Shadow root");
 const auto vs=read_shader(texture_shaders/"shadow.vs.cso");
 const D3D12_INPUT_ELEMENT_DESC input{"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0};
 D3D12_GRAPHICS_PIPELINE_STATE_DESC state{};state.pRootSignature=candidate_root.Get();state.VS={vs.data(),vs.size()};
 state.BlendState.RenderTarget[0].SrcBlend=D3D12_BLEND_ONE;state.BlendState.RenderTarget[0].DestBlend=D3D12_BLEND_ZERO;state.BlendState.RenderTarget[0].BlendOp=D3D12_BLEND_OP_ADD;
 state.BlendState.RenderTarget[0].SrcBlendAlpha=D3D12_BLEND_ONE;state.BlendState.RenderTarget[0].DestBlendAlpha=D3D12_BLEND_ZERO;state.BlendState.RenderTarget[0].BlendOpAlpha=D3D12_BLEND_OP_ADD;state.BlendState.RenderTarget[0].LogicOp=D3D12_LOGIC_OP_NOOP;
 state.SampleMask=UINT_MAX;state.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;state.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;state.RasterizerState.DepthClipEnable=TRUE;
 state.DepthStencilState.DepthEnable=TRUE;state.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ALL;state.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_LESS;
 state.InputLayout={&input,1};state.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;state.DSVFormat=DXGI_FORMAT_D32_FLOAT;state.SampleDesc.Count=1;
 ComPtr<ID3D12PipelineState> candidate;checked(device->CreateGraphicsPipelineState(&state,IID_PPV_ARGS(&candidate)),"Shadow depth pipeline");
 shadow_root.Swap(candidate_root);shadow_pipeline.Swap(candidate);
}
LightingStage stage_lighting(const SceneLighting& lighting){
 LightingStage staged;staged.constants=pack_scene_lighting(lighting);
 if(staged.constants.controls[0]&&staged.constants.controls[2]){
  shadow_pipeline_initialize();const auto resolution=lighting.shadow.resolution;
  if(directional_shadow&&directional_shadow->resolution==resolution)staged.shadow=directional_shadow;
  else{
   auto shadow=std::make_shared<ShadowGpu>();shadow->resolution=resolution;
   D3D12_RESOURCE_DESC desc{};desc.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;desc.Width=resolution;desc.Height=resolution;desc.DepthOrArraySize=1;desc.MipLevels=1;desc.Format=DXGI_FORMAT_R32_TYPELESS;desc.SampleDesc.Count=1;desc.Flags=D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL;
   const auto allocation=device->GetResourceAllocationInfo(0,1,&desc);if(allocation.SizeInBytes>32u*1024u*1024u)throw std::invalid_argument("Directional shadow exceeds32MiB GPU budget");
   D3D12_CLEAR_VALUE clear{};clear.Format=DXGI_FORMAT_D32_FLOAT;clear.DepthStencil.Depth=1;
   const auto heap=heap_properties(D3D12_HEAP_TYPE_DEFAULT);checked(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,&clear,IID_PPV_ARGS(&shadow->texture)),"Directional shadow resource");
   D3D12_DESCRIPTOR_HEAP_DESC dsv{};dsv.Type=D3D12_DESCRIPTOR_HEAP_TYPE_DSV;dsv.NumDescriptors=1;checked(device->CreateDescriptorHeap(&dsv,IID_PPV_ARGS(&shadow->dsv)),"Directional shadow DSV heap");
   D3D12_DEPTH_STENCIL_VIEW_DESC view{};view.Format=DXGI_FORMAT_D32_FLOAT;view.ViewDimension=D3D12_DSV_DIMENSION_TEXTURE2D;device->CreateDepthStencilView(shadow->texture.Get(),&view,shadow->dsv->GetCPUDescriptorHandleForHeapStart());
   staged.shadow=std::move(shadow);
  }
 }
 D3D12_DESCRIPTOR_HEAP_DESC heap{};heap.Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV;heap.NumDescriptors=1;heap.Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;
 checked(device->CreateDescriptorHeap(&heap,IID_PPV_ARGS(&staged.heap)),"Lighting descriptor heap");shadow_descriptor(staged.shadow?staged.shadow->texture.Get():nullptr,staged.heap->GetCPUDescriptorHandleForHeapStart());return staged;
}
ComPtr<ID3D12DescriptorHeap> texture_heap_with_shadow(const TextureGpu& layer,ID3D12Resource* shadow){
 D3D12_DESCRIPTOR_HEAP_DESC desc{};desc.Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV;desc.NumDescriptors=static_cast<UINT>(layer.images.size()+1);desc.Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;
 ComPtr<ID3D12DescriptorHeap> heap;checked(device->CreateDescriptorHeap(&desc,IID_PPV_ARGS(&heap)),"Replacement texture/shadow descriptors");
 auto handle=heap->GetCPUDescriptorHandleForHeapStart();const auto step=device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
 // Shader-visible heaps cannot be descriptor-copy sources. Recreate each SRV
 // from the still-owned resource rather than reading a shader-visible heap.
 for(const auto& image:layer.images){const auto resource=image->GetDesc();D3D12_SHADER_RESOURCE_VIEW_DESC view{};view.Format=resource.Format;view.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2D;view.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;view.Texture2D.MipLevels=resource.MipLevels;device->CreateShaderResourceView(image.Get(),&view,handle);handle.ptr+=step;}
 shadow_descriptor(shadow,handle);return heap;
}
void publish_lighting(LightingStage& staged)noexcept{
 lighting_constants=staged.constants;directional_shadow.swap(staged.shadow);lighting_heap.Swap(staged.heap);
}
void lighting_initialize(){
 const auto desc=buffer_description(lighting_upload_bytes);const auto heap=heap_properties(D3D12_HEAP_TYPE_UPLOAD);
 for(auto& buffer:lighting_buffers)checked(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&buffer)),"Lighting frame constant buffer");
 auto staged=stage_lighting(SceneLighting{});publish_lighting(staged);
}
void replace_lighting(const SceneLighting& lighting){
 require_healthy();auto staged=stage_lighting(lighting);ComPtr<ID3D12DescriptorHeap> descriptors;
 if(textures)descriptors=texture_heap_with_shadow(*textures,staged.shadow?staged.shadow->texture.Get():nullptr);
 auto character_descriptors=stage_character_shadow(staged.shadow?staged.shadow->texture.Get():nullptr);
 idle();if(textures)textures->heap.Swap(descriptors);publish_character_shadow(character_descriptors);publish_lighting(staged);
}
void upload_lighting(UINT frame){
 void* mapped=nullptr;const D3D12_RANGE empty{0,0};checked(lighting_buffers[frame]->Map(0,&empty,&mapped),"Map lighting frame constants");
 std::memcpy(mapped,&lighting_constants,sizeof(lighting_constants));const D3D12_RANGE written{0,sizeof(lighting_constants)};lighting_buffers[frame]->Unmap(0,&written);
}
void shadow_pass(UINT transient_count,const D3D12_VERTEX_BUFFER_VIEW& transient_view){
 if(!lighting_constants.controls[0]||!lighting_constants.controls[2]||!directional_shadow)return;
 auto& shadow=*directional_shadow;auto barrier=transition(shadow.texture.Get(),D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_DEPTH_WRITE);commands->ResourceBarrier(1,&barrier);
 commands->SetPipelineState(shadow_pipeline.Get());commands->SetGraphicsRootSignature(shadow_root.Get());commands->SetGraphicsRoot32BitConstants(0,16,lighting_constants.shadow_view_projection.data(),0);
 const D3D12_VIEWPORT viewport{0,0,static_cast<float>(shadow.resolution),static_cast<float>(shadow.resolution),0,1};const D3D12_RECT rect{0,0,static_cast<LONG>(shadow.resolution),static_cast<LONG>(shadow.resolution)};
 commands->RSSetViewports(1,&viewport);commands->RSSetScissorRects(1,&rect);const auto depth_view=shadow.dsv->GetCPUDescriptorHandleForHeapStart();commands->OMSetRenderTargets(0,nullptr,FALSE,&depth_view);commands->ClearDepthStencilView(depth_view,D3D12_CLEAR_FLAG_DEPTH,1,0,0,nullptr);commands->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
 if(vertex_count){commands->IASetVertexBuffers(0,1,&vertex_view);commands->DrawInstanced(vertex_count,1,0,0);}
 if(textures){commands->IASetVertexBuffers(0,1,&textures->view);commands->DrawInstanced(static_cast<UINT>(textured_vertex_count()),1,0,0);}
 if(transient_count){commands->IASetVertexBuffers(0,1,&transient_view);commands->DrawInstanced(transient_count,1,0,0);}
 barrier=transition(shadow.texture.Get(),D3D12_RESOURCE_STATE_DEPTH_WRITE,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);commands->ResourceBarrier(1,&barrier);
}
