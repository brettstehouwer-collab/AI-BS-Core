# Official SQLite amalgamation, immutable release URL and verified archive hash.
# SQLite is built into the SDK as a static library; no SQLite DLL is required.
include(FetchContent)
FetchContent_Declare(SQLiteSource
  URL https://sqlite.org/2026/sqlite-amalgamation-3540100.zip
  URL_HASH SHA256=0a9c8e34352dad46006aa82836d5383bff9dc6bc9ce5a60553c05aa30e6ad1f9
  DOWNLOAD_EXTRACT_TIMESTAMP FALSE)
FetchContent_MakeAvailable(SQLiteSource)
add_library(aibs_SQLite STATIC ${sqlitesource_SOURCE_DIR}/sqlite3.c)
set_target_properties(aibs_SQLite PROPERTIES EXPORT_NAME SQLite)
add_library(AIBS::SQLite ALIAS aibs_SQLite)
target_include_directories(aibs_SQLite PUBLIC
  $<BUILD_INTERFACE:${sqlitesource_SOURCE_DIR}>)
target_compile_definitions(aibs_SQLite PRIVATE
  SQLITE_THREADSAFE=1 SQLITE_DQS=0 SQLITE_OMIT_LOAD_EXTENSION)
install(TARGETS aibs_SQLite EXPORT AIBSTargets
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES ${CMAKE_CURRENT_LIST_DIR}/../third_party/SQLite-NOTICE.txt
  DESTINATION share/AIBS/licenses)
