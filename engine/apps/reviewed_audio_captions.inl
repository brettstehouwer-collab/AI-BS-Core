// Private cooker helper: included after Windows/audio assets and standard
// algorithm/array/charconv/map/set/string_view headers, inside the CLI namespace.
// No public ABI, arbitrary JSON DOM, recursive descent or file access.
namespace aibs_caption_tool {
inline constexpr std::size_t reviewed_caption_json_limit=1024u*1024u;
inline constexpr std::string_view reviewed_caption_declaration="Human-supplied listening review declarations validated; this tool did not listen or verify spoken wording.";
struct ReviewedAudioCaptions {
 std::vector<::aibs::AudioCaption> captions;
 std::string draft_sha256,review_sha256,reviewer,reviewed_at_utc;
};
namespace caption_detail {
inline void need(bool v,const char* message){if(!v)throw std::invalid_argument(message);}
inline std::wstring unicode(std::string_view value){
 need(value.size()<=reviewed_caption_json_limit,"Reviewed caption text exceeds bounded input");
 if(value.empty())return {};
 const auto n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value.data(),static_cast<int>(value.size()),nullptr,0);
 need(n>0,"Reviewed caption JSON text is not valid UTF8");std::wstring out(static_cast<std::size_t>(n),L'\0');
 need(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value.data(),static_cast<int>(value.size()),out.data(),n)==n,"Reviewed caption UTF8 conversion failed");return out;
}
inline bool space(wchar_t c){return(c>=9&&c<=13)||(c>=28&&c<=32)||c==0x85||c==0xa0||c==0x1680||(c>=0x2000&&c<=0x200a)||c==0x2028||c==0x2029||c==0x202f||c==0x205f||c==0x3000;}
inline void nonempty(std::string_view value,std::size_t maximum,bool single=false){
 need(!value.empty()&&value.size()<=maximum&&value.find('\0')==value.npos,"Reviewed caption text is empty/NUL/oversized");const auto wide=unicode(value);
 need(std::any_of(wide.begin(),wide.end(),[](wchar_t c){return !space(c);}),"Reviewed caption text is only whitespace");
 if(single)need(std::none_of(wide.begin(),wide.end(),[](wchar_t c){return c<32||c==127;}),"Reviewer must be a single line");
}
inline void hash(std::string_view v){need(v.size()==64&&std::all_of(v.begin(),v.end(),[](char c){return(c>='0'&&c<='9')||(c>='a'&&c<='f');}),"Reviewed caption provenance needs canonical SHA256");}
inline void utf8(std::string& out,std::uint32_t c){
 if(c<0x80)out.push_back(static_cast<char>(c));else if(c<0x800){out.push_back(static_cast<char>(0xc0|(c>>6)));out.push_back(static_cast<char>(0x80|(c&63)));}
 else if(c<0x10000){out.push_back(static_cast<char>(0xe0|(c>>12)));out.push_back(static_cast<char>(0x80|((c>>6)&63)));out.push_back(static_cast<char>(0x80|(c&63)));}
 else{out.push_back(static_cast<char>(0xf0|(c>>18)));out.push_back(static_cast<char>(0x80|((c>>12)&63)));out.push_back(static_cast<char>(0x80|((c>>6)&63)));out.push_back(static_cast<char>(0x80|(c&63)));}
}
struct Reader {
 std::string_view input;std::size_t position=0;
 void ws(){while(position<input.size()&&(input[position]==' '||input[position]=='\t'||input[position]=='\r'||input[position]=='\n'))++position;}
 bool take(char c){ws();if(position<input.size()&&input[position]==c){++position;return true;}return false;}
 void expect(char c){need(take(c),"Malformed reviewed caption JSON structure");}
 unsigned hex4(){need(input.size()-position>=4,"Truncated caption Unicode escape");unsigned n=0;for(unsigned i=0;i<4;++i){const auto c=input[position++];const auto d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:16;need(d<16,"Invalid caption Unicode escape");n=(n<<4)|static_cast<unsigned>(d);}return n;}
 std::string text(std::size_t limit){
  expect('"');std::string out;bool ended=false;
  while(position<input.size()){
   const auto c=static_cast<unsigned char>(input[position++]);if(c=='"'){ended=true;break;}need(c>=32,"Unescaped JSON control character");
   if(c!='\\')out.push_back(static_cast<char>(c));else{
    need(position<input.size(),"Truncated caption JSON escape");const char escaped=input[position++];
    switch(escaped){case '"':case '\\':case '/':out.push_back(escaped);break;case 'b':out.push_back('\b');break;case 'f':out.push_back('\f');break;case 'n':out.push_back('\n');break;case 'r':out.push_back('\r');break;case 't':out.push_back('\t');break;
    case 'u':{auto scalar=hex4();if(scalar>=0xd800&&scalar<=0xdbff){need(input.size()-position>=2&&input[position]=='\\'&&input[position+1]=='u',"Unpaired caption high surrogate");position+=2;const auto low=hex4();need(low>=0xdc00&&low<=0xdfff,"Invalid caption surrogate pair");scalar=0x10000+((scalar-0xd800)<<10)+(low-0xdc00);}else need(scalar<0xdc00||scalar>0xdfff,"Unpaired caption low surrogate");utf8(out,scalar);break;}
    default:need(false,"Unknown caption JSON escape");}
   }
   need(out.size()<=limit,"Reviewed caption JSON string exceeds bound");
  }
  need(ended,"Unterminated caption JSON string");(void)unicode(out);return out;
 }
 std::uint64_t integer(){
  ws();const auto start=position;while(position<input.size()&&input[position]>='0'&&input[position]<='9')++position;
  need(position>start&&(position-start==1||input[start]!='0'),"Reviewed caption field needs a strict unsigned integer");
  std::uint64_t value=0;const auto result=std::from_chars(input.data()+start,input.data()+position,value);
  need(result.ec==std::errc{}&&result.ptr==input.data()+position,"Reviewed caption integer overflows uint64");return value;
 }
 void no_automatic(){ws();need(input.substr(position,5)=="false","Reviewed captions cannot be automatically approved");position+=5;}
};
inline unsigned number(std::string_view value,std::size_t start,std::size_t length){unsigned n=0;need(start+length<=value.size(),"Review timestamp is truncated");for(std::size_t i=0;i<length;++i){const char c=value[start+i];need(c>='0'&&c<='9',"Review timestamp is not ISO8601 UTC");n=n*10+static_cast<unsigned>(c-'0');}return n;}
inline void timestamp(std::string_view value){
 need(value.size()>=20&&value.size()<=64&&value[4]=='-'&&value[7]=='-'&&(value[10]=='T'||value[10]==' ' )&&value[13]==':'&&value[16]==':',"Review timestamp needs explicit ISO8601 UTC");
 const auto year=number(value,0,4),month=number(value,5,2),day=number(value,8,2),hour=number(value,11,2),minute=number(value,14,2),second=number(value,17,2);
 need(year>0&&month>0&&month<=12&&hour<24&&minute<60&&second<60,"Review timestamp has invalid calendar/time fields");
 const std::array<unsigned,12> days{31,28,31,30,31,30,31,31,30,31,30,31};const auto max_day=days[month-1]+(month==2&&year%4==0&&(year%100!=0||year%400==0)?1u:0u);need(day>0&&day<=max_day,"Review timestamp has invalid date");
 std::size_t offset=19;if(offset<value.size()&&value[offset]=='.'){const auto first=++offset;while(offset<value.size()&&value[offset]>='0'&&value[offset]<='9')++offset;need(offset>first&&offset-first<=9,"Review timestamp fraction outside bound");}
 need(value.substr(offset)=="Z"||value.substr(offset)=="+00:00"||value.substr(offset)=="+00:00:00","Review timestamp must explicitly use UTC");
}
inline std::vector<::aibs::AudioCaption> captions(Reader& r){
 std::vector<::aibs::AudioCaption> output;std::size_t bytes=0;r.expect('[');if(r.take(']'))return output;
 for(;;){need(output.size()<::aibs::audio_asset_maximum_captions,"Reviewed caption count exceeds2048");r.expect('{');unsigned mask=0;::aibs::AudioCaption cue;
  for(;;){const auto key=r.text(64);r.expect(':');const unsigned bit=key=="start_frame"?1:key=="end_frame"?2:key=="text"?4:0;need(bit!=0&&(mask&bit)==0,"Unknown/duplicate caption cue field");mask|=bit;
   if(bit==1)cue.start_frame=r.integer();else if(bit==2)cue.end_frame=r.integer();else cue.text=r.text(::aibs::audio_asset_maximum_caption_text_bytes);
   if(r.take('}'))break;r.expect(',');}
  need(mask==7,"Caption cue requires start/end/text");nonempty(cue.text,::aibs::audio_asset_maximum_caption_text_bytes);need(cue.text.size()<=::aibs::audio_asset_maximum_caption_text_bytes-bytes,"Reviewed caption text closure exceeds256KiB");bytes+=cue.text.size();
  output.push_back(std::move(cue));if(r.take(']'))break;r.expect(',');
 }return output;
}
}
inline ReviewedAudioCaptions parse_reviewed_captions(std::string_view input,const ::aibs::AudioAsset& source){
 using namespace caption_detail;need(!input.empty()&&input.size()<=reviewed_caption_json_limit,"Reviewed caption JSON is empty or exceeds1MiB");::aibs::validate_audio_asset(source);
 Reader r{input};if(input.starts_with("\xef\xbb\xbf"))r.position=3;r.expect('{');std::set<std::string> seen;ReviewedAudioCaptions result;
 std::string source_hash;std::uint64_t rate=0,channels=0,frames=0,count=0;
 for(;;){const auto key=r.text(64);need(seen.insert(key).second,"Duplicate reviewed caption JSON field");r.expect(':');
  if(key=="schema_version")need(r.integer()==1,"Unsupported reviewed caption schema");
  else if(key=="status")need(r.text(128)=="LISTENING_REVIEW_VALIDATED_FOR_NATIVE_ATTACHMENT","Only a completed validated listening declaration can be attached");
  else if(key=="caption_review")need(r.text(16)=="checked","Draft captions cannot be attached as checked");
  else if(key=="source_sha256")source_hash=r.text(64);
  else if(key=="source_caption_draft_sha256")result.draft_sha256=r.text(64);
  else if(key=="review_export_sha256")result.review_sha256=r.text(64);
  else if(key=="sample_rate")rate=r.integer();else if(key=="channels")channels=r.integer();else if(key=="frame_count")frames=r.integer();else if(key=="caption_count")count=r.integer();
  else if(key=="captions")result.captions=captions(r);
  else if(key=="reviewer")result.reviewer=r.text(400);
  else if(key=="reviewed_at_utc")result.reviewed_at_utc=r.text(64);
  else if(key=="automatic_approval")r.no_automatic();
  else if(key=="declaration")need(r.text(256)==reviewed_caption_declaration,"Unknown listening-review declaration scope");
  else if(key=="native_attachment_status")need(r.text(128)=="not_supported_by_current_audio_cooker_cli","Unknown adapter attachment marker");
  else need(false,"Unknown reviewed caption JSON field");
  if(r.take('}'))break;r.expect(',');
 }
 r.ws();need(r.position==input.size(),"Trailing reviewed caption JSON data");need(seen.size()==16,"Reviewed caption export requires all16 schema fields");
 hash(source_hash);hash(result.draft_sha256);hash(result.review_sha256);need(source_hash==source.source_sha256,"Reviewed captions belong to a different complete WAV");
 need(rate==source.sample_rate&&channels==source.channels&&frames==source.frame_count,"Reviewed caption source rate/channels/frame count differs from WAV");need(count>0&&count==result.captions.size(),"Reviewed caption count differs from complete cue list");
 nonempty(result.reviewer,400,true);const auto wide=unicode(result.reviewer);std::size_t scalars=0;for(std::size_t i=0;i<wide.size();++i){++scalars;if(wide[i]>=0xd800&&wide[i]<=0xdbff)++i;}need(scalars<=100,"Reviewer exceeds100 Unicode characters");timestamp(result.reviewed_at_utc);
 std::uint64_t previous=0;for(const auto& cue:result.captions){need(cue.start_frame>=previous&&cue.start_frame<cue.end_frame&&cue.end_frame<=source.frame_count,"Reviewed captions overlap/reorder/exceed source frames");previous=cue.end_frame;}
 return result;
}
}
