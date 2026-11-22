// Included inside Dx12Renderer::Impl; all objects belong to this renderer.
struct TextureGpu {
 ComPtr<ID3D12DescriptorHeap> heap;
 std::vector<ComPtr<ID3D12Resource>> images;
 ComPtr<ID3D12Resource> vertices;
 D3D12_VERTEX_BUFFER_VIEW view{};
 std::vector<TexturedDraw> draws;
};
std::unique_ptr<TextureGpu> textures;
struct InFlightResources {
 std::unique_ptr<CharacterGpu> character;
 std::unique_ptr<TextureGpu> textures;
 ComPtr<ID3D12CommandAllocator> allocator;
 ComPtr<ID3D12GraphicsCommandList> commands;
 std::vector<ComPtr<ID3D12Resource>> staging;
 ComPtr<ID3D12Resource> readback;
};
detail::SubmissionLifetime<InFlightResources> submissions;
std::size_t textured_vertex_count()const noexcept{return textures?textures->view.SizeInBytes/sizeof(TexturedVertex):0;}
ComPtr<ID3D12RootSignature> texture_root;
ComPtr<ID3D12PipelineState> texture_pipeline;

void texture_pipeline_initialize(){
 if(texture_pipeline)return;
 D3D12_DESCRIPTOR_RANGE range{};range.RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_SRV;range.NumDescriptors=1;range.BaseShaderRegister=0;
 D3D12_DESCRIPTOR_RANGE shadow_range{};shadow_range.RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_SRV;shadow_range.NumDescriptors=1;shadow_range.BaseShaderRegister=1;
 D3D12_ROOT_PARAMETER params[5]{};
 params[0].ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;params[0].Constants.Num32BitValues=16;params[0].Constants.ShaderRegister=0;params[0].ShaderVisibility=D3D12_SHADER_VISIBILITY_VERTEX;
 params[1].ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;params[1].DescriptorTable.NumDescriptorRanges=1;params[1].DescriptorTable.pDescriptorRanges=&range;params[1].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 params[2].ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;params[2].Constants.Num32BitValues=4;params[2].Constants.ShaderRegister=1;params[2].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 params[3].ParameterType=D3D12_ROOT_PARAMETER_TYPE_CBV;params[3].Descriptor.ShaderRegister=2;params[3].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 params[4].ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;params[4].DescriptorTable.NumDescriptorRanges=1;params[4].DescriptorTable.pDescriptorRanges=&shadow_range;params[4].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 D3D12_STATIC_SAMPLER_DESC sampler{};sampler.Filter=D3D12_FILTER_MIN_MAG_MIP_LINEAR;sampler.AddressU=sampler.AddressV=sampler.AddressW=D3D12_TEXTURE_ADDRESS_MODE_WRAP;sampler.MaxAnisotropy=1;sampler.ComparisonFunc=D3D12_COMPARISON_FUNC_ALWAYS;sampler.MaxLOD=D3D12_FLOAT32_MAX;sampler.ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 const D3D12_STATIC_SAMPLER_DESC samplers[]={sampler,shadow_sampler()};
 D3D12_ROOT_SIGNATURE_DESC desc{};desc.NumParameters=5;desc.pParameters=params;desc.NumStaticSamplers=2;desc.pStaticSamplers=samplers;desc.Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;
 ComPtr<ID3DBlob> signature,error;checked(D3D12SerializeRootSignature(&desc,D3D_ROOT_SIGNATURE_VERSION_1,&signature,&error),"Texture root serialization");
 ComPtr<ID3D12RootSignature> candidate_root;checked(device->CreateRootSignature(0,signature->GetBufferPointer(),signature->GetBufferSize(),IID_PPV_ARGS(&candidate_root)),"Texture root");
 const auto vs=read_shader(texture_shaders/"textured.vs.cso"),ps=read_shader(texture_shaders/"textured.ps.cso");
 const D3D12_INPUT_ELEMENT_DESC layout[]={{"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},{"NORMAL",0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},{"TEXCOORD",0,DXGI_FORMAT_R32G32_FLOAT,0,24,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0}};
 D3D12_GRAPHICS_PIPELINE_STATE_DESC state{};state.pRootSignature=candidate_root.Get();state.VS={vs.data(),vs.size()};state.PS={ps.data(),ps.size()};
 auto& blend=state.BlendState.RenderTarget[0];blend.SrcBlend=D3D12_BLEND_ONE;blend.DestBlend=D3D12_BLEND_ZERO;blend.BlendOp=D3D12_BLEND_OP_ADD;blend.SrcBlendAlpha=D3D12_BLEND_ONE;blend.DestBlendAlpha=D3D12_BLEND_ZERO;blend.BlendOpAlpha=D3D12_BLEND_OP_ADD;blend.LogicOp=D3D12_LOGIC_OP_NOOP;blend.RenderTargetWriteMask=D3D12_COLOR_WRITE_ENABLE_ALL;
 state.SampleMask=UINT_MAX;state.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;state.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;state.RasterizerState.DepthClipEnable=TRUE;
 state.DepthStencilState.DepthEnable=TRUE;state.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ALL;state.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_LESS;
 state.InputLayout={layout,static_cast<UINT>(std::size(layout))};state.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;state.NumRenderTargets=1;state.RTVFormats[0]=DXGI_FORMAT_R8G8B8A8_UNORM;state.DSVFormat=DXGI_FORMAT_D32_FLOAT;state.SampleDesc.Count=1;
 ComPtr<ID3D12PipelineState> candidate_pipeline;checked(device->CreateGraphicsPipelineState(&state,IID_PPV_ARGS(&candidate_pipeline)),"Textured pipeline");texture_root.Swap(candidate_root);texture_pipeline.Swap(candidate_pipeline);
}
std::unique_ptr<TextureGpu> stage_textured(const TexturedScene& scene){
 require_healthy();
 validate_textured_scene(scene);
 if(scene.vertices.empty())return {};
 texture_pipeline_initialize();auto candidate=std::make_unique<TextureGpu>();candidate->draws=scene.draws;
 D3D12_DESCRIPTOR_HEAP_DESC hd{};hd.Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV;hd.NumDescriptors=static_cast<UINT>(scene.images.size()+1);hd.Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;checked(device->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&candidate->heap)),"Texture descriptors");
 const auto vbytes=static_cast<UINT64>(scene.vertices.size()*sizeof(TexturedVertex));auto buffer=buffer_description(vbytes);const auto upload_heap=heap_properties(D3D12_HEAP_TYPE_UPLOAD);
 checked(device->CreateCommittedResource(&upload_heap,D3D12_HEAP_FLAG_NONE,&buffer,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&candidate->vertices)),"Textured vertices");
 const D3D12_RANGE no_read{0,0};void* mapped=nullptr;checked(candidate->vertices->Map(0,&no_read,&mapped),"Map textured vertices");std::memcpy(mapped,scene.vertices.data(),static_cast<std::size_t>(vbytes));candidate->vertices->Unmap(0,nullptr);candidate->view={candidate->vertices->GetGPUVirtualAddress(),static_cast<UINT>(vbytes),sizeof(TexturedVertex)};
 ComPtr<ID3D12CommandAllocator> allocator;ComPtr<ID3D12GraphicsCommandList> list;checked(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)),"Texture upload allocator");checked(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,IID_PPV_ARGS(&list)),"Texture upload commands");
 std::vector<ComPtr<ID3D12Resource>> staging;auto descriptor=candidate->heap->GetCPUDescriptorHandleForHeapStart();const auto stride=device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);UINT64 resident=vbytes;
 for(const auto& image:scene.images){
  D3D12_RESOURCE_DESC td{};td.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;td.Width=image.levels[0].width;td.Height=image.levels[0].height;td.DepthOrArraySize=1;td.MipLevels=static_cast<UINT16>(image.levels.size());td.Format=image.semantic==ImageSemantic::srgb_color?DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:DXGI_FORMAT_R8G8B8A8_UNORM;td.SampleDesc.Count=1;
  const auto allocation=device->GetResourceAllocationInfo(0,1,&td);if(allocation.SizeInBytes>256u*1024u*1024u-resident)throw std::invalid_argument("Texture GPU residency exceeds256MiB");resident+=allocation.SizeInBytes;
  ComPtr<ID3D12Resource> texture;const auto gpu_heap=heap_properties(D3D12_HEAP_TYPE_DEFAULT);checked(device->CreateCommittedResource(&gpu_heap,D3D12_HEAP_FLAG_NONE,&td,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&texture)),"Texture resource");
  const auto count=static_cast<UINT>(image.levels.size());std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(count);std::vector<UINT> rows(count);std::vector<UINT64> row_sizes(count);UINT64 total=0;device->GetCopyableFootprints(&td,0,count,0,footprints.data(),rows.data(),row_sizes.data(),&total);
  ComPtr<ID3D12Resource> upload;buffer=buffer_description(total);checked(device->CreateCommittedResource(&upload_heap,D3D12_HEAP_FLAG_NONE,&buffer,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&upload)),"Texture staging buffer");checked(upload->Map(0,&no_read,&mapped),"Map texture staging");
  for(UINT mip=0;mip<count;++mip){const auto& level=image.levels[mip];const auto& fp=footprints[mip];for(UINT y=0;y<level.height;++y)std::memcpy(static_cast<unsigned char*>(mapped)+fp.Offset+static_cast<std::size_t>(y)*fp.Footprint.RowPitch,level.rgba.data()+static_cast<std::size_t>(y)*level.width*4,static_cast<std::size_t>(level.width)*4);}
  upload->Unmap(0,nullptr);
  for(UINT mip=0;mip<count;++mip){D3D12_TEXTURE_COPY_LOCATION source{},destination{};source.pResource=upload.Get();source.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;source.PlacedFootprint=footprints[mip];destination.pResource=texture.Get();destination.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;destination.SubresourceIndex=mip;list->CopyTextureRegion(&destination,0,0,0,&source,nullptr);}
  auto barrier=transition(texture.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);list->ResourceBarrier(1,&barrier);
  D3D12_SHADER_RESOURCE_VIEW_DESC srv{};srv.Format=td.Format;srv.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2D;srv.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;srv.Texture2D.MipLevels=count;device->CreateShaderResourceView(texture.Get(),&srv,descriptor);descriptor.ptr+=stride;candidate->images.push_back(std::move(texture));staging.push_back(std::move(upload));
 }
 shadow_descriptor(directional_shadow?directional_shadow->texture.Get():nullptr,descriptor);
 checked(list->Close(),"Close texture uploads");
 auto job=std::make_unique<InFlightResources>();job->textures=std::move(candidate);job->allocator=std::move(allocator);job->commands=std::move(list);job->staging=std::move(staging);
 auto* submitted=job.get();submissions.prepare(std::move(job));
 auto completed=submissions.submit_and_wait([&]{ID3D12CommandList* lists[]={submitted->commands.Get()};queue->ExecuteCommandLists(1,lists);},[&]{idle();});
 return std::move(completed->textures);
}
void replace_textured(const TexturedScene& scene){
 require_healthy();
 validate_textured_scene(scene);
 if(scene.vertices.size()>1000000-vertex_count)throw std::invalid_argument("Combined base/textured geometry exceeds one million vertices");
 auto candidate=stage_textured(scene);if(!candidate)idle();textures.swap(candidate);
}
void draw_textured(const std::array<float,16>& matrix,UINT frame){
 if(!textures)return;
 commands->SetPipelineState(texture_pipeline.Get());commands->SetGraphicsRootSignature(texture_root.Get());commands->SetGraphicsRoot32BitConstants(0,16,matrix.data(),0);
 ID3D12DescriptorHeap* heaps[]={textures->heap.Get()};commands->SetDescriptorHeaps(1,heaps);commands->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);commands->IASetVertexBuffers(0,1,&textures->view);
 const auto stride=device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
 commands->SetGraphicsRootConstantBufferView(3,lighting_buffers[frame]->GetGPUVirtualAddress());auto shadow=textures->heap->GetGPUDescriptorHandleForHeapStart();shadow.ptr+=static_cast<UINT64>(textures->images.size())*stride;commands->SetGraphicsRootDescriptorTable(4,shadow);
 for(const auto&draw:textures->draws){auto handle=textures->heap->GetGPUDescriptorHandleForHeapStart();handle.ptr+=static_cast<UINT64>(draw.image)*stride;commands->SetGraphicsRootDescriptorTable(1,handle);const float material[]={draw.tint.x,draw.tint.y,draw.tint.z,draw.emission};commands->SetGraphicsRoot32BitConstants(2,4,material,0);commands->DrawInstanced(draw.count,1,draw.first,0);}
}
