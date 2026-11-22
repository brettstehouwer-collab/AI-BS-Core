#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <string>
int wmain(int argc,wchar_t** argv){
 for(int n=1;n<argc;++n)if(std::wstring(argv[n])==L"h264_nvenc")return 9;
 const std::wstring output=argc>1?argv[argc-1]:L"";
 if(output.find(L"exit")!=std::wstring::npos)return 7;
 Sleep(30000);return 0;
}
