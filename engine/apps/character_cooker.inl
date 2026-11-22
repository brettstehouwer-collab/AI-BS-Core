// Included inside the cooker's private namespace after the existing immutable
// publication helpers. No source URI ever becomes an implicit filesystem read.
std::string character_fields(const aibs::CharacterAsset& character,std::size_t decoded_bytes){
 std::size_t images=0;for(const auto& image:character.images)images+=aibs::image_resident_bytes(image);
 return ",\"name\":"+json_quote(character.name)+",\"triangles\":"+std::to_string(character.mesh.indices.size()/3)+
  ",\"materials\":"+std::to_string(character.materials.size())+",\"kind\":\"character\",\"image_count\":"+std::to_string(character.images.size())+
  ",\"decoded_image_bytes\":"+std::to_string(images)+",\"decoded_bytes\":"+std::to_string(decoded_bytes)+
  ",\"joint_count\":"+std::to_string(character.mesh.joints.size())+",\"clip_count\":"+std::to_string(character.mesh.clips.size())+
  ",\"vertices\":"+std::to_string(character.mesh.vertices.size());
}
std::string typed_fields(const aibs::StoredTypedAsset& asset){
 if(const auto* character=std::get_if<aibs::CharacterAsset>(&asset.payload))return character_fields(*character,asset.decoded_bytes);
 const auto* surface=std::get_if<aibs::SurfaceMeshAsset>(&asset.payload);
 const auto& mesh=surface?surface->geometry:std::get<aibs::MeshAsset>(asset.payload);
 std::size_t images=0,image_bytes=0;if(surface){images=surface->images.size();for(const auto& image:surface->images)image_bytes+=aibs::image_resident_bytes(image);}
 return ",\"name\":"+json_quote(mesh.name)+",\"triangles\":"+std::to_string(mesh.indices.size()/3)+
  ",\"materials\":"+std::to_string(mesh.materials.size())+",\"kind\":"+json_quote(surface?"surface":"mesh")+
  ",\"image_count\":"+std::to_string(images)+",\"decoded_image_bytes\":"+std::to_string(image_bytes)+
  ",\"decoded_bytes\":"+std::to_string(asset.decoded_bytes);
}
std::uint32_t character_option_integer(std::wstring_view value){
 const auto token=utf8(std::wstring(value));std::uint32_t result=0;const auto parsed=std::from_chars(token.data(),token.data()+token.size(),result);
 require(parsed.ec==std::errc{}&&parsed.ptr==token.data()+token.size(),"Character numeric options require complete unsigned integers");return result;
}
int cook_character(int argc,wchar_t** argv){
 const std::set<std::wstring> allowed{L"--source",L"--asset-id",L"--name",L"--license",L"--output",L"--bake-rate"};
 std::map<std::wstring,std::wstring> values;std::map<std::string,fs::path> resource_paths;aibs::CharacterImportOptions options;
 for(int index=2;index<argc;++index){const std::wstring key(argv[index]);
  if(key==L"--clip"){
   require(index+3<argc&&options.clips.size()<aibs::character_maximum_clips,"Character clip requires INDEX NAME loop|once; at most8 mappings");
   const auto source_index=character_option_integer(argv[index+1]);const auto name=utf8(argv[index+2]);const std::wstring_view mode(argv[index+3]);
   require(mode==L"loop"||mode==L"once","Character clip playback must explicitly be loop or once");
   options.clips.push_back({source_index,name,mode==L"loop"});index+=3;
  }else if(key==L"--resource"){
   require(index+2<argc&&resource_paths.size()<96,"Character resource requires explicit URI FILE; at most96 resources");
   const auto uri=utf8(argv[index+1]);require(resource_paths.emplace(uri,fs::path(argv[index+2])).second,"Duplicate character resource URI");index+=2;
  }else{
   require(allowed.contains(key)&&index+1<argc&&values.emplace(key,argv[index+1]).second,"Unknown, duplicate or incomplete character cooker option");++index;
  }
 }
 for(const auto* key:{L"--source",L"--asset-id",L"--name",L"--license",L"--output"})require(values.contains(key),"Character cooker requires source, asset-id, name, license and output");
 options.asset_id=utf8(values.at(L"--asset-id"));options.name=utf8(values.at(L"--name"));if(values.contains(L"--bake-rate"))options.bake_rate=character_option_integer(values.at(L"--bake-rate"));
 require(options.bake_rate>=1&&options.bake_rate<=60,"Character bake rate must be1..60");
 const auto output=fs::absolute(fs::path(values.at(L"--output"))).lexically_normal();
 require(output.has_filename()&&!fs::exists(output),"Character output must be a fresh directory; existing paths are preserved");
 const auto parent=plain_path(output.parent_path());require(fs::is_directory(parent),"Character output parent must be an existing unredirected directory");
 const auto source=read_bounded(fs::path(values.at(L"--source")),aibs::character_asset_max_input_bytes);
 const auto license=read_bounded(fs::path(values.at(L"--license")),text_limit);
 require(!license.empty()&&std::none_of(license.begin(),license.end(),[](std::byte c){return c==std::byte{};})&&std::any_of(license.begin(),license.end(),[](std::byte c){return std::to_integer<unsigned char>(c)>32;}),"An explicit nonempty UTF-8 license/rights declaration is required");(void)json_quote(text(license));
 std::map<std::string,Bytes> owned_resources;std::size_t source_bytes=source.size();
 for(const auto& [uri,path]:resource_paths){auto data=read_bounded(path,aibs::character_asset_max_input_bytes-source_bytes);require(!data.empty(),"Character resource file is empty");source_bytes+=data.size();owned_resources.emplace(uri,std::move(data));}
 std::vector<aibs::GltfInputResource> resources;resources.reserve(owned_resources.size());
 std::string resource_records="[";for(const auto& [uri,data]:owned_resources){resources.push_back({uri,data});if(resource_records.size()>1)resource_records+=',';auto record=input_record(data);record.erase(record.begin());resource_records+="{\"uri\":"+json_quote(uri)+","+record;}resource_records+=']';
 aibs::CharacterImportDiagnostics diagnostics;const auto asset=aibs::import_character_gltf(source,resources,options,&diagnostics);
 const auto encoded=aibs::encode_character_asset(asset);const auto digest=aibs::asset_sha256(encoded),filename=digest+".aibchar";
 const auto catalog="AIBCAT 2\ncharacter "+asset.asset_id+" "+digest+" "+filename+"\n";
 std::string clip_records="[";for(const auto& clip:options.clips){if(clip_records.size()>1)clip_records+=',';clip_records+="{\"source_animation\":"+std::to_string(clip.source_animation)+",\"name\":"+json_quote(clip.name)+",\"looping\":"+(clip.looping?"true":"false")+"}";}clip_records+=']';
 std::string joint_map="[";for(auto joint:diagnostics.source_skin_to_cooked){if(joint_map.size()>1)joint_map+=',';joint_map+=std::to_string(joint);}joint_map+=']';
 std::ostringstream intervals;intervals.imbue(std::locale::classic());intervals<<std::setprecision(17)<<'[';for(std::size_t i=0;i<diagnostics.baked_intervals_seconds.size();++i){const auto value=diagnostics.baked_intervals_seconds[i];require(std::isfinite(value)&&value>0,"Importer returned invalid uniform bake interval");if(i)intervals<<',';intervals<<value;}intervals<<']';
 const auto cost=aibs::character_asset_cost(asset);
 const auto provenance="{\n  \"schema_version\":2,\n  \"asset_id\":"+json_quote(asset.asset_id)+",\n  \"name\":"+json_quote(asset.name)+
  ",\n  \"source\":"+input_record(source)+",\n  \"resources\":"+resource_records+",\n  \"source_manifest\":{\"format\":\"AIBS_GLTF_SOURCE 1\",\"sha256\":"+json_quote(asset.source_sha256)+"},"+
  "\n  \"license\":"+input_record(license)+",\n  \"license_review\":\"Supplied UTF-8 declaration copied verbatim; ownership/permission not inferred\","+
  "\n  \"importer\":{\"name\":\"aibs-gltf-character\",\"format_version\":2,\"cgltf_version\":\"1.15\",\"commit\":\"360db1a95480fe102ae9c69b27c5d101167ff5ba\",\"header_sha256\":\"e378a21c084bf1f288bb799de827bb26906efb024255f1ecf1705ea13f11c6ec\",\"license\":\"MIT\",\"license_notice\":\"Full cgltf MIT notice is distributed with the engine dependency and installed SDK licenses\"},"+
  "\n  \"options\":{\"units\":\"meters\",\"up_axis\":\"+Y\",\"forward_axis\":\"+Z\",\"axis_conversion\":\"right-handed glTF to left-handed engine by X reflection\",\"bind_shape\":\"coherent joint-bind times inverse-bind; skinned mesh-node transform is ignored\",\"bake_rate\":"+std::to_string(options.bake_rate)+",\"clips\":"+clip_records+",\"source_skin_to_cooked\":"+joint_map+",\"baked_intervals_seconds\":"+intervals.str()+",\"interpolation\":\"LINEAR TRS baked uniformly including endpoints; per-channel clamping\",\"opaque_alpha\":\"source alpha ignored and set to255 before linear-light sRGB mip generation; hologram opacity belongs to runtime instance\",\"external_resources\":\"exact explicit URI map only; no filesystem or network fallback\",\"weight_policy\":\"at most four influences; bounded float/UNORM quantization normalization only\"},"+
  "\n  \"import_memory\":{\"parser_peak_bytes\":"+std::to_string(diagnostics.parser_peak_bytes)+",\"engine_owned_live_upper_bound_bytes\":"+std::to_string(diagnostics.engine_owned_live_upper_bound_bytes)+",\"scope\":\"private parser and conservative engine-owned accounting; not WIC, driver or whole-process memory\"},"+
  "\n  \"cooked\":{\"file\":"+json_quote(filename)+",\"sha256\":"+json_quote(digest)+",\"bytes\":"+std::to_string(encoded.size())+",\"decoded_bytes\":"+std::to_string(cost.decoded_bytes)+"}\n}\n";
 const auto success="{\"status\":\"passed\",\"asset_id\":"+json_quote(asset.asset_id)+",\"sha256\":"+json_quote(digest)+",\"output_root\":"+json_quote(utf8(output.wstring()))+character_fields(asset,cost.decoded_bytes)+"}\n";
 require(provenance.size()<=text_limit&&success.size()<=text_limit,"Character provenance/receipt exceeds64KiB");
 Stage stage(parent,output.filename());stage.add(filename,encoded);stage.add("catalog.aibcat",bytes(catalog));stage.add("LICENSE.txt",license);stage.add("provenance.json",bytes(provenance));
 const auto checked=aibs::inspect_asset_pack(stage.directory);require(checked.kind==aibs::StoredAssetKind::character_v2&&checked.reference.asset_id==asset.asset_id&&checked.reference.asset_sha256==digest,"Cooked character staged pack failed independent typed inspection");
 stage.publish(output);std::cout<<success;return 0;
}
