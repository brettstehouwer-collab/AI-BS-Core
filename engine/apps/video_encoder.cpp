#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <psapi.h>
#include "video_encoder.hpp"
#include <algorithm>
#include <atomic>
#include <cstring>
#include <cwctype>
#include <stdexcept>
#include <utility>
namespace aibs::recording {
namespace {
using Clock=std::chrono::steady_clock;
struct Handle {
 HANDLE value=nullptr;Handle()=default;explicit Handle(HANDLE v):value(v){}
 ~Handle(){reset();}Handle(const Handle&)=delete;Handle& operator=(const Handle&)=delete;
 void reset(HANDLE v=nullptr)noexcept{if(value&&value!=INVALID_HANDLE_VALUE)CloseHandle(value);value=v;}
 HANDLE get()const noexcept{return value;}explicit operator bool()const noexcept{return value&&value!=INVALID_HANDLE_VALUE;}
};
std::atomic<void*> recorder_owner{nullptr};
std::wstring quote(const std::wstring& value){
 std::wstring out=L"\"";std::size_t slashes=0;
 for(const auto ch:value){if(ch==L'\\'){++slashes;continue;}if(ch==L'\"'){out.append(slashes*2+1,L'\\');out+=ch;}else{out.append(slashes,L'\\');out+=ch;}slashes=0;}
 out.append(slashes*2,L'\\');out+=L'\"';return out;
}
bool local_absolute(const std::filesystem::path& path){
 const auto native=path.native();const auto drive=GetDriveTypeW(path.root_path().c_str());return path.is_absolute()&&native.size()>3&&native.size()<32700&&drive!=DRIVE_REMOTE&&drive!=DRIVE_UNKNOWN&&drive!=DRIVE_NO_ROOT_DIR&&
  ((native[0]>=L'A'&&native[0]<=L'Z')||(native[0]>=L'a'&&native[0]<=L'z'))&&native[1]==L':'&&native.find(L'\n')==std::wstring::npos&&native.find(L'\r')==std::wstring::npos;
}
std::wstring lowercase(std::wstring value){for(auto& ch:value)ch=static_cast<wchar_t>(std::towlower(ch));return value;}
DWORD remaining_ms(Clock::time_point deadline,DWORD maximum=10000){
 const auto left=std::chrono::duration_cast<std::chrono::milliseconds>(deadline-Clock::now()).count();return left<=0?0:static_cast<DWORD>(std::min<std::int64_t>(left,maximum));
}
void spawn(const std::filesystem::path& exe,const std::vector<std::wstring>& arguments,HANDLE input,HANDLE error,HANDLE output,HANDLE& result){
 std::wstring command;for(const auto& arg:arguments){if(!command.empty())command+=L' ';command+=quote(arg);}
 if(command.size()>=32767)throw std::invalid_argument("Encoder argument list exceeds the Windows bound");
 SIZE_T attribute_bytes=0;InitializeProcThreadAttributeList(nullptr,1,0,&attribute_bytes);std::vector<std::byte> storage(attribute_bytes);
 auto* attributes=reinterpret_cast<LPPROC_THREAD_ATTRIBUTE_LIST>(storage.data());
 if(!InitializeProcThreadAttributeList(attributes,1,0,&attribute_bytes))throw std::runtime_error("Cannot restrict child handle inheritance");
 struct Cleanup{LPPROC_THREAD_ATTRIBUTE_LIST list;~Cleanup(){DeleteProcThreadAttributeList(list);}} cleanup{attributes};
 HANDLE allowed[]={input,error,output};
 if(!UpdateProcThreadAttribute(attributes,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,allowed,sizeof(allowed),nullptr,nullptr))throw std::runtime_error("Cannot restrict encoder handles");
 STARTUPINFOEXW startup{};startup.StartupInfo.cb=sizeof(startup);startup.lpAttributeList=attributes;startup.StartupInfo.dwFlags=STARTF_USESTDHANDLES;
 startup.StartupInfo.hStdInput=input;startup.StartupInfo.hStdError=error;startup.StartupInfo.hStdOutput=output;
 PROCESS_INFORMATION child{};
 if(!CreateProcessW(exe.c_str(),command.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW|EXTENDED_STARTUPINFO_PRESENT,nullptr,nullptr,&startup.StartupInfo,&child))throw std::runtime_error("Cannot start the trusted local encoder");
 result=child.hProcess;CloseHandle(child.hThread);
}
}
struct VideoEncoder::Impl {
 RecordingReport report;std::vector<std::byte> frame;
 Handle pipe,input,error_read,error_write,output,process,event;
 OVERLAPPED overlapped{};bool pending=false,running=false,claimed=false;
 Clock::time_point begun{},last_capture{},first_write{},rate_time{};std::uint64_t last_present=0;double rate_tokens=1;bool rate_initialized=false;
 static constexpr std::size_t maximum_frames=54000,stderr_limit=16384;
 Impl(){report.error.reserve(512);report.encoder_stderr.reserve(stderr_limit);report.hardware_probe_stderr.reserve(stderr_limit);report.fallback_reason.reserve(512);}
 void error(const char* text)noexcept{report.failed=true;try{report.error.assign(text, std::min<std::size_t>(std::strlen(text),511));}catch(...){}}
 void stderr_drain()noexcept{
  if(process){PROCESS_MEMORY_COUNTERS_EX counters{};counters.cb=sizeof(counters);
   if(GetProcessMemoryInfo(process.get(),reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&counters),sizeof(counters))){
    report.encoder_peak_working_set_bytes=std::max<std::uint64_t>(report.encoder_peak_working_set_bytes,counters.PeakWorkingSetSize);
    report.encoder_sampled_private_bytes_peak=std::max<std::uint64_t>(report.encoder_sampled_private_bytes_peak,counters.PrivateUsage);
   }
  }
  if(!error_read)return;char bytes[4096];
  for(unsigned n=0;n<4;++n){DWORD available=0;if(!PeekNamedPipe(error_read.get(),nullptr,0,nullptr,&available,nullptr)||!available)return;
   DWORD read=0;if(!ReadFile(error_read.get(),bytes,std::min<DWORD>(available,sizeof(bytes)),&read,nullptr)||!read)return;
   try{auto& target=report.encoder_stderr;if(target.size()+read>stderr_limit)target.erase(0,target.size()+read-stderr_limit);target.append(bytes,read);}catch(...){return;}
  }
 }
 bool complete_pending()noexcept{
  if(!pending)return true;DWORD written=0;
  if(GetOverlappedResult(pipe.get(),&overlapped,&written,FALSE)){pending=false;return true;}
  if(GetLastError()!=ERROR_IO_INCOMPLETE){pending=false;return true;}return false;
 }
 void release_claim()noexcept{if(claimed){void* expected=this;recorder_owner.compare_exchange_strong(expected,nullptr);claimed=false;}}
 void close_completed()noexcept{
  if(pending)return;pipe.reset();input.reset();error_write.reset();output.reset();event.reset();
  stderr_drain();error_read.reset();process.reset();running=false;
  std::vector<std::byte>().swap(frame); // Free the pixel slot before another recorder can claim it.
  release_claim();
 }
 void abort()noexcept{
  if(pending)CancelIoEx(pipe.get(),&overlapped);
  if(process&&WaitForSingleObject(process.get(),0)==WAIT_TIMEOUT){TerminateProcess(process.get(),0xA1B5);WaitForSingleObject(process.get(),100);}
  if(pending){WaitForSingleObject(event.get(),100);complete_pending();}
  if(pending||(process&&WaitForSingleObject(process.get(),0)==WAIT_TIMEOUT)){
   // A single global recording claim bounds this exceptional retained owner.
   // The destructor deliberately retains it if the OS cannot prove I/O stopped.
   report.quarantined=true;running=false;return;
  }
  close_completed();
 }
 bool probe_nvenc(const std::filesystem::path& exe){
  report.hardware_probe_attempted=true;const auto start=Clock::now();
  const std::vector<std::wstring> arguments={exe.native(),L"-hide_banner",L"-loglevel",L"error",L"-nostdin",L"-f",L"lavfi",L"-i",L"color=c=black:s="+std::to_wstring(report.width)+L"x"+std::to_wstring(report.height)+L":r=1",
   L"-frames:v",L"1",L"-an",L"-vf",L"format=bgra",L"-c:v",L"h264_nvenc",L"-pix_fmt",L"bgra",L"-rgb_mode",L"yuv420",L"-preset",L"p1",L"-tune",L"ull",
   L"-rc",L"constqp",L"-qp",L"23",L"-bf",L"0",L"-rc-lookahead",L"0",L"-zerolatency",L"1",L"-delay",L"0",L"-surfaces",L"4",L"-f",L"null",L"NUL"};
  HANDLE child=nullptr;spawn(exe,arguments,input.get(),error_write.get(),output.get(),child);process.reset(child);
  const auto deadline=start+std::chrono::seconds(3);
  while(WaitForSingleObject(process.get(),0)==WAIT_TIMEOUT&&Clock::now()<deadline){stderr_drain();WaitForSingleObject(process.get(),std::min<DWORD>(10,remaining_ms(deadline)));}
  if(WaitForSingleObject(process.get(),0)==WAIT_TIMEOUT){TerminateProcess(process.get(),0xA1B5);WaitForSingleObject(process.get(),100);}
  if(WaitForSingleObject(process.get(),0)==WAIT_TIMEOUT)throw std::runtime_error("NVENC preflight process cannot be stopped");
  DWORD code=0;if(!GetExitCodeProcess(process.get(),&code))throw std::runtime_error("Cannot inspect NVENC preflight exit");
  stderr_drain();process.reset();report.hardware_probe_seconds=std::chrono::duration<double>(Clock::now()-start).count();
  report.hardware_probe_exit_code=code;report.hardware_probe_passed=code==0;report.hardware_probe_stderr=report.encoder_stderr;report.encoder_stderr.clear();return code==0;
 }
 bool write(Clock::time_point captured,bool repeated,DWORD budget){
  if(!running||!process||report.timestamps.size()>=maximum_frames){error("Recording frame limit reached or encoder is unavailable");abort();return false;}
  stderr_drain();if(WaitForSingleObject(process.get(),0)!=WAIT_TIMEOUT){error("Encoder exited before frame delivery");abort();return false;}
  ResetEvent(event.get());overlapped={};overlapped.hEvent=event.get();DWORD written=0;
  const auto started=Clock::now();
  if(!WriteFile(pipe.get(),frame.data(),static_cast<DWORD>(frame.size()),&written,&overlapped)){
   if(GetLastError()!=ERROR_IO_PENDING){error("Encoder frame write failed");abort();return false;}
   pending=true;const auto deadline=started+std::chrono::milliseconds(budget);
   for(;;){
    HANDLE handles[]={event.get(),process.get()};const auto wait=WaitForMultipleObjects(2,handles,FALSE,remaining_ms(deadline,10));stderr_drain();
    if(wait==WAIT_OBJECT_0){
     if(!GetOverlappedResult(pipe.get(),&overlapped,&written,FALSE)){pending=false;error("Encoder rejected a frame");abort();return false;}pending=false;break;
    }
    if(wait==WAIT_OBJECT_0+1||wait==WAIT_FAILED){error("Encoder stopped while receiving a frame");abort();return false;}
    if(Clock::now()>=deadline){++report.backpressure_events;error("Encoder backpressure exceeded the bounded write deadline");abort();return false;}
   }
  }
  if(written!=frame.size()){error("Encoder accepted an incomplete frame");abort();return false;}
  const auto finished=Clock::now();const auto seconds=std::chrono::duration<double>(finished-begun).count();
  if(!report.frames_written){first_write=finished;report.first_frame_seconds=seconds;}
  report.last_frame_seconds=seconds;report.total_write_seconds+=std::chrono::duration<double>(finished-started).count();report.maximum_write_seconds=std::max(report.maximum_write_seconds,std::chrono::duration<double>(finished-started).count());
  ++report.frames_written;if(repeated)++report.repeated_at_stop;
  report.timestamps.push_back({last_present,std::chrono::duration<double>(captured-begun).count(),seconds,repeated});return true;
 }
};
VideoEncoder::VideoEncoder():impl_(std::make_unique<Impl>()){}
VideoEncoder::~VideoEncoder(){
 finish(std::chrono::milliseconds(250));
 if(impl_->report.quarantined){(void)impl_.release();} // At most one <=32MiB retained frame; no detached worker.
}
bool VideoEncoder::begin(const std::filesystem::path& exe,const std::filesystem::path& file,std::uint32_t width,std::uint32_t height,std::uint32_t fps,EncoderMode mode)noexcept{
 auto& p=*impl_;if(p.report.started||p.report.finished||p.report.failed){p.error("A VideoEncoder instance supports one recording only");return false;}
 try{
  if(mode!=EncoderMode::software&&mode!=EncoderMode::h264_nvenc&&mode!=EncoderMode::automatic)throw std::invalid_argument("Unknown encoder selection");
  if(!width||!height||width>8192||height>8192||width%2||height%2||static_cast<std::uint64_t>(width)*height*4>CapturedFrame::maximum_bytes||!fps||fps>60)
   throw std::invalid_argument("Recording requires even dimensions, 1..60fps and one <=32MiB BGRA slot");
  if(!local_absolute(exe)||lowercase(exe.filename().native())!=L"ffmpeg.exe"||!std::filesystem::is_regular_file(exe))throw std::invalid_argument("Select the trusted installed local ffmpeg.exe");
  if(!local_absolute(file)||lowercase(file.extension().native())!=L".mp4"||!std::filesystem::is_directory(file.parent_path())||std::filesystem::exists(file))throw std::invalid_argument("Recording output must be a new absolute local .mp4 in an existing folder");
  void* expected=nullptr;if(!recorder_owner.compare_exchange_strong(expected,&p))throw std::runtime_error("Another recorder is active or retains unfinished OS I/O");p.claimed=true;
  p.frame.reserve(CapturedFrame::maximum_bytes);p.frame.resize(static_cast<std::size_t>(width)*height*4);
  p.report.timestamps.reserve(Impl::maximum_frames);p.report.encoder_frame_capacity=p.frame.capacity();p.report.timestamp_capacity_bytes=p.report.timestamps.capacity()*sizeof(FrameTimestamp);
  p.report.width=width;p.report.height=height;p.report.target_fps=fps;
  unsigned char random[16]{};if(BCryptGenRandom(nullptr,random,sizeof(random),BCRYPT_USE_SYSTEM_PREFERRED_RNG)!=0)throw std::runtime_error("Cannot create a private recording pipe");
  std::wstring name=L"\\\\.\\pipe\\AIBS-OwnRenderer-";constexpr wchar_t hex[]=L"0123456789abcdef";
  for(const auto byte:random){name+=hex[byte>>4];name+=hex[byte&15];}
  p.pipe.reset(CreateNamedPipeW(name.c_str(),PIPE_ACCESS_OUTBOUND|FILE_FLAG_OVERLAPPED|FILE_FLAG_FIRST_PIPE_INSTANCE,
   PIPE_TYPE_BYTE|PIPE_READMODE_BYTE|PIPE_WAIT|PIPE_REJECT_REMOTE_CLIENTS,1,65536,65536,0,nullptr));
  if(!p.pipe)throw std::runtime_error("Cannot create the bounded local recording pipe");
  SECURITY_ATTRIBUTES inherited{sizeof(SECURITY_ATTRIBUTES),nullptr,TRUE};
  p.input.reset(CreateFileW(name.c_str(),GENERIC_READ,0,&inherited,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr));
  if(!p.input)throw std::runtime_error("Cannot connect the local recording pipe");
  // Use the retained OVERLAPPED/event even for connection, so an unexpected
  // pending connection cannot outlive a stack variable on an error path.
  p.event.reset(CreateEventW(nullptr,TRUE,FALSE,nullptr));if(!p.event)throw std::runtime_error("Cannot initialize recording event");
  p.overlapped={};p.overlapped.hEvent=p.event.get();
  if(!ConnectNamedPipe(p.pipe.get(),&p.overlapped)){
   const auto code=GetLastError();
   if(code==ERROR_IO_PENDING){
    p.pending=true;DWORD transferred=0;
    if(WaitForSingleObject(p.event.get(),250)!=WAIT_OBJECT_0||!GetOverlappedResult(p.pipe.get(),&p.overlapped,&transferred,FALSE))
     throw std::runtime_error("Cannot complete the bounded local recording connection");
    p.pending=false;
   }else if(code!=ERROR_PIPE_CONNECTED)throw std::runtime_error("Cannot confirm the local recording pipe");
  }
  HANDLE read=nullptr,write=nullptr;if(!CreatePipe(&read,&write,&inherited,65536))throw std::runtime_error("Cannot create bounded encoder diagnostics");
  p.error_read.reset(read);p.error_write.reset(write);SetHandleInformation(p.error_read.get(),HANDLE_FLAG_INHERIT,0);
  p.output.reset(CreateFileW(L"NUL",GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,&inherited,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr));
  if(!p.output)throw std::runtime_error("Cannot initialize encoder output handle");
  p.report.requested_encoder=mode==EncoderMode::software?"software":mode==EncoderMode::h264_nvenc?"nvenc":"auto";
  bool hardware=false;
  if(mode!=EncoderMode::software){hardware=p.probe_nvenc(exe);if(!hardware){
   if(mode==EncoderMode::h264_nvenc)throw std::runtime_error("Explicit NVENC selection failed the actual hardware preflight");
   p.report.fallback_reason="NVENC hardware preflight failed; recording uses software libx264";
  }}
  p.report.encoder=hardware?"h264_nvenc":"libx264";
  std::vector<std::wstring> arguments={exe.native(),L"-hide_banner",L"-loglevel",L"error",L"-nostats",L"-nostdin",L"-n",
   L"-f",L"rawvideo",L"-pixel_format",L"bgra",L"-video_size",std::to_wstring(width)+L"x"+std::to_wstring(height),
   L"-thread_queue_size",L"1",L"-framerate",L"1000",L"-use_wallclock_as_timestamps",L"1",L"-i",L"pipe:0",L"-copyts",L"-start_at_zero",L"-an"};
  const std::vector<std::wstring> codec=hardware?std::vector<std::wstring>{L"-c:v",L"h264_nvenc",L"-pix_fmt",L"bgra",L"-rgb_mode",L"yuv420",L"-preset",L"p1",L"-tune",L"ull",L"-rc",L"constqp",L"-qp",L"23",L"-bf",L"0",L"-rc-lookahead",L"0",L"-zerolatency",L"1",L"-delay",L"0",L"-surfaces",L"4"}:
   std::vector<std::wstring>{L"-c:v",L"libx264",L"-preset",L"ultrafast",L"-tune",L"zerolatency",L"-crf",L"23",L"-threads",L"2",L"-pix_fmt",L"yuv420p"};
  arguments.insert(arguments.end(),codec.begin(),codec.end());
  const std::vector<std::wstring> mux={L"-fps_mode",L"vfr",L"-enc_time_base",L"1:1000",L"-video_track_timescale",L"1000",L"-movflags",L"+faststart",file.native()};arguments.insert(arguments.end(),mux.begin(),mux.end());
  HANDLE child=nullptr;p.begun=Clock::now();spawn(exe,arguments,p.input.get(),p.error_write.get(),p.output.get(),child);
  p.process.reset(child);p.input.reset();p.error_write.reset();p.output.reset();p.running=true;p.report.started=true;return true;
 }catch(const std::exception& failure){p.error(failure.what());p.abort();p.report.finished=true;return false;}catch(...){p.error("Recording initialization failed");p.abort();p.report.finished=true;return false;}
}
bool VideoEncoder::submit(const CapturedFrame& frame,Clock::time_point captured)noexcept{
 auto& p=*impl_;if(!active())return false;++p.report.frames_received;
 try{
  const auto now=Clock::now();if(captured>now+std::chrono::milliseconds(50)||captured<now-std::chrono::milliseconds(250)||
   (p.report.frames_written&&captured<p.last_capture))throw std::invalid_argument("Capture timestamps must be monotonic and current");
  if(frame.width!=p.report.width||frame.height!=p.report.height||frame.bgra.size()!=p.frame.size()||frame.bgra.capacity()>CapturedFrame::maximum_bytes||!frame.present_id)
   throw std::invalid_argument("Capture dimensions/bytes changed or present identity is missing");
  p.report.producer_frame_capacity_peak=std::max(p.report.producer_frame_capacity_peak,frame.bgra.capacity());
  // Two bounded scheduling tokens tolerate jittered arrivals (16ms/50ms at
  // nominal30Hz) without discarding half the real presents. Tokens are numbers,
  // not queued frames: elapsed average rate is capped and pixel ownership stays one slot.
  if(p.rate_initialized){
   if(captured<p.rate_time)throw std::invalid_argument("All capture timestamps must remain monotonic");
   p.rate_tokens=std::min(2.0,p.rate_tokens+std::chrono::duration<double>(captured-p.rate_time).count()*p.report.target_fps);
  }else p.rate_initialized=true;
  p.rate_time=captured;
  if(p.report.frames_written&&(p.rate_tokens+1e-6<1.0||frame.present_id==p.last_present)){++p.report.dropped_for_rate;return false;}
  p.rate_tokens-=1;
  if(p.report.frames_written){const auto slots=static_cast<std::uint64_t>(std::chrono::duration<double>(captured-p.last_capture).count()*p.report.target_fps);if(slots>1)p.report.missed_capture_slots+=slots-1;}
  std::memcpy(p.frame.data(),frame.bgra.data(),frame.bgra.size());p.last_present=frame.present_id;p.last_capture=captured;
  return p.write(captured,false,p.report.frames_written?100:250);
 }catch(const std::exception& failure){p.error(failure.what());p.abort();return false;}catch(...){p.error("Recording submission failed");p.abort();return false;}
}
bool VideoEncoder::finish(std::chrono::milliseconds budget)noexcept{
 auto& p=*impl_;if(p.report.finished)return !p.report.failed;
 const auto retained_stop=[&]()noexcept{p.report.finished=true;p.report.wall_seconds=std::chrono::duration<double>(Clock::now()-p.begun).count();return false;};
 if(p.report.quarantined)return retained_stop();
 if(!p.report.started){p.report.finished=true;return !p.report.failed;}
 try{
  const auto bounded=std::clamp<std::int64_t>(budget.count(),1,10000);const auto deadline=Clock::now()+std::chrono::milliseconds(bounded);
  if(p.running&&!p.report.failed&&p.report.frames_written&&Clock::now()-p.last_capture>std::chrono::milliseconds(16))
   p.write(Clock::now(),true,std::min<DWORD>(100,remaining_ms(deadline)));
  if(p.report.quarantined)return retained_stop();
  if(p.pending){p.error("Recording stopped with incomplete pipe I/O");p.abort();if(p.report.quarantined)return retained_stop();}
  if(!p.pending)p.pipe.reset(); // EOF requests muxer/encoder drain.
  while(p.process&&WaitForSingleObject(p.process.get(),0)==WAIT_TIMEOUT&&Clock::now()<deadline){p.stderr_drain();WaitForSingleObject(p.process.get(),std::min<DWORD>(10,remaining_ms(deadline)));}
  if(p.process){
   if(WaitForSingleObject(p.process.get(),0)==WAIT_TIMEOUT){p.error("Encoder exit exceeded the stop deadline");p.abort();if(p.report.quarantined)return retained_stop();}
   else{DWORD code=0;if(!GetExitCodeProcess(p.process.get(),&code)){p.error("Cannot inspect encoder exit status");}else{p.report.encoder_exit_code=code;if(code)p.error("Encoder exited unsuccessfully; inspect bounded diagnostics");}}
  }
  p.stderr_drain();p.running=false;p.report.wall_seconds=std::chrono::duration<double>(Clock::now()-p.begun).count();
  if(!p.report.frames_written)p.error("No complete frames were recorded");
  if(!p.report.quarantined)p.close_completed();p.report.finished=true;return !p.report.failed;
 }catch(...){p.error("Recording shutdown failed");if(!p.report.quarantined)p.abort();p.report.finished=true;return false;}
}
bool VideoEncoder::active()const noexcept{return impl_->running&&!impl_->report.failed&&!impl_->report.finished;}
const RecordingReport& VideoEncoder::report()const noexcept{impl_->report.encoder_frame_capacity_active=impl_->frame.capacity();return impl_->report;}
}


