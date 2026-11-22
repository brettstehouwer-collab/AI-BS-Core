#include <aibs/initial_view.hpp>
#include <aibs/opening_tour.hpp>
#include <aibs/frame_measurement.hpp>
#include <aibs/audio_codec.hpp>
#include <aibs/warm_opening.hpp>
#include <aibs/opening_inspections.hpp>
#include <aibs/memory_playback.hpp>
#include <aibs/textured_scene.hpp>
#include <aibs/surface_assets.hpp>
#include <aibs/surface_codec.hpp>
#include <aibs/guide_controller.hpp>
#include <aibs/character_scene.hpp>
#include <aibs/guide_presentation.hpp>
#include <aibs/character_import.hpp>
#include <aibs/character_codec.hpp>
#include <aibs/content_dependencies.hpp>
#include <aibs/companion_runtime.hpp>
#include <aibs/persistence.hpp>
#include <aibs/creator_host.hpp>
#include <aibs/first_boot_content.hpp>
#include <aibs/content_authoring.hpp>
#include <aibs/chapter_viewport.hpp>
#include <aibs/render.hpp>
#include <aibs/scene.hpp>
#include <aibs/assets.hpp>
#include <aibs/asset_scene.hpp>
#include <aibs/placed_assets.hpp>
#include <aibs/first_boot.hpp>
#include <aibs/player.hpp>
#include <aibs/movement_course.hpp>
#include <aibs/gameplay.hpp>
#include <aibs/gameplay_worker.hpp>
#include <aibs/gameplay_world.hpp>
#include <aibs/durable_first_boot.hpp>
#include <aibs/first_boot_chapter.hpp>
#include <aibs/content_lighting.hpp>
#include <cmath>
#include <algorithm>
#include <bit>
#include <fstream>
#include <iostream>
#include <stdexcept>
int main() {
 {
  // Synthetic clock endpoints test installed algorithm/linkage, not hardware FPS.
  aibs::FrameMeasurementConfig cfg;cfg.maximum_samples=32;
  aibs::FrameObservation observation;observation.width=1920;observation.height=1080;
  observation.active=true;observation.memory_valid=true;observation.private_bytes=1024;
  aibs::FrameMeasurement measurement(cfg,{},observation);
  for(unsigned tick=1;tick<=17;++tick){observation.presented_frames=tick;measurement.observe(aibs::FrameMeasurement::Clock::time_point{}+std::chrono::seconds(tick),observation);}
  const auto measured=measurement.summary();
  if(!measured||measured->frame_count!=15||measured->frames_per_second!=1||measured->instrumentation_bytes!=measurement.instrumentation_bytes())return 1;
  aibs::CreatorSession source(aibs::first_boot_schema(),"sdk-opening-view","main");
  if(!aibs::seed_first_boot(source).ok)return 1;
  const auto draft=aibs::make_warm_opening_draft(source,{});
  const auto content=aibs::FirstBootContent::create(draft.definition);
  const auto target=aibs::first_boot_initial_view(content.definition());
  if(!target||target->target_id!=draft.tour.ids[static_cast<std::size_t>(aibs::OpeningTourRole::controller)])return 1;
  const auto encoded=aibs::encode_opening_tour(content,draft.tour);
  if(aibs::decode_opening_tour(encoded,content).ids!=draft.tour.ids)return 1;
 }

 {
  // This fixture links the installed opening factory and inspection module;
  // canonical source headers/libraries are not part of this consumer build.
  aibs::CreatorSession source(aibs::first_boot_schema(),"sdk-opening","main");
  if(!aibs::seed_first_boot(source).ok)return 1;
  const auto original_revision=source.revision();
  const auto opening=aibs::FirstBootContent::create(aibs::make_warm_opening_definition(source,{}));
  aibs::OpeningInspectionCatalog catalog(opening.definition());
  if(source.revision()!=original_revision||catalog.entries().size()!=7||catalog.resident_bytes()==0||catalog.resident_bytes()>512u*1024u)return 1;
  const auto first=catalog.entries().front();aibs::OpeningInspectionSession reading(catalog);
  if(!reading.select(first.fixture_id,first.center,true)||!reading.snapshot()||reading.snapshot()->source!=first.source||reading.resident_bytes()<catalog.resident_bytes())return 1;
  reading.close();if(reading.snapshot())return 1;
  const auto observations=aibs::content_authoring_rows(opening);
  const auto found=std::find_if(observations.begin(),observations.end(),[&](const auto& row){return row.entity_id==first.fixture_id;});
  if(found==observations.end()||found->fields.size()!=20||!found->fields.contains("inspection_text"))return 1;
 }

 // Installed headers/libraries own a complete source-rate asset and controller.
 // This consumer never opens an audio device or plays original speech.
 aibs::AudioAsset sdk_audio;sdk_audio.asset_id=aibs::new_uuid();sdk_audio.name="Synthetic SDK silence";sdk_audio.source_sha256=std::string(64,'a');sdk_audio.sample_rate=8000;sdk_audio.channels=1;sdk_audio.frame_count=800;sdk_audio.pcm.resize(1600);sdk_audio.captions={{0,800,"Synthetic caption"}};sdk_audio.caption_review=aibs::AudioCaptionReview::checked;
 auto sdk_audio_copy=std::make_shared<const aibs::AudioAsset>(aibs::decode_audio_asset(aibs::encode_audio_asset(sdk_audio)));
 if(*sdk_audio_copy!=sdk_audio||aibs::memory_caption_index(*sdk_audio_copy,799)!=0||aibs::memory_caption_index(*sdk_audio_copy,800))return 1;
 aibs::MemoryPlaybackSession sdk_memory;const auto sdk_station=aibs::new_uuid();
 if(!sdk_memory.bind(sdk_station,sdk_audio_copy,0))return 1;
 const auto sdk_memory_state=sdk_memory.snapshot();if(sdk_memory_state.station_id()!=sdk_station||sdk_memory_state.playback.state!=aibs::AudioPlaybackState::stopped||sdk_memory_state.playback.source_voice||sdk_memory_state.caption_index||sdk_memory_state.review_pending)return 1;
 if(!sdk_memory.close()||sdk_memory.snapshot().asset)return 1;

 aibs::AssetPackReference sdk_character_reference;
 const auto sdk_character_root=std::filesystem::temp_directory_path()/("aibs-sdk-character-"+aibs::new_uuid());
 const auto sdk_character_store=sdk_character_root/"store";
 {
  // Source bytes and URI resources are synthetic and supplied through public
  // memory APIs; no test reaches back into a canonical engine checkout.
  std::vector<std::byte> buffer;
  const auto word=[&](std::uint32_t value){for(unsigned shift=0;shift<32;shift+=8)buffer.push_back(static_cast<std::byte>((value>>shift)&255));};
  for(float value:{0.f,0.f,0.f,1.f,0.f,0.f,0.f,1.f,0.f,0.f,0.f,1.f,0.f,0.f,1.f,0.f,0.f,1.f})word(std::bit_cast<std::uint32_t>(value));
  for(unsigned i=0;i<12;++i)buffer.push_back(std::byte{});
  for(unsigned vertex=0;vertex<3;++vertex)for(float weight:{1.f,0.f,0.f,0.f})word(std::bit_cast<std::uint32_t>(weight));
  for(unsigned index:{0u,1u,2u}){buffer.push_back(static_cast<std::byte>(index));buffer.push_back(std::byte{});}
  if(buffer.size()!=138)return 1;
  const std::string source=R"({"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0,1]}],"nodes":[{}, {"mesh":0,"skin":0}],"skins":[{"joints":[0]}],"meshes":[{"primitives":[{"attributes":{"POSITION":0,"NORMAL":1,"JOINTS_0":2,"WEIGHTS_0":3},"indices":4,"material":0}]}],"materials":[{"doubleSided":true,"pbrMetallicRoughness":{"metallicFactor":0,"roughnessFactor":1,"baseColorFactor":[1,1,1,1]}}],"buffers":[{"byteLength":138,"uri":"mesh.bin"}],"bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":36},{"buffer":0,"byteOffset":36,"byteLength":36},{"buffer":0,"byteOffset":72,"byteLength":12},{"buffer":0,"byteOffset":84,"byteLength":48},{"buffer":0,"byteOffset":132,"byteLength":6}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3","min":[0,0,0],"max":[1,1,0]},{"bufferView":1,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":2,"componentType":5121,"count":3,"type":"VEC4"},{"bufferView":3,"componentType":5126,"count":3,"type":"VEC4"},{"bufferView":4,"componentType":5123,"count":3,"type":"SCALAR"}]})";
  const auto raw=std::span(reinterpret_cast<const std::byte*>(source.data()),source.size());
  const aibs::GltfInputResource resource{"mesh.bin",buffer};aibs::CharacterImportOptions options;options.asset_id=aibs::new_uuid();options.name="Installed SDK character";
  aibs::CharacterImportDiagnostics diagnostics;
  auto character=aibs::import_character_gltf(raw,std::span(&resource,1),options,&diagnostics);
  if(character.mesh.vertices.size()!=3||character.mesh.vertices[1].position.x!=-1||character.mesh.indices!=std::vector<std::uint32_t>{0,2,1}||diagnostics.source_skin_to_cooked!=std::vector<std::uint16_t>{0}||diagnostics.parser_peak_bytes==0||aibs::character_import_live_parser_bytes()!=0)return 1;
  // This memory-import fixture has no source animations. Author the four
  // minimal bind-pose clips explicitly to satisfy the companion contract.
  for(const char* name:{"idle","walk","catchup","guidance"}){aibs::CharacterClip clip;clip.name=name;clip.looping=clip.name!="guidance";for(const auto& joint:character.mesh.joints)clip.samples.push_back(joint.bind_local);character.mesh.clips.push_back(std::move(clip));}
  const auto encoded=aibs::encode_character_asset(character);if(aibs::encode_character_asset(aibs::decode_character_asset(encoded))!=encoded)return 1;
  bool rejected=false;try{(void)aibs::import_character_gltf(raw,{},options);}catch(const std::invalid_argument&){rejected=true;}if(!rejected)return 1;
  auto malformed=encoded;malformed.back()^=std::byte{1};rejected=false;try{(void)aibs::decode_character_asset(malformed);}catch(const std::invalid_argument&){rejected=true;}if(!rejected)return 1;
  std::filesystem::create_directory(sdk_character_root);std::filesystem::create_directory(sdk_character_store);const auto pack=sdk_character_root/"pack";std::filesystem::create_directory(pack);
  const auto write=[&](const std::filesystem::path& file,std::span<const std::byte> body){std::ofstream f(file,std::ios::binary);f.write(reinterpret_cast<const char*>(body.data()),static_cast<std::streamsize>(body.size()));if(!f.good())throw std::runtime_error("Cannot write installed SDK synthetic pack");};
  const auto text=[&](const std::filesystem::path& file,std::string_view body){write(file,{reinterpret_cast<const std::byte*>(body.data()),body.size()});};
  const auto digest=aibs::asset_sha256(encoded);write(pack/(digest+".aibchar"),encoded);text(pack/"catalog.aibcat","AIBCAT 2\ncharacter "+character.asset_id+" "+digest+" "+digest+".aibchar\n");text(pack/"LICENSE.txt","Self-authored installed SDK test fixture.\n");text(pack/"provenance.json","{\"source\":\"synthetic-public-sdk-memory-import\"}\n");
  sdk_character_reference=aibs::adopt_asset_pack(pack,sdk_character_store);
  if(aibs::encode_character_asset(aibs::load_stored_character_asset(sdk_character_store,sdk_character_reference).payload)!=encoded)return 1;
 }
  aibs::TexturedScene textures; aibs::validate_textured_scene(textures);
  aibs::ImageAsset pixel{aibs::ImageSemantic::srgb_color,{{1,1,{255,255,255,255}}}}; aibs::generate_image_mips(pixel);
  const std::vector<aibs::MeshMaterial> surface_material{{"plain",{1,1,1},0}};
  const auto surface=aibs::import_surface_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n",surface_material,aibs::new_uuid(),"External UV triangle",aibs::ObjUvOrigin::bottom_left);
  if(aibs::surface_scene(surface).vertices.size()!=3)return 1;
  const auto surface_bytes=aibs::encode_surface_asset(surface);
  if(aibs::encode_surface_asset(aibs::decode_surface_asset(surface_bytes))!=surface_bytes)return 1;
  aibs::TexturedScene combined_surfaces;
  aibs::append_surface_scene(combined_surfaces,surface,{1,0,0});
  aibs::append_surface_scene(combined_surfaces,surface,{3,0,0});
  if(combined_surfaces.vertices.size()!=6||combined_surfaces.images.size()!=1)return 1;
 {
  aibs::CharacterMesh character;character.joints.emplace_back();
  for(const aibs::Vec3 point:{aibs::Vec3{0,0,0},aibs::Vec3{1,0,0},aibs::Vec3{0,1,0}}){aibs::CharacterVertex vertex;vertex.position=point;vertex.normal={0,0,1};character.vertices.push_back(vertex);}
  character.indices={0,1,2};aibs::CharacterClip clip;clip.name="sdk-guidance";clip.duration_seconds=1;clip.frame_count=2;clip.looping=false;
  clip.samples.resize(2);clip.samples[1].rotation={0,0,.7071067812f,.7071067812f};character.clips.push_back(clip);
  aibs::validate_character_mesh(character);const auto bind=aibs::character_bind_pose(character);
  if(bind.joint_count!=1||aibs::character_mesh_cost(character).gpu_index_bytes!=3*sizeof(std::uint32_t))return 1;
  aibs::CharacterInstance instance;instance.pose=aibs::sample_character_clip(character,0,.5);
  aibs::CharacterJointTransform placement;placement.translation={2,0,0};instance.world=aibs::character_transform_matrix(placement);
  aibs::validate_character_instance(character,instance);
  const auto vertex=aibs::character_skin_vertex(character.vertices[1],aibs::character_skin_palette(character,instance.pose),instance.world);
  if(std::abs(vertex.position.x-2.7071067812f)>4e-5f||std::abs(vertex.position.y-.7071067812f)>4e-5f||std::abs(vertex.position.z)>4e-5f||vertex.normal!=aibs::Vec3{0,0,1})return 1;
 }

 {
  const auto figure=aibs::make_guide_placeholder();aibs::GuidePresentation presentation(figure);
  aibs::GuideState guide;guide.character.feet={2,0,3};guide.character.grounded=true;
  guide.activity=aibs::GuideActivity::waiting;guide.intent=aibs::GuideIntent::wait;
  const auto instance=presentation.sample(guide,.1);
  if(!instance||instance->world[12]!=2||instance->world[14]!=3||figure.clips.size()!=4)return 1;
  aibs::validate_character_instance(figure,*instance);
  if(presentation.sample(std::nullopt,0)||presentation.sample(guide,0,false,true))return 1;
 }
 const std::vector<aibs::MeshMaterial> asset_materials={{"copper",{.8f,.35f,.05f},.2f}};
 const auto asset=aibs::import_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl copper\nf 1 2 3\n",asset_materials,aibs::new_uuid(),"Installed SDK triangle");
 const auto cooked=aibs::encode_mesh_asset(asset);
 const auto decoded=aibs::decode_mesh_asset(cooked);
 aibs::SceneMesh imported;
 aibs::append_asset_mesh(imported,decoded,{0,0,0});
 if(imported.vertices.size()!=3 || imported.vertices.front().color!=asset_materials.front().base_color ||
    aibs::asset_sha256(cooked).size()!=64 || aibs::encode_mesh_asset(decoded)!=cooked) return 1;
 if (aibs::make_motherboard_scene().vertices.empty()) return 1;
 aibs::SceneSnapshot scene{aibs::new_uuid(), 0, {}};
 if (!aibs::mesh_from_snapshot(scene).vertices.empty()) return 1;
 aibs::CreatorSession sample(aibs::first_boot_schema(), "external-game-module", "main");
 if (!aibs::seed_first_boot(sample).ok || aibs::mesh_from_snapshot(aibs::first_boot_scene(sample)).vertices.empty()) return 1;
 {
  auto definition=aibs::FirstBootContent::from_template(sample).definition();definition.format_version=2;
  const auto content=aibs::FirstBootContent::create(definition);
  const auto bytes=aibs::first_boot_content_encode(content);
  if(aibs::first_boot_content_decode(bytes).definition().format_version!=2) return 1;
  const aibs::PlacedAssetVisuals visual(content,{});
  if(visual.placement_count()!=0 || visual.mesh(aibs::first_boot_scene(sample)).vertices.empty()) return 1;
 }
 aibs::PlayerController walker(aibs::first_boot_scene(sample), {-32,0.2f,-25});
 for (int i=0; i<120; ++i) walker.update({},1.0/60);
 if (!walker.state().grounded) return 1;
 aibs::CreatorSession course(aibs::movement_course_schema(),"external-course","main");
 if (!aibs::seed_movement_course(course).ok || aibs::mesh_from_snapshot(aibs::movement_course_scene(course)).vertices.empty()) return 1;
 const auto core=sample.world().at("core-01").persistent_id;
 aibs::GameplayScope scope{"external-game-module",sample.world_id(),"main",aibs::new_uuid()};
 const auto game_baseline=aibs::durable_first_boot_baseline(sample);
 const aibs::GameplayStoreRecovery game_view{scope,game_baseline.revision,game_baseline.sequence,game_baseline.components};
 aibs::durable_first_boot_validate(game_view);
 if(game_view.revision!=0 || game_view.sequence!=0 || aibs::durable_first_boot_world(game_view)!=sample.world() ||
    aibs::mesh_from_snapshot(aibs::durable_first_boot_scene(game_view)).vertices.size()!=
    aibs::mesh_from_snapshot(aibs::first_boot_scene(sample)).vertices.size()) return 1;
 {
  aibs::first_boot_chapter_preflight(game_view);
  const auto install=aibs::first_boot_chapter_install(game_view,"sdk.chapter.install");
  if(!install || install->schema_version!=2 || install->deltas.size()!=6 || aibs::first_boot_chapter_schemas().size()!=5) return 1;
  auto chapter=game_view;chapter.revision=install->revision;chapter.sequence=install->events.back().sequence;
  for(const auto& delta:install->deltas) chapter.components.push_back(delta.component);
  aibs::first_boot_chapter_rules(game_view,chapter,*install,{});
  if(aibs::mesh_from_snapshot(aibs::first_boot_chapter_scene(chapter)).vertices.empty()) return 1;
  auto bs=aibs::first_boot_chapter_player(chapter);
  for(int i=0;i<60;++i) bs.update({},1.0/60);
  if(!bs.state().grounded) return 1;
 }
 aibs::GameplayAdmission admission(scope,{{"sample.Power",1,{{"capacity",aibs::GameplayValueKind::number,true,0,100}}}});
 aibs::GameplayChangeBatch batch;
 batch.scope=scope;batch.operation_id="sdk.repair";batch.revision=1;
 batch.deltas.push_back({aibs::ComponentAction::upsert,{core,"sample.Power",1,{{"capacity",100.0}}}});
 aibs::SemanticEvent event;
 event.event_id=aibs::new_uuid();event.scope=scope;event.sequence=1;event.operation_id=batch.operation_id;
 event.subject_ids={core};event.source_revision=1;event.provenance={aibs::GameplayProvenance::gameplay_rule,"sdk.repair.v1"};
 event.payload=aibs::RepairOutcome{core,0,100};batch.events.push_back(event);
 const auto admitted=admission.reserve(batch,[&](const std::string& id){return id==core;});
 if(admitted.status!=aibs::AdmissionStatus::accepted ||
    admission.state().durable_revision!=0 || !admission.next_visible()) return 1;
 if(!admission.acknowledge({scope,batch.operation_id,1,aibs::GameplayPhase::world_or_document_applied}).ok) return 1;
 const auto database=std::filesystem::temp_directory_path()/("aibs-sdk-store-"+aibs::new_uuid()+".db");
 {
  aibs::GameplaySaveWorker worker(database,scope,{{"sample.Power",1,{{"capacity",aibs::GameplayValueKind::number,true,0,100}}}});
  if(worker.submit(admitted.batch).status!=aibs::WorkerSubmitStatus::accepted || !worker.close().ok) return 1;
  const auto completion=worker.poll();
  if(!completion || completion->result.status!=aibs::GameplayStoreStatus::committed ||
     !admission.acknowledge(completion->result.acknowledgement).ok || admission.state().durable_revision!=1) return 1;
 }
 {
  aibs::GameplayStore reopened(database,scope,{{"sample.Power",1,{{"capacity",aibs::GameplayValueKind::number,true,0,100}}}});
  if(reopened.recover().revision!=1 || !reopened.lookup_batch(batch.operation_id) || !reopened.verify().ok) return 1;
 }
 {
  aibs::GameplayWorld runtime(database,scope,{{"sample.Power",1,{{"capacity",aibs::GameplayValueKind::number,true,0,100}}}});
  auto route=batch;route.operation_id="sdk.route";route.expected_revision=1;route.revision=2;route.deltas.clear();
  auto& outcome=route.events.front();outcome.event_id=aibs::new_uuid();outcome.sequence=2;
  outcome.operation_id=route.operation_id;outcome.source_revision=2;outcome.provenance.source_id="sdk.route.v1";
  outcome.payload=aibs::RouteOutcome{core,true};
  const auto prepared=runtime.prepare(route);
  if(prepared.status!=aibs::GameplayPrepareStatus::prepared || !runtime.publish(prepared.change).ok ||
     runtime.state().durable_revision!=1 || !runtime.close().ok || !runtime.state().saved ||
     runtime.state().durable_revision!=2 || runtime.read_batches(0).size()!=2) return 1;
 }
 {
  const std::vector<aibs::ComponentSchema> old_schemas={{"sample.Power",1,{{"capacity",aibs::GameplayValueKind::number,true,0,100}}}};
  auto extended=old_schemas;extended.push_back({"sample.Door",1,{{"open",aibs::GameplayValueKind::boolean},{"stage",aibs::GameplayValueKind::text}}});
  const auto migration=aibs::GameplayStore::extend_registry(database,scope,old_schemas,extended,"sdk.add-door",2,2);
  if(migration.status!=aibs::GameplayStoreStatus::committed || aibs::GameplayStore::inspect_registry(database,scope).size()!=2) return 1;
  aibs::GameplayWorld runtime(database,scope,extended);
  aibs::GameplayChangeBatch mechanism;mechanism.schema_version=2;mechanism.scope=scope;mechanism.operation_id="sdk.open-door";mechanism.expected_revision=2;mechanism.revision=3;
  mechanism.deltas.push_back({aibs::ComponentAction::upsert,{core,"sample.Door",1,{{"open",true},{"stage",std::string("hub")}}}});
  auto changed=event;changed.event_id=aibs::new_uuid();changed.payload_version=2;changed.sequence=3;changed.operation_id=mechanism.operation_id;changed.source_revision=3;
  changed.payload=aibs::MechanismOutcome{core,"open",false,true};mechanism.events.push_back(changed);
  changed.event_id=aibs::new_uuid();changed.sequence=4;changed.payload=aibs::QuestOutcome{core,aibs::QuestState::unavailable,aibs::QuestState::active,"","hub"};mechanism.events.push_back(changed);
  const auto prepared=runtime.prepare(mechanism);
  if(prepared.status!=aibs::GameplayPrepareStatus::prepared || !runtime.publish(prepared.change).ok || !runtime.close().ok || runtime.state().durable_sequence!=4) return 1;
  aibs::GameplayStore reopened(database,scope,extended);
  if(!reopened.verify().ok || reopened.recover().revision!=3 || !reopened.lookup_batch(mechanism.operation_id) ||
     !aibs::gameplay_batch_exact(*reopened.lookup_batch(mechanism.operation_id),mechanism) || !reopened.lookup_batch(batch.operation_id)) return 1;
 }
 std::filesystem::remove(database);
 auto wal=database;wal+=L"-wal";std::filesystem::remove(wal);
 auto shm=database;shm+=L"-shm";std::filesystem::remove(shm);
 aibs::Camera camera;
 if (camera.view_projection(16.0f / 9.0f).empty()) return 1;
 aibs::SchemaRegistry registry;
 if (!registry.add({"capacity", 0, 100})) return 1;
 aibs::CreatorSession session(registry, "external-sdk-project", "main");
 if (!session.apply({"create", 0, {aibs::Create{{"core", "External Core", {{"capacity", 50}}}}}}).ok) return 1;
 aibs::FixedStep clock;
 if (clock.advance(aibs::FixedStep::tick_seconds) != 1) return 1;
 const auto path = std::filesystem::temp_directory_path() / ("aibs-sdk-" + aibs::new_uuid() + ".aibs");
 if (!aibs::CheckpointStore::save(path, session).ok) return 1;
 aibs::CreatorSession restored(registry, "external-sdk-project", "main");
 if (!aibs::CheckpointStore::load(path, restored).ok || restored.world() != session.world() || restored.memory().events() != session.memory().events()) return 1;
 aibs::CreatorHost creator(std::move(restored));
 const auto authored = creator.snapshot();
 const aibs::Transaction edit{"sdk.creator.edit", authored->revision,
  {aibs::SetField{"core", "capacity", 75, authored->world.at("core").persistent_id}}, "SDK creator edit"};
 const auto preview = creator.preview(authored->scope, edit);
 if (preview.status != aibs::CreatorHostStatus::prepared || !preview.change || !preview.change->dependencies().save.compatible ||
     creator.snapshot() != authored || creator.apply(preview.change).status != aibs::CreatorHostStatus::applied ||
     creator.save(path).status != aibs::CreatorHostStatus::saved) return 1;
 auto reopened_creator = aibs::CreatorHost::open(path, registry, "external-sdk-project", "main");
 if (reopened_creator.snapshot()->scope != authored->scope || reopened_creator.snapshot()->world.at("core").fields.at("capacity") != 75 ||
     reopened_creator.apply(authored->scope, edit).status != aibs::CreatorHostStatus::duplicate) return 1;
 std::filesystem::remove(path);
 auto lock = path; lock += L".lock"; std::filesystem::remove(lock);
 aibs::CreatorSession content_source(aibs::first_boot_schema(),"sdk-content","main");
 if(!aibs::seed_first_boot(content_source).ok)return 1;
 const auto content=aibs::FirstBootContent::from_template(content_source);
 auto modern_definition=content.definition();modern_definition.format_version=3;
 modern_definition.asset_profile=aibs::AssetContentProfile::warm_beginning;modern_definition.exposure=1.5f;
 aibs::FirstBootLightDefinition reserve;reserve.entity_id=aibs::new_uuid();reserve.name="SDK warm reserve";
 reserve.position={-32,3,-25};reserve.color={1,.5f,.2f};reserve.intensity=2;reserve.radius=12;
 auto restored_light=reserve;restored_light.entity_id=aibs::new_uuid();restored_light.name="SDK restored circuit";
 restored_light.power=aibs::FirstBootLightPower::restored;
 modern_definition.lights={reserve,restored_light};
 const auto modern_content=aibs::FirstBootContent::create(modern_definition);
 const auto modern_roundtrip=aibs::first_boot_content_decode(aibs::first_boot_content_encode(modern_content));
 if(modern_roundtrip.definition().format_version!=3||modern_roundtrip.definition().asset_profile!=aibs::AssetContentProfile::warm_beginning||modern_roundtrip.definition().exposure!=1.5f)return 1;
 {
  const auto baseline=aibs::first_boot_content_baseline(modern_roundtrip);
  const aibs::GameplayStoreRecovery runtime{{"sdk-content",modern_roundtrip.definition().world_id,"main",aibs::new_uuid(),aibs::GameplayContext::temporary_play},baseline.revision,baseline.sequence,baseline.components};
  const auto saved_components=runtime.components;
  const auto supply=aibs::first_boot_content_supply(runtime,modern_roundtrip);
  const auto lighting=aibs::first_boot_content_lighting(runtime,modern_roundtrip);
  // External callers get only reserve illumination before an actual repair.
  // Projection must preserve the authoritative components and history.
  if(supply.main||supply.bypass||!lighting.enabled||lighting.points.size()!=1||lighting.directional||
     lighting.exposure!=1.5f||lighting.points.front().color!=reserve.color||
     runtime.components!=saved_components||runtime.revision!=baseline.revision||runtime.sequence!=baseline.sequence)return 1;
  aibs::validate_scene_lighting(lighting);
  const auto constants=aibs::pack_scene_lighting(lighting);
  if(constants.controls[0]!=1||constants.controls[1]!=1||constants.controls[2]!=0||
     constants.points[0].position_radius[3]!=reserve.radius||constants.ambient_exposure[3]!=1.5f)return 1;
  const auto lit=aibs::evaluate_scene_lighting(lighting,{-32,0,-25},{0,1,0},{.25f,.25f,.25f},0);
  if(!std::isfinite(lit.x)||!std::isfinite(lit.y)||!std::isfinite(lit.z)||
     !(lit.x>lit.y&&lit.y>lit.z&&lit.z>0&&lit.x<=1))return 1;
  auto invalid=lighting;invalid.exposure=0;
  bool rejected=false;try{aibs::validate_scene_lighting(invalid);}catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)return 1;
 }
 {
  // A separate compatible branch exercises optional companion exports without
  // changing the lighting-only v3 registry or its existing checks above.
  auto companion_definition=content.definition();companion_definition.format_version=3;companion_definition.asset_profile=aibs::AssetContentProfile::warm_beginning;
  aibs::FirstBootCompanionBinding adam;adam.entity_id=aibs::new_uuid();adam.name="SDK Adam memory";adam.spawn=companion_definition.jenison_returns.front();adam.spawn.x+=2;companion_definition.companions.push_back(adam);
  const auto companion_content=aibs::FirstBootContent::create(companion_definition);
  {
   auto bound_definition=companion_definition;bound_definition.companions.front().model=sdk_character_reference;
   const auto bound=aibs::FirstBootContent::create(bound_definition);const auto dependencies=aibs::first_boot_content_dependencies(bound);
   if(dependencies.size()!=1||dependencies.front().kind!=aibs::FirstBootDependencyKind::character||dependencies.front().reference!=sdk_character_reference)return 1;
   const auto complete=aibs::load_first_boot_content_assets(bound,sdk_character_store);
   if(complete.assets.size()!=1||complete.encoded_bytes==0||complete.decoded_bytes==0||!std::holds_alternative<aibs::CharacterAsset>(complete.require(sdk_character_reference,aibs::FirstBootDependencyKind::character).payload))return 1;
  }
  const auto companion_schemas=aibs::first_boot_content_schemas(companion_content);
  if(companion_schemas.size()!=aibs::first_boot_content_schemas(modern_roundtrip).size()+1)return 1;
  const aibs::GameplayScope companion_scope{"sdk-companion",companion_content.definition().world_id,"main",aibs::new_uuid(),aibs::GameplayContext::temporary_play};
  const auto companion_database=std::filesystem::temp_directory_path()/("aibs-sdk-companion-"+aibs::new_uuid()+".sqlite");
  {aibs::GameplayStore seed(companion_database,companion_scope,companion_schemas);if(seed.seed(aibs::first_boot_content_baseline(companion_content)).status!=aibs::GameplayStoreStatus::committed)return 1;}
  aibs::GuideIntentRecord saved_wait;
  {
   aibs::GameplayWorld world(companion_database,companion_scope,companion_schemas);aibs::CompanionRuntime guide(*world.snapshot(),companion_content);
   if(!guide.state().guide||guide.state().recall_required||guide.state().saved.intent!=aibs::GuideIntent::follow)return 1;
   aibs::GroundedCharacter bs(aibs::first_boot_content_scene(*world.snapshot(),companion_content),companion_content.definition().jenison_returns.front());
   for(int tick=0;tick<32;++tick)(void)bs.advance({},1.0/60);
   if(!bs.state().grounded)return 1;
   const aibs::CompanionActor actor{{bs.state().feet,true,guide.state().scene_revision},false,false,32};
   const auto before=world.snapshot();auto choice=guide.prepare_choice(*before,aibs::CompanionAction::wait,actor,{},"sdk.companion.wait");
   if(!choice||!guide.ready(*choice)||choice->batch().schema_version!=3||choice->batch().events.size()!=1||!std::holds_alternative<aibs::CompanionOutcome>(choice->batch().events.front().payload))return 1;
   const auto prepared=world.prepare(choice->batch(),[&](const auto& prior,const auto& after,const auto& batch){guide.validate_choice(*choice,prior,after,batch,actor);});
   if(prepared.status!=aibs::GameplayPrepareStatus::prepared||world.snapshot()!=before||guide.state().saved.intent!=aibs::GuideIntent::follow)return 1;
   if(!world.publish(prepared.change).ok||!guide.publish(std::move(choice))||guide.state().saved.intent!=aibs::GuideIntent::wait)return 1;
   saved_wait=guide.state().saved;if(!world.close().ok||!world.state().saved||world.state().durable_revision!=1||world.state().durable_sequence!=1)return 1;
  }
  {
   aibs::GameplayStore reopened(companion_database,companion_scope,companion_schemas);if(!reopened.verify().ok)return 1;
   aibs::CompanionRuntime restored_guide(reopened.recover(),companion_content);
   if(!restored_guide.state().guide||restored_guide.state().recall_required||restored_guide.state().saved.intent!=aibs::GuideIntent::wait||restored_guide.state().saved.waiting_anchor!=saved_wait.waiting_anchor)return 1;
  }
  std::filesystem::remove(companion_database);auto companion_wal=companion_database;companion_wal+=L"-wal";std::filesystem::remove(companion_wal);auto companion_shm=companion_database;companion_shm+=L"-shm";std::filesystem::remove(companion_shm);
 }
 const auto content_baseline=aibs::first_boot_content_baseline(content);
 aibs::GameplayStoreRecovery content_runtime{{"sdk-content",content.definition().world_id,"main",aibs::new_uuid(),aibs::GameplayContext::temporary_play},0,0,content_baseline.components};
 aibs::first_boot_content_validate(content_runtime,content);
 if(aibs::first_boot_content_decode(aibs::first_boot_content_encode(content)).fingerprint()!=content.fingerprint())return 1;
 aibs::ContentAuthoringHost content_editor(content,"sdk-content","main");const auto editor_head=content_editor.snapshot();
 const aibs::ChapterViewportSnapshot chapter_projection{aibs::new_uuid(),editor_head->scope,"","",47,content};
 const auto projected_chapter=aibs::chapter_viewport_scene(chapter_projection);
 if(projected_chapter.world_id!=content.definition().world_id||projected_chapter.revision!=47||projected_chapter.objects.empty())return 1;
 const aibs::ContentEditRequest authored_cue{"sdk-authored-cue",editor_head->revision,editor_head->content.fingerprint(),"SDK authored guidance",{aibs::ContentSetField{content.definition().definition_id,"hint.adam.danger",std::string("Authored Adam hint: Start with the safe edge.")}}};
 if(content_editor.apply(editor_head->scope,authored_cue).status!=aibs::ContentAuthoringStatus::applied)return 1;
 const auto author_dir=std::filesystem::temp_directory_path()/("aibs-sdk-author-"+aibs::new_uuid());std::filesystem::create_directory(author_dir);const auto author_file=author_dir/"chapter.aiba";
 if(content_editor.save(author_file).status!=aibs::ContentAuthoringStatus::saved)return 1;
 auto restored_editor=aibs::ContentAuthoringHost::open(author_file,"sdk-content","main");
 if(restored_editor.apply(editor_head->scope,authored_cue).status!=aibs::ContentAuthoringStatus::duplicate||restored_editor.snapshot()->undo_depth!=1)return 1;
 std::filesystem::remove(author_file);auto author_lock=author_file;author_lock+=L".lock";std::filesystem::remove(author_lock);std::filesystem::remove(author_dir);
 for(const auto& directory:{sdk_character_root/"pack",sdk_character_store/sdk_character_reference.pack_sha256}){for(const auto& filename:{sdk_character_reference.asset_sha256+".aibchar",std::string("catalog.aibcat"),std::string("LICENSE.txt"),std::string("provenance.json")})std::filesystem::remove(directory/filename);std::filesystem::remove(directory);}std::filesystem::remove(sdk_character_store);std::filesystem::remove(sdk_character_root);
 std::cout << "Installed AIBS SDK linked and executed successfully, including immutable chapter content, authored lighting, indexed character sampling, bounded character import/codec/typed closure and admitted companion choices/restart, bounded audio codec, owned memory/caption controller and warm opening factory/inspection authoring.\n";
 return 0;
}
