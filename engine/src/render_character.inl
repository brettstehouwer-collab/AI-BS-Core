// Included inside Dx12Renderer::Impl. Indexed geometry and pose storage are
// independent of the legacy transient path and static scenery resources.
static constexpr UINT64 character_constant_bytes=8448;
static constexpr UINT64 character_gpu_limit=32u*1024u*1024u;
struct CharacterConstants {
 std::array<CharacterMatrix,character_maximum_joints> skin{},normal{};
 CharacterMatrix world{},world_normal{};
 std::array<float,4> tint_emission{};
 float opacity=1;std::uint32_t joint_count=0,pad0=0,pad1=0;
 std::array<float,4> camera_world{};
};
static_assert(sizeof(CharacterVertex)==72&&offsetof(CharacterVertex,joints)==48&&offsetof(CharacterVertex,weights)==56);
static_assert(sizeof(CharacterConstants)==8368&&character_constant_bytes%256==0);
struct CharacterGpu {
 CharacterMesh skeleton;
 std::array<double,3> position_bounds{};
 ComPtr<ID3D12Resource> vertices,indices,constants[frame_count];
 D3D12_VERTEX_BUFFER_VIEW vertex_view{};D3D12_INDEX_BUFFER_VIEW index_view{};
 UINT index_count=0;UINT64 resident=0;bool legacy_mesh=true;
 ComPtr<ID3D12DescriptorHeap> heap;
 std::vector<ComPtr<ID3D12Resource>> images;
 std::vector<CharacterMaterial> materials;std::vector<CharacterDraw> draws;
};
std::unique_ptr<CharacterGpu> character;
ComPtr<ID3D12RootSignature> character_root;
ComPtr<ID3D12PipelineState> character_depth_pipeline[2],character_pipeline[2];

CharacterMatrix character_world_normal(const CharacterMatrix& a)const{
 const auto at=[&](unsigned i){return static_cast<double>(a[i]);};
 const double d=at(0)*(at(5)*at(10)-at(6)*at(9))-at(1)*(at(4)*at(10)-at(6)*at(8))+at(2)*(at(4)*at(9)-at(5)*at(8));
 CharacterMatrix n=character_identity_matrix;
 n[0]=static_cast<float>((at(5)*at(10)-at(6)*at(9))/d);n[1]=static_cast<float>((at(6)*at(8)-at(4)*at(10))/d);n[2]=static_cast<float>((at(4)*at(9)-at(5)*at(8))/d);
 n[4]=static_cast<float>((at(2)*at(9)-at(1)*at(10))/d);n[5]=static_cast<float>((at(0)*at(10)-at(2)*at(8))/d);n[6]=static_cast<float>((at(1)*at(8)-at(0)*at(9))/d);
 n[8]=static_cast<float>((at(1)*at(6)-at(2)*at(5))/d);n[9]=static_cast<float>((at(2)*at(4)-at(0)*at(6))/d);n[10]=static_cast<float>((at(0)*at(5)-at(1)*at(4))/d);return n;
}
CharacterConstants prepare_character(const CharacterInstance& instance,const std::array<float,16>* projection=nullptr)const{
 if(!character)throw std::invalid_argument("Character instance has no adopted indexed resource");
 validate_character_instance(character->skeleton,instance);
 const auto palette=character_skin_palette(character->skeleton,instance.pose);
 CharacterConstants packed;packed.skin=palette.skin;packed.normal=palette.normal;packed.world=instance.world;
 packed.world_normal=character_world_normal(instance.world);packed.tint_emission={instance.tint.x,instance.tint.y,instance.tint.z,instance.emission};packed.opacity=instance.opacity;packed.joint_count=palette.joint_count;
 // A conservative component-wise envelope proves every influenced position
 // and intermediate multiply/sum finite without rescanning vertices per frame.
 // CPU matrices are bounded to1e12, source positions to1e6. Keep substantial
 // headroom below float max for arithmetic, interpolation and projection.
 std::array<double,3> skinned{};
 for(unsigned j=0;j<palette.joint_count;++j)for(unsigned axis=0;axis<3;++axis){
  const auto& m=palette.skin[j];double bound=std::abs(static_cast<double>(m[12+axis]));
  for(unsigned k=0;k<3;++k)bound+=character->position_bounds[k]*std::abs(static_cast<double>(m[k*4+axis]));
  skinned[axis]=std::max(skinned[axis],bound*1.00001);
 }
 constexpr double safe=static_cast<double>(std::numeric_limits<float>::max())/64;
 std::array<double,3> world_bounds{};
 for(unsigned axis=0;axis<3;++axis){
  double bound=std::abs(static_cast<double>(instance.world[12+axis]));for(unsigned k=0;k<3;++k)bound+=skinned[k]*std::abs(static_cast<double>(instance.world[k*4+axis]));
  if(!std::isfinite(bound)||bound>safe)throw std::invalid_argument("Character pose exceeds finite GPU position envelope");
  world_bounds[axis]=bound;
 }
 if(projection){
  for(float value:*projection)if(!std::isfinite(value))throw std::invalid_argument("Character camera projection must be finite");
  for(unsigned axis=0;axis<4;++axis){
   double bound=std::abs(static_cast<double>((*projection)[12+axis]));for(unsigned k=0;k<3;++k)bound+=world_bounds[k]*std::abs(static_cast<double>((*projection)[k*4+axis]));
   if(!std::isfinite(bound)||bound>safe)throw std::invalid_argument("Character pose/camera exceeds finite GPU clip envelope");
  }
 }
 return packed;
}
void character_pipeline_initialize(){
 if(character_pipeline[0])return;
 D3D12_DESCRIPTOR_RANGE shadow_range{};shadow_range.RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_SRV;shadow_range.NumDescriptors=1;shadow_range.BaseShaderRegister=1;
 D3D12_DESCRIPTOR_RANGE albedo_range{};albedo_range.RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_SRV;albedo_range.NumDescriptors=1;albedo_range.BaseShaderRegister=0;
 D3D12_ROOT_PARAMETER parameters[6]{};
 parameters[0].ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;parameters[0].Constants.Num32BitValues=16;parameters[0].Constants.ShaderRegister=0;parameters[0].ShaderVisibility=D3D12_SHADER_VISIBILITY_VERTEX;
 parameters[1].ParameterType=D3D12_ROOT_PARAMETER_TYPE_CBV;parameters[1].Descriptor.ShaderRegister=1;parameters[1].ShaderVisibility=D3D12_SHADER_VISIBILITY_ALL;
 parameters[2].ParameterType=D3D12_ROOT_PARAMETER_TYPE_CBV;parameters[2].Descriptor.ShaderRegister=2;parameters[2].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 parameters[3].ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;parameters[3].DescriptorTable.NumDescriptorRanges=1;parameters[3].DescriptorTable.pDescriptorRanges=&shadow_range;parameters[3].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 parameters[4].ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;parameters[4].DescriptorTable.NumDescriptorRanges=1;parameters[4].DescriptorTable.pDescriptorRanges=&albedo_range;parameters[4].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 parameters[5].ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;parameters[5].Constants.Num32BitValues=6;parameters[5].Constants.ShaderRegister=3;parameters[5].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 D3D12_STATIC_SAMPLER_DESC albedo{};albedo.Filter=D3D12_FILTER_MIN_MAG_MIP_LINEAR;albedo.AddressU=albedo.AddressV=albedo.AddressW=D3D12_TEXTURE_ADDRESS_MODE_WRAP;albedo.MaxAnisotropy=1;albedo.ComparisonFunc=D3D12_COMPARISON_FUNC_ALWAYS;albedo.MaxLOD=D3D12_FLOAT32_MAX;albedo.ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
 const D3D12_STATIC_SAMPLER_DESC samplers[]={albedo,shadow_sampler()};D3D12_ROOT_SIGNATURE_DESC desc{};desc.NumParameters=6;desc.pParameters=parameters;desc.NumStaticSamplers=2;desc.pStaticSamplers=samplers;desc.Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;
 // 16 camera DWORDs + two2-DWORD CBVs + two1-DWORD tables +6material=28.
 ComPtr<ID3DBlob> signature,error;checked(D3D12SerializeRootSignature(&desc,D3D_ROOT_SIGNATURE_VERSION_1,&signature,&error),"Character root serialization");
 ComPtr<ID3D12RootSignature> candidate_root;checked(device->CreateRootSignature(0,signature->GetBufferPointer(),signature->GetBufferSize(),IID_PPV_ARGS(&candidate_root)),"Character root");
 const auto vs=read_shader(texture_shaders/"character.vs.cso"),ps=read_shader(texture_shaders/"character.ps.cso");
 const D3D12_INPUT_ELEMENT_DESC layout[]={
  {"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
  {"NORMAL",0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
  {"COLOR",0,DXGI_FORMAT_R32G32B32_FLOAT,0,24,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
  {"TEXCOORD",0,DXGI_FORMAT_R32_FLOAT,0,36,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
  {"TEXCOORD",1,DXGI_FORMAT_R32G32_FLOAT,0,40,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
  {"BLENDINDICES",0,DXGI_FORMAT_R16G16B16A16_UINT,0,48,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
  {"BLENDWEIGHT",0,DXGI_FORMAT_R32G32B32A32_FLOAT,0,56,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0}};
 D3D12_GRAPHICS_PIPELINE_STATE_DESC state{};state.pRootSignature=candidate_root.Get();state.VS={vs.data(),vs.size()};
 auto& blend=state.BlendState.RenderTarget[0];blend.SrcBlend=D3D12_BLEND_ONE;blend.DestBlend=D3D12_BLEND_ZERO;blend.BlendOp=D3D12_BLEND_OP_ADD;blend.SrcBlendAlpha=D3D12_BLEND_ONE;blend.DestBlendAlpha=D3D12_BLEND_ZERO;blend.BlendOpAlpha=D3D12_BLEND_OP_ADD;blend.LogicOp=D3D12_LOGIC_OP_NOOP;
 state.SampleMask=UINT_MAX;state.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;state.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;state.RasterizerState.DepthClipEnable=TRUE;
 state.DepthStencilState.DepthEnable=TRUE;state.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ALL;state.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_LESS;
 state.InputLayout={layout,static_cast<UINT>(std::size(layout))};state.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;state.DSVFormat=DXGI_FORMAT_D32_FLOAT;state.SampleDesc.Count=1;
 ComPtr<ID3D12PipelineState> candidate_depth[2],candidate_color[2];
 for(unsigned culling=0;culling<2;++culling){
  state.RasterizerState.CullMode=culling?D3D12_CULL_MODE_BACK:D3D12_CULL_MODE_NONE;
  state.PS={};state.NumRenderTargets=0;state.RTVFormats[0]=DXGI_FORMAT_UNKNOWN;blend.BlendEnable=FALSE;blend.RenderTargetWriteMask=0;
  state.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ALL;state.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_LESS;
  checked(device->CreateGraphicsPipelineState(&state,IID_PPV_ARGS(&candidate_depth[culling])),"Character nearest depth pipeline");
  state.PS={ps.data(),ps.size()};state.NumRenderTargets=1;state.RTVFormats[0]=DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
  state.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ZERO;state.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_EQUAL;
  blend.BlendEnable=TRUE;blend.SrcBlend=D3D12_BLEND_SRC_ALPHA;blend.DestBlend=D3D12_BLEND_INV_SRC_ALPHA;blend.SrcBlendAlpha=D3D12_BLEND_ONE;blend.DestBlendAlpha=D3D12_BLEND_INV_SRC_ALPHA;blend.RenderTargetWriteMask=D3D12_COLOR_WRITE_ENABLE_ALL;
  checked(device->CreateGraphicsPipelineState(&state,IID_PPV_ARGS(&candidate_color[culling])),"Character linear blend pipeline");
 }
 character_root.Swap(candidate_root);for(unsigned culling=0;culling<2;++culling){character_depth_pipeline[culling].Swap(candidate_depth[culling]);character_pipeline[culling].Swap(candidate_color[culling]);}
}
UINT64 character_allocation(const D3D12_RESOURCE_DESC& desc)const{
 const auto value=device->GetResourceAllocationInfo(0,1,&desc).SizeInBytes;
 if(value==UINT64_MAX||value>character_gpu_limit)throw std::invalid_argument("Character GPU allocation exceeds32MiB");return value;
}
ComPtr<ID3D12DescriptorHeap> character_heap_with_shadow(const CharacterGpu& resource,ID3D12Resource* shadow){
 D3D12_DESCRIPTOR_HEAP_DESC desc{};desc.Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV;desc.NumDescriptors=static_cast<UINT>(resource.images.size()+1);desc.Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;
 ComPtr<ID3D12DescriptorHeap> heap;checked(device->CreateDescriptorHeap(&desc,IID_PPV_ARGS(&heap)),"Character material/shadow descriptors");
 auto handle=heap->GetCPUDescriptorHandleForHeapStart();const auto step=device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
 // Never use shader-visible descriptors as copy sources. Resources retain all
 // information needed to recreate SRVs into the new, not-yet-published heap.
 for(const auto& image:resource.images){const auto td=image->GetDesc();D3D12_SHADER_RESOURCE_VIEW_DESC view{};view.Format=td.Format;view.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2D;view.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;view.Texture2D.MipLevels=td.MipLevels;device->CreateShaderResourceView(image.Get(),&view,handle);handle.ptr+=step;}
 shadow_descriptor(shadow,handle);return heap;
}
ComPtr<ID3D12DescriptorHeap> stage_character_shadow(ID3D12Resource* shadow){return character?character_heap_with_shadow(*character,shadow):ComPtr<ID3D12DescriptorHeap>{};}
void publish_character_shadow(ComPtr<ID3D12DescriptorHeap>& heap)noexcept{if(character)character->heap.Swap(heap);}
std::unique_ptr<CharacterGpu> stage_character(const CharacterMesh& mesh,const CharacterAsset* asset=nullptr){
 require_healthy();validate_character_mesh(mesh);if(asset)validate_character_asset(*asset);
 const auto cost=character_mesh_cost(mesh);const auto vb=buffer_description(cost.gpu_vertex_bytes),ib=buffer_description(cost.gpu_index_bytes),cb=buffer_description(character_constant_bytes);
 const auto vcost=character_allocation(vb),icost=character_allocation(ib),ccost=character_allocation(cb);
 UINT64 resident=vcost+icost+frame_count*ccost,uploads=vcost+icost;
 // Explicit fallback image is owned by the adopted resource, including the
 // legacy vertex-colored entry point. It makes every draw's SRV well-defined.
 const ImageAsset white{ImageSemantic::srgb_color,{{1,1,{255,255,255,255}}}};
 struct ImageLayout {const ImageAsset* source;D3D12_RESOURCE_DESC desc{};std::array<D3D12_PLACED_SUBRESOURCE_FOOTPRINT,13> footprints{};UINT64 bytes=0;};
 std::vector<ImageLayout> images;images.reserve((asset?asset->images.size():0)+1);
 const auto preflight_image=[&](const ImageAsset& image){
  ImageLayout layout;layout.source=&image;auto& td=layout.desc;td.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;td.Width=image.levels[0].width;td.Height=image.levels[0].height;td.DepthOrArraySize=1;td.MipLevels=static_cast<UINT16>(image.levels.size());td.Format=DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;td.SampleDesc.Count=1;
  const auto charge=character_allocation(td);if(charge>character_gpu_limit-resident)throw std::invalid_argument("Character images exceed32MiB active GPU profile");resident+=charge;
  device->GetCopyableFootprints(&td,0,td.MipLevels,0,layout.footprints.data(),nullptr,nullptr,&layout.bytes);
  if(layout.bytes==0||layout.bytes==UINT64_MAX)throw std::invalid_argument("Invalid character texture staging footprint");
  const auto staging=character_allocation(buffer_description(layout.bytes));if(staging>96u*1024u*1024u-uploads)throw std::invalid_argument("Character staging exceeds96MiB replacement profile");uploads+=staging;images.push_back(layout);
 };
 if(resident>character_gpu_limit)throw std::invalid_argument("Character active GPU profile exceeds32MiB");
 if(asset)for(const auto& image:asset->images)preflight_image(image);preflight_image(white);
 const auto peak=(character?character->resident:0)+resident+uploads;
 if(peak>96u*1024u*1024u)throw std::invalid_argument("Character replacement residency exceeds96MiB");
 character_pipeline_initialize();auto staged=std::make_unique<CharacterGpu>();staged->skeleton.joints=mesh.joints;staged->resident=resident;staged->legacy_mesh=asset==nullptr;staged->index_count=static_cast<UINT>(mesh.indices.size());staged->images.reserve(images.size());
 if(asset){staged->materials=asset->materials;staged->draws=asset->draws;}else{staged->materials.emplace_back();staged->draws.push_back({0,staged->index_count,0});}
 for(const auto& vertex:mesh.vertices){staged->position_bounds[0]=std::max(staged->position_bounds[0],std::abs(static_cast<double>(vertex.position.x)));staged->position_bounds[1]=std::max(staged->position_bounds[1],std::abs(static_cast<double>(vertex.position.y)));staged->position_bounds[2]=std::max(staged->position_bounds[2],std::abs(static_cast<double>(vertex.position.z)));}
 const auto gpu=heap_properties(D3D12_HEAP_TYPE_DEFAULT),upload=heap_properties(D3D12_HEAP_TYPE_UPLOAD);
 checked(device->CreateCommittedResource(&gpu,D3D12_HEAP_FLAG_NONE,&vb,D3D12_RESOURCE_STATE_COMMON,nullptr,IID_PPV_ARGS(&staged->vertices)),"Character indexed vertices");
 checked(device->CreateCommittedResource(&gpu,D3D12_HEAP_FLAG_NONE,&ib,D3D12_RESOURCE_STATE_COMMON,nullptr,IID_PPV_ARGS(&staged->indices)),"Character indices");
 for(auto& constant:staged->constants)checked(device->CreateCommittedResource(&upload,D3D12_HEAP_FLAG_NONE,&cb,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&constant)),"Character fixed pose buffer");
 ComPtr<ID3D12Resource> vertex_upload,index_upload;checked(device->CreateCommittedResource(&upload,D3D12_HEAP_FLAG_NONE,&vb,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&vertex_upload)),"Character vertex upload");checked(device->CreateCommittedResource(&upload,D3D12_HEAP_FLAG_NONE,&ib,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&index_upload)),"Character index upload");
 const auto copy=[&](ID3D12Resource* target,const void* data,std::size_t bytes){void* mapped=nullptr;const D3D12_RANGE none{0,0};checked(target->Map(0,&none,&mapped),"Character upload map");std::memcpy(mapped,data,bytes);const D3D12_RANGE written{0,bytes};target->Unmap(0,&written);};
 copy(vertex_upload.Get(),mesh.vertices.data(),cost.gpu_vertex_bytes);copy(index_upload.Get(),mesh.indices.data(),cost.gpu_index_bytes);
 ComPtr<ID3D12CommandAllocator> allocator;ComPtr<ID3D12GraphicsCommandList> list;checked(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)),"Character upload allocator");checked(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,IID_PPV_ARGS(&list)),"Character upload commands");
 const D3D12_RESOURCE_BARRIER copy_barriers[]={transition(staged->vertices.Get(),D3D12_RESOURCE_STATE_COMMON,D3D12_RESOURCE_STATE_COPY_DEST),transition(staged->indices.Get(),D3D12_RESOURCE_STATE_COMMON,D3D12_RESOURCE_STATE_COPY_DEST)};list->ResourceBarrier(2,copy_barriers);
 list->CopyBufferRegion(staged->vertices.Get(),0,vertex_upload.Get(),0,cost.gpu_vertex_bytes);list->CopyBufferRegion(staged->indices.Get(),0,index_upload.Get(),0,cost.gpu_index_bytes);
 const D3D12_RESOURCE_BARRIER barriers[]={transition(staged->vertices.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER),transition(staged->indices.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_INDEX_BUFFER)};list->ResourceBarrier(2,barriers);
 std::vector<ComPtr<ID3D12Resource>> staging;staging.reserve(images.size()+2);staging.push_back(vertex_upload);staging.push_back(index_upload);
 for(const auto& image:images){
  ComPtr<ID3D12Resource> texture;checked(device->CreateCommittedResource(&gpu,D3D12_HEAP_FLAG_NONE,&image.desc,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&texture)),"Character albedo image");
  const auto upload_desc=buffer_description(image.bytes);ComPtr<ID3D12Resource> image_upload;checked(device->CreateCommittedResource(&upload,D3D12_HEAP_FLAG_NONE,&upload_desc,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&image_upload)),"Character image staging");
  const D3D12_RANGE none{0,0};void* mapped=nullptr;checked(image_upload->Map(0,&none,&mapped),"Map character image staging");
  for(UINT mip=0;mip<image.desc.MipLevels;++mip){const auto& level=image.source->levels[mip];const auto& fp=image.footprints[mip];for(UINT y=0;y<level.height;++y)std::memcpy(static_cast<unsigned char*>(mapped)+fp.Offset+static_cast<std::size_t>(y)*fp.Footprint.RowPitch,level.rgba.data()+static_cast<std::size_t>(y)*level.width*4,static_cast<std::size_t>(level.width)*4);}
  const D3D12_RANGE written{0,static_cast<SIZE_T>(image.bytes)};image_upload->Unmap(0,&written);
  for(UINT mip=0;mip<image.desc.MipLevels;++mip){D3D12_TEXTURE_COPY_LOCATION from{},to{};from.pResource=image_upload.Get();from.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;from.PlacedFootprint=image.footprints[mip];to.pResource=texture.Get();to.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;to.SubresourceIndex=mip;list->CopyTextureRegion(&to,0,0,0,&from,nullptr);}
  const auto barrier=transition(texture.Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);list->ResourceBarrier(1,&barrier);staged->images.push_back(std::move(texture));staging.push_back(std::move(image_upload));
 }
 staged->heap=character_heap_with_shadow(*staged,directional_shadow?directional_shadow->texture.Get():nullptr);
 checked(list->Close(),"Character upload close");
 staged->vertex_view={staged->vertices->GetGPUVirtualAddress(),static_cast<UINT>(cost.gpu_vertex_bytes),sizeof(CharacterVertex)};staged->index_view={staged->indices->GetGPUVirtualAddress(),static_cast<UINT>(cost.gpu_index_bytes),DXGI_FORMAT_R32_UINT};
 auto job=std::make_unique<InFlightResources>();job->character=std::move(staged);job->allocator=std::move(allocator);job->commands=std::move(list);job->staging=std::move(staging);
 auto* submitted=job.get();submissions.prepare(std::move(job));
 auto completed=submissions.submit_and_wait([&]{ID3D12CommandList* lists[]={submitted->commands.Get()};queue->ExecuteCommandLists(1,lists);},[&]{idle();});
 statistics.character_replacement_peak_gpu_bytes=std::max(statistics.character_replacement_peak_gpu_bytes,peak);return std::move(completed->character);
}
void publish_character(std::unique_ptr<CharacterGpu>& staged)noexcept{
 character.swap(staged);++statistics.character_replacements;
 if(character){statistics.character_buffer_allocations+=frame_count+2;statistics.character_texture_allocations+=character->images.size();}
 statistics.character_active_gpu_bytes=character?character->resident:0;
}
void replace_character(const CharacterMesh* mesh){
 require_healthy();auto staged=mesh?stage_character(*mesh):std::unique_ptr<CharacterGpu>{};
 if(!mesh)idle();publish_character(staged);
}
void replace_character_asset(const CharacterAsset& asset){auto staged=stage_character(asset.mesh,&asset);publish_character(staged);}
void upload_character(UINT frame,const CharacterConstants& packed){
 void* mapped=nullptr;const D3D12_RANGE none{0,0};checked(character->constants[frame]->Map(0,&none,&mapped),"Map character pose constants");std::memcpy(mapped,&packed,sizeof(packed));const D3D12_RANGE written{0,sizeof(packed)};character->constants[frame]->Unmap(0,&written);
}
void draw_character(const std::array<float,16>& camera,UINT frame){
 if(!character)return;
 commands->SetGraphicsRootSignature(character_root.Get());commands->SetGraphicsRoot32BitConstants(0,16,camera.data(),0);commands->SetGraphicsRootConstantBufferView(1,character->constants[frame]->GetGPUVirtualAddress());commands->SetGraphicsRootConstantBufferView(2,lighting_buffers[frame]->GetGPUVirtualAddress());
 ID3D12DescriptorHeap* heaps[]={character->heap.Get()};commands->SetDescriptorHeaps(1,heaps);
 const auto step=device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);auto shadow=character->heap->GetGPUDescriptorHandleForHeapStart();shadow.ptr+=static_cast<UINT64>(character->images.size())*step;commands->SetGraphicsRootDescriptorTable(3,shadow);
 commands->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);commands->IASetVertexBuffers(0,1,&character->vertex_view);commands->IASetIndexBuffer(&character->index_view);
 const auto depth_view=dsv_heap->GetCPUDescriptorHandleForHeapStart();commands->OMSetRenderTargets(0,nullptr,FALSE,&depth_view);// Every depth draw uses the same material culling as its later color draw.
 for(const auto& draw:character->draws){commands->SetPipelineState(character_depth_pipeline[character->materials[draw.material].double_sided?0:1].Get());commands->DrawIndexedInstanced(draw.index_count,1,draw.first_index,0,0);}
 auto color=rtv_heap->GetCPUDescriptorHandleForHeapStart();color.ptr+=static_cast<SIZE_T>(frame_count+frame)*descriptor_size;
 commands->OMSetRenderTargets(1,&color,FALSE,&depth_view);
 for(const auto& draw:character->draws){
  const auto& material=character->materials[draw.material];commands->SetPipelineState(character_pipeline[material.double_sided?0:1].Get());const auto image=material.albedo_image==character_no_image?character->images.size()-1:material.albedo_image;
  auto descriptor=character->heap->GetGPUDescriptorHandleForHeapStart();descriptor.ptr+=static_cast<UINT64>(image)*step;commands->SetGraphicsRootDescriptorTable(4,descriptor);
  const float constants[]={material.base_color.x,material.base_color.y,material.base_color.z,material.emission};commands->SetGraphicsRoot32BitConstants(5,4,constants,0);const std::uint32_t options=character->legacy_mesh?0u:(material.double_sided?3u:2u);commands->SetGraphicsRoot32BitConstants(5,1,&options,4);
  commands->SetGraphicsRoot32BitConstants(5,1,&material.roughness,5);
  commands->DrawIndexedInstanced(draw.index_count,1,draw.first_index,0,0);++statistics.character_material_draws;
 }
}
