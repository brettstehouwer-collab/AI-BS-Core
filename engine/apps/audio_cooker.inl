#include "reviewed_audio_captions.inl"
// Included after immutable publication helpers and character typed fields.
// Complete source WAV is read once; only owned PCM/metadata enter the pack.
std::string audio_digest(std::span<const std::byte> body){
 require(body.size()<=aibs::asset_store_maximum_audio_pack_bytes,"Audio CLI hash exceeds50MiB bound");
 struct Algorithm{BCRYPT_ALG_HANDLE value=nullptr;~Algorithm(){if(value)BCryptCloseAlgorithmProvider(value,0);}} algorithm;
 if(BCryptOpenAlgorithmProvider(&algorithm.value,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)throw std::runtime_error("Audio CLI SHA256 provider unavailable");
 std::array<unsigned char,32> value{};
 if(BCryptHash(algorithm.value,nullptr,0,const_cast<PUCHAR>(reinterpret_cast<const unsigned char*>(body.data())),static_cast<ULONG>(body.size()),value.data(),static_cast<ULONG>(value.size()))<0)throw std::runtime_error("Audio CLI SHA256 computation failed");
 constexpr char hex[]="0123456789abcdef";std::string result;result.reserve(64);for(const auto c:value){result.push_back(hex[c>>4]);result.push_back(hex[c&15]);}return result;
}
fs::path audio_native_path(const fs::path& input){
 const auto path=fs::absolute(input).lexically_normal();const auto& value=path.native();
 require(value.size()<=32760,"Audio source/output path exceeds Windows length bound");
 if(value.starts_with(L"\\\\?\\"))return path;
 return fs::path(value.starts_with(L"\\\\")?L"\\\\?\\UNC\\"+value.substr(2):L"\\\\?\\"+value);
}
Bytes audio_read_bounded(const fs::path& source,std::size_t maximum){
 const auto path=plain_store_path(source);Handle file;
 file.value=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
 require(file.value!=INVALID_HANDLE_VALUE,"Could not open regular audio input");BY_HANDLE_FILE_INFORMATION info{};
 require(GetFileInformationByHandle(file.value,&info)!=0&&(info.dwFileAttributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY))==0,"Audio input must be a regular unredirected file");
 LARGE_INTEGER size{};require(GetFileSizeEx(file.value,&size)!=0&&size.QuadPart>=0&&static_cast<unsigned long long>(size.QuadPart)<=maximum,"Audio input exceeds bounded source profile");
 Bytes result(static_cast<std::size_t>(size.QuadPart));std::size_t offset=0;
 while(offset<result.size()){const auto wanted=static_cast<DWORD>(std::min<std::size_t>(1024u*1024u,result.size()-offset));DWORD received=0;require(ReadFile(file.value,result.data()+offset,wanted,&received,nullptr)!=0&&received==wanted,"Audio source changed or could not be read");offset+=received;}
 LARGE_INTEGER final_size{};require(GetFileSizeEx(file.value,&final_size)!=0&&final_size.QuadPart==size.QuadPart,"Audio source length changed while reading");return result;
}
struct AudioStage:Stage{
 using Stage::Stage;
 void add(const std::string& name,const Bytes& value){
  const auto path=directory/name;owned_files.push_back(path);write_new(path,value);
  require(audio_read_bounded(path,value.size())==value,"Audio staging readback differs");
 }
};
std::string audio_input_record(const Bytes& source){return "{\"sha256\":"+json_quote(audio_digest(source))+",\"bytes\":"+std::to_string(source.size())+"}";}
std::string audio_fields(const aibs::AudioAsset& asset,std::size_t decoded){
 const auto cost=aibs::audio_asset_cost(asset);
 return ",\"name\":"+json_quote(asset.name)+",\"kind\":\"audio\",\"sample_rate\":"+std::to_string(asset.sample_rate)+
  ",\"channels\":"+std::to_string(asset.channels)+",\"bits_per_sample\":16,\"frame_count\":"+std::to_string(asset.frame_count)+
  ",\"pcm_bytes\":"+std::to_string(asset.pcm.size())+",\"decoded_bytes\":"+std::to_string(decoded)+
  ",\"payload_bytes\":"+std::to_string(cost.payload_bytes)+",\"caption_text_bytes\":"+std::to_string(cost.caption_text_bytes)+
  ",\"caption_count\":"+std::to_string(asset.captions.size())+",\"caption_review\":"+json_quote(asset.caption_review==aibs::AudioCaptionReview::checked?"checked":"draft");
}
std::string fields_for_asset(const aibs::StoredTypedAsset& asset){
 if(const auto* audio=std::get_if<aibs::AudioAsset>(&asset.payload))return audio_fields(*audio,asset.decoded_bytes);
 return typed_fields(asset);
}
int cook_audio(int argc,wchar_t** argv){
 const std::set<std::wstring> required{L"--source",L"--asset-id",L"--name",L"--license",L"--output"};
 auto allowed=required;allowed.insert(L"--captions-reviewed");
 std::map<std::wstring,std::wstring> options;
 for(int i=2;i<argc;++i){const std::wstring key(argv[i]);require(allowed.contains(key)&&i+1<argc&&options.emplace(key,argv[i+1]).second,"Unknown, duplicate or incomplete audio cooker option");++i;}
 for(const auto& key:required)require(options.contains(key),"Audio cooker requires source, asset-id, name, license and output");
 const auto output=fs::absolute(fs::path(options.at(L"--output"))).lexically_normal();
 require(output.has_filename()&&!fs::exists(audio_native_path(output)),"Audio output must be a fresh directory; existing paths are preserved");
 const auto parent=plain_store_path(output.parent_path());require(fs::is_directory(parent),"Audio output parent must be an existing plain directory");
 const auto source=audio_read_bounded(fs::path(options.at(L"--source")),aibs::audio_wav_maximum_input_bytes);
 const auto license=audio_read_bounded(fs::path(options.at(L"--license")),text_limit);
 require(!license.empty()&&std::none_of(license.begin(),license.end(),[](std::byte c){return c==std::byte{};})&&std::any_of(license.begin(),license.end(),[](std::byte c){return std::to_integer<unsigned char>(c)>32;}),"An explicit nonempty UTF-8 license/rights declaration is required");(void)json_quote(text(license));
 auto asset=aibs::import_pcm_wav(source,utf8(options.at(L"--asset-id")),utf8(options.at(L"--name")));
 require(asset.source_sha256==audio_digest(source),"Audio importer did not preserve entire source WAV hash");
 aibs_caption_tool::ReviewedAudioCaptions reviewed;Bytes caption_source;const bool has_review=options.contains(L"--captions-reviewed");
 if(has_review){caption_source=audio_read_bounded(fs::path(options.at(L"--captions-reviewed")),aibs_caption_tool::reviewed_caption_json_limit);reviewed=aibs_caption_tool::parse_reviewed_captions(text(caption_source),asset);asset.captions=std::move(reviewed.captions);asset.caption_review=aibs::AudioCaptionReview::checked;aibs::validate_audio_asset(asset);}
 const std::string caption_provenance=has_review?"\n  \"caption_review\":{\"schema_version\":1,\"caption_count\":"+std::to_string(asset.captions.size())+",\"sidecar_sha256\":"+json_quote(audio_digest(caption_source))+",\"source_caption_draft_sha256\":"+json_quote(reviewed.draft_sha256)+",\"review_export_sha256\":"+json_quote(reviewed.review_sha256)+",\"reviewer\":"+json_quote(reviewed.reviewer)+",\"reviewed_at_utc\":"+json_quote(reviewed.reviewed_at_utc)+",\"automatic_approval\":false,\"declaration\":"+json_quote(aibs_caption_tool::reviewed_caption_declaration)+"},":"";

 const auto encoded=aibs::encode_audio_asset(asset);const auto digest=audio_digest(encoded),filename=digest+".aibaud";const auto cost=aibs::audio_asset_cost(asset);
 const auto catalog="AIBCAT 2\naudio "+asset.asset_id+" "+digest+" "+filename+"\n";
 const auto provenance="{\n  \"schema_version\":2,\n  \"asset_id\":"+json_quote(asset.asset_id)+",\n  \"name\":"+json_quote(asset.name)+
  ",\n  \"source\":"+audio_input_record(source)+",\n  \"license\":"+input_record(license)+
  ",\n  \"license_review\":\"Supplied UTF-8 rights declaration copied verbatim; ownership and permission are not inferred\","+
  "\n  \"importer\":{\"name\":\"aibs-riff-wave-pcm16le\",\"format_version\":2},"+
  "\n  \"conversion\":{\"source_format\":\"RIFF/WAVE PCM16LE\",\"retained_sample_rate\":"+std::to_string(asset.sample_rate)+",\"retained_channels\":"+std::to_string(asset.channels)+",\"frame_count\":"+std::to_string(asset.frame_count)+",\"resampling\":false,\"channel_mixing\":false,\"pcm_bytes\":"+std::to_string(asset.pcm.size())+",\"pcm_sha256\":"+json_quote(audio_digest(asset.pcm))+",\"source_hash_scope\":\"Complete input WAV including skipped chunks and padding\",\"captions\":"+json_quote(has_review?"Checked captions from explicit human-supplied listening-review declarations; spoken wording not verified by cooker":"Empty draft; no transcript or checked-caption claim")+"},"+caption_provenance+
  "\n  \"cooked\":{\"file\":"+json_quote(filename)+",\"sha256\":"+json_quote(digest)+",\"bytes\":"+std::to_string(encoded.size())+",\"decoded_bytes\":"+std::to_string(cost.decoded_bytes)+"}\n}\n";
 const auto success="{\"status\":\"passed\",\"asset_id\":"+json_quote(asset.asset_id)+",\"sha256\":"+json_quote(digest)+",\"output_root\":"+json_quote(utf8(output.wstring()))+audio_fields(asset,cost.decoded_bytes)+"}\n";
 require(provenance.size()<=text_limit&&success.size()<=text_limit,"Audio provenance/receipt exceeds64KiB");
 AudioStage stage(parent,output.filename());stage.add(filename,encoded);stage.add("catalog.aibcat",bytes(catalog));stage.add("LICENSE.txt",license);stage.add("provenance.json",bytes(provenance));
 const auto inspected=aibs::inspect_asset_pack(stage.directory,aibs::asset_store_maximum_audio_pack_bytes);
 require(inspected.kind==aibs::StoredAssetKind::audio_v2&&inspected.reference.asset_id==asset.asset_id&&inspected.reference.asset_sha256==digest,"Cooked audio staged pack failed independent typed inspection");
 stage.publish(audio_native_path(output));std::cout<<success;return 0;
}
